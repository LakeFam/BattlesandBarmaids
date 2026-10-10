import os
from datetime import datetime

from sqlalchemy import ForeignKey, and_, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# Defaults to the Compose db on localhost:5434.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5434/battles_and_barmaids",
)

engine = create_engine(DATABASE_URL)

# Match the CHECK constraints in schema.sql.
BARMAID_CLASSES = ("Marigold", "Saffron", "Bunhilda")
ADVENTURER_CLASSES = ("Paladin", "Warrior", "Ranger", "Rogue", "Mage")

# New-save defaults.
STARTING_GOLD = 10
STARTING_PANTRY_QTY = 6

# schema.sql defines the tables; these models only describe them for queries.
class Base(DeclarativeBase):
    pass

# "Row" suffix avoids confusion with entities.py's Player and Monster.

class ItemRow(Base):
    __tablename__ = "items"
    item_nbr: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    emoji: Mapped[str]
    cost: Mapped[int]

class ChapterRow(Base):
    __tablename__ = "chapters"
    chapter_nbr: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]

class ZoneRow(Base):
    __tablename__ = "zones"
    zone_nbr: Mapped[int] = mapped_column(primary_key=True)
    chapter_nbr: Mapped[int] = mapped_column(ForeignKey("chapters.chapter_nbr"))
    name: Mapped[str]
    description: Mapped[str]
    tavern_name: Mapped[str]
    culinary_theme: Mapped[str]

class QuestRow(Base):
    __tablename__ = "quests"
    quest_nbr: Mapped[int] = mapped_column(primary_key=True)
    zone_nbr: Mapped[int] = mapped_column(ForeignKey("zones.zone_nbr"))
    name: Mapped[str]
    description: Mapped[str]
    is_boss: Mapped[bool]

class QuestDropRow(Base):
    __tablename__ = "quest_drops"
    quest_nbr: Mapped[int] = mapped_column(ForeignKey("quests.quest_nbr"), primary_key=True)
    item_nbr: Mapped[int] = mapped_column(ForeignKey("items.item_nbr"), primary_key=True)
    quantity: Mapped[int]

class MonsterRow(Base):
    __tablename__ = "monsters"
    quest_nbr: Mapped[int] = mapped_column(ForeignKey("quests.quest_nbr"), primary_key=True)
    course: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    hp: Mapped[int]
    speed: Mapped[int]
    attack: Mapped[int]
    emoji: Mapped[str]
    resistant_damage_type: Mapped[str | None]
    resistant_element: Mapped[str | None]

class PlayerRow(Base):
    __tablename__ = "players"
    player_nbr: Mapped[int] = mapped_column(primary_key=True)
    barmaid_class: Mapped[str]
    gold: Mapped[int]
    barmaid_super_charge: Mapped[int]
    current_zone_nbr: Mapped[int] = mapped_column(ForeignKey("zones.zone_nbr"))
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

class PlayerInventoryRow(Base):
    __tablename__ = "player_inventory"
    player_nbr: Mapped[int] = mapped_column(ForeignKey("players.player_nbr"), primary_key=True)
    item_nbr: Mapped[int] = mapped_column(ForeignKey("items.item_nbr"), primary_key=True)
    quantity: Mapped[int]

class EquipmentRow(Base):
    __tablename__ = "equipment"
    equipment_nbr: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    type: Mapped[str]
    tier: Mapped[str]
    rarity: Mapped[str]
    damage_type: Mapped[str | None]
    element: Mapped[str | None]
    power: Mapped[int]
    cost: Mapped[int]

class PlayerAdventurerRow(Base):
    __tablename__ = "player_adventurers"
    player_nbr: Mapped[int] = mapped_column(ForeignKey("players.player_nbr"), primary_key=True)
    adventurer_class: Mapped[str] = mapped_column(primary_key=True)
    level: Mapped[int]
    weapon_nbr: Mapped[int | None] = mapped_column(ForeignKey("equipment.equipment_nbr"))
    armor_nbr: Mapped[int | None] = mapped_column(ForeignKey("equipment.equipment_nbr"))

# migrations/001_quest_runs.sql
class QuestRunRow(Base):
    __tablename__ = "quest_runs"
    run_nbr: Mapped[int] = mapped_column(primary_key=True)
    player_nbr: Mapped[int] = mapped_column(ForeignKey("players.player_nbr"))
    quest_nbr: Mapped[int] = mapped_column(ForeignKey("quests.quest_nbr"))
    status: Mapped[str] = mapped_column(server_default="drafting")
    course: Mapped[int] = mapped_column(server_default="1")
    round_nbr: Mapped[int] = mapped_column(server_default="1")
    monster_hp: Mapped[int | None]
    monster_attack: Mapped[int | None]
    monster_speed: Mapped[int | None]
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ended_at: Mapped[datetime | None]

class QuestRunPatronRow(Base):
    __tablename__ = "quest_run_patrons"
    run_nbr: Mapped[int] = mapped_column(ForeignKey("quest_runs.run_nbr"), primary_key=True)
    slot: Mapped[int] = mapped_column(primary_key=True)
    adventurer_class: Mapped[str]
    is_drafted: Mapped[bool] = mapped_column(server_default="false")
    hp: Mapped[int]
    max_hp: Mapped[int]
    attack_power: Mapped[int]
    power_meter: Mapped[int] = mapped_column(server_default="0")
    defense_buff: Mapped[int] = mapped_column(server_default="0")
    ignore_def: Mapped[bool] = mapped_column(server_default="false")
    weapon_nbr: Mapped[int | None] = mapped_column(ForeignKey("equipment.equipment_nbr"))
    armor_nbr: Mapped[int | None] = mapped_column(ForeignKey("equipment.equipment_nbr"))

# {"emoji name": cost}
def get_ingredients():
    with Session(engine) as session:
        rows = session.execute(select(ItemRow).order_by(ItemRow.item_nbr)).scalars().all()

    ingredients = {}
    for item in rows:
        ingredients[f"{item.emoji} {item.name}"] = item.cost
    return ingredients

# {quest_nbr: {name, description, zone_nbr, is_boss, drops, enemies}}
def get_quests():
    with Session(engine) as session:
        quest_rows = session.execute(select(QuestRow).order_by(QuestRow.quest_nbr)).scalars().all()
        drop_rows = session.execute(
            select(QuestDropRow.quest_nbr, ItemRow.emoji, ItemRow.name, QuestDropRow.quantity)
            .join(ItemRow, ItemRow.item_nbr == QuestDropRow.item_nbr)
        ).all()
        monster_rows = session.execute(
            select(MonsterRow).order_by(MonsterRow.quest_nbr, MonsterRow.course)
        ).scalars().all()

    quests = {}
    for quest in quest_rows:
        quests[quest.quest_nbr] = {
            "name": quest.name,
            "description": quest.description,
            "zone_nbr": quest.zone_nbr,
            "is_boss": quest.is_boss,
            "drops": {},
            "enemies": {},
        }

    for quest_nbr, emoji, item_name, qty in drop_rows:
        quests[quest_nbr]["drops"][f"{emoji} {item_name}"] = qty

    for monster in monster_rows:
        quests[monster.quest_nbr]["enemies"][monster.course] = {
            "name": monster.name,
            "hp": monster.hp,
            "speed": monster.speed,
            "attack": monster.attack,
            "emoji": monster.emoji,
            "resistant_damage_type": monster.resistant_damage_type,
            "resistant_element": monster.resistant_element,
        }

    return quests

# {zone_nbr: {chapter_nbr, name, description, tavern_name, culinary_theme}}
def get_zones():
    with Session(engine) as session:
        rows = session.execute(select(ZoneRow).order_by(ZoneRow.zone_nbr)).scalars().all()

    zones = {}
    for zone in rows:
        zones[zone.zone_nbr] = {
            "chapter_nbr": zone.chapter_nbr,
            "name": zone.name,
            "description": zone.description,
            "tavern_name": zone.tavern_name,
            "culinary_theme": zone.culinary_theme,
        }
    return zones

# {equipment_nbr: {equipment_nbr, name, type, tier, rarity, damage_type, element, power, cost}}
def get_equipment():
    with Session(engine) as session:
        rows = session.execute(select(EquipmentRow).order_by(EquipmentRow.equipment_nbr)).scalars().all()

    equipment = {}
    for item in rows:
        equipment[item.equipment_nbr] = {
            "equipment_nbr": item.equipment_nbr,
            "name": item.name,
            "type": item.type,
            "tier": item.tier,
            "rarity": item.rarity,
            "damage_type": item.damage_type,
            "element": item.element,
            "power": item.power,
            "cost": item.cost,
        }
    return equipment

# {"emoji name": qty} in item order. New items appear at 0.
def load_pantry(session, player_nbr):
    rows = session.execute(
        select(ItemRow.emoji, ItemRow.name, PlayerInventoryRow.quantity)
        .outerjoin(PlayerInventoryRow, and_(
            PlayerInventoryRow.item_nbr == ItemRow.item_nbr,
            PlayerInventoryRow.player_nbr == player_nbr,
        ))
        .order_by(ItemRow.item_nbr)
    ).all()
    return {f"{emoji} {name}": qty or 0 for emoji, name, qty in rows}

# Save as {gold, barmaid_super_charge, current_zone_nbr, pantry}, or None.
def get_player(barmaid_class):
    with Session(engine) as session:
        player = session.execute(
            select(PlayerRow).where(PlayerRow.barmaid_class == barmaid_class)
        ).scalar_one_or_none()
        if player is None:
            return None

        return {
            "gold": player.gold,
            "barmaid_super_charge": player.barmaid_super_charge,
            "current_zone_nbr": player.current_zone_nbr,
            "pantry": load_pantry(session, player.player_nbr),
        }

# {"emoji name": item_nbr}
def get_item_nbrs(session):
    rows = session.execute(select(ItemRow.item_nbr, ItemRow.emoji, ItemRow.name)).all()
    return {f"{emoji} {name}": item_nbr for item_nbr, emoji, name in rows}

# Copies an entities.Player's progress onto its PlayerRow and inventory. The caller commits.
def store_player(session, row, player):
    row.gold = player.gold
    row.barmaid_super_charge = player.barmaid_super_charge
    row.current_zone_nbr = player.current_zone_nbr

    item_nbrs = get_item_nbrs(session)
    inventory = {
        inv.item_nbr: inv
        for inv in session.execute(
            select(PlayerInventoryRow).where(PlayerInventoryRow.player_nbr == row.player_nbr)
        ).scalars()
    }
    for item, qty in player.pantry.items():
        item_nbr = item_nbrs[item]
        # Item added since this player last saved.
        if item_nbr not in inventory:
            session.add(PlayerInventoryRow(player_nbr=row.player_nbr, item_nbr=item_nbr, quantity=qty))
        else:
            inventory[item_nbr].quantity = qty

# Inserts a new save.
def create_player(player):
    with Session(engine) as session:
        row = PlayerRow(
            barmaid_class=player.barmaid_class,
            gold=player.gold,
            barmaid_super_charge=player.barmaid_super_charge,
            current_zone_nbr=player.current_zone_nbr,
        )
        session.add(row)
        session.flush()  # assigns row.player_nbr
        store_player(session, row, player)
        session.commit()

# Updates an existing save.
def save_player(player):
    with Session(engine) as session:
        row = session.execute(
            select(PlayerRow).where(PlayerRow.barmaid_class == player.barmaid_class)
        ).scalar_one()
        store_player(session, row, player)
        session.commit()
