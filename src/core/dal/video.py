from core import models
from infra.db.utils.dal.async_ import SqlAlchemyAsyncDAL


class VideoAsyncDAL(SqlAlchemyAsyncDAL):
    class Meta(SqlAlchemyAsyncDAL.Meta):
        model = models.Video
