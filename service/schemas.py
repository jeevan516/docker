from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Fields shared by user creation, update, and response contracts."""

    # Same limit as the database column, so invalid names fail with 422
    # before they reach PostgreSQL.
    name: str = Field(min_length=1, max_length=100)
    # EmailStr rejects malformed addresses during request validation.
    email: EmailStr


class UserCreate(UserBase):
    """Request body used to create a user."""


class UserUpdate(UserBase):
    """Request body used to replace a user."""


class UserOut(UserBase):
    """Response body returned for persisted users."""

    # Lets FastAPI build this response directly from a models.User instance.
    model_config = ConfigDict(from_attributes=True)

    # Only responses expose the id; clients never send it in a request body.
    id: int
