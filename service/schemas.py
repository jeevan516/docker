from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Fields shared by user creation, update, and response contracts."""

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    """Request body used to create a user."""


class UserUpdate(UserBase):
    """Request body used to replace a user."""


class UserOut(UserBase):
    """Response body returned for persisted users."""

    model_config = ConfigDict(from_attributes=True)

    id: int
