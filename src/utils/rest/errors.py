from utils.rest.types import RestJSONDataType


class BaseRestApiError(Exception):
    def __init__(self, data: RestJSONDataType | None = None):  # noqa: B042
        self.data = data or {}


class RestApiInternalError(BaseRestApiError):
    pass


class RestApiServiceUnavailableError(BaseRestApiError):
    pass


class RestApiBadGatewayError(BaseRestApiError):
    pass


class RestApiGatewayTimeoutError(BaseRestApiError):
    pass


class RestApiTooManyRequestsError(BaseRestApiError):
    def __init__(  # noqa: B042
        self,
        data: RestJSONDataType | None = None,
        retry_after: int | None = None,
    ):
        super().__init__(data)
        self.retry_after = retry_after


class RestApiForbiddenError(BaseRestApiError):
    pass


class RestApiBadRequestError(BaseRestApiError):
    pass


class RestApiUnauthorizedError(BaseRestApiError):
    pass


class RestApiNotFoundError(BaseRestApiError):
    pass


class RestApiUnexpectedError(BaseRestApiError):
    pass


class RestClientTimeoutError(BaseRestApiError):
    pass


class RestClientPaymentRequiredError(BaseRestApiError):
    pass


class RestApiUpgradeRequiredError(BaseRestApiError):
    pass


class RestApiUnprocessedEntityError(BaseRestApiError):
    pass


class RestApiPreconditionalRequiredError(BaseRestApiError):
    pass
