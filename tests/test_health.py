# GET /health, used by the Compose healthcheck and CI.
from sqlalchemy import create_engine

import app as api

def test_health_reports_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok", "database": "ok"}

def test_health_reports_an_unreachable_database(client, monkeypatch):
    # Nothing listens on port 1.
    unreachable = create_engine("postgresql+psycopg://nobody:nothing@127.0.0.1:1/none", connect_args={"connect_timeout": 1})
    monkeypatch.setattr(api, "engine", unreachable)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json["database"] == "unreachable"
