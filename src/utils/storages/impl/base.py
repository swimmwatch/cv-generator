import abc
import typing

from utils.storages.types import CopyResult
from utils.storages.types import DeleteResult
from utils.storages.types import FolderInfo
from utils.storages.types import ObjectHead
from utils.storages.types import PutResult
from utils.storages.types import StorageEntry


class AsyncStorage(abc.ABC):
    # Files
    @abc.abstractmethod
    async def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> PutResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    @abc.abstractmethod
    def iter_chunks(self, key: str, *, chunk_size: int = 8 * 1024 * 1024) -> typing.AsyncIterator[bytes]:
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, key: str, *, version_id: str | None = None) -> DeleteResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def head(self, key: str) -> ObjectHead:
        raise NotImplementedError

    @abc.abstractmethod
    async def copy(self, *, source_key: str, dest_key: str) -> CopyResult:
        raise NotImplementedError

    # Folders (prefix-based)
    @abc.abstractmethod
    async def create_folder(self, folder: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def folder_exists(self, folder: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_folder(self, folder: str) -> FolderInfo:
        raise NotImplementedError

    @abc.abstractmethod
    def iter_folder(
        self,
        folder: str,
        *,
        page_size: int = 1000,
        include_folders: bool = True,
        include_files: bool = True,
    ) -> typing.AsyncIterator[StorageEntry]:
        """Iterate only direct children of `folder` (1 level)."""
        raise NotImplementedError

    @abc.abstractmethod
    def walk_folder_bfs(
        self,
        folder: str,
        *,
        page_size: int = 1000,
        max_queue_size: int = 10_000,
        include_folders: bool = True,
        include_files: bool = True,
    ) -> typing.AsyncIterator[StorageEntry]:
        """
        Recursive traversal.

        Uses BFS queue until `max_queue_size` is reached.
        When queue is full, it *spills* the discovered subtree into a depth-first traversal
        immediately (streaming), so memory won't blow up.
        """
        raise NotImplementedError
