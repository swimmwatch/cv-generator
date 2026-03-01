import typing

from fastapi import APIRouter
from fastapi import Depends
from taskiq_pipelines import Pipeline

from apps.api.depends.auth import DebugAuthProbe
from apps.api.depends.auth import JwtAuthProbe
from apps.worker.app import broker
from apps.worker.tasks import aggregate
from apps.worker.tasks import build_work
from apps.worker.tasks import finalize
from apps.worker.tasks import process_item
from apps.worker.tasks import run_most_popular_discovery
from core import dto
from utils.depends.auth import GetCurrentUserProvider
from utils.errors.http_ import HttpUnauthorizedError

router = APIRouter(prefix="/agents", tags=["Agents"])

auth = GetCurrentUserProvider(
    [
        JwtAuthProbe(),
        DebugAuthProbe(),
    ],
    on_failure=HttpUnauthorizedError,
)
auth_depends = Depends(auth.dependency())
CurrentUser = typing.Annotated[
    dto.UserOutDTO,
    auth_depends,
]


@router.post("/pipelines/test")
async def run_test_pipeline(_: CurrentUser):
    """Test endpoint for running a pipeline."""
    pipe = Pipeline(broker, build_work).map(process_item).call_next(aggregate).call_next(finalize)

    task = await pipe.kiq(n=5)
    result = await task.wait_result(timeout=30)
    return {"result": result}


@router.post("/pipelines/test2")
async def run_test_pipeline2(_: CurrentUser):
    """Test endpoint for running a pipeline."""
    task = await run_most_popular_discovery.kiq()
    result = await task.wait_result(timeout=10)
    return {"result": result}
