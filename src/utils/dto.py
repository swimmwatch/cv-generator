import typing
from collections.abc import Iterable
from datetime import datetime
from inspect import isclass

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined


def parse_lookups(lookups: Iterable[str]) -> dict[str, typing.Any]:
    """
    Parse Django ORM-style lookup strings into a nested dictionary.

    Example:
        parse_lookups(["author", "author__profile", "comments__author"])
        # Returns: {"author": {"profile": True}, "comments": {"author": True}}
    """
    result: dict[str, typing.Any] = {}

    for lookup in lookups:
        parts = lookup.split("__")
        current = result

        for i, part in enumerate(parts):
            is_last = i == len(parts) - 1

            if part not in current:
                current[part] = True if is_last else {}
            elif current[part] is True and not is_last:
                current[part] = {}

            if not is_last:
                current = current[part]

    return result


class BaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_schema(cls, obj: BaseModel, **kwargs) -> typing.Self:
        """Create a DTO instance from a schema object.

        Args:
            obj: The source schema object to convert.
        Returns:
            An instance of the DTO class populated with data from the schema.
        """
        return cls.model_validate(obj, **kwargs)

    @classmethod
    def from_model(
        cls,
        obj: typing.Any,
        relations_loading: Iterable[str] | None = None,
        **kwargs,
    ) -> typing.Self:
        """Create a DTO instance from a model object.

        Args:
            obj: The source model object to convert.
            relations_loading: A list of Django ORM-style lookup strings specifying
            which relations to load. Uses double underscore (__) notation for
            nested relations. Example: ["author", "author__profile", "comments__author"]

        Returns:
            An instance of the DTO class populated with data from the model.
        """
        known_data = kwargs

        relations_loading_data = parse_lookups(relations_loading) if relations_loading else {}
        relations_loading_list = list(relations_loading) if relations_loading else []

        data = {}
        for field, field_info in cls.model_fields.items():
            if field in known_data:
                data[field] = known_data[field]
                continue

            default_is_defined, default_value = cls.get_field_default_value(field_info)

            field_origin, field_args = typing.get_origin(field_info.annotation), typing.get_args(field_info.annotation)

            if field_args:
                class_candidate = field_args[0]
            else:
                class_candidate = field_info.annotation

            is_relation = class_candidate and isclass(class_candidate) and issubclass(class_candidate, BaseDTO)

            if not is_relation:
                data[field] = getattr(obj, field)
                continue

            loading_data = relations_loading_data.get(field, False)
            if not loading_data:
                data[field] = default_value
                continue

            obj_attr = getattr(obj, field)
            if not obj_attr:
                data[field] = obj_attr
                continue

            # Extract nested lookups for this field
            prefix = f"{field}__"
            nested_lookups = [lookup[len(prefix) :] for lookup in relations_loading_list if lookup.startswith(prefix)]

            if isinstance(obj_attr, Iterable):
                field_data = [
                    class_candidate.from_model(element, relations_loading=nested_lookups) for element in obj_attr
                ]
                # TODO: handle none and empty cases
                data[field] = field_origin(field_data)  # type: ignore[misc]
            else:
                data[field] = class_candidate.from_model(
                    obj_attr,
                    relations_loading=nested_lookups,
                )

        return cls(**data)

    @staticmethod
    def get_field_default_value(field_info: FieldInfo) -> tuple[bool, typing.Any]:
        default_value = field_info.default
        is_defined = default_value is not PydanticUndefined

        return is_defined, default_value


class TimedMixinDTO:
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    is_active: bool
