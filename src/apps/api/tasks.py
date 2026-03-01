from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from apps.worker.app import broker
from infra.logger.utils import get_logger

logger = get_logger(__name__)


@broker.task()
@inject
async def ping(config=Provide["config"]) -> None:
    logger.debug("Ping task executed", config=config)
