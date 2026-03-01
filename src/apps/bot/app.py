from aiogram import Bot
from aiogram import Dispatcher

from infra.bot.middlewares.audit import LoggerMiddleware
from infra.bot.middlewares.audit import RequestIdMiddleware
from infra.bot.middlewares.db import DBSessionMiddleware
from infra.bot.middlewares.user import UpdateOrCreateUserMiddleware
from infra.di.container import Container

from .handlers import router


def create_bot(container: Container) -> Bot:
    config = container.config
    return Bot(token=config.telegram_bot.token().get_secret_value())


def create_dispatcher(container: Container) -> Dispatcher:
    dp = Dispatcher()

    db = container.async_db()

    dp.update.outer_middleware(RequestIdMiddleware())
    dp.update.outer_middleware(DBSessionMiddleware(db))
    dp.update.outer_middleware(UpdateOrCreateUserMiddleware())
    dp.update.outer_middleware(LoggerMiddleware())

    dp.include_router(router)
    return dp
