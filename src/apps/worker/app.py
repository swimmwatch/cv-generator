from taskiq import AsyncResultBackend
from taskiq import SimpleRetryMiddleware
from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_pipelines import PipelineMiddleware
from taskiq_redis import ListQueueBroker
from taskiq_redis import RedisAsyncResultBackend

from infra.di.container import Container
from infra.worker.middlewares import DIMiddleware
from infra.worker.middlewares import StartupTasksMiddleware
from infra.worker.middlewares import StructlogMiddleware

container = Container()
config = container.config
backend: AsyncResultBackend = RedisAsyncResultBackend(config.worker.result_backend())
broker = ListQueueBroker(url=config.worker.broker_url())
broker = broker.with_middlewares(
    StructlogMiddleware(
        config.logger.env(),
        config.logger.level(),
    ),
    DIMiddleware(container),
    StartupTasksMiddleware(),
    SimpleRetryMiddleware(config.worker.default_retry_count()),
    PipelineMiddleware(),
)
broker = broker.with_result_backend(backend)
scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
