import abc
import contextlib
import typing


class BaseTransactionManager(contextlib.AbstractContextManager, abc.ABC):
    pass


class BaseAsyncTransactionManager(contextlib.AbstractAsyncContextManager, abc.ABC):
    pass


class TransactionManager(contextlib.AbstractContextManager):
    def __init__(self, managers: typing.Sequence[BaseTransactionManager]) -> None:
        self._managers = managers

    def __enter__(self) -> "TransactionManager":
        for manager in self._managers:
            manager.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for manager in self._managers:
            manager.__exit__(exc_type, exc_val, exc_tb)


class AsyncTransactionManager(contextlib.AbstractAsyncContextManager):
    def __init__(self, managers: typing.Sequence[BaseAsyncTransactionManager]) -> None:
        self._managers = managers

    async def __aenter__(self):
        for manager in self._managers:
            await manager.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for manager in self._managers:
            await manager.__aexit__(exc_type, exc_val, exc_tb)
