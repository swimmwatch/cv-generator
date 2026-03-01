import typing

from taskiq import TaskiqMessage
from taskiq import TaskiqMiddleware
from taskiq import TaskiqResult

from infra.db.session_scope import clear_session_scope
from infra.db.session_scope import set_session_scope
from infra.di.container import Container
from infra.logger.utils import get_logger
from utils.config import RunLevelEnum
from utils.logger import setup_logger

logger = get_logger(__name__)


class DIMiddleware(TaskiqMiddleware):
    def __init__(self, container: Container) -> None:
        super().__init__()
        self._container = container
        self._db = None
        self._mongo_db = None

    async def startup(self) -> None:
        self._db = self._container.async_db()
        self._mongo_db = self._container.async_mongo_db()
        self._container.init_resources()
        self._container.wire(
            modules=[
                "apps.api.tasks",
                "apps.worker.tasks",
            ],
        )

    async def shutdown(self) -> None:
        if self._container:
            self._container.unwire()
            await self._db.stop()
            await self._mongo_db.stop()
            self._container.shutdown_resources()

            logger.info("Shutdown DI resources.")

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        # Bind one session per task using message.task_id as the scope key
        set_session_scope(message.task_id)
        return message

    async def post_execute(
        self,
        message: "TaskiqMessage",
        result: "TaskiqResult[typing.Any]",
    ) -> None:
        # Ensure we operate on the correct scoped session, even if the context changed
        set_session_scope(message.task_id)

        try:
            await self._db.commit_scoped_session()
        finally:
            clear_session_scope()
            await self._db.remove_scoped_session()

    async def on_error(
        self,
        message: "TaskiqMessage",
        result: "TaskiqResult[typing.Any]",
        exception: BaseException,
    ) -> None:
        # Ensure we operate on the correct scoped session, even if the context changed
        set_session_scope(message.task_id)

        try:
            await self._db.rollback_scoped_session()
        finally:
            clear_session_scope()
            await self._db.remove_scoped_session()


class StructlogMiddleware(TaskiqMiddleware):
    def __init__(
        self,
        env: RunLevelEnum = RunLevelEnum.LOCAL,
        level: str = "INFO",
    ) -> None:
        super().__init__()

        self._env = env
        self._level = level

    async def startup(self) -> None:
        setup_logger(
            json_logs=self._env == RunLevelEnum.PRODUCTION,
            log_level=self._level,
        )


class StartupTasksMiddleware(TaskiqMiddleware):
    """Middleware to run tasks on broker startup."""

    async def startup(self) -> None:
        runnable_tasks = [task for task in self.broker.get_all_tasks().values() if task.labels.get("run_on_startup")]
        runnable_tasks = sorted(runnable_tasks, key=lambda task: task.labels.get("run_priority", 0))
        for task in runnable_tasks:
            await task.kiq()
