from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from infra.mongo.transactions import AsyncMongoTransactionManager


class TestAsyncMongoTransactionManager:
    @staticmethod
    def _make_mock_client() -> AsyncMock:
        mock_client = AsyncMock()
        mock_session = MagicMock()
        mock_session.start_transaction = MagicMock()
        mock_session.commit_transaction = AsyncMock()
        mock_session.abort_transaction = AsyncMock()
        mock_session.end_session = AsyncMock()
        mock_client.start_session = AsyncMock(return_value=mock_session)
        return mock_client

    async def test_commit_on_success(self) -> None:
        mock_client = self._make_mock_client()
        manager = AsyncMongoTransactionManager(mock_client)

        async with manager:
            pass

        mock_session = await mock_client.start_session()
        mock_session.commit_transaction.assert_called_once()
        mock_session.abort_transaction.assert_not_called()
        mock_session.end_session.assert_called_once()

    async def test_rollback_on_error(self) -> None:
        mock_client = self._make_mock_client()
        manager = AsyncMongoTransactionManager(mock_client)

        try:
            async with manager:
                raise ValueError("Test error")
        except ValueError:
            pass

        mock_session = await mock_client.start_session()
        mock_session.abort_transaction.assert_called_once()
        mock_session.commit_transaction.assert_not_called()
        mock_session.end_session.assert_called_once()

    async def test_session_is_none_after_exit(self) -> None:
        mock_client = self._make_mock_client()
        manager = AsyncMongoTransactionManager(mock_client)

        async with manager:
            assert manager.session is not None

        assert manager.session is None

    async def test_session_is_none_after_error(self) -> None:
        mock_client = self._make_mock_client()
        manager = AsyncMongoTransactionManager(mock_client)

        try:
            async with manager:
                assert manager.session is not None
                raise ValueError("Test error")
        except ValueError:
            pass

        assert manager.session is None
