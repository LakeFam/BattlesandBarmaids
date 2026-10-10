# Catalog endpoints, against the schema.sql seed data.
import pytest

def test_items_lists_seeded_ingredients(client):
    response = client.get("/items")

    assert response.status_code == 200
    assert len(response.json) == 6
    assert response.json[0] == {"item_nbr": 1, "name": "Mighty Malt", "emoji": "🌾", "cost": 5}

def test_zones_can_be_filtered_by_chapter(client):
    response = client.get("/zones?chapter_nbr=2")

    assert response.status_code == 200
    assert [zone["name"] for zone in response.json] == ["The Taplands"]

def test_missing_zone_returns_404(client):
    response = client.get("/zones/99")

    assert response.status_code == 404
    assert response.json == {"error": "Zone 99 not found."}

def test_zone_quests_lists_quests_in_that_zone(client):
    response = client.get("/zones/1/quests")

    assert response.status_code == 200
    assert [quest["quest_nbr"] for quest in response.json] == [1, 2, 3]

def test_quest_includes_three_courses_and_drops(client):
    response = client.get("/quests/3")
    quest = response.json

    assert response.status_code == 200
    assert quest["is_boss"] is True
    assert [monster["course"] for monster in quest["monsters"]] == [1, 2, 3]
    assert quest["monsters"][2]["name"] == "The Baconnator"
    assert quest["monsters"][2]["resistant_element"] == "frosty"
    assert {drop["name"]: drop["quantity"] for drop in quest["drops"]} == {"Watery Onion": 4, "Holy Ham": 6}

def test_equipment_can_be_filtered_by_type(client):
    response = client.get("/equipment?type=armor")

    assert response.status_code == 200
    assert len(response.json) == 2
    assert all(item["type"] == "armor" for item in response.json)

@pytest.mark.parametrize("query", ["type=shield", "tier=legendary", "rarity=epic"])
def test_equipment_rejects_unknown_filter_values(client, query):
    response = client.get(f"/equipment?{query}")

    assert response.status_code == 422
    assert "must be one of" in response.json["error"]

def test_unknown_route_returns_json_404(client):
    response = client.get("/tavern-secrets")

    assert response.status_code == 404
    assert "error" in response.json

def test_wrong_method_returns_json_405(client):
    response = client.put("/items")

    assert response.status_code == 405
    assert "error" in response.json

# `config` comes from pytest-flask.
def test_app_runs_in_testing_mode(config):
    assert config["TESTING"] is True
