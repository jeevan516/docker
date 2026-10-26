# Package FastAPI With Docker

Lesson 2 ran the database in Docker while the API stayed on the host. This lesson packages the Python 3.13 service into its own image, then connects the API and PostgreSQL containers over a [user-defined bridge network](https://docs.docker.com/engine/network/drivers/bridge/).

The manual workflow makes every build, network, environment, and port decision visible before Docker Compose automates them in lesson 5.

## Target Architecture

```mermaid
flowchart LR
    Client["Browser or curl"] -->|"localhost:8000"| API["fastapi_cont"]
    API -->|"postgres_cont:5432"| DB["postgres_cont"]
    API --- Network["api-network"]
    DB --- Network
    DB --> Volume["postgres-data"]
```

Inside a container, `localhost` refers to that same container. The API therefore uses `postgres_cont` as the database hostname on the shared network.

## The API Dockerfile

[`service/Dockerfile`](service/Dockerfile) builds from the repository root so the lockfile and service package are both available:

```Dockerfile
FROM ghcr.io/astral-sh/uv:0.12.6 AS uv
FROM python:3.13-slim-bookworm

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY service ./service

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

| Instruction | Purpose |
| --- | --- |
| `FROM ... uv` | Provide the versioned uv binary from its official image |
| `FROM python:3.13-slim-bookworm` | Use the required Python runtime on a small Debian base |
| `COPY pyproject.toml uv.lock` | Copy dependency metadata before application code for layer caching |
| `uv sync --locked --no-dev` | Install exactly the locked runtime dependencies |
| `COPY service ./service` | Add only the application package after dependencies |
| `uv run --no-sync` | Start Uvicorn without changing the installed environment |

The root [`.dockerignore`](.dockerignore) uses a short allowlist: only `pyproject.toml`, `uv.lock`, and Python files under `service/` enter the build context. Local environments, Git metadata, lessons, tests, generated data, and secrets never reach the builder.

## Build the API Image

Run from the repository root:

```bash
docker build -f service/Dockerfile -t user-directory-api .
```

The final `.` is important. It makes the repository root the build context, allowing Docker to copy `pyproject.toml`, `uv.lock`, and `service/`.

Inspect the result:

```bash
docker image ls user-directory-api
```

## Create the Shared Network

Remove the lesson 2 container if it still exists, then create the network:

```bash
docker rm -f postgres_cont 2>/dev/null || true
docker network create api-network
```

## Start PostgreSQL on the Network

```bash
docker run -d --name postgres_cont \
    --network api-network \
    --env-file .env \
    -v postgres-data:/var/lib/postgresql/data \
    postgres:17
```

The database port does not need to be published for container-to-container traffic. Both services communicate through `api-network`.

Check readiness before starting the API:

```bash
docker exec postgres_cont pg_isready -U postgres -d fastapi_db
```

## Start the API Container

Stop the host-based Uvicorn process from lesson 3 with `Ctrl+C` in its terminal before starting the container. This frees port `8000` for the containerized API.

```bash
docker run -d --name fastapi_cont \
    --network api-network \
    -e DB_CONN='postgresql+psycopg://postgres:postgres@postgres_cont:5432/fastapi_db' \
    -p 8000:8000 \
    user-directory-api
```

The API port is published because the host browser and `curl` need to reach it. The PostgreSQL connection remains private to the Docker network.

## Verify the Running Containers

```bash
docker ps
docker logs fastapi_cont
curl http://localhost:8000/
curl http://localhost:8000/users
```

Open <http://localhost:8000/docs> to exercise the same typed contract through Swagger UI.

Inspect network membership and container configuration:

```bash
docker network inspect api-network
docker inspect fastapi_cont
```

## Clean Up

```bash
docker rm -f fastapi_cont postgres_cont
docker network rm api-network
```

The named `postgres-data` volume is preserved for reuse with the manual Docker workflow. Lesson 5 creates a separate, project-prefixed Compose volume, so its database starts without the records created here.

## Checkpoint

**Why copy `pyproject.toml` and `uv.lock` before copying `service/`?**

**Answer:** Docker can reuse the dependency layer while application code changes. Dependencies are reinstalled only when their metadata changes, which makes repeated builds faster and more predictable.

## Summary

You built a locked Python 3.13 image, kept secrets outside the image, connected two containers by hostname on a private network, and published only the API boundary required by clients.
