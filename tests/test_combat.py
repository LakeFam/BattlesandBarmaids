# Unit tests for the combat rules in combat.py and entities.py, using the
# game's real patron, monster and barmaid classes.
import combat
from entities import Bunhilda, Monster, Paladin, Warrior

SKILLET = {"name": "Cast-Iron Skillet", "damage_type": "tenderize", "element": None, "power": 6}
FROST_TONGS = {"name": "Frosted Ice Tongs", "damage_type": None, "element": "frosty", "power": 8}
OVEN_MITTS = {"name": "Quilted Oven Mitts", "damage_type": None, "element": None, "power": 5}

def make_monster(**overrides):
    stats = {"hp": 100, "speed": 5, "attack": 20}
    stats.update(overrides)
    return Monster("Test Rat", **stats)

# --- Weapon resistance ---

def test_no_weapon_does_full_damage():
    patron = Warrior(Warrior.name)

    assert combat.apply_monster_resistance(patron, make_monster(), 15) == (15, False)

def test_resisted_damage_type_halves_damage():
    patron = Warrior(Warrior.name)
    patron.weapon = SKILLET

    monster = make_monster(resistant_damage_type="tenderize")

    assert combat.apply_monster_resistance(patron, monster, 15) == (7, True)

def test_resisted_element_halves_damage():
    patron = Warrior(Warrior.name)
    patron.weapon = FROST_TONGS

    monster = make_monster(resistant_element="frosty")

    assert combat.apply_monster_resistance(patron, monster, 20) == (10, True)

def test_unresisted_weapon_does_full_damage():
    patron = Warrior(Warrior.name)
    patron.weapon = SKILLET

    monster = make_monster(resistant_element="frosty")

    assert combat.apply_monster_resistance(patron, monster, 15) == (15, False)

def test_resisted_damage_never_drops_below_one():
    patron = Warrior(Warrior.name)
    patron.weapon = SKILLET

    monster = make_monster(resistant_damage_type="tenderize")

    assert combat.apply_monster_resistance(patron, monster, 1) == (1, True)

# --- Turns ---

def test_monster_attack_is_reduced_by_armor():
    patron = Paladin(Paladin.name)  # 60 HP
    patron.armor = OVEN_MITTS
    monster = make_monster(attack=20)

    combat.take_turn({"type": "monster"}, [patron], monster)

    assert patron.hp == 60 - (20 - 5)
    assert patron.power_meter == 35

def test_patron_attack_adds_weapon_power():
    patron = Warrior(Warrior.name)  # attack 11
    patron.weapon = SKILLET
    monster = make_monster(hp=100)

    combat.take_turn({"type": "patron", "ref": patron}, [patron], monster)

    assert monster.hp == 100 - (11 + 6)
    assert patron.power_meter == 25

def test_ignore_defense_adds_five_damage_once():
    patron = Warrior(Warrior.name)
    patron.ignore_def = True
    monster = make_monster(hp=100)

    combat.take_turn({"type": "patron", "ref": patron}, [patron], monster)

    assert monster.hp == 100 - (11 + 5)
    assert patron.ignore_def is False

# --- Barmaid ---

def test_barmaid_has_supplies_for_affordable_cost():
    barmaid = Bunhilda()  # starts with 6 of each ingredient

    assert barmaid.check_supplies({"🍖 Holy Ham": 2}) is True
    assert barmaid.check_supplies({"🍖 Holy Ham": 7}) is False

def test_deduct_supplies_removes_ingredients():
    barmaid = Bunhilda()

    barmaid.deduct_supplies({"🍖 Holy Ham": 2})

    assert barmaid.pantry["🍖 Holy Ham"] == 4

def test_flaming_shot_deals_twelve_damage():
    barmaid = Bunhilda()
    monster = make_monster(hp=100)

    barmaid.flaming_shot(monster)

    assert monster.hp == 88
