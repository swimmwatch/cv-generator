import enum
import typing
from dataclasses import dataclass
from datetime import datetime

AddressingStyleLiteral = typing.Literal["auto", "path", "virtual"]


@dataclass(slots=True)
class PutResult:
    etag: str | None = None
    version_id: str | None = None


@dataclass(slots=True)
class DeleteResult:
    deleted: bool
    version_id: str | None = None
    delete_marker: bool | None = None


@dataclass(slots=True)
class CopyResult:
    etag: str | None = None
    last_modified: datetime | None = None
    version_id: str | None = None


@dataclass(slots=True)
class ObjectHead:
    key: str
    size: int
    etag: str | None
    last_modified: datetime | None
    content_type: str | None
    metadata: dict[str, str]


class EntryKind(enum.StrEnum):
    FILE = "file"
    FOLDER = "folder"


@dataclass(slots=True)
class StorageEntry:
    kind: EntryKind
    key: str  # for folder: normalized prefix ending with "/"
    size: int | None = None
    etag: str | None = None
    last_modified: datetime | None = None


@dataclass(slots=True)
class FolderInfo:
    prefix: str
    exists: bool
