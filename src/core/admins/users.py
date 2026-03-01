from sqladmin import ModelView

from core import models


class UserAdmin(ModelView, model=models.User):
    column_list = [
        "id",
        "username",
        "first_name",
        "last_name",
        "created_at",
        "updated_at",
    ]
