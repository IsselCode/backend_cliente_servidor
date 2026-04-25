from core.app.enums import UserRole
from core.database.repositories.user_repository import UserRepository


def bootstrap_admin_user(users: UserRepository, password_service, username: str, password: str) -> None:
    if users.find_by_username(username):
        return

    users.create_user(
        username=username,
        dp_name="Administrator",
        password_hash=password_service.hash_password(password),
        role=UserRole.ADMIN,
    )
