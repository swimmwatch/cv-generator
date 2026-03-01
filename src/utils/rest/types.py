import typing

from httpx import Response

RestJSONDataType = dict[str, typing.Any]
RestResponseType = tuple[Response, RestJSONDataType]
