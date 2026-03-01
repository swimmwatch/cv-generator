import asyncio
import random
import typing

from dependency_injector.wiring import Closing
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from taskiq_pipelines import Pipeline

from apps.worker.app import broker
from core import domains
from core import dto
from core import repos
from infra.logger.utils import get_logger
from infra.youtube.client import YouTubeClient
from infra.youtube.client import YouTubeVideoCandidate
from utils.yt.dlp import YtDlpVideoMetadataClient

logger = get_logger(__name__)


@broker.task(
    schedule=[
        {
            "cron": "*/1 * * * *",
            "kwargs": {"msg": "tick"},
            "cron_offset": "UTC",
        }
    ]
)
async def heartbeat(msg: str) -> None:
    logger.debug(f"heartbeat: {msg}")


@broker.task
async def build_work(n: int) -> list[int]:
    """Step 1: build the list of jobs — this is where we dynamically define N."""
    return list(range(1, n + 1))


@broker.task
async def process_item(x: int) -> int:
    """Step 2: will be started N times in parallel (map)."""
    await asyncio.sleep(0.1)  # simulate workload
    return x * x


@broker.task
async def aggregate(values: list[int]) -> dict[str, typing.Any]:
    """Step 3: runs after ALL process_item tasks have finished."""
    return {"count": len(values), "sum": sum(values), "values": values}


@broker.task
async def finalize(summary: dict) -> str:
    """Step 4: final task."""
    return f"done: count={summary['count']} sum={summary['sum']} values={summary['values']}"


@broker.task
@inject
async def upsert_page_candidates(
    raw_items: list[dict[str, typing.Any]],
    region_code: str = "US",
    time_window_days: int = 7,
    video_repo: repos.VideoRepository = Closing[Provide["sql_video_repo"]],
):
    source_type = "youtube"
    log = logger.bind(
        source_type=source_type,
        region_code=region_code,
        time_window_days=time_window_days,
    )

    candidates = [YouTubeVideoCandidate.model_validate(i) for i in raw_items]
    upsert_data = [
        dto.VideoUpsertDTO(
            source_type=source_type,
            source_pk=c.video_id,
            title=c.title,
            description=c.description,
            published_at=c.published_at,
        )
        for c in candidates
    ]
    upsert_results = await video_repo.bulk_upsert_discovered(upsert_data)

    attempted = [
        (r.source_pk, r.source_type)
        for r in upsert_results
        if r is not None and r.processing_status == domains.VideoProcessingStatus.PENDING
    ]

    log.info(
        "Search completed",
        candidate_count=len(candidates),
        attempted_count=len(attempted),
    )

    return attempted


@broker.task
@inject
async def save_yt_video_metadata(
    source: tuple[str, str],
    video_metadata_repo: repos.VideoMetadataRepository = Closing[Provide["mongo_video_metadata_repo"]],
    yt_dlp_metadata_client: YtDlpVideoMetadataClient = Provide["yt_dlp_metadata_client"],
):
    source_pk, source_type = source
    raw_item = await yt_dlp_metadata_client.fetch(source_pk)
    await video_metadata_repo.upsert_one(
        source_type,
        source_pk,
        raw_item,
    )


@broker.task
@inject
async def run_most_popular_discovery(
    region_code: str = "US",
    time_window_days: int = 7,
    max_results: int = 50,
    youtube_client: YouTubeClient = Provide["youtube_client"],
):
    page_token = None
    while True:
        candidates, page_token = await youtube_client.most_popular(
            region_code=region_code,
            time_window_days=time_window_days,
            max_results=max_results,
            page_token=page_token,
        )

        if not candidates:
            logger.info("No more candidates; discovery complete for this run.")
            break

        payload = [c.model_dump(mode="json") for c in candidates]
        pipe = Pipeline(broker, upsert_page_candidates).map(save_yt_video_metadata).filter(prefilter_yt_metadata)
        await pipe.kiq(
            payload,
            region_code,
            time_window_days,
        )

        if not page_token:
            logger.info("No page token returned; discovery complete for this run.")
            break


@broker.task
async def prefilter_yt_metadata(source: tuple[str, str]) -> bool:
    return random.randint(0, 1) == 0
