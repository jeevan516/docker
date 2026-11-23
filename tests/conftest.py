"""Point the service at a throwaway SQLite file before it is imported.

service/database.py reads DB_CONN at import time (load_dotenv does not override
a variable that is already set), and service/main.py creates the tables at
import, so this must happen before any test imports the service.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

_DB_DIR = tempfile.mkdtemp(prefix="user-api-tests-")
atexit.register(shutil.rmtree, _DB_DIR, ignore_errors=True)
os.environ["DB_CONN"] = f"sqlite:///{Path(_DB_DIR) / 'users.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from service import models  # noqa: E402
from service.database import SessionLocal  # noqa: E402
from service.main import app  # noqa: E402


@pytest.fixture
def client():
    with SessionLocal() as session:
        session.query(models.User).delete()
        session.commit()
    return TestClient(app)
