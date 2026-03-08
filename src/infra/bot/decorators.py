import functools
import typing

from utils.patterns.specification import BaseSpecification


def authorized(
    permission: BaseSpecification,
    fallback: typing.Callable[..., typing.Awaitable[typing.Any]] | None = None,
):
    """Authorization decorator for bot handlers.

    Works with both PTB-style (update, context) and aiogram-style (event, data)
    call signatures as long as a user object is available either in:
    - `context.user_data["user"]` (PTB)
    - `data["user"]` (aiogram middleware)
    """

    def decorator(func: typing.Callable[..., typing.Awaitable[typing.Any]]):
        @functools.wraps(func)
        async def wrapper(*args: typing.Any, **kwargs: typing.Any):
            user = None

            # PTB: (update, context, ...)
            if len(args) >= 2 and hasattr(args[1], "user_data"):
                context = args[1]
                user_data = typing.cast(dict, getattr(context, "user_data", {}))
                user = user_data.get("user")

            # aiogram: (event, data)
            if user is None and len(args) >= 2 and isinstance(args[1], dict):
                data = args[1]
                user = data.get("user")

            if not user:
                return None

            allowed = await permission(user=user)
            if allowed:
                return await func(*args, **kwargs)

            if fallback is not None:
                return await fallback(*args, **kwargs)

            return None

        return wrapper

    return decorator
