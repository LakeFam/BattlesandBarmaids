# Battles and Barmaids: Flask REST API
# Serves the game's world catalog and player saves over HTTP. Only imports
# database.py, so it doesn't need pygame or a terminal like main.py does.
from flask import Flask, abort, jsonify, request, url_for
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from werkzeug.exceptions import HTTPException

from database import (
    ADVENTURER_CLASSES, BARMAID_CLASSES, STARTING_GOLD, STARTING_PANTRY_QTY,
    ChapterRow, EquipmentRow, ItemRow, MonsterRow, PlayerAdventurerRow,
    PlayerInventoryRow, PlayerRow, QuestDropRow, QuestRow, ZoneRow, engine,
)

app = Flask(__name__)
app.json.sort_keys = False    # keep fields in the order they're built below
app.json.ensure_ascii = False  # send emoji as-is instead of \u escapes

EQUIPMENT_TYPES = ("weapon", "armor", "both")
EQUIPMENT_TIERS = ("novice", "veteran", "elite")
EQUIPMENT_RARITIES = ("common", "uncommon", "rare", "shiny")
MAX_NAME_LENGTH = 40

# Every error (including Flask's own 404/405) comes back as {"error": "..."}.
@app.errorhandler(HTTPException)
def handle_http_error(err):
    return jsonify(error=err.description), err.code

# --- Request helpers ---

# Returns the request's JSON body, or a 422 if it isn't a JSON object.
def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(422, "Request body must be a JSON object (send Content-Type: application/json).")
    return body

# Reads an optional query parameter, rejecting values outside `allowed`.
def query_choice(name, allowed):
    value = request.args.get(name)
    if value is not None and value not in allowed:
        abort(422, f"{name} must be one of: {', '.join(allowed)}.")
    return value

# Reads an optional integer query parameter.
def query_int(name):
    value = request.args.get(name)
    if value is None:
        return None
    if not value.isdigit():
        abort(422, f"{name} must be a whole number.")
    return int(value)

# bool is a subclass of int in Python, so True/False are ruled out explicitly.
def is_positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0

def get_player_or_404(session, barmaid_name, lock=False):
    query = select(PlayerRow).where(PlayerRow.barmaid_name == barmaid_name)
    if lock:
        query = query.with_for_update()  # stops two purchases from spending the same gold
    player = session.execute(query).scalar_one_or_none()
    if player is None:
        abort(404, f"No save found for barmaid '{barmaid_name}'.")
    return player

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

# Every catalog item with the player's quantity, so items added to the
# catalog after the player last saved show up at 0 (same as database.get_player).
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
        "barmaid_name": player.barmaid_name,
        "barmaid_class": player.barmaid_class,
        "gold": player.gold,
        "barmaid_super_charge": player.barmaid_super_charge,
        "current_zone_nbr": player.current_zone_nbr,
        "updated_at": player.updated_at.isoformat(),
        "pantry": inventory_json(session, player),
    }

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
    body = json_body()
    barmaid_name = body.get("barmaid_name")
    barmaid_class = body.get("barmaid_class")

    if not isinstance(barmaid_name, str) or not barmaid_name.strip():
        abort(422, "barmaid_name is required.")
    barmaid_name = barmaid_name.strip()
    if len(barmaid_name) > MAX_NAME_LENGTH:
        abort(422, f"barmaid_name can be at most {MAX_NAME_LENGTH} characters.")
    if "/" in barmaid_name:
        abort(422, "barmaid_name can't contain '/', since it's used in the URL.")
    if barmaid_class not in BARMAID_CLASSES:
        abort(422, f"barmaid_class must be one of: {', '.join(BARMAID_CLASSES)}.")

    with Session(engine) as session:
        player = PlayerRow(
            barmaid_name=barmaid_name,
            barmaid_class=barmaid_class,
            gold=STARTING_GOLD,
            barmaid_super_charge=0,
            current_zone_nbr=1,
        )
        session.add(player)
        try:
            session.flush()  # assigns player.player_nbr; fails here if the name is taken
        except IntegrityError:
            abort(409, f"A save named '{barmaid_name}' already exists.")

        for item_nbr in session.execute(select(ItemRow.item_nbr)).scalars():
            session.add(PlayerInventoryRow(
                player_nbr=player.player_nbr, item_nbr=item_nbr, quantity=STARTING_PANTRY_QTY,
            ))
        session.commit()

        response = jsonify(player_json(session, player))
        response.status_code = 201
        response.headers["Location"] = url_for("get_player", barmaid_name=barmaid_name)
        return response

@app.get("/players/<barmaid_name>")
def get_player(barmaid_name):
    with Session(engine) as session:
        return jsonify(player_json(session, get_player_or_404(session, barmaid_name)))

# player_inventory and player_adventurers rows go with it (ON DELETE CASCADE).
@app.delete("/players/<barmaid_name>")
def delete_player(barmaid_name):
    with Session(engine) as session:
        session.delete(get_player_or_404(session, barmaid_name))
        session.commit()
    return "", 204

@app.get("/players/<barmaid_name>/inventory")
def get_inventory(barmaid_name):
    with Session(engine) as session:
        return jsonify(inventory_json(session, get_player_or_404(session, barmaid_name)))

@app.post("/players/<barmaid_name>/purchases")
def purchase(barmaid_name):
    body = json_body()
    item_nbr = body.get("item_nbr")
    quantity = body.get("quantity", 1)
    if not is_positive_int(item_nbr):
        abort(422, "item_nbr must be a positive whole number.")
    if not is_positive_int(quantity):
        abort(422, "quantity must be a positive whole number.")

    with Session(engine) as session:
        player = get_player_or_404(session, barmaid_name, lock=True)
        item = session.get(ItemRow, item_nbr)
        if item is None:
            abort(404, f"Item {item_nbr} not found.")

        total_cost = item.cost * quantity
        if player.gold < total_cost:
            abort(422, f"{quantity}x {item.name} costs {total_cost} gold, but {barmaid_name} only has {player.gold}.")

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

# Every adventurer class, at level 1 with no gear if the player has no row for it yet.
@app.get("/players/<barmaid_name>/adventurers")
def get_adventurers(barmaid_name):
    with Session(engine) as session:
        player = get_player_or_404(session, barmaid_name)
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
