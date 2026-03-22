from utils.errors.base import BaseError


class InvalidResumeError(BaseError):
    type = "invalid_resume"
    message = "The uploaded file does not contain a valid resume."
