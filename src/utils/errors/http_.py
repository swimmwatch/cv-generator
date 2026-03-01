import typing
from copy import deepcopy
from http import HTTPStatus

from starlette.responses import JSONResponse

from .base import BaseError
from .types import BaseErrorType


class BaseHttpError(BaseError):
    status_code: HTTPStatus

    def to_response(self):
        """Convert the error to a JSON response."""
        content = self.to_json()
        return JSONResponse(
            content=content,
            status_code=self.status_code,
        )


class HttpBadRequestError(BaseHttpError):
    type = "bad_request_error"
    message = "Bad request error"
    status_code = HTTPStatus.BAD_REQUEST


class HttpInternalServerError(BaseHttpError):
    type = "internal_server_error"
    message = "Internal Server Error. Please try again later."
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class HttpUnauthorizedError(BaseHttpError):
    type = "unauthorized_error"
    message = "Unauthorized. Please log in."
    status_code = HTTPStatus.UNAUTHORIZED


class HttpNotFoundError(BaseHttpError):
    type = "not_found_error"
    message = "Not found."
    status_code = HTTPStatus.NOT_FOUND


class HttpForbiddenError(BaseHttpError):
    type = "forbidden_error"
    message = "Forbidden. You do not have permission to access this resource."
    status_code = HTTPStatus.FORBIDDEN


class HttpServiceUnavailableError(BaseHttpError):
    type = "service_unavailable_error"
    message = "Service Unavailable. Please try again later."
    status_code = HTTPStatus.SERVICE_UNAVAILABLE


class HttpTooManyRequestsError(BaseHttpError):
    type = "too_many_requests_error"
    message = "Too many requests. Please slow down."
    status_code = HTTPStatus.TOO_MANY_REQUESTS


def http_error_adapter(exc: BaseErrorType, status_code: HTTPStatus) -> type:
    return type(
        f"AdaptedHttp{exc.__class__.__name__}",
        (BaseHttpError,),
        {
            "type": exc.type,
            "message": exc.message,
            "status_code": status_code,
            "data": deepcopy(exc.data),
        },
    )


def http_compare_error(exc: BaseErrorType, response: dict[str, typing.Any]) -> bool:
    # compare only type and message
    cp_response = deepcopy(response)
    if "data" in cp_response:
        cp_response.pop("data")
    expected = exc.to_json()
    expected.pop("data")
    return expected == cp_response
