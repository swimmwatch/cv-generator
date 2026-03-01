import uuid

from utils.schema import BaseSchema
from utils.schema import TimedSchemaMixin


class GetCurrentUserOut(
    BaseSchema,
    TimedSchemaMixin,
):
    id: uuid.UUID
    messenger_id: str
    username: str | None = None
    first_name: str
    last_name: str | None = None
    is_superuser: bool
    is_staff: bool
