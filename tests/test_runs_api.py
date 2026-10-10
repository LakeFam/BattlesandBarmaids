# Quest-run endpoints. Tests set up state in the database so combat outcomes don't depend on luck.
import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

import database
import runs
from database import PlayerInventoryRow, QuestRunPatronRow, QuestRunRow

pytestmark = pytest.mark.usefixtures("new_player")

GHOST_PEPPERONI = 6  # item_nbr

def start(client, quest_nbr=1):
    response = client.post("/players/Bunhilda/runs", json={"quest_nbr": quest_nbr})
    assert response.status_code == 201
    return response.json["run_nbr"]

def start_and_draft(client, quest_nbr=1, picks=(1, 2, 3)):
    run_nbr = start(client, quest_nbr)
    assert client.post(f"/runs/{run_nbr}/party", json={"picks": list(picks)}).status_code == 200
    return run_nbr

def act(client, run_nbr, action, **body):
    round_nbr = client.get(f"/runs/{run_nbr}").json["round_nbr"]
    return client.post(f"/runs/{run_nbr}/actions", json={"round_nbr": round_nbr, "action": action, **body})

def update_run(run_nbr, **fields):
    with Session(database.engine) as session:
        session.execute(update(QuestRunRow).where(QuestRunRow.run_nbr == run_nbr).values(**fields))
        session.commit()

def update_patron(run_nbr, slot, **fields):
    with Session(database.engine) as session:
        session.execute(
            update(QuestRunPatronRow)
            .where(QuestRunPatronRow.run_nbr == run_nbr, QuestRunPatronRow.slot == slot)
            .values(**fields)
        )
        session.commit()

def pantry(client):
    return {item["name"]: item["quantity"] for item in client.get("/players/Bunhilda").json["pantry"]}

# --- Starting and drafting ---

def test_start_run_rolls_a_pool_of_five_patrons(client):
    response = client.post("/players/Bunhilda/runs", json={"quest_nbr": 1})
    run = response.json

    assert response.status_code == 201
    assert response.headers["Location"] == f"/runs/{run['run_nbr']}"
    assert run["status"] == "drafting"
    assert run["monster"] is None
    assert [p["slot"] for p in run["patrons"]] == [1, 2, 3, 4, 5]
    assert all(p["weapon"] and p["armor"] and not p["is_drafted"] for p in run["patrons"])
    assert [a["action"] for a in run["barmaid"]["actions"]] == [1, 2, 3, 4, 5]

def test_second_unfinished_run_conflicts(client):
    start(client)

    assert client.post("/players/Bunhilda/runs", json={"quest_nbr": 2}).status_code == 409

@pytest.mark.parametrize("quest_nbr, status", [("1", 422), (0, 422), (99, 404)])
def test_start_run_rejects_bad_quests(client, quest_nbr, status):
    assert client.post("/players/Bunhilda/runs", json={"quest_nbr": quest_nbr}).status_code == status

def test_quests_beyond_the_players_chapter_are_locked():
    by_chapter = {zone["chapter_nbr"]: zone_nbr for zone_nbr, zone in runs.zones().items()}

    assert runs.zone_reached(by_chapter[1], by_chapter[1])
    assert runs.zone_reached(by_chapter[2], by_chapter[1])
    assert not runs.zone_reached(by_chapter[1], by_chapter[2])

def test_draft_serves_the_first_course(client):
    run_nbr = start(client)

    response = client.post(f"/runs/{run_nbr}/party", json={"picks": [5, 1, 3]})
    run = response.json["run"]

    assert response.status_code == 200
    assert run["status"] == "in_combat"
    assert [p["slot"] for p in run["patrons"] if p["is_drafted"]] == [1, 3, 5]
    assert run["monster"]["name"] == "Lil Nibbler"
    assert run["monster"]["hp"] == run["monster"]["max_hp"] == 70
    assert "COURSE 1 OF 3" in response.json["events"][0]["text"]

@pytest.mark.parametrize("picks", [[1, 2], [1, 1, 2], [1, 2, 6], [True, 2, 3], "123"])
def test_draft_rejects_invalid_picks(client, picks):
    run_nbr = start(client)

    assert client.post(f"/runs/{run_nbr}/party", json={"picks": picks}).status_code == 422

def test_party_can_only_be_drafted_once(client):
    run_nbr = start_and_draft(client)

    assert client.post(f"/runs/{run_nbr}/party", json={"picks": [1, 2, 3]}).status_code == 409

# --- Actions ---

def test_action_before_drafting_conflicts(client):
    run_nbr = start(client)

    assert client.post(f"/runs/{run_nbr}/actions", json={"round_nbr": 1, "action": 4}).status_code == 409

def test_resent_round_is_rejected(client):
    run_nbr = start_and_draft(client)
    update_run(run_nbr, monster_hp=999)  # survives the round
    body = {"round_nbr": 1, "action": 4}

    assert client.post(f"/runs/{run_nbr}/actions", json=body).status_code == 200
    assert client.post(f"/runs/{run_nbr}/actions", json=body).status_code == 409

def test_polish_tumblers_plays_a_round(client):
    run_nbr = start_and_draft(client)
    update_run(run_nbr, monster_hp=999)

    response = act(client, run_nbr, 4)

    assert response.status_code == 200
    assert response.json["run"]["round_nbr"] == 2
    assert "polish a copper mug" in response.json["events"][0]["text"]
    assert sum(pantry(client).values()) == 6 * 6 + 1

def test_unknown_action_is_rejected(client):
    run_nbr = start_and_draft(client)

    response = act(client, run_nbr, 9)

    assert response.status_code == 422
    assert "from 1 to 5" in response.json["error"]
    assert client.get(f"/runs/{run_nbr}").json["round_nbr"] == 1

def test_missing_ingredients_are_rejected(client):
    run_nbr = start_and_draft(client)
    with Session(database.engine) as session:
        session.execute(
            update(PlayerInventoryRow).where(PlayerInventoryRow.item_nbr == GHOST_PEPPERONI).values(quantity=0)
        )
        session.commit()

    response = act(client, run_nbr, 2)  # Ghost Pepperoni Slice

    assert response.status_code == 422
    assert response.json["error"].startswith("Missing ingredients")

@pytest.mark.parametrize("body, status", [
    pytest.param({}, 422, id="no target"),
    pytest.param({"target_slot": 4}, 422, id="target not drafted"),
    pytest.param({"target_slot": 2}, 200, id="drafted target"),
])
def test_patron_ability_needs_a_party_target(client, body, status):
    run_nbr = start_and_draft(client)
    update_run(run_nbr, monster_hp=999)

    assert act(client, run_nbr, 3, **body).status_code == status  # Bar Rag Bandage

def test_killing_the_monster_serves_the_next_course(client):
    run_nbr = start_and_draft(client)
    update_run(run_nbr, monster_hp=1)

    response = act(client, run_nbr, 4)
    run = response.json["run"]

    assert run["status"] == "in_combat"
    assert run["course"] == 2
    assert run["monster"]["name"] == "Ratta Rogue"
    assert run["monster"]["hp"] == 100
    assert any(e["text"] == "✨ Course 1 cleared!" for e in response.json["events"])

def test_clearing_course_three_wins_the_quest(client):
    run_nbr = start_and_draft(client)
    update_run(run_nbr, course=3, monster_hp=1)

    response = act(client, run_nbr, 2)  # leaves Mighty Malt alone
    run = response.json["run"]

    assert run["status"] == "won"
    assert run["ended_at"] is not None
    assert 10 + 30 <= run["barmaid"]["gold"] <= 10 + 60
    assert pantry(client)["Mighty Malt"] == 6 + 4  # quest 1 drop

def test_beating_a_boss_opens_the_next_zone(client):
    run_nbr = start_and_draft(client, quest_nbr=3)
    update_run(run_nbr, course=3, monster_hp=1)

    act(client, run_nbr, 2)

    zone = client.get("/players/Bunhilda").json["current_zone_nbr"]
    assert runs.zones()[zone]["chapter_nbr"] == 2

def test_losing_the_party_loses_the_quest(client):
    run_nbr = start_and_draft(client)
    update_run(run_nbr, monster_hp=999, monster_attack=50)
    update_patron(run_nbr, 1, hp=0)
    update_patron(run_nbr, 2, hp=0)
    update_patron(run_nbr, 3, hp=1)

    response = act(client, run_nbr, 2)
    run = response.json["run"]

    assert run["status"] == "lost"
    assert run["barmaid"]["gold"] == 0  # 10 - 15, floored
    assert all(p["hp"] == 0 for p in run["patrons"] if p["is_drafted"])
    assert act(client, run_nbr, 4).status_code == 409

# --- Abandoning and history ---

def test_abandoned_run_is_kept_and_frees_the_player(client):
    run_nbr = start(client)

    assert client.delete(f"/runs/{run_nbr}").status_code == 204
    run = client.get(f"/runs/{run_nbr}").json
    assert run["status"] == "abandoned"
    assert run["ended_at"] is not None
    assert client.delete(f"/runs/{run_nbr}").status_code == 409
    start(client)

def test_run_history_is_newest_first_and_filterable(client):
    first = start(client)
    client.delete(f"/runs/{first}")
    second = start(client)

    assert [r["run_nbr"] for r in client.get("/players/Bunhilda/runs").json] == [second, first]
    assert [r["run_nbr"] for r in client.get("/players/Bunhilda/runs?status=abandoned").json] == [first]
    assert client.get("/players/Bunhilda/runs?status=sleeping").status_code == 422

def test_missing_run_returns_404(client):
    assert client.get("/runs/999").status_code == 404

def test_runs_are_stored_with_hp_never_below_zero(client):
    run_nbr = start_and_draft(client)
    update_run(run_nbr, monster_hp=1)

    act(client, run_nbr, 4)

    with Session(database.engine) as session:
        hps = session.scalars(select(QuestRunPatronRow.hp).where(QuestRunPatronRow.run_nbr == run_nbr)).all()
    assert all(hp >= 0 for hp in hps)
