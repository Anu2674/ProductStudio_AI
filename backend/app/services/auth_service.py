from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, AuthError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def register(self, email: str, password: str, full_name: str | None):
        if self.repo.get_by_email(email):
            raise AppError("Email already registered", status_code=400)
        return self.repo.create(email, hash_password(password), full_name)

    def authenticate(self, email: str, password: str):
        user = self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password")
        return user

    def create_token_for_user(self, user) -> str:
        return create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
