# Quest-run tables in schema.sql.
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import database
import migrate
from database import PlayerRow, QuestRunPatronRow, QuestRunRow

pytestmark = pytest.mark.usefixtures("new_player")

def player_nbr(session):
    return session.execute(select(PlayerRow.player_nbr).where(PlayerRow.barmaid_class == "Bunhilda")).scalar_one()

def add_run(session, **fields):
    run = QuestRunRow(player_nbr=player_nbr(session), quest_nbr=1, rng_seed=1, **fields)
    session.add(run)
    session.flush()
    return run

def add_patron(session, run, **fields):
    stats = {"slot": 1, "adventurer_class": "Paladin", "hp": 60, "max_hp": 60, "attack_power": 8}
    stats.update(fields)
    session.add(QuestRunPatronRow(run_nbr=run.run_nbr, **stats))
    session.flush()

def test_migrations_are_applied_once():
    assert migrate.migrate() == []

def test_new_run_starts_drafting_on_course_one():
    with Session(database.engine) as session:
        run = add_run(session)
        session.refresh(run)

        assert (run.status, run.course, run.round_nbr) == ("drafting", 1, 1)
        assert run.monster_hp is None

def test_player_can_have_only_one_unfinished_run():
    with Session(database.engine) as session:
        add_run(session)

        with pytest.raises(IntegrityError):
            add_run(session, status="in_combat", monster_hp=70, monster_attack=8, monster_speed=4)

def test_finished_runs_do_not_block_a_new_one():
    with Session(database.engine) as session:
        add_run(session, status="won", ended_at=datetime.now())

        add_run(session)

@pytest.mark.parametrize("fields", [
    pytest.param({"status": "lost"}, id="finished without ended_at"),
    pytest.param({"ended_at": datetime.now()}, id="unfinished with ended_at"),
    pytest.param({"status": "in_combat"}, id="in combat without a monster"),
    pytest.param({"course": 4}, id="course out of range"),
])
def test_run_rejects_inconsistent_state(fields):
    with Session(database.engine) as session:
        with pytest.raises(IntegrityError):
            add_run(session, **fields)

@pytest.mark.parametrize("fields", [
    pytest.param({"hp": 61}, id="hp above max"),
    pytest.param({"power_meter": 101}, id="meter above 100"),
    pytest.param({"slot": 6}, id="slot out of range"),
])
def test_patron_rejects_invalid_state(fields):
    with Session(database.engine) as session:
        run = add_run(session)

        with pytest.raises(IntegrityError):
            add_patron(session, run, **fields)

def test_each_class_appears_once_per_run():
    with Session(database.engine) as session:
        run = add_run(session)
        add_patron(session, run)

        with pytest.raises(IntegrityError):
            add_patron(session, run, slot=2)

def test_deleting_a_player_deletes_their_runs(client):
    with Session(database.engine) as session:
        run = add_run(session)
        add_patron(session, run)
        session.commit()

    client.delete("/players/Bunhilda")

    with Session(database.engine) as session:
        assert session.scalars(select(QuestRunRow)).all() == []
        assert session.scalars(select(QuestRunPatronRow)).all() == []
