# Shared test setup. The tests run against their own database,
# battles_and_barmaids_test, which is rebuilt from schema.sql at the start of
# every run, so the game's real saves are never touched.
import os
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

# These have to be set before anything imports database.py (which builds its
# engine from DATABASE_URL) or data.py (which starts the pygame mixer).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5434/battles_and_barmaids_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SDL_AUDIODRIVER"] = "dummy"  # sounds "play" silently during tests
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

SCHEMA_SQL = Path(__file__).parent.parent / "schema.sql"

# Runs before any test file is imported. That matters because importing
# entities.py (and so combat.py) reads the ingredient list from the database.
def pytest_configure(config):
    url = make_url(TEST_DATABASE_URL)
    # This database gets dropped, so make sure it isn't the real one.
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

    # schema.sql is many statements in one file. psycopg can run them in a
    # single execute() as long as there are no query parameters.
    libpq_url = url.set(drivername="postgresql").render_as_string(hide_password=False)
    with psycopg.connect(libpq_url) as conn:
        conn.execute(SCHEMA_SQL.read_text(encoding="utf-8"))

# pytest-flask looks for a fixture named `app` and builds its `client`
# fixture from it. Every test that uses it starts with no player saves.
@pytest.fixture
def app():
    import app as api
    import database

    api.app.config["TESTING"] = True
    yield api.app

    # Removing the players also removes their inventory and adventurers (ON DELETE CASCADE).
    with database.engine.begin() as conn:
        conn.execute(text("TRUNCATE players CASCADE"))

# A fresh save for tests that need a player to work with.
@pytest.fixture
def new_player(client):
    response = client.post("/players", json={"barmaid_name": "Bran", "barmaid_class": "Bunhilda"})
    assert response.status_code == 201
    return response.json
