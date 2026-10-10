# Tests use their own database, rebuilt from schema.sql every run.
import os
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

# Must be set before database.py is imported.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5434/battles_and_barmaids_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

SCHEMA_SQL = Path(__file__).parent.parent / "schema.sql"

# Runs before test modules import entities.py, which queries the database.
def pytest_configure(config):
    url = make_url(TEST_DATABASE_URL)
    # Never drop a non-test database.
    if not url.database.endswith("_test"):
        pytest.exit(f"TEST_DATABASE_URL must point at a *_test database, not '{url.database}'.")

    server = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with server.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    except OperationalError:
        pytest.exit(f"Can't reach Postgres at {url.host}:{url.port}. Start the database first: docker compose up -d db")
    finally:
        server.dispose()

    # Multi-statement execute() works without parameters.
    libpq_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(libpq_url) as conn:
        conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))

# pytest-flask builds `client` from this fixture.
@pytest.fixture
def app():
    import app as api
    import database

    api.app.config["TESTING"] = True
    yield api.app

    # Cascades to inventory and adventurers.
    with database.engine.begin() as conn:
        conn.execute(text("TRUNCATE players CASCADE"))

@pytest.fixture
def new_player(client):
    response = client.post("/players", json={"barmaid_class": "Bunhilda"})
    assert response.status_code == 201
    return response.json
