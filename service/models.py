from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from service.database import Base


class User(Base):
    """Database row for one user in the ``users`` table."""

    __tablename__ = "users"

    # PostgreSQL assigns the identifier automatically on insert.
    id: Mapped[int] = mapped_column(primary_key=True)
    # Matches the 100-character limit enforced by schemas.UserBase.
    name: Mapped[str] = mapped_column(String(100))
    # 320 is the maximum length of an email address (64 local + @ + 255 domain).
    # The unique index backs the 409 conflict handling in main.py.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
