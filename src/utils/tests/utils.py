from sqlalchemy.ext.asyncio import AsyncSession


class DontCloseAsyncSessionCM:
    """
    Polyfactory async persistence does: `async with self.session as session: ...`
    (and a regular AsyncSession would be closed when exiting that context).

    This context manager yields *your* AsyncSession but DOES NOT close it.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False  # don't suppress exceptions and don't close the session
