# Integration tests for player saves and the shop. Each test starts with no
# players (see the `app` fixture in conftest.py).
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import database

def test_create_player_starts_with_gold_and_full_pantry(client):
    response = client.post("/players", json={"barmaid_name": "Bran", "barmaid_class": "Bunhilda"})
    player = response.json

    assert response.status_code == 201
    assert response.headers["Location"] == "/players/Bran"
    assert player["barmaid_class"] == "Bunhilda"
    assert player["gold"] == 10
    assert player["current_zone_nbr"] == 1
    assert len(player["pantry"]) == 6
    assert all(item["quantity"] == 6 for item in player["pantry"])

@pytest.mark.usefixtures("new_player")
def test_create_player_with_taken_name_conflicts(client):
    response = client.post("/players", json={"barmaid_name": "Bran", "barmaid_class": "Saffron"})

    assert response.status_code == 409

@pytest.mark.parametrize("body", [
    pytest.param({"barmaid_class": "Bunhilda"}, id="no name"),
    pytest.param({"barmaid_name": "   ", "barmaid_class": "Bunhilda"}, id="blank name"),
    pytest.param({"barmaid_name": "B" * 41, "barmaid_class": "Bunhilda"}, id="name too long"),
    pytest.param({"barmaid_name": "Bran/Ann", "barmaid_class": "Bunhilda"}, id="slash in name"),
    pytest.param({"barmaid_name": "Bran", "barmaid_class": "Wizard"}, id="unknown class"),
])
def test_create_player_rejects_invalid_input(client, body):
    response = client.post("/players", json=body)

    assert response.status_code == 422

def test_create_player_rejects_non_json_body(client):
    response = client.post("/players", data="Bran")

    assert response.status_code == 422

@pytest.mark.usefixtures("new_player")
def test_get_player_returns_the_save(client):
    response = client.get("/players/Bran")

    assert response.status_code == 200
    assert response.json["barmaid_name"] == "Bran"

def test_get_unknown_player_returns_404(client):
    response = client.get("/players/Nobody")

    assert response.status_code == 404

@pytest.mark.usefixtures("new_player")
def test_delete_player_removes_save_and_inventory(client):
    response = client.delete("/players/Bran")

    assert response.status_code == 204
    assert client.get("/players/Bran").status_code == 404
    # The pantry rows go with the player (ON DELETE CASCADE in schema.sql).
    with Session(database.engine) as session:
        assert session.scalars(select(database.PlayerInventoryRow)).all() == []

@pytest.mark.usefixtures("new_player")
def test_purchase_spends_gold_and_adds_to_inventory(client):
    response = client.post("/players/Bran/purchases", json={"item_nbr": 1, "quantity": 2})

    assert response.status_code == 200
    assert response.json["gold"] == 0  # 2 Mighty Malt at 5 gold each
    assert response.json["inventory"][0]["quantity"] == 8

@pytest.mark.usefixtures("new_player")
def test_purchase_player_cannot_afford_is_rejected(client):
    response = client.post("/players/Bran/purchases", json={"item_nbr": 6, "quantity": 1})

    assert response.status_code == 422
    assert client.get("/players/Bran").json["gold"] == 10

@pytest.mark.parametrize("body", [
    pytest.param({"item_nbr": True}, id="item is a boolean"),
    pytest.param({"item_nbr": 0}, id="item is zero"),
    pytest.param({"item_nbr": "1"}, id="item is a string"),
    pytest.param({"item_nbr": 1, "quantity": -1}, id="negative quantity"),
])
@pytest.mark.usefixtures("new_player")
def test_purchase_rejects_invalid_input(client, body):
    response = client.post("/players/Bran/purchases", json=body)

    assert response.status_code == 422

@pytest.mark.usefixtures("new_player")
def test_purchase_unknown_item_returns_404(client):
    response = client.post("/players/Bran/purchases", json={"item_nbr": 99})

    assert response.status_code == 404

def test_purchase_for_unknown_player_returns_404(client):
    response = client.post("/players/Nobody/purchases", json={"item_nbr": 1})

    assert response.status_code == 404

@pytest.mark.usefixtures("new_player")
def test_adventurers_start_at_level_one_without_gear(client):
    response = client.get("/players/Bran/adventurers")

    assert response.status_code == 200
    adventurers = response.json
    assert [a["adventurer_class"] for a in adventurers] == ["Paladin", "Warrior", "Ranger", "Rogue", "Mage"]
    assert all(a["level"] == 1 for a in adventurers)
    assert all(a["weapon"] is None and a["armor"] is None for a in adventurers)
