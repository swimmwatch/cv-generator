from core.repos import UserRepository
from core.validators.users import UniqueUserEmailValidator
from utils.forms.base import BaseForm
from utils.forms.types import FormFieldsType
from utils.forms.validators import DataRequiredValidator
from utils.forms.validators import RegexValidator


class UserAdminCreateForm(BaseForm):
    def __init__(self, user_repo: UserRepository, **data):
        super().__init__(**data)
        self._user_repo = user_repo

    @property
    def fields(self) -> FormFieldsType:
        return {
            "email": [
                DataRequiredValidator(),
                RegexValidator(UserValidation.REGEX, UsernameRegexValidation.MESSAGE),
                UniqueUserEmailValidator(self._user_repo),
            ],
            "password": [
                RegexValidator(PasswordRegexValidation.REGEX, PasswordRegexValidation.MESSAGE),
            ],
        }
