from app.core.security import hash_password, verify_password
from app.repositories.user_repository import UserRepository


def test_create_and_get_user_by_email(db_session):
    repo = UserRepository(db_session)
    repo.create(email="repo@example.com", hashed_password=hash_password("secret123"), full_name="Repo Test")

    fetched = repo.get_by_email("repo@example.com")
    assert fetched is not None
    assert fetched.email == "repo@example.com"
    assert verify_password("secret123", fetched.hashed_password)


def test_get_by_email_returns_none_when_missing(db_session):
    repo = UserRepository(db_session)
    assert repo.get_by_email("missing@example.com") is None
