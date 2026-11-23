"""Packaging sanity checks; the Compose check needs only the docker CLI, no daemon or containers."""

import shutil
import subprocess

import pytest

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_installs_locked_deps_and_runs_service():
    dockerfile = (ROOT / "service" / "Dockerfile").read_text()
    assert "uv sync --locked --no-dev" in dockerfile
    assert "COPY service ./service" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert '"service.main:app"' in dockerfile


def test_dockerignore_ships_only_service_and_lockfiles():
    lines = [l for l in (ROOT / ".dockerignore").read_text().splitlines() if l and not l.startswith("#")]
    assert lines[0] == "**"
    assert set(lines[1:]) == {"!pyproject.toml", "!uv.lock", "!service/", "!service/*.py"}


def test_env_example_has_every_compose_variable():
    keys = {
        line.split("=", 1)[0]
        for line in (ROOT / ".env.example").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    }
    assert {"POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DB_CONN"} <= keys


def test_compose_config_is_valid():
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("docker CLI is not installed")
    if subprocess.run([docker, "compose", "version"], capture_output=True).returncode != 0:
        pytest.skip("docker compose plugin is not available")
    result = subprocess.run(
        [docker, "compose", "--env-file", ".env.example", "-f", "docker-compose.yaml", "config", "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    import json

    config = json.loads(result.stdout)
    app, db = config["services"]["app"], config["services"]["db"]
    assert app["depends_on"]["db"]["condition"] == "service_healthy"
    assert app["environment"]["DB_CONN"] == "postgresql+psycopg://postgres:postgres@db:5432/fastapi_db"
    assert any(p["target"] == 8000 for p in app["ports"])
    assert db["image"] == "postgres:17"
