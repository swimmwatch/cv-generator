import asyncio
import typing

from apps.worker.app import broker
from infra.logger.utils import get_logger

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
