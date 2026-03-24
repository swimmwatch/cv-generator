import typing
from collections import deque
from contextlib import asynccontextmanager

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from utils.storages.errors import StorageObjectNotFoundError
from utils.storages.impl.base import AsyncStorage
from utils.storages.types import CopyResult
from utils.storages.types import DeleteResult
from utils.storages.types import EntryKind
from utils.storages.types import FolderInfo
from utils.storages.types import ObjectHead
from utils.storages.types import PutResult
from utils.storages.types import StorageEntry

if typing.TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client
else:
    S3Client = typing.Any


class S3AsyncStorage(AsyncStorage):
    def __init__(
        self,
        *,
        bucket: str,
        region_name: str | None = None,
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        verify_ssl: bool | str | None = None,
        addressing_style: typing.Literal["auto", "virtual", "path"] | None = None,
    ) -> None:
        self._bucket = bucket
        self._region_name = region_name
        self._endpoint_url = endpoint_url
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token
        self._verify_ssl = verify_ssl
        self._addressing_style = addressing_style

        self._session = aioboto3.Session()

    @property
    def bucket(self) -> str:
        return self._bucket

    def _client_kwargs(self) -> dict[str, typing.Any]:
        cfg = None
        if self._addressing_style:
            s3_cfg = {"addressing_style": self._addressing_style}
            cfg = Config(s3=s3_cfg)  # type: ignore[arg-type]

        kwargs: dict[str, typing.Any] = {
            "service_name": "s3",
            "region_name": self._region_name,
            "endpoint_url": self._endpoint_url,
            "aws_access_key_id": self._aws_access_key_id,
            "aws_secret_access_key": self._aws_secret_access_key,
            "aws_session_token": self._aws_session_token,
            "verify": self._verify_ssl,
        }
        if cfg is not None:
            kwargs["config"] = cfg

        return {k: v for k, v in kwargs.items() if v is not None}

    @asynccontextmanager
    async def _client(self) -> typing.AsyncIterator[S3Client]:
        async with self._session.client(**self._client_kwargs()) as s3:
            yield s3

    @staticmethod
    def _norm_folder(folder: str) -> str:
        # S3 "folder" = prefix, commonly ends with "/"
        if folder == "":
            return ""
        return folder if folder.endswith("/") else folder + "/"

    async def put_bytes(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> PutResult:
        async with self._client() as s3:
            kwargs: dict[str, typing.Any] = {
                "Bucket": self.bucket,
                "Key": key,
                "Body": data,
            }
            if content_type:
                kwargs["ContentType"] = content_type
            if metadata:
                kwargs["Metadata"] = metadata

            resp = await s3.put_object(**kwargs)
            return PutResult(etag=resp.get("ETag"), version_id=resp.get("VersionId"))

    async def get_bytes(self, key: str) -> bytes:
        async with self._client() as s3:
            try:
                resp = await s3.get_object(Bucket=self.bucket, Key=key)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in {"NoSuchKey", "404", "NotFound"}:
                    raise StorageObjectNotFoundError(f"S3 object not found: {key}") from e
                raise
            return await resp["Body"].read()

    def iter_chunks(self, key: str, *, chunk_size: int = 8 * 1024 * 1024) -> typing.AsyncIterator[bytes]:
        async def _gen() -> typing.AsyncIterator[bytes]:
            async with self._client() as s3:
                try:
                    resp = await s3.get_object(Bucket=self.bucket, Key=key)
                except ClientError as e:
                    code = e.response.get("Error", {}).get("Code")
                    if code in {"NoSuchKey", "404", "NotFound"}:
                        raise StorageObjectNotFoundError(f"S3 object not found: {key}") from e
                    raise
                body = resp["Body"]
                while True:
                    chunk = await body.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        return _gen()

    async def delete(self, key: str, *, version_id: str | None = None) -> DeleteResult:
        async with self._client() as s3:
            kwargs: dict[str, typing.Any] = {"Bucket": self.bucket, "Key": key}
            if version_id:
                kwargs["VersionId"] = version_id
            resp = await s3.delete_object(**kwargs)
            return DeleteResult(
                deleted=True,  # S3 delete is idempotent
                version_id=resp.get("VersionId"),
                delete_marker=resp.get("DeleteMarker"),
            )

    async def exists(self, key: str) -> bool:
        async with self._client() as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in {"404", "NoSuchKey", "NotFound"}:
                    return False
                raise

    async def head(self, key: str) -> ObjectHead:
        async with self._client() as s3:
            try:
                resp = await s3.head_object(Bucket=self.bucket, Key=key)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in {"404", "NoSuchKey", "NotFound"}:
                    raise StorageObjectNotFoundError(f"S3 object not found: {key}") from e
                raise

            return ObjectHead(
                key=key,
                size=int(resp.get("ContentLength", 0)),
                etag=resp.get("ETag"),
                last_modified=resp.get("LastModified"),
                content_type=resp.get("ContentType"),
                metadata=dict(resp.get("Metadata") or {}),
            )

    async def copy(self, *, source_key: str, dest_key: str) -> CopyResult:
        async with self._client() as s3:
            resp = await s3.copy_object(
                Bucket=self.bucket,
                Key=dest_key,
                CopySource={"Bucket": self.bucket, "Key": source_key},
            )
            copy_obj = resp.get("CopyObjectResult") or {}
            return CopyResult(
                etag=copy_obj.get("ETag"),
                last_modified=copy_obj.get("LastModified"),
                version_id=resp.get("VersionId"),
            )

    async def create_folder(self, folder: str) -> None:
        """
        Creates a "folder marker" object with trailing slash.
        In S3 it's optional, but useful if you want folder to be visible in some UIs.
        """
        prefix = self._norm_folder(folder)
        if prefix == "":
            return  # root
        await self.put_bytes(prefix, b"", content_type="application/x-directory")

    async def folder_exists(self, folder: str) -> bool:
        prefix = self._norm_folder(folder)
        async with self._client() as s3:
            resp = await s3.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=1,
            )
            return bool(resp.get("KeyCount", 0))

    async def get_folder(self, folder: str) -> FolderInfo:
        prefix = self._norm_folder(folder)
        return FolderInfo(prefix=prefix, exists=await self.folder_exists(prefix))

    async def _iter_folder_pages(
        self,
        s3: S3Client,
        *,
        prefix: str,
        page_size: int,
    ) -> typing.AsyncIterator[typing.Any]:
        paginator = s3.get_paginator("list_objects_v2")
        async for page in paginator.paginate(
            Bucket=self.bucket,
            Prefix=prefix,
            Delimiter="/",  # 1-level listing
            PaginationConfig={"PageSize": page_size},
        ):
            yield page

    def iter_folder(
        self,
        folder: str,
        *,
        page_size: int = 1000,
        include_folders: bool = True,
        include_files: bool = True,
    ) -> typing.AsyncIterator[StorageEntry]:
        """
        Direct children only (files + subfolders).
        Streamed, paginated.
        """

        async def _gen() -> typing.AsyncIterator[StorageEntry]:
            prefix = self._norm_folder(folder)
            async with self._client() as s3:
                async for page in self._iter_folder_pages(s3, prefix=prefix, page_size=page_size):
                    if include_folders:
                        for cp in page.get("CommonPrefixes") or []:
                            pfx = cp.get("Prefix")
                            if pfx:
                                yield StorageEntry(kind=EntryKind.FOLDER, key=pfx)

                    if include_files:
                        for obj in page.get("Contents") or []:
                            key = obj.get("Key")
                            if not key:
                                continue
                            # skip the folder marker itself (e.g. "a/b/")
                            if prefix and key == prefix:
                                continue
                            yield StorageEntry(
                                kind=EntryKind.FILE,
                                key=key,
                                size=int(obj.get("Size", 0)),
                                etag=obj.get("ETag"),
                                last_modified=obj.get("LastModified"),
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
            # DFS spill: no sibling-prefix accumulation => bounded memory (by depth and current page).
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
            root = self._norm_folder(folder)
            q: deque[str] = deque([root])

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

                    # BFS queue bounded: never allow unbounded growth.
                    if len(q) < max_queue_size:
                        q.append(entry.key)
                    else:
                        # Spill subtree immediately (DFS), streaming.
                        async for x in _walk_dfs(entry.key):
                            yield x

        return _gen()
