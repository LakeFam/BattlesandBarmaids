# Battles and Barmaids REST API.
from flask import Flask, abort, jsonify, request, url_for
from sqlalchemy import and_, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from werkzeug.exceptions import HTTPException

import runs
from database import (
    ADVENTURER_CLASSES, BARMAID_CLASSES, STARTING_GOLD, STARTING_PANTRY_QTY,
    ChapterRow, EquipmentRow, ItemRow, MonsterRow, PlayerAdventurerRow,
    PlayerInventoryRow, PlayerRow, QuestDropRow, QuestRow, QuestRunRow, ZoneRow, engine,
)
from entities import POLISH_LABEL, ActionError

app = Flask(__name__)
app.json.sort_keys = False    # keep field order
app.json.ensure_ascii = False  # emoji as-is

EQUIPMENT_TYPES = ("weapon", "armor", "both")
EQUIPMENT_TIERS = ("novice", "veteran", "elite")
EQUIPMENT_RARITIES = ("common", "uncommon", "rare", "shiny")

# All errors as {"error": "..."}.
@app.errorhandler(HTTPException)
def handle_http_error(err):
    return jsonify(error=err.description), err.code

# --- Request helpers ---

# JSON object body, else 422.
def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(422, "Request body must be a JSON object (send Content-Type: application/json).")
    return body

# Optional query param limited to `allowed`.
def query_choice(name, allowed):
    value = request.args.get(name)
    if value is not None and value not in allowed:
        abort(422, f"{name} must be one of: {', '.join(allowed)}.")
    return value

# Optional integer query param.
def query_int(name):
    value = request.args.get(name)
    if value is None:
        return None
    if not value.isdigit():
        abort(422, f"{name} must be a whole number.")
    return int(value)

# Rejects bools (bool subclasses int).
def is_positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0

def get_player_or_404(session, barmaid_class, lock=False):
    query = select(PlayerRow).where(PlayerRow.barmaid_class == barmaid_class)
    if lock:
        query = query.with_for_update()  # no double-spending
    player = session.execute(query).scalar_one_or_none()
    if player is None:
        abort(404, f"No save found for {barmaid_class}.")
    return player

def get_run_or_404(session, run_nbr, lock=False):
    run = session.get(QuestRunRow, run_nbr, with_for_update=lock)
    if run is None:
        abort(404, f"Run {run_nbr} not found.")
    return run

# --- JSON shapes ---

def chapter_json(chapter):
    return {
        "chapter_nbr": chapter.chapter_nbr,
        "name": chapter.name,
        "description": chapter.description,
    }

def zone_json(zone):
    return {
        "zone_nbr": zone.zone_nbr,
        "chapter_nbr": zone.chapter_nbr,
        "name": zone.name,
        "description": zone.description,
        "tavern_name": zone.tavern_name,
        "culinary_theme": zone.culinary_theme,
    }

def quest_json(quest):
    return {
        "quest_nbr": quest.quest_nbr,
        "zone_nbr": quest.zone_nbr,
        "name": quest.name,
        "description": quest.description,
        "is_boss": quest.is_boss,
    }

def monster_json(monster):
    return {
        "course": monster.course,
        "name": monster.name,
        "emoji": monster.emoji,
        "hp": monster.hp,
        "speed": monster.speed,
        "attack": monster.attack,
        "resistant_damage_type": monster.resistant_damage_type,
        "resistant_element": monster.resistant_element,
    }

def item_json(item):
    return {
        "item_nbr": item.item_nbr,
        "name": item.name,
        "emoji": item.emoji,
        "cost": item.cost,
    }

def equipment_json(equipment):
    return {
        "equipment_nbr": equipment.equipment_nbr,
        "name": equipment.name,
        "type": equipment.type,
        "tier": equipment.tier,
        "rarity": equipment.rarity,
        "damage_type": equipment.damage_type,
        "element": equipment.element,
        "power": equipment.power,
        "cost": equipment.cost,
    }

# Every item, at 0 if the player has none.
def inventory_json(session, player):
    rows = session.execute(
        select(ItemRow, PlayerInventoryRow.quantity)
        .outerjoin(PlayerInventoryRow, and_(
            PlayerInventoryRow.item_nbr == ItemRow.item_nbr,
            PlayerInventoryRow.player_nbr == player.player_nbr,
        ))
        .order_by(ItemRow.item_nbr)
    ).all()
    return [
        {"item_nbr": item.item_nbr, "name": item.name, "emoji": item.emoji, "quantity": qty or 0}
        for item, qty in rows
    ]

def player_json(session, player):
    return {
        "barmaid_class": player.barmaid_class,
        "gold": player.gold,
        "barmaid_super_charge": player.barmaid_super_charge,
        "current_zone_nbr": player.current_zone_nbr,
        "updated_at": player.updated_at.isoformat(),
        "pantry": inventory_json(session, player),
    }

# For Docker and CI: is the API up, and can it reach Postgres?
@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        return jsonify(status="unavailable", database="unreachable"), 503
    return jsonify(status="ok", database="ok")

# --- World catalog (read-only) ---

@app.get("/chapters")
def list_chapters():
    with Session(engine) as session:
        chapters = session.execute(select(ChapterRow).order_by(ChapterRow.chapter_nbr)).scalars()
        return jsonify([chapter_json(c) for c in chapters])

@app.get("/zones")
def list_zones():
    chapter_nbr = query_int("chapter_nbr")
    query = select(ZoneRow).order_by(ZoneRow.zone_nbr)
    if chapter_nbr is not None:
        query = query.where(ZoneRow.chapter_nbr == chapter_nbr)
    with Session(engine) as session:
        return jsonify([zone_json(z) for z in session.execute(query).scalars()])

@app.get("/zones/<int:zone_nbr>")
def get_zone(zone_nbr):
    with Session(engine) as session:
        zone = session.get(ZoneRow, zone_nbr)
        if zone is None:
            abort(404, f"Zone {zone_nbr} not found.")
        return jsonify(zone_json(zone))

@app.get("/zones/<int:zone_nbr>/quests")
def list_zone_quests(zone_nbr):
    with Session(engine) as session:
        if session.get(ZoneRow, zone_nbr) is None:
            abort(404, f"Zone {zone_nbr} not found.")
        quests = session.execute(
            select(QuestRow).where(QuestRow.zone_nbr == zone_nbr).order_by(QuestRow.quest_nbr)
        ).scalars()
        return jsonify([quest_json(q) for q in quests])

@app.get("/quests/<int:quest_nbr>")
def get_quest(quest_nbr):
    with Session(engine) as session:
        quest = session.get(QuestRow, quest_nbr)
        if quest is None:
            abort(404, f"Quest {quest_nbr} not found.")
        monsters = session.execute(
            select(MonsterRow).where(MonsterRow.quest_nbr == quest_nbr).order_by(MonsterRow.course)
        ).scalars()
        drops = session.execute(
            select(ItemRow, QuestDropRow.quantity)
            .join(QuestDropRow, QuestDropRow.item_nbr == ItemRow.item_nbr)
            .where(QuestDropRow.quest_nbr == quest_nbr)
            .order_by(ItemRow.item_nbr)
        ).all()

        result = quest_json(quest)
        result["monsters"] = [monster_json(m) for m in monsters]
        result["drops"] = [{**item_json(item), "quantity": qty} for item, qty in drops]
        return jsonify(result)

@app.get("/items")
def list_items():
    with Session(engine) as session:
        items = session.execute(select(ItemRow).order_by(ItemRow.item_nbr)).scalars()
        return jsonify([item_json(i) for i in items])

@app.get("/equipment")
def list_equipment():
    equipment_type = query_choice("type", EQUIPMENT_TYPES)
    tier = query_choice("tier", EQUIPMENT_TIERS)
    rarity = query_choice("rarity", EQUIPMENT_RARITIES)

    query = select(EquipmentRow).order_by(EquipmentRow.equipment_nbr)
    if equipment_type is not None:
        query = query.where(EquipmentRow.type == equipment_type)
    if tier is not None:
        query = query.where(EquipmentRow.tier == tier)
    if rarity is not None:
        query = query.where(EquipmentRow.rarity == rarity)
    with Session(engine) as session:
        return jsonify([equipment_json(e) for e in session.execute(query).scalars()])

# --- Players ---

@app.post("/players")
def create_player():
    barmaid_class = json_body().get("barmaid_class")
    if barmaid_class not in BARMAID_CLASSES:
        abort(422, f"barmaid_class must be one of: {', '.join(BARMAID_CLASSES)}.")

    with Session(engine) as session:
        player = PlayerRow(
            barmaid_class=barmaid_class,
            gold=STARTING_GOLD,
            barmaid_super_charge=0,
            current_zone_nbr=1,
        )
        session.add(player)
        try:
            session.flush()  # raises if this barmaid already has a save
        except IntegrityError:
            abort(409, f"{barmaid_class} already has a save.")

        for item_nbr in session.execute(select(ItemRow.item_nbr)).scalars():
            session.add(PlayerInventoryRow(
                player_nbr=player.player_nbr, item_nbr=item_nbr, quantity=STARTING_PANTRY_QTY,
            ))
        session.commit()

        response = jsonify(player_json(session, player))
        response.status_code = 201
        response.headers["Location"] = url_for("get_player", barmaid_class=barmaid_class)
        return response

@app.get("/players/<barmaid_class>")
def get_player(barmaid_class):
    with Session(engine) as session:
        return jsonify(player_json(session, get_player_or_404(session, barmaid_class)))

# Inventory and adventurers cascade.
@app.delete("/players/<barmaid_class>")
def delete_player(barmaid_class):
    with Session(engine) as session:
        session.delete(get_player_or_404(session, barmaid_class))
        session.commit()
    return "", 204

@app.get("/players/<barmaid_class>/inventory")
def get_inventory(barmaid_class):
    with Session(engine) as session:
        return jsonify(inventory_json(session, get_player_or_404(session, barmaid_class)))

@app.post("/players/<barmaid_class>/purchases")
def purchase(barmaid_class):
    body = json_body()
    item_nbr = body.get("item_nbr")
    quantity = body.get("quantity", 1)
    if not is_positive_int(item_nbr):
        abort(422, "item_nbr must be a positive whole number.")
    if not is_positive_int(quantity):
        abort(422, "quantity must be a positive whole number.")

    with Session(engine) as session:
        player = get_player_or_404(session, barmaid_class, lock=True)
        item = session.get(ItemRow, item_nbr)
        if item is None:
            abort(404, f"Item {item_nbr} not found.")

        total_cost = item.cost * quantity
        if player.gold < total_cost:
            abort(422, f"{quantity}x {item.name} costs {total_cost} gold, but {barmaid_class} only has {player.gold}.")

        player.gold -= total_cost
        inventory_row = session.get(PlayerInventoryRow, (player.player_nbr, item_nbr))
        if inventory_row is None:
            session.add(PlayerInventoryRow(player_nbr=player.player_nbr, item_nbr=item_nbr, quantity=quantity))
        else:
            inventory_row.quantity += quantity
        session.commit()

        return jsonify({
            "purchased": {**item_json(item), "quantity": quantity, "total_cost": total_cost},
            "gold": player.gold,
            "inventory": inventory_json(session, player),
        })

# Classes without a row default to level 1, no gear.
@app.get("/players/<barmaid_class>/adventurers")
def get_adventurers(barmaid_class):
    with Session(engine) as session:
        player = get_player_or_404(session, barmaid_class)
        rows = session.execute(
            select(PlayerAdventurerRow).where(PlayerAdventurerRow.player_nbr == player.player_nbr)
        ).scalars()
        by_class = {row.adventurer_class: row for row in rows}

        def gear(equipment_nbr):
            if equipment_nbr is None:
                return None
            return equipment_json(session.get(EquipmentRow, equipment_nbr))

        adventurers = []
        for adventurer_class in ADVENTURER_CLASSES:
            row = by_class.get(adventurer_class)
            adventurers.append({
                "adventurer_class": adventurer_class,
                "level": row.level if row else 1,
                "weapon": gear(row.weapon_nbr) if row else None,
                "armor": gear(row.armor_nbr) if row else None,
            })
        return jsonify(adventurers)

# --- Quest runs ---

def iso(timestamp):
    return timestamp.isoformat() if timestamp else None

def cost_json(cost):
    return [{"item": item, "quantity": qty} for item, qty in cost.items()]

# The barmaid's numbered actions for POST /runs/<run_nbr>/actions.
def barmaid_actions_json(player):
    barmaid = runs.BARMAID_CLASSES[player.barmaid_class]()
    actions = [
        {"action": i, "label": a["label"], "target": a["target"], "cost": cost_json(a["cost"])}
        for i, a in enumerate(barmaid.abilities, start=1)
    ]
    actions.append({"action": barmaid.polish_choice, "label": POLISH_LABEL, "target": None, "cost": []})
    actions.append({
        "action": barmaid.special_choice, "label": barmaid.special["label"], "target": barmaid.special["target"],
        "cost": cost_json(barmaid.special["cost"]), "requires_full_charge": True,
    })
    return actions

def run_patron_json(row, regulars):
    return {
        "slot": row.slot,
        "adventurer_class": row.adventurer_class,
        "name": runs.PATRON_CLASSES[row.adventurer_class].name,
        "is_regular": row.adventurer_class in regulars,
        "is_drafted": row.is_drafted,
        "hp": row.hp,
        "max_hp": row.max_hp,
        "attack_power": row.attack_power,
        "power_meter": row.power_meter,
        "defense_buff": row.defense_buff,
        "double_strike": row.double_strike,
        "weapon": runs.equipment().get(row.weapon_nbr),
        "armor": runs.equipment().get(row.armor_nbr),
    }

def run_summary_json(run):
    return {
        "run_nbr": run.run_nbr,
        "quest_nbr": run.quest_nbr,
        "quest_name": runs.quests()[run.quest_nbr]["name"],
        "status": run.status,
        "course": run.course,
        "round_nbr": run.round_nbr,
        "started_at": iso(run.started_at),
        "ended_at": iso(run.ended_at),
    }

def run_json(session, run):
    player = session.get(PlayerRow, run.player_nbr)
    regulars = runs.BARMAID_CLASSES[player.barmaid_class].regulars
    monster = None
    if run.monster_hp is not None:
        enemy = runs.quests()[run.quest_nbr]["enemies"][run.course]
        monster = {
            "course": run.course,
            "name": enemy["name"],
            "emoji": enemy["emoji"],
            "hp": run.monster_hp,
            "max_hp": enemy["hp"],
            "attack": run.monster_attack,
            "speed": run.monster_speed,
        }
    return {
        **run_summary_json(run),
        "barmaid_class": player.barmaid_class,
        "monster": monster,
        "patrons": [run_patron_json(row, regulars) for row in runs.patron_rows(session, run)],
        "barmaid": {
            "gold": player.gold,
            "super_charge": player.barmaid_super_charge,
            "pantry": inventory_json(session, player),
            "actions": barmaid_actions_json(player),
        },
    }

@app.post("/players/<barmaid_class>/runs")
def start_run(barmaid_class):
    quest_nbr = json_body().get("quest_nbr")
    if not is_positive_int(quest_nbr):
        abort(422, "quest_nbr must be a positive whole number.")

    with Session(engine) as session:
        player = get_player_or_404(session, barmaid_class, lock=True)
        quest = runs.quests().get(quest_nbr)
        if quest is None:
            abort(404, f"Quest {quest_nbr} not found.")
        if not runs.zone_reached(player.current_zone_nbr, quest["zone_nbr"]):
            abort(422, f"{barmaid_class} hasn't reached quest {quest_nbr}'s zone yet.")
        open_run = session.execute(
            select(QuestRunRow)
            .where(QuestRunRow.player_nbr == player.player_nbr, QuestRunRow.status.in_(runs.OPEN_STATUSES))
        ).scalar_one_or_none()
        if open_run is not None:
            abort(409, f"{barmaid_class} already has an unfinished run ({open_run.run_nbr}).")

        run = runs.start_run(session, player, quest_nbr)
        session.commit()

        response = jsonify(run_json(session, run))
        response.status_code = 201
        response.headers["Location"] = url_for("get_run", run_nbr=run.run_nbr)
        return response

# Newest first. Optional ?status=
@app.get("/players/<barmaid_class>/runs")
def list_runs(barmaid_class):
    status = query_choice("status", runs.RUN_STATUSES)
    with Session(engine) as session:
        player = get_player_or_404(session, barmaid_class)
        query = (
            select(QuestRunRow)
            .where(QuestRunRow.player_nbr == player.player_nbr)
            .order_by(QuestRunRow.run_nbr.desc())
        )
        if status is not None:
            query = query.where(QuestRunRow.status == status)
        return jsonify([run_summary_json(r) for r in session.execute(query).scalars()])

@app.get("/runs/<int:run_nbr>")
def get_run(run_nbr):
    with Session(engine) as session:
        return jsonify(run_json(session, get_run_or_404(session, run_nbr)))

@app.post("/runs/<int:run_nbr>/party")
def draft_party(run_nbr):
    picks = json_body().get("picks")
    valid = (
        isinstance(picks, list) and len(picks) == 3 and len(set(picks)) == 3
        and all(is_positive_int(p) and p <= 5 for p in picks)
    )
    if not valid:
        abort(422, "picks must be 3 different slots from 1 to 5.")

    with Session(engine) as session:
        run = get_run_or_404(session, run_nbr, lock=True)
        if run.status != "drafting":
            abort(409, f"Run {run_nbr} is {run.status}, not drafting.")
        events = runs.draft_party(session, run, picks)
        session.commit()
        return jsonify({"events": events, "run": run_json(session, run)})

@app.post("/runs/<int:run_nbr>/actions")
def take_action(run_nbr):
    body = json_body()
    round_nbr = body.get("round_nbr")
    action = body.get("action")
    target_slot = body.get("target_slot")
    if not is_positive_int(round_nbr):
        abort(422, "round_nbr must be a positive whole number.")
    if not is_positive_int(action):
        abort(422, "action must be a positive whole number.")
    if target_slot is not None and not is_positive_int(target_slot):
        abort(422, "target_slot must be a positive whole number.")

    with Session(engine) as session:
        # Lock order run, then player.
        run = get_run_or_404(session, run_nbr, lock=True)
        if run.status != "in_combat":
            abort(409, f"Run {run_nbr} is {run.status}, not in combat.")
        if round_nbr != run.round_nbr:
            abort(409, f"Run {run_nbr} is on round {run.round_nbr}, not {round_nbr}.")

        player = session.get(PlayerRow, run.player_nbr, with_for_update=True)
        try:
            events = runs.play_action(session, run, player, action, target_slot)
        except ActionError as err:
            abort(422, str(err).removeprefix("❌ "))
        session.commit()
        return jsonify({"events": events, "run": run_json(session, run)})

# Kept as "abandoned" for history.
@app.delete("/runs/<int:run_nbr>")
def abandon_run(run_nbr):
    with Session(engine) as session:
        run = get_run_or_404(session, run_nbr, lock=True)
        if run.status not in runs.OPEN_STATUSES:
            abort(409, f"Run {run_nbr} is already {run.status}.")
        runs.finish(run, "abandoned")
        session.commit()
    return "", 204
