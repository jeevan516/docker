import pytest
from sqlalchemy import inspect

from service.database import engine


def create(client, name="Ada Lovelace", email="ada@example.com"):
    return client.post("/users", json={"name": name, "email": email})


def test_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_users_table_created_at_startup():
    columns = {c["name"] for c in inspect(engine).get_columns("users")}
    assert columns == {"id", "name", "email"}
    indexes = {i["name"]: i for i in inspect(engine).get_indexes("users")}
    assert indexes["ix_users_email"]["unique"]


def test_list_starts_empty(client):
    assert client.get("/users").json() == []


def test_create_returns_201_with_id(client):
    response = create(client)
    assert response.status_code == 201
    body = response.json()
    assert body == {"name": "Ada Lovelace", "email": "ada@example.com", "id": body["id"]}
    assert isinstance(body["id"], int)


def test_get_user(client):
    user_id = create(client).json()["id"]
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"


def test_list_is_ordered_by_id(client):
    ids = [create(client, f"User {i}", f"user{i}@example.com").json()["id"] for i in range(3)]
    assert [u["id"] for u in client.get("/users").json()] == sorted(ids)


def test_duplicate_email_is_409(client):
    create(client)
    response = create(client, name="Someone Else")
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}
    assert len(client.get("/users").json()) == 1


def test_update_user(client):
    user_id = create(client).json()["id"]
    response = client.put(f"/users/{user_id}", json={"name": "Ada King", "email": "ada.king@example.org"})
    assert response.status_code == 200
    assert response.json() == {"id": user_id, "name": "Ada King", "email": "ada.king@example.org"}
    assert client.get(f"/users/{user_id}").json()["name"] == "Ada King"


def test_update_keeping_own_email_is_allowed(client):
    user_id = create(client).json()["id"]
    response = client.put(f"/users/{user_id}", json={"name": "Renamed", "email": "ada@example.com"})
    assert response.status_code == 200


def test_update_to_another_users_email_is_409(client):
    create(client)
    other = create(client, "Grace Hopper", "grace@example.com").json()["id"]
    response = client.put(f"/users/{other}", json={"name": "Grace", "email": "ada@example.com"})
    assert response.status_code == 409


def test_delete_user(client):
    user_id = create(client).json()["id"]
    response = client.delete(f"/users/{user_id}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/users/{user_id}").status_code == 404


@pytest.mark.parametrize(
    ("method", "body"),
    [("get", None), ("put", {"name": "X", "email": "x@example.com"}), ("delete", None)],
)
def test_unknown_user_is_404(client, method, body):
    kwargs = {"json": body} if body else {}
    response = getattr(client, method)("/users/9999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "No Email"},
        {"name": "Bad Email", "email": "not-an-email"},
        {"name": "", "email": "empty@example.com"},
        {"name": "x" * 101, "email": "long@example.com"},
    ],
)
def test_invalid_payload_is_422(client, payload):
    assert client.post("/users", json=payload).status_code == 422


def test_non_integer_id_is_422(client):
    assert client.get("/users/abc").status_code == 422


def test_openapi_lists_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) == {"/", "/users", "/users/{user_id}"}
