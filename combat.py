import random
import time

from entities import deal_damage, print_monster_death, sounds

def get_speed(actor):
    return actor["speed"]

# Checks the patron's equipped weapon against the monster's resistances. If either
# the weapon's damage_type or element matches, damage is halved (floored at 1).
def apply_monster_resistance(patron, monster, dmg):
    if patron.weapon is None:
        return dmg, False

    matches = False
    if patron.weapon["damage_type"] is not None and patron.weapon["damage_type"] == monster.resistant_damage_type:
        matches = True
    if patron.weapon["element"] is not None and patron.weapon["element"] == monster.resistant_element:
        matches = True

    if not matches:
        return dmg, False
    return max(1, dmg // 2), True

# Combat loop for a single course. Returns True if the monster was defeated, False if all patrons were defeated.
def run_course(course, patrons, monster, player):
    round_num = 1
    while monster.is_alive():
        living_patrons = [p for p in patrons if p.is_alive()]
        if not living_patrons:
            return False

        print(f"\n--- BATTLE ROUND {round_num} (Course {course}) ---")
        print(f"Monster: {monster.name} ({monster.hp}/{monster.max_hp} HP)")
        print("Patron Status:")
        # Only lists living Patrons
        for p in living_patrons:
            print(f"  - {p.name}: {p.hp}/{p.max_hp} HP [Appetite Meter: {p.power_meter}%]")
        time.sleep(1)

        player.take_turn(patrons, monster)
        #Some randomness to the turn order to make it more dynamic.
        turn_order = [{"type": "monster", "speed": monster.speed + random.randint(-2, 2)}]
        for p in living_patrons:
            turn_order.append({"type": "patron", "ref": p, "speed": p.speed + random.randint(-2, 2)})
        turn_order.sort(key=get_speed, reverse=True)
        # Life checks.
        for actor in turn_order:
            if not any(p.is_alive() for p in patrons) or not monster.is_alive():
                break
            take_turn(actor, patrons, monster)
            time.sleep(1)
        # Increments the round.
        round_num += 1

    return True

# Non-Player turn logic.
def take_turn(actor, patrons, monster):
    living_patrons = [p for p in patrons if p.is_alive()]

    if actor["type"] == "patron" and actor["ref"].is_alive():
        patron = actor["ref"]
        if patron.power_meter >= 100:
            patron.execute_special(monster, living_patrons)
            patron.power_meter = 0
            return

        sounds[patron.attack_sound].play()
        dmg = patron.attack_power
        if patron.weapon is not None:
            dmg += patron.weapon["power"]
        # Nice little logic to make an attack ignore defense, then reset it back to normal.
        if patron.ignore_def:
            dmg += 5
            patron.ignore_def = False
        dmg, resisted = apply_monster_resistance(patron, monster, dmg)
        deal_damage(monster, dmg, "monster_death")
        # A flavor text randomizer to make the combat more dynamic and fun.
        flavor_verb = random.choice(patron.flavor_text)
        print(f"{patron.attack_emoji} {patron.name} {flavor_verb} the {monster.name} for {dmg} damage!")
        if resisted:
            trait = patron.weapon["damage_type"] or patron.weapon["element"]
            print(f"🍽️  {monster.name} is resistant to {trait}! The {patron.weapon['name']} only lands a glancing blow.")
        print_monster_death(monster)
        # Increments the power meter for the Patron.
        patron.power_meter = min(100, patron.power_meter + 25)
    # Monster mash...
    elif actor["type"] == "monster":
        sounds[monster.attack_sound].play()
        weights = []
        # Uses random.choices with weights to select a single patron influenced by their aggro level.
        for p in living_patrons:
            weights.append(p.aggro)
        target = random.choices(living_patrons, weights=weights, k=1)[0]

        armor_power = 0
        if target.armor is not None:
            armor_power = target.armor["power"]
        dmg = max(1, monster.attack_power - target.defense_buff - armor_power)
        deal_damage(target, dmg, "patron_death")

        # A flavor text randomizer to make the combat more dynamic and fun.
        flavor_verb = random.choice(monster.flavor_text)
        print(f"{monster.attack_emoji} {monster.name} {flavor_verb} {target.name} for {dmg} damage!")

        # Checks if the target Patron is dead and prints a death message if so.
        if not target.is_alive():
            print(target.death_message)
        # Decreases the target Patron's defense buff by 1, but not below 0.
        target.defense_buff = max(0, target.defense_buff - 1)
        # Increments the power meter for the Patron attacked.
        target.power_meter = min(100, target.power_meter + 35)
