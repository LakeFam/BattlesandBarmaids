import random

from entities import event, monster_death_events

def get_speed(actor):
    return actor["speed"]

# Halves damage (min 1) if the monster resists the weapon's damage type or element.
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

def party_defeated(patrons):
    return not any(p.is_alive() for p in patrons)

# Patron and monster turns after the barmaid acts. Returns one event list per turn.
def play_round(patrons, monster):
    # Jitter the turn order a little.
    turn_order = [{"type": "monster", "speed": monster.speed + random.randint(-2, 2)}]
    for p in patrons:
        if p.is_alive():
            turn_order.append({"type": "patron", "ref": p, "speed": p.speed + random.randint(-2, 2)})
    turn_order.sort(key=get_speed, reverse=True)

    turns = []
    for actor in turn_order:
        if party_defeated(patrons) or not monster.is_alive():
            break
        events = take_turn(actor, patrons, monster)
        if events:
            turns.append(events)
    return turns

# Patron or monster turn. Returns its events.
def take_turn(actor, patrons, monster):
    living_patrons = [p for p in patrons if p.is_alive()]

    if actor["type"] == "patron" and actor["ref"].is_alive():
        patron = actor["ref"]
        if patron.power_meter >= 100:
            events = patron.execute_special(monster, living_patrons)
            patron.power_meter = 0
            return events

        dmg = patron.attack_power
        if patron.weapon is not None:
            dmg += patron.weapon["power"]
        # One-time +5 armor-piercing bonus
        if patron.ignore_def:
            dmg += 5
            patron.ignore_def = False
        dmg, resisted = apply_monster_resistance(patron, monster, dmg)
        monster.hp -= dmg
        flavor_verb = random.choice(patron.flavor_text)
        events = [event(f"{patron.attack_emoji} {patron.name} {flavor_verb} the {monster.name} for {dmg} damage!", patron.attack_sound)]
        if resisted:
            trait = patron.weapon["damage_type"] or patron.weapon["element"]
            events.append(event(f"🍽️  {monster.name} is resistant to {trait}! The {patron.weapon['name']} only lands a glancing blow."))
        events += monster_death_events(monster)
        patron.power_meter = min(100, patron.power_meter + 25)
        return events
    # Monster mash...
    elif actor["type"] == "monster":
        weights = []
        # Target weighted by aggro
        for p in living_patrons:
            weights.append(p.aggro)
        target = random.choices(living_patrons, weights=weights, k=1)[0]

        armor_power = 0
        if target.armor is not None:
            armor_power = target.armor["power"]
        dmg = max(1, monster.attack_power - target.defense_buff - armor_power)
        target.hp -= dmg

        flavor_verb = random.choice(monster.flavor_text)
        events = [event(f"{monster.attack_emoji} {monster.name} {flavor_verb} {target.name} for {dmg} damage!", monster.attack_sound)]
        if not target.is_alive():
            events.append(event(target.death_message, "patron_death"))
        target.defense_buff = max(0, target.defense_buff - 1)
        target.power_meter = min(100, target.power_meter + 35)
        return events
    return []

# Healing snack before the next course.
def heal_between_courses(patrons):
    for p in patrons:
        if p.is_alive():
            p.hp = min(p.max_hp, p.hp + 7)
