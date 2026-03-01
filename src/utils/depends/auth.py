import abc
import inspect
import typing

from fastapi import Security
from fastapi.security.base import SecurityBase
from starlette.requests import Request

from utils.errors.http_ import BaseHttpError

KeyT = typing.TypeVar("KeyT", bound=typing.Any)


class GetCurrentUserProvider:
    def __init__(
        self,
        probes: typing.Sequence["BaseAuthProbe"],
        on_failure: type[BaseHttpError] | None = None,
    ):
        if not probes:
            raise ValueError("At least one auth probe must be provided")

        self._probes = probes
        self._on_failure = on_failure

        self._dependency = self._build_dependency()

    def _build_dependency(self):
        schemas: list[SecurityBase] = [probe.schema for probe in self._probes]

        async def _dep(
            request: Request,
            **injected_keys: typing.Any,
        ) -> typing.Any | None:
            for idx, probe in enumerate(self._probes):
                key = injected_keys.get(f"key{idx}")
                user = await probe.authenticate(request, key)  # type: ignore[func-returns-value]
                if user is not None:
                    return user

            if self._on_failure:
                raise self._on_failure

            return None

        # Dynamically expose every security scheme to FastAPI.
        params: list[inspect.Parameter] = [
            inspect.Parameter(
                "request",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=Request,
            )
        ]
        for idx, schema in enumerate(schemas):
            params.append(
                inspect.Parameter(
                    f"key{idx}",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=typing.Any,
                    default=Security(typing.cast(typing.Any, schema)),
                )
            )

        _dep.__signature__ = inspect.Signature(parameters=params)  # type: ignore[attr-defined]
        return _dep

    def dependency(self):
        return self._dependency


class BaseAuthProbe(typing.Generic[KeyT], abc.ABC):
    schema: typing.ClassVar[SecurityBase]

    @abc.abstractmethod
    async def authenticate(
        self,
        request: Request,
        key: KeyT | None = None,
    ) -> typing.Any | None:
        raise NotImplementedError
