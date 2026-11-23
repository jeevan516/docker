# APIs, PostgreSQL and Docker: project notes

_Last updated: 23 Nov 2026_

## Project
**APIs, PostgreSQL and Docker.** Build a small user-directory web service step by step:
from JSON basics to a typed FastAPI CRUD API on PostgreSQL, then package it with Docker and
run the whole stack with Docker Compose.

- **Data:** no dataset. Users (name, email) created through the API; a seed script makes
  synthetic users on reserved example domains. The JSON notebook uses sample records and
  the public JSONPlaceholder todos API.
- **Stack:** FastAPI + Pydantic schemas, SQLAlchemy, PostgreSQL 17, Docker (image built with
  `uv` on `python:3.13-slim-bookworm`), Docker Compose with health checks.

## Approach
1. **JSON** (notebook 01): `dumps`/`loads` round trips, read and write JSON files, fetch
   todos from an API, validate records with Pydantic; finished the practice exercise.
2. **Docker basics** (guide 02): run Postgres from the official image with a named volume
   and inspect it with `docker exec ... psql`.
3. **FastAPI** (guide 03, `service/`): typed request and response models and CRUD endpoints
   for `/users` (list, get, create, update, delete) with 404 and duplicate-email checks.
4. **API in Docker** (guide 04, `service/Dockerfile`): build the API image and connect it to
   Postgres over a user-defined network.
5. **Docker Compose** (guide 05, `docker-compose.yaml`): `db` and `app` services; the app
   waits until Postgres is healthy, and has its own health check on `/`.
6. **Extras:** documented the service code, added `scripts/seed_users.py` (default 50 users,
   seed 42, sent through `POST /users`), PowerShell tips in the README.
7. **Tests:** pytest suite in `tests/` (`uv run pytest -q`): every CRUD endpoint through
   FastAPI's TestClient on a throwaway SQLite database (201/200/204, 404, 409 duplicate email,
   422 validation), the race-condition guard that turns a PostgreSQL unique violation into 409,
   the seed script (deterministic users, rerun skips existing), Dockerfile/.dockerignore checks
   and `docker compose config` (skipped when the docker CLI is missing; no containers started).

## Results
| Check | Result |
|---|---|
| JSON notebook | **9 of 10** code cells have saved outputs; all run without errors |
| API example in the notebook | status **200**, **200** todos fetched; parsed objects match |
| Practice exercise | **5** todos validated with Pydantic and saved to `data/validated_todos.json` |
| CRUD API | 6 routes: health `/` plus 5 `/users` endpoints |
| Automated tests (23 Nov 2026) | **33 passed** (`uv run pytest -q`, under 1 s) |
| Docker / Compose run | not recorded in the repo |

## Future engineering
- Run the same tests against PostgreSQL (service container) to cover the real unique-index error path.
- Use Alembic migrations instead of creating tables at startup.
- Add a GitHub Actions workflow that builds the image and checks that the stack starts.
- Add paging and search to `GET /users` for larger seeded data.
- Record a Compose run (health check passing, seed script output) in the README.

## Update log
- 26 Oct 2026: repository created; JSON practice finished, service code documented, seed script added.
- 29 Oct 2026: notebook switched to the project kernel; PowerShell tips added to the README.
- 30 Oct 2026: small updates to `.env.example` and VS Code settings.
- 15 Nov 2026: project notes created.
- 16 Nov 2026: presentation deck added: presentation/apis-postgres-docker.pptx (9 slides).
- 23 Nov 2026: pytest suite added (33 tests: CRUD API on SQLite, conflict handling, seed script, Docker/Compose config) and `.warden.yml` test_cmd.
