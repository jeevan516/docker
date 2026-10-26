from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from service import models, schemas
from service.database import Base, engine, get_db

app = FastAPI(title="User Directory API", version="1.0.0")

# Create any missing tables at startup. Existing tables are left unchanged,
# so this is not a substitute for migrations when a model changes.
Base.metadata.create_all(bind=engine)

# Route parameters typed with this alias receive one session per request.
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_user_or_404(db: Session, user_id: int) -> models.User:
    """Return one user or raise the public not-found response."""
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def ensure_email_available(
    db: Session, email: str, *, exclude_user_id: int | None = None
) -> None:
    """Raise a conflict when another user already owns an email address."""
    statement = select(models.User).where(models.User.email == email)
    if exclude_user_id is not None:
        statement = statement.where(models.User.id != exclude_user_id)
    if db.scalar(statement) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")


def commit_user_change(db: Session) -> None:
    """Handle email conflicts that occur after the availability check."""
    # Two requests can both pass ensure_email_available before either commits;
    # the database unique index is the final guard against that race.
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Covers the index name SQLAlchemy creates and PostgreSQL's default
        # unique-constraint name. Any other integrity error is re-raised.
        if isinstance(exc.orig, UniqueViolation) and exc.orig.diag.constraint_name in {
            "ix_users_email",
            "users_email_key",
        }:
            raise HTTPException(
                status_code=409, detail="Email already registered"
            ) from exc
        raise


@app.get("/", tags=["health"])
def index() -> dict[str, str]:
    """Return a lightweight service status response."""
    return {"status": "ok"}


@app.get("/users", response_model=list[schemas.UserOut])
def get_all_users(db: DatabaseSession) -> list[models.User]:
    """Return all persisted users ordered by identifier."""
    statement = select(models.User).order_by(models.User.id)
    return list(db.scalars(statement))


@app.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: DatabaseSession) -> models.User:
    """Return one persisted user by identifier."""
    return get_user_or_404(db, user_id)


@app.post("/users", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(request: schemas.UserCreate, db: DatabaseSession) -> models.User:
    """Validate and persist a new user."""
    email = str(request.email)
    ensure_email_available(db, email)

    new_user = models.User(name=request.name, email=email)
    db.add(new_user)
    commit_user_change(db)
    # Reload the row to pick up the database-generated id.
    db.refresh(new_user)
    return new_user


@app.put("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int, request: schemas.UserUpdate, db: DatabaseSession
) -> models.User:
    """Replace the editable fields of one user."""
    existing_user = get_user_or_404(db, user_id)

    email = str(request.email)
    # Excluding this user allows an update that keeps the same email.
    ensure_email_available(db, email, exclude_user_id=user_id)

    existing_user.name = request.name
    existing_user.email = email
    commit_user_change(db)
    db.refresh(existing_user)
    return existing_user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: DatabaseSession) -> Response:
    """Delete one user or return 404 when it does not exist."""
    user = get_user_or_404(db, user_id)

    db.delete(user)
    db.commit()
    # Return an empty Response so FastAPI does not add a JSON body to the 204.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
