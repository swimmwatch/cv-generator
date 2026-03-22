from utils.errors.base import BaseError


class InvalidJobError(BaseError):
    type = "invalid_job"
    message = "The provided link does not contain a valid job posting."
