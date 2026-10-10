# Combat rules, using the game's real classes.
import sys

import pytest

import combat
from entities import ActionError, Bunhilda, Marigold, Monster, Paladin, Ranger, Warrior

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
    barmaid = Bunhilda()  # 6 of each ingredient

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

# --- Barmaid actions ---

def make_party():
    return [Paladin(Paladin.name), Warrior(Warrior.name), Ranger(Ranger.name)]

def test_action_spends_ingredients_and_builds_charge():
    barmaid = Bunhilda()
    monster = make_monster(hp=100)

    events = barmaid.act(1, make_party(), monster)  # Flaming Shot

    assert monster.hp == 88
    assert barmaid.pantry["🌶️ Chilly Peppers"] == 5
    assert barmaid.barmaid_super_charge == 30
    assert events[0]["sounds"] == ["barmaid_fireshot"]

def test_patron_ability_heals_the_chosen_target():
    barmaid = Marigold()
    party = make_party()
    party[1].hp = 10

    barmaid.act(1, party, make_monster(), target=party[1])  # Tend the Wounds

    assert party[1].hp == 35
    assert party[1].defense_buff == 3

def test_patron_ability_needs_a_living_target():
    barmaid = Marigold()
    party = make_party()
    party[0].hp = 0

    with pytest.raises(ActionError):
        barmaid.act(1, party, make_monster(), target=party[0])

def test_missing_ingredients_are_rejected_without_spending():
    barmaid = Bunhilda()
    barmaid.pantry["🍕 Ghost Pepperoni"] = 0

    with pytest.raises(ActionError, match="Missing ingredients"):
        barmaid.act(1, make_party(), make_monster())
    assert barmaid.pantry["🌶️ Chilly Peppers"] == 6

def test_special_needs_full_charge():
    barmaid = Bunhilda()

    with pytest.raises(ActionError) as err:
        barmaid.act(barmaid.special_choice, make_party(), make_monster())
    assert err.value.sound == "barmaid_fail"

def test_special_resets_charge():
    barmaid = Bunhilda()
    barmaid.barmaid_super_charge = 100
    monster = make_monster(hp=100)

    barmaid.act(barmaid.special_choice, make_party(), monster)  # Holy Ham Grenade

    assert monster.hp == 80
    assert barmaid.barmaid_super_charge == 0

def test_polish_tumblers_finds_one_ingredient():
    barmaid = Bunhilda()

    barmaid.act(barmaid.polish_choice, make_party(), make_monster())

    assert sum(barmaid.pantry.values()) == 6 * 6 + 1

def test_unknown_action_is_rejected():
    with pytest.raises(ActionError):
        Bunhilda().act(9, make_party(), make_monster())

# --- Rounds ---

def test_round_gives_every_living_actor_a_turn():
    party = make_party()
    monster = make_monster(hp=500, attack=1)

    turns = combat.play_round(party, monster)

    assert len(turns) == 4  # 3 patrons + monster
    assert all(isinstance(e["text"], str) for turn in turns for e in turn)

def test_round_stops_when_the_monster_dies():
    monster = make_monster(hp=1)

    turns = combat.play_round(make_party(), monster)

    assert not monster.is_alive()
    assert len(turns) <= 2  # the monster may act first

# The API will import these rules, so they must not load pygame.
def test_rules_do_not_load_pygame():
    assert "pygame" not in sys.modules
