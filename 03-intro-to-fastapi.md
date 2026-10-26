# Build a Typed CRUD API With FastAPI

An application programming interface defines how software components exchange requests and responses. This lesson uses [FastAPI](https://fastapi.tiangolo.com/tutorial/) to expose an HTTP API, [Pydantic](https://docs.pydantic.dev/latest/concepts/models/) to validate its JSON contracts, and [SQLAlchemy](https://docs.sqlalchemy.org/en/20/tutorial/) to persist users in PostgreSQL.

The service implements CRUD operations:

- **Create** a user with `POST`
- **Read** users with `GET`
- **Update** a user with `PUT`
- **Delete** a user with `DELETE`

## Request Lifecycle

![Typed FastAPI request moving through Pydantic, a route, SQLAlchemy, and PostgreSQL](assets/02-fastapi-request-lifecycle.png)

*Diagram based on the official guides for [FastAPI request bodies](https://fastapi.tiangolo.com/tutorial/body/), [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), and [SQLAlchemy sessions](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).*

Each boundary has one responsibility. FastAPI handles HTTP, Pydantic owns the external data contract, and SQLAlchemy owns database access.

## Before You Start

Reuse the `.env` file from lesson 2 and start its PostgreSQL container:

```bash
docker start postgres_cont
docker exec postgres_cont pg_isready -U postgres -d fastapi_db
```

The host-based service uses this connection string:

```dotenv
DB_CONN=postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_db
```

`localhost` is correct here because Uvicorn will run on the host. Lesson 4 changes the hostname when the API moves into a container.

## Service Structure

```text
service/
├── __init__.py
├── database.py
├── models.py
├── schemas.py
└── main.py
```

| File | Responsibility |
| --- | --- |
| `database.py` | Load `DB_CONN`, create the engine, and provide request-scoped sessions |
| `models.py` | Map Python classes to database tables |
| `schemas.py` | Define validated request and response bodies |
| `main.py` | Configure FastAPI and implement routes |

## Database Connection and Session

The central parts of `service/database.py` are:

```python
DATABASE_URL = os.getenv("DB_CONN")

if DATABASE_URL is None:
    raise ValueError("DB_CONN environment variable is required")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Base class shared by the service's SQLAlchemy models."""


def get_db() -> Generator[Session]:
    """Yield one database session for a request, then close it."""
    with SessionLocal() as session:
        yield session
```

`get_db()` is a FastAPI dependency. The context manager closes the session after the request succeeds or fails, so a route does not need to duplicate connection cleanup.

For this self-contained lesson, `Base.metadata.create_all()` creates missing tables when the service starts. Production systems normally manage reviewed, reversible schema changes with a migration tool such as [Alembic](https://alembic.sqlalchemy.org/en/latest/) instead of relying on automatic table creation.

## SQLAlchemy Model

`service/models.py` uses SQLAlchemy 2 typed mappings:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
```

The Python annotations describe model attributes, while `mapped_column()` describes database behavior such as the primary key, maximum length, uniqueness, and index.

This directory API intentionally stores only profile data. Authentication and password storage require a separate security design and should not be represented by saving plain-text passwords in a CRUD example.

## Pydantic Contracts

`service/schemas.py` separates incoming payloads from outgoing representations:

```python
class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class UserCreate(UserBase):
    pass


class UserUpdate(UserBase):
    pass


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
```

`EmailStr` rejects malformed addresses before a route reaches the database. `from_attributes=True` lets Pydantic serialize a SQLAlchemy model into the public response shape.

Separate class names keep the API contract explicit even when two request bodies currently have the same fields. They can evolve independently later.

## Request-Scoped Dependency

FastAPI can combine a type annotation with a dependency:

```python
DatabaseSession = Annotated[Session, Depends(get_db)]
```

Routes that declare `db: DatabaseSession` receive one open SQLAlchemy session. FastAPI calls the dependency and handles its cleanup automatically.

## CRUD Routes

The create route validates the request, writes a row, and returns the persisted model with a `201 Created` status:

```python
@app.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(request: schemas.UserCreate, db: DatabaseSession) -> models.User:
    new_user = models.User(name=request.name, email=str(request.email))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
```

The list route uses SQLAlchemy's `select()` interface and a deterministic order:

```python
@app.get("/users", response_model=list[schemas.UserOut])
def get_all_users(db: DatabaseSession) -> list[models.User]:
    statement = select(models.User).order_by(models.User.id)
    return list(db.scalars(statement))
```

Update and delete first retrieve the target row with `db.get()`. Missing identifiers return `404 Not Found` instead of silently succeeding.

| Method | Path | Success response |
| --- | --- | --- |
| `GET` | `/` | Service status |
| `GET` | `/users` | Ordered list of users |
| `GET` | `/users/{user_id}` | One user or `404 Not Found` |
| `POST` | `/users` | `201` and the created user |
| `PUT` | `/users/{user_id}` | Updated user |
| `DELETE` | `/users/{user_id}` | `204 No Content` |

Malformed request bodies return `422 Unprocessable Content`, missing identifiers return `404 Not Found`, and duplicate email addresses return `409 Conflict`. These responses keep validation and domain failures at the HTTP boundary instead of exposing a database exception.

## Run the Host-Based API

From the repository root:

```bash
uv run uvicorn service.main:app --reload --port 8000
```

Open the generated [Swagger UI](http://localhost:8000/docs) or inspect the [OpenAPI schema](http://localhost:8000/openapi.json).

## Exercise the Contract

Check the service and initial collection:

```bash
curl http://localhost:8000/
curl http://localhost:8000/users
```

Create a user:

```bash
curl -X POST http://localhost:8000/users \
    -H "Content-Type: application/json" \
    -d '{"name":"Jane Doe","email":"jane.doe@example.com"}'
```

Read user `1` directly:

```bash
curl http://localhost:8000/users/1
```

Update user `1`:

```bash
curl -X PUT http://localhost:8000/users/1 \
    -H "Content-Type: application/json" \
    -d '{"name":"Jane Smith","email":"jane.smith@example.com"}'
```

Delete the same user:

```bash
curl -i -X DELETE http://localhost:8000/users/1
```

The delete response has status `204` and no JSON body. Repeating the request returns `404` because the row no longer exists.

## Checkpoint

**Why use both a SQLAlchemy model and a Pydantic model for a user?**

**Answer:** The SQLAlchemy model describes database persistence. The Pydantic models describe public request and response contracts. Keeping them separate prevents database implementation details from becoming accidental API fields and lets each boundary evolve independently.

## Summary

The service now validates typed JSON payloads, opens one SQLAlchemy session per request, implements all four CRUD operations, returns meaningful HTTP status codes, and exposes an automatically generated OpenAPI contract.
