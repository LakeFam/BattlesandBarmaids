from datetime import datetime

from sqlalchemy import ForeignKey, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# Fill these in to match your local Postgres server.
HOST = "localhost"
PORT = 5432
DBNAME = "python_fundamentals"
USER = "postgres"
PASSWORD = "changeme"

engine = create_engine(f"postgresql+psycopg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}")

# schema.sql is the source of truth for the actual table definitions
# (constraints, defaults, indexes). These model classes just describe the
# same tables/columns to SQLAlchemy so it can build queries against them —
# they are never used to create or migrate the schema.
class Base(DeclarativeBase):
    pass

# Named with a "Row" suffix since entities.py already has its own Player
# and Monster classes for in-memory game state — these classes represent
# persisted database rows instead, and the two should not be confused.

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
    barmaid_name: Mapped[str]
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

# Returns the ingredient catalog as {"emoji name": cost}, same shape as the old INGREDIENTS dict.
def get_ingredients():
    with Session(engine) as session:
        rows = session.execute(select(ItemRow).order_by(ItemRow.item_nbr)).scalars().all()

    ingredients = {}
    for item in rows:
        ingredients[f"{item.emoji} {item.name}"] = item.cost
    return ingredients

# Returns the quest catalog as {quest_nbr: {name, description, zone_nbr, is_boss, drops, enemies}},
# same shape as the old QUESTS dict, plus zone_nbr/is_boss for zone progression.
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

# Returns the zone catalog as {zone_nbr: {chapter_nbr, name, description, tavern_name, culinary_theme}}.
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

# Returns the equipment catalog as {equipment_nbr: {name, type, tier, rarity, damage_type, element, power, cost}}.
def get_equipment():
    with Session(engine) as session:
        rows = session.execute(select(EquipmentRow).order_by(EquipmentRow.equipment_nbr)).scalars().all()

    equipment = {}
    for item in rows:
        equipment[item.equipment_nbr] = {
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

# Returns {gold, barmaid_super_charge, current_zone_nbr, pantry} for a saved barmaid, or None if no save exists.
# Any item added to the catalog after this barmaid last saved is backfilled into the pantry at 0.
def get_player(barmaid_name):
    with Session(engine) as session:
        player = session.execute(
            select(PlayerRow).where(PlayerRow.barmaid_name == barmaid_name)
        ).scalar_one_or_none()
        if player is None:
            return None

        inventory_rows = session.execute(
            select(ItemRow.emoji, ItemRow.name, PlayerInventoryRow.quantity)
            .join(ItemRow, ItemRow.item_nbr == PlayerInventoryRow.item_nbr)
            .where(PlayerInventoryRow.player_nbr == player.player_nbr)
        ).all()
        all_items = session.execute(select(ItemRow.emoji, ItemRow.name)).all()

        pantry = {}
        for emoji, name, qty in inventory_rows:
            pantry[f"{emoji} {name}"] = qty
        for emoji, name in all_items:
            pantry.setdefault(f"{emoji} {name}", 0)

        return {
            "gold": player.gold,
            "barmaid_super_charge": player.barmaid_super_charge,
            "current_zone_nbr": player.current_zone_nbr,
            "pantry": pantry,
        }

# Inserts a brand-new save row for a Player that has no existing save yet.
def create_player(player):
    with Session(engine) as session:
        row = PlayerRow(
            barmaid_name=player.barmaid_name,
            gold=player.gold,
            barmaid_super_charge=player.barmaid_super_charge,
            current_zone_nbr=player.current_zone_nbr,
        )
        session.add(row)
        session.flush()  # assigns row.player_nbr so the inventory rows below can reference it

        for item, qty in player.pantry.items():
            name = item.split(" ", 1)[1]
            item_row = session.execute(select(ItemRow).where(ItemRow.name == name)).scalar_one()
            session.add(PlayerInventoryRow(player_nbr=row.player_nbr, item_nbr=item_row.item_nbr, quantity=qty))

        session.commit()

# Updates an existing save row to match the Player's current gold/charge/zone/pantry.
def save_player(player):
    with Session(engine) as session:
        row = session.execute(
            select(PlayerRow).where(PlayerRow.barmaid_name == player.barmaid_name)
        ).scalar_one()
        row.gold = player.gold
        row.barmaid_super_charge = player.barmaid_super_charge
        row.current_zone_nbr = player.current_zone_nbr

        for item, qty in player.pantry.items():
            name = item.split(" ", 1)[1]
            item_row = session.execute(select(ItemRow).where(ItemRow.name == name)).scalar_one()
            inventory_row = session.execute(
                select(PlayerInventoryRow).where(
                    PlayerInventoryRow.player_nbr == row.player_nbr,
                    PlayerInventoryRow.item_nbr == item_row.item_nbr,
                )
            ).scalar_one_or_none()
            # A player who saved before this item existed won't have a row for
            # it yet, so it's inserted here instead of updated.
            if inventory_row is None:
                session.add(PlayerInventoryRow(player_nbr=row.player_nbr, item_nbr=item_row.item_nbr, quantity=qty))
            else:
                inventory_row.quantity = qty

        session.commit()
