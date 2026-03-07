from utils.forms.errors import BaseValidationError


class UserSignUpValidationError(BaseValidationError):
    type = "signup_form"
    message = "Signup form validation error."
