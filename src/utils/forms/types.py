import typing

from utils.forms.validators import BaseValidator

FormFieldsType: typing.TypeAlias = dict[str, list[BaseValidator]]
