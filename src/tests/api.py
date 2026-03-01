import typing
from http import HTTPMethod
from urllib.parse import urlencode

import httpx
import pytest
from _pytest.monkeypatch import MonkeyPatch
from fastapi import FastAPI
from starlette.requests import Request

from apps.api.depends.auth import DebugAuthProbe
from core import domains
from core import dto
from core import services


class ApiTestCase:
    """Base class for API tests."""

    class Meta:
        url_name: typing.ClassVar[str]
        method_name: typing.ClassVar[HTTPMethod]

    @pytest.fixture(autouse=True)
    def _request_client(self, api_client: httpx.AsyncClient) -> None:
        self.client = api_client

    @pytest.fixture(autouse=True)
    def _request_app(self, api_app: FastAPI) -> None:
        self.app = api_app

    @pytest.fixture(autouse=True)
    def _request_monkeypatch(self, monkeypatch: MonkeyPatch) -> None:
        self.monkeypatch = monkeypatch

    @pytest.fixture(autouse=True)
    def _user_service(self, user_service: services.UserService) -> None:
        self._user_service = user_service

    def reverse_url(
        self,
        *,
        url_name: str | None = None,
        params: typing.Mapping[str, typing.Any] | None = None,
        **path_params: typing.Any,
    ) -> str:
        name = url_name or self.Meta.url_name
        assert name, "'url_name' parameter must be not empty"

        path = self.app.url_path_for(name, **path_params)
        url = str(path)

        if params:
            query = urlencode(params, doseq=True)
            url = f"{url}?{query}"

        return url

    def authorize(
        self,
        user_id: domains.UserID,
    ) -> httpx.AsyncClient:
        this = self

        async def _authenticate(
            _,
            __: Request,
            ___: str | None = None,
        ) -> dto.UserOutDTO | None:
            nonlocal user_id  # noqa: F824
            user = await this._user_service.get_current_user(user_id)
            return user

        self.monkeypatch.setattr(
            DebugAuthProbe,
            "authenticate",
            _authenticate,
        )

        return self.client

    def unauthorize(self):
        self.monkeypatch.undo()
        return self.client

    async def request(
        self,
        url: str,
        method: HTTPMethod | None = None,
        **kwargs: typing.Any,
    ) -> httpx.Response:
        method = method or self.Meta.method_name
        return await self.client.request(method.value, url, **kwargs)
