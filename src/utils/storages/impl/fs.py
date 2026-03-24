import asyncio
import hashlib
import os
import shutil
import typing
from collections import deque
from datetime import datetime
from datetime import timezone
from pathlib import Path

import aiofiles
import aiofiles.os

from utils.storages.errors import StorageObjectNotFoundError
from utils.storages.impl.base import AsyncStorage
from utils.storages.types import CopyResult
from utils.storages.types import DeleteResult
from utils.storages.types import EntryKind
from utils.storages.types import FolderInfo
from utils.storages.types import ObjectHead
from utils.storages.types import PutResult
from utils.storages.types import StorageEntry


class FSAsyncStorage(AsyncStorage):
    def __init__(self, *, root: str) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, key: str) -> Path:
        return self._root / key

    @staticmethod
    def _norm_folder(folder: str) -> str:
        if folder == "":
            return ""
        return folder.rstrip("/") + "/"

    @staticmethod
    def _etag(st: os.stat_result) -> str:
        return hashlib.md5(f"{st.st_size}-{st.st_mtime_ns}".encode(), usedforsecurity=False).hexdigest()

    @staticmethod
    def _last_modified(st: os.stat_result) -> datetime:
        return datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> PutResult:
        path = self._resolve(key)
        await aiofiles.os.makedirs(path.parent, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        st = await aiofiles.os.stat(path)
        return PutResult(etag=self._etag(st))

    async def get_bytes(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.is_file():
            raise StorageObjectNotFoundError(f"File not found: {key}")
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    def iter_chunks(self, key: str, *, chunk_size: int = 8 * 1024 * 1024) -> typing.AsyncIterator[bytes]:
        async def _gen() -> typing.AsyncIterator[bytes]:
            path = self._resolve(key)
            if not path.is_file():
                raise StorageObjectNotFoundError(f"File not found: {key}")
            async with aiofiles.open(path, "rb") as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        return _gen()

    async def delete(self, key: str, *, version_id: str | None = None) -> DeleteResult:
        path = self._resolve(key)
        if not path.exists():
            return DeleteResult(deleted=False)
        if path.is_dir():
            await asyncio.to_thread(shutil.rmtree, path)
        else:
            await aiofiles.os.remove(path)
        return DeleteResult(deleted=True)

    async def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    async def head(self, key: str) -> ObjectHead:
        path = self._resolve(key)
        if not path.is_file():
            raise StorageObjectNotFoundError(f"File not found: {key}")
        st = await aiofiles.os.stat(path)
        return ObjectHead(
            key=key,
            size=st.st_size,
            etag=self._etag(st),
            last_modified=self._last_modified(st),
            content_type=None,
            metadata={},
        )

    async def copy(self, *, source_key: str, dest_key: str) -> CopyResult:
        src = self._resolve(source_key)
        if not src.is_file():
            raise StorageObjectNotFoundError(f"File not found: {source_key}")
        dst = self._resolve(dest_key)
        await aiofiles.os.makedirs(dst.parent, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, str(src), str(dst))
        st = await aiofiles.os.stat(dst)
        return CopyResult(
            etag=self._etag(st),
            last_modified=self._last_modified(st),
        )

    async def create_folder(self, folder: str) -> None:
        if folder == "":
            return
        path = self._resolve(folder.rstrip("/"))
        await aiofiles.os.makedirs(path, exist_ok=True)

    async def folder_exists(self, folder: str) -> bool:
        if folder == "":
            return self._root.is_dir()
        return self._resolve(folder.rstrip("/")).is_dir()

    async def get_folder(self, folder: str) -> FolderInfo:
        prefix = self._norm_folder(folder)
        return FolderInfo(prefix=prefix, exists=await self.folder_exists(folder))

    def iter_folder(
        self,
        folder: str,
        *,
        page_size: int = 1000,
        include_folders: bool = True,
        include_files: bool = True,
    ) -> typing.AsyncIterator[StorageEntry]:
        async def _gen() -> typing.AsyncIterator[StorageEntry]:
            dir_path = self._resolve(folder.rstrip("/")) if folder else self._root
            if not dir_path.is_dir():
                return
            children = await asyncio.to_thread(lambda: sorted(dir_path.iterdir()))
            for child in children:
                if child.is_dir() and include_folders:
                    rel = str(child.relative_to(self._root)) + "/"
                    yield StorageEntry(kind=EntryKind.FOLDER, key=rel)
                elif child.is_file() and include_files:
                    rel = str(child.relative_to(self._root))
                    st = child.stat()
                    yield StorageEntry(
                        kind=EntryKind.FILE,
                        key=rel,
                        size=st.st_size,
                        etag=self._etag(st),
                        last_modified=self._last_modified(st),
                    )

        return _gen()

    def walk_folder_bfs(
        self,
        folder: str,
        *,
        page_size: int = 1000,
        max_queue_size: int = 10_000,
        include_folders: bool = True,
        include_files: bool = True,
    ) -> typing.AsyncIterator[StorageEntry]:
        async def _walk_dfs(prefix: str) -> typing.AsyncIterator[StorageEntry]:
            async for entry in self.iter_folder(
                prefix,
                page_size=page_size,
                include_folders=include_folders,
                include_files=include_files,
            ):
                yield entry
                if entry.kind == EntryKind.FOLDER:
                    async for x in _walk_dfs(entry.key):
                        yield x

        async def _gen() -> typing.AsyncIterator[StorageEntry]:
            root_prefix = self._norm_folder(folder)
            q: deque[str] = deque([root_prefix])

            while q:
                current = q.popleft()

                async for entry in self.iter_folder(
                    current,
                    page_size=page_size,
                    include_folders=include_folders,
                    include_files=include_files,
                ):
                    yield entry

                    if entry.kind != EntryKind.FOLDER:
                        continue

                    if len(q) < max_queue_size:
                        q.append(entry.key)
                    else:
                        async for x in _walk_dfs(entry.key):
                            yield x

        return _gen()
