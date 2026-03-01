import typing

from utils.patterns.specification import BaseSpecification

PayloadDataT = typing.TypeVar("PayloadDataT", bound=typing.Dict[str, typing.Any])
HandlerType = typing.Callable[[PayloadDataT], typing.Awaitable[None]]


class Dispatcher(typing.Generic[PayloadDataT]):
    """A dispatcher that routes events to handlers based on specifications."""

    def __init__(self):
        self._routes: typing.List[tuple[BaseSpecification, HandlerType]] = []

    def route(self, spec: BaseSpecification):
        """Decorator to register a handler for a given specification."""

        def decorator(handler: HandlerType):
            self._routes.append((spec, handler))
            return handler

        return decorator

    async def dispatch(self, event: PayloadDataT):
        """Dispatch an event to the appropriate handler based on specifications."""
        for spec, handler in self._routes:
            if await spec.is_satisfied(data=event):
                await handler(event)

    def include(self, other: "Dispatcher[PayloadDataT]"):
        """Include routes from another dispatcher."""
        self._routes.extend(other._routes)
