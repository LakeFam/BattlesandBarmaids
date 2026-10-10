# Quest runs for the API: loads a saved run as game objects, plays it with the shared rules, and saves it back.
import functools
import random
import secrets

from sqlalchemy import func, select

import combat
import database
from database import QuestRunPatronRow, QuestRunRow
from entities import ActionError, Monster, Patron, Player, roll_equipment

BARMAID_CLASSES = {cls.__name__: cls for cls in Player.classes}
PATRON_CLASSES = {cls.__name__: cls for cls in Patron.classes}
RUN_STATUSES = ("drafting", "in_combat", "won", "lost", "abandoned")
OPEN_STATUSES = ("drafting", "in_combat")

# Catalogs load on first use, then stay cached.
@functools.cache
def quests():
    return database.get_quests()

@functools.cache
def zones():
    return database.get_zones()

@functools.cache
def equipment():
    return database.get_equipment()

def new_seed():
    return secrets.randbits(53)

# Each round gets its own dice, so it replays the same no matter when it's played.
def round_rng(run, round_nbr):
    return random.Random(f"{run.rng_seed}:{round_nbr}")

# A quest is open if its zone's chapter is no later than the player's.
def zone_reached(current_zone_nbr, quest_zone_nbr):
    return zones()[quest_zone_nbr]["chapter_nbr"] <= zones()[current_zone_nbr]["chapter_nbr"]

def patron_rows(session, run, drafted_only=False):
    query = select(QuestRunPatronRow).where(QuestRunPatronRow.run_nbr == run.run_nbr).order_by(QuestRunPatronRow.slot)
    if drafted_only:
        query = query.where(QuestRunPatronRow.is_drafted)
    return session.execute(query).scalars().all()

# New run with a pool of 5 patrons in rolled gear. The caller commits.
def start_run(session, player_row, quest_nbr):
    run = QuestRunRow(player_nbr=player_row.player_nbr, quest_nbr=quest_nbr, rng_seed=new_seed())
    session.add(run)
    session.flush()  # assigns run.run_nbr

    pool = [cls(cls.name) for cls in Patron.classes]
    roll_equipment(pool, equipment().values(), round_rng(run, 0))  # round 0: the draft pool
    for slot, patron in enumerate(pool, start=1):
        session.add(QuestRunPatronRow(
            run_nbr=run.run_nbr, slot=slot, adventurer_class=type(patron).__name__,
            hp=patron.hp, max_hp=patron.max_hp, attack_power=patron.attack_power,
            weapon_nbr=patron.weapon["equipment_nbr"], armor_nbr=patron.armor["equipment_nbr"],
        ))
    return run

# Drafts 3 slots and serves the first course.
def draft_party(session, run, picks):
    for row in patron_rows(session, run):
        row.is_drafted = row.slot in picks
    run.status = "in_combat"
    monster = Monster.from_enemy(quests()[run.quest_nbr]["enemies"][1])
    save_monster(run, monster)
    return combat.serve_course(1, monster)

def finish(run, status):
    run.status = status
    run.ended_at = func.now()

# One barmaid action plus the rest of the round. Raises ActionError before changing anything.
def play_action(session, run, player_row, action, target_slot=None):
    barmaid = load_barmaid(session, player_row)
    rows = patron_rows(session, run, drafted_only=True)
    patrons = [load_patron(row) for row in rows]
    monster = load_monster(run)

    target = None
    if target_slot is not None:
        by_slot = {row.slot: patron for row, patron in zip(rows, patrons)}
        if target_slot not in by_slot:
            raise ActionError(f"Slot {target_slot} isn't in the party.")
        target = by_slot[target_slot]

    rng = round_rng(run, run.round_nbr)
    events = barmaid.act(action, patrons, monster, target, rng)
    for turn in combat.play_round(patrons, monster, rng):
        events += turn

    quest = quests()[run.quest_nbr]
    if not monster.is_alive():
        events += combat.clear_course(run.course, patrons)
        if run.course < 3:
            run.course += 1
            monster = Monster.from_enemy(quest["enemies"][run.course])
            events += combat.serve_course(run.course, monster)
        else:
            finish(run, "won")
            events += combat.win_quest(barmaid, quest, zones(), rng)
    elif combat.party_defeated(patrons):
        finish(run, "lost")
        events += combat.lose_quest(barmaid)

    # Never resets, so a resent request can't act twice.
    run.round_nbr += 1
    save_monster(run, monster)
    for row, patron in zip(rows, patrons):
        save_patron(row, patron)
    database.store_player(session, player_row, barmaid)
    return events

def load_barmaid(session, player_row):
    barmaid = BARMAID_CLASSES[player_row.barmaid_class]()
    barmaid.gold = player_row.gold
    barmaid.barmaid_super_charge = player_row.barmaid_super_charge
    barmaid.current_zone_nbr = player_row.current_zone_nbr
    barmaid.pantry = database.load_pantry(session, player_row.player_nbr)
    return barmaid

def load_patron(row):
    cls = PATRON_CLASSES[row.adventurer_class]
    patron = cls(cls.name)
    patron.hp = row.hp
    patron.max_hp = row.max_hp
    patron.attack_power = row.attack_power
    patron.power_meter = row.power_meter
    patron.defense_buff = row.defense_buff
    patron.ignore_def = row.ignore_def
    patron.weapon = equipment().get(row.weapon_nbr)
    patron.armor = equipment().get(row.armor_nbr)
    return patron

def save_patron(row, patron):
    row.hp = max(0, patron.hp)  # combat can overshoot below 0
    row.attack_power = patron.attack_power
    row.power_meter = patron.power_meter
    row.defense_buff = patron.defense_buff
    row.ignore_def = patron.ignore_def

def load_monster(run):
    monster = Monster.from_enemy(quests()[run.quest_nbr]["enemies"][run.course])
    monster.hp = run.monster_hp
    monster.attack_power = run.monster_attack
    monster.speed = run.monster_speed
    return monster

def save_monster(run, monster):
    run.monster_hp = max(0, monster.hp)
    run.monster_attack = monster.attack_power
    run.monster_speed = monster.speed
