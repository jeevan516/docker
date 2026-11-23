"""commit_user_change: the database unique index is the last guard against races."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError

from service.main import commit_user_change


def unique_violation(constraint):
    class FakeUniqueViolation(UniqueViolation):
        diag = SimpleNamespace(constraint_name=constraint)

    return FakeUniqueViolation("duplicate key value violates unique constraint")


class FakeSession:
    def __init__(self, error=None):
        self.error = error
        self.rolled_back = False

    def commit(self):
        if self.error:
            raise IntegrityError("INSERT ...", {}, self.error)

    def rollback(self):
        self.rolled_back = True


def test_commit_success():
    session = FakeSession()
    commit_user_change(session)
    assert not session.rolled_back


@pytest.mark.parametrize("constraint", ["ix_users_email", "users_email_key"])
def test_email_unique_violation_becomes_409(constraint):
    session = FakeSession(unique_violation(constraint))
    with pytest.raises(HTTPException) as caught:
        commit_user_change(session)
    assert caught.value.status_code == 409
    assert session.rolled_back


def test_other_unique_violation_is_reraised():
    session = FakeSession(unique_violation("some_other_index"))
    with pytest.raises(IntegrityError):
        commit_user_change(session)
    assert session.rolled_back


def test_non_postgres_integrity_error_is_reraised():
    session = FakeSession(ValueError("not a psycopg error"))
    with pytest.raises(IntegrityError):
        commit_user_change(session)
