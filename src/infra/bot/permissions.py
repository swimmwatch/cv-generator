from core import models
from utils.patterns.specification import BaseSpecification


class _IsAdmin(BaseSpecification):
    async def is_satisfied(self, **kwargs) -> bool:
        user: models.User = kwargs["user"]
        return user.admin


class _IsApproved(BaseSpecification):
    async def is_satisfied(self, **kwargs) -> bool:
        user: models.User = kwargs["user"]
        return user.approved


IS_ADMIN = _IsAdmin()
IS_APPROVED = _IsApproved()
