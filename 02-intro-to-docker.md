# Run PostgreSQL With Docker

[Docker](https://docs.docker.com/get-started/docker-overview/) packages software into isolated containers. In this lesson, the application still runs on your machine, while [PostgreSQL](https://hub.docker.com/_/postgres) runs from its official container image.

This keeps the database version and startup configuration reproducible without installing a PostgreSQL server directly on every participant's computer.

## Core Concepts

| Term | Meaning in this lesson |
| --- | --- |
| **Image** | Read-only template containing PostgreSQL and its runtime |
| **Container** | Running instance created from the image |
| **Port mapping** | Connection from host port `5432` to container port `5432` |
| **Environment variable** | Startup configuration such as database name and credentials |
| **Volume** | Docker-managed storage that survives container replacement |
| **Dockerfile** | Recipe for building a custom image, used later for the API |

We do not need a custom PostgreSQL Dockerfile. The official image already exposes the server entrypoint and accepts the configuration required for this lesson.

## Development Architecture

![Official PostgreSQL image configured and started as a persistent local container](assets/01-docker-image-container-lifecycle.png)

*Diagram based on Docker's official explanations of [images and containers](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-an-image/) and [persistent volumes](https://docs.docker.com/engine/storage/volumes/).*

## Prepare the Environment File

From the repository root, create the local `.env` file if it does not exist yet:

```bash
cp .env.example .env
```

The file contains development-only values:

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fastapi_db
DB_CONN=postgresql+psycopg://postgres:postgres@localhost:5432/fastapi_db
```

Real secrets must stay outside source control. The repository tracks `.env.example` as a documented template and ignores `.env`.

## Start PostgreSQL

Run the official PostgreSQL 17 image and load its variables from `.env`:

```bash
docker run -d --name postgres_cont \
    --env-file .env \
    -v postgres-data:/var/lib/postgresql/data \
    -p 5432:5432 \
    postgres:17
```

| Option | Purpose |
| --- | --- |
| `-d` | Run in the background |
| `--name postgres_cont` | Give the container a stable local name |
| `--env-file .env` | Supply the PostgreSQL initialization values |
| `-v postgres-data:...` | Persist the database in a named volume |
| `-p 5432:5432` | Publish PostgreSQL to the host machine |
| `postgres:17` | Use the official versioned image |

The initialization variables are applied only when the data directory is empty. Reusing `postgres-data` preserves the existing database and credentials.

## Check Readiness

```bash
docker logs postgres_cont
docker exec postgres_cont pg_isready -U postgres -d fastapi_db
```

The readiness command should report that the server is accepting connections.

## Connect With psql

The most portable option is to use the client already available inside the container:

```bash
docker exec -it postgres_cont psql -U postgres -d fastapi_db
```

When `psql` is installed on the host, this equivalent command uses the published port:

```bash
psql -h localhost -p 5432 -U postgres -d fastapi_db
```

## Create and Inspect the Table

The FastAPI service will create the table automatically, but running the SQL manually makes the database contract visible:

```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(320) UNIQUE NOT NULL
);

INSERT INTO users (name, email)
VALUES ('Jane Doe', 'jane.doe@example.com');

SELECT id, name, email FROM users;
```

Useful `psql` commands:

| Command | Purpose |
| --- | --- |
| `\dt` | List tables |
| `\d users` | Describe the `users` table |
| `\q` | Exit `psql` |

Remove the sample row before starting the API lesson if you want an empty initial list:

```sql
DELETE FROM users;
```

## Container Lifecycle

```bash
docker stop postgres_cont
docker start postgres_cont
docker ps -a
```

To replace the container while keeping the database volume:

```bash
docker rm -f postgres_cont
```

Delete the persistent data only when you intentionally want a clean database:

```bash
docker volume rm postgres-data
```

## Checkpoint

**Why does the API use `localhost` when it runs on the host, but a container name when it later runs inside Docker?**

**Answer:** `localhost` always means the current network namespace. On the host it reaches the published database port. Inside the API container it would point back to the API container itself, so containers on a shared Docker network use the database container or service name instead.

## Summary

You started a versioned PostgreSQL image, supplied local configuration outside source control, published its port, persisted its state in a named volume, and verified the server from both sides of the container boundary.
