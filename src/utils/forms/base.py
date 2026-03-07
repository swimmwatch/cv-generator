from typing import Any

from utils.errors.form import BaseFormValidationError
from utils.forms.field import FieldError
from utils.validators import BaseValidator


class BaseForm:
    def __init__(self, **data: Any):
        self._raw_data = data
        self._errors: list[FieldError] = []
        self._validated = False

    @property
    def fields(self) -> dict[str, list[BaseValidator]]:
        return {}

    async def is_valid(self) -> bool:
        try:
            await self.validate()
        except BaseFormValidationError:
            return False
        return True

    async def validate(self) -> None:
        if self._validated:
            return

        self._validated = True
        await self._validate_fields()

        if self._errors:
            raise BaseFormValidationError(errors=self._errors)

    async def _validate_fields(self):
        for field_name, validators in self.fields.items():
            value = self._raw_data.get(field_name, "")
            for validator in validators:
                try:
                    await validator(field_name, value)
                except FieldError as err:
                    self._errors.append(err)

    @property
    async def errors(self) -> list[FieldError]:
        if self._validated:
            return self._errors

        self._validated = True
        await self._validate_fields()
        return self._errors
