import asyncio
import contextlib
import json
from http import HTTPStatus

import structlog
from aiogram import Bot
from aiogram import Dispatcher
from aiogram.types import Update
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Security
from fastapi.security import APIKeyHeader
from starlette.requests import Request
from starlette.responses import Response

from infra.bot.runtime.base import PTBRunner

logger = structlog.get_logger(__name__)


class AiogramPoller(PTBRunner):
    def __init__(
        self,
        bot: Bot,
        dp: Dispatcher,
    ) -> None:
        self._bot = bot
        self._dp = dp
        self._polling_task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self):
        if self._running:
            return
        self._polling_task = asyncio.create_task(self._dp.start_polling(self._bot))
        self._running = True
        logger.info("Polling bot has started.")

    async def stop(self):
        if not self._running:
            return
        if self._polling_task:
            self._polling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._polling_task
        await self._bot.session.close()
        self._running = False
        logger.info("Polling bot has stopped.")


class AiogramWebhookServer(PTBRunner):
    _SECRET_TOKEN_HEADER_NAME = "X-Telegram-Bot-Api-Secret-Token"  # noqa: S105
    _SECRET_TOKEN_HEADER = APIKeyHeader(
        name=_SECRET_TOKEN_HEADER_NAME,
        auto_error=False,
        scheme_name="Telegram Bot Secret Token",
    )

    _UNAUTHORIZED_ERROR = HTTPException(
        status_code=HTTPStatus.UNAUTHORIZED,
        detail="Invalid request token",
    )
    _INVALID_BODY_ERROR = HTTPException(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        detail="Invalid request body",
    )
    _INTERNAL_ERROR = HTTPException(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail="Internal error",
    )

    def __init__(
        self,
        bot: Bot,
        dp: Dispatcher,
        fastapi_app: FastAPI,
        url: str,
        secret_token: str | None = None,
        path: str = "/tgbot",
    ) -> None:
        self._bot = bot
        self._dp = dp
        self._fastapi_app = fastapi_app
        self._url = url
        self._path = path
        self._secret_token = secret_token
        self._running = False

        self._fastapi_app.add_api_route(
            description="Telegram Bot Webhook",
            path=self._path,
            endpoint=self._handle_update,
            methods=["POST"],
            tags=["Telegram"],
            dependencies=[Security(self._get_secret_token)],
        )

    def _get_secret_token(
        self,
        secret_token: str | None = Security(_SECRET_TOKEN_HEADER),  # noqa: B008
    ) -> str:
        if not secret_token or secret_token != self._secret_token:
            raise self._UNAUTHORIZED_ERROR
        return secret_token

    async def _handle_update(self, request: Request) -> Response:
        try:
            body = await request.body()
            update = Update.model_validate(json.loads(body))
        except (json.JSONDecodeError, ValueError, KeyError) as err:
            logger.exception(err)
            raise self._INVALID_BODY_ERROR
        except Exception as err:
            logger.exception(err)
            raise self._INTERNAL_ERROR

        await self._dp.feed_update(self._bot, update)
        return Response(status_code=HTTPStatus.OK)

    async def start(self):
        if self._running:
            logger.warning("Cannot start Telegram Bot Webhook due to it's already running")
            return

        await self._bot.set_webhook(
            url=self._url + self._path,
            secret_token=self._secret_token,
        )
        self._running = True
        logger.info("Telegram Bot Webhook started")

    async def stop(self):
        if not self._running:
            logger.warning("Cannot stop Telegram Bot Webhook due to it's not running")
            return

        await self._bot.delete_webhook(drop_pending_updates=False)
        await self._bot.session.close()

        self._running = False
        logger.info("Telegram Bot Webhook stopped")
