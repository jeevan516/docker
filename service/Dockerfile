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
