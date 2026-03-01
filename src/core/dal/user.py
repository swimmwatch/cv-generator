from core import models
from infra.db.utils.dal.async_ import SqlAlchemyAsyncDAL


class UserAsyncDAL(SqlAlchemyAsyncDAL):
    class Meta(SqlAlchemyAsyncDAL.Meta):
        model = models.User
