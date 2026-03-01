from sqladmin import Admin

from core import admins


def register_admin_views(admin: Admin) -> None:
    admin.add_view(admins.UserAdmin)
