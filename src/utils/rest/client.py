import typing
from http import HTTPStatus
from json import JSONDecodeError

import structlog
from httpx import AsyncClient as HttpClient
from httpx import Response
from httpx import TimeoutException

from utils.iter import random_switch_case
from utils.rest.errors import RestApiBadGatewayError
from utils.rest.errors import RestApiBadRequestError
from utils.rest.errors import RestApiForbiddenError
from utils.rest.errors import RestApiGatewayTimeoutError
from utils.rest.errors import RestApiInternalError
from utils.rest.errors import RestApiNotFoundError
from utils.rest.errors import RestApiPreconditionalRequiredError
from utils.rest.errors import RestApiServiceUnavailableError
from utils.rest.errors import RestApiTooManyRequestsError
from utils.rest.errors import RestApiUnauthorizedError
from utils.rest.errors import RestApiUnprocessedEntityError
from utils.rest.errors import RestApiUpgradeRequiredError
from utils.rest.errors import RestClientPaymentRequiredError
from utils.rest.errors import RestClientTimeoutError
from utils.rest.types import RestJSONDataType
from utils.rest.types import RestResponseType

logger = structlog.get_logger(__name__)


class RestClient:
    BASE_URL = ""

    def __init__(
        self,
        client: HttpClient,
        base_url: str | None = None,
        random_endpoint: bool = False,
    ) -> None:
        self._client = client

        if base_url is None:
            self._base_url = self.BASE_URL
        else:
            self._base_url = base_url

        assert self._base_url, "Base URL is not set"

        self._random_endpoint = random_endpoint

    @staticmethod
    def _match_error(response: Response, data: RestJSONDataType) -> None:
        logger.debug("REST API error", status=response.status_code, data=data)

        status_code = typing.cast(HTTPStatus, response.status_code)
        match status_code:
            case HTTPStatus.BAD_REQUEST:
                raise RestApiBadRequestError(data)
            case HTTPStatus.PAYMENT_REQUIRED:
                raise RestClientPaymentRequiredError(data)
            case HTTPStatus.FORBIDDEN:
                raise RestApiForbiddenError(data)
            case HTTPStatus.NOT_FOUND:
                raise RestApiNotFoundError(data)
            case HTTPStatus.UNPROCESSABLE_ENTITY:
                raise RestApiUnprocessedEntityError(data)
            case HTTPStatus.UPGRADE_REQUIRED:
                raise RestApiUpgradeRequiredError(data)
            case HTTPStatus.PRECONDITION_REQUIRED:
                raise RestApiPreconditionalRequiredError(data)
            case HTTPStatus.TOO_MANY_REQUESTS:
                retry_after = response.headers.get("Retry-After")

                # TODO: parse http-date format
                try:
                    retry_after = float(retry_after) if retry_after else None
                except ValueError:
                    logger.debug("REST API retry after is not a number: %s", retry_after)
                    retry_after = None

                raise RestApiTooManyRequestsError(
                    data,
                    retry_after=retry_after,
                )
            case HTTPStatus.INTERNAL_SERVER_ERROR:
                raise RestApiInternalError(data)
            case HTTPStatus.BAD_GATEWAY:
                raise RestApiBadGatewayError(data)
            case HTTPStatus.SERVICE_UNAVAILABLE:
                raise RestApiServiceUnavailableError(data)
            case HTTPStatus.GATEWAY_TIMEOUT:
                raise RestApiGatewayTimeoutError(data)
            case HTTPStatus.UNAUTHORIZED:
                raise RestApiUnauthorizedError(data)

    def _get_full_url(self, endpoint: str) -> str:
        return f"{self._base_url}/{endpoint}"

    async def request(
        self,
        method: str,
        endpoint: str,
        etag: str | None = None,
        **kwargs,
    ) -> RestResponseType:
        headers = self._client.headers

        if self._random_endpoint:
            endpoint = random_switch_case(endpoint)

        for key, value in kwargs.pop("headers", {}):
            headers[key] = value

        if etag is not None:
            headers["If-None-Match"] = etag

        try:
            response = await self._client.request(
                method,
                self._get_full_url(endpoint),
                headers=headers,
                **kwargs,
            )
        except TimeoutException:
            raise RestClientTimeoutError

        try:
            data = response.json()
        except JSONDecodeError:
            data = {}

        if response.status_code >= HTTPStatus.BAD_REQUEST:
            self._match_error(response, data)

        return response, data

    async def get(self, endpoint: str, **kwargs) -> RestResponseType:
        return await self.request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> RestResponseType:
        return await self.request("POST", endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs) -> RestResponseType:
        return await self.request("PUT", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> RestResponseType:
        return await self.request("DELETE", endpoint, **kwargs)
