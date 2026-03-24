from core import models
from infra.db.utils.dal.async_ import SqlAlchemyAsyncDAL


class GeneratedCVAsyncDAL(SqlAlchemyAsyncDAL):
    class Meta(SqlAlchemyAsyncDAL.Meta):
        model = models.GeneratedCV
