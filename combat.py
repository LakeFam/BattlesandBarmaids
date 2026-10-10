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

def serve_course(course, monster):
    return [event(f"🍽️  --- COURSE {course} OF 3: {monster.name} IS SERVED! --- 🍽️", flash=True)]

# After a course's monster dies; heals the party if another course follows.
def clear_course(course, patrons):
    events = [event(f"✨ Course {course} cleared!")]
    if course < 3:
        heal_between_courses(patrons)
        events.append(event("You quickly toss a healing snack to your patrons as the next course arrives...", "next_course"))
    return events

# Gold tips, the quest's drops, and the next zone after a boss.
def win_quest(player, quest, zones):
    reward_gold = random.randint(30, 60)
    player.gold += reward_gold
    events = [
        event("🎉 ALL 3 COURSES CLEARED! THE MEAL ENDS IN VICTORY! 🎉", "quest_victory", "barmaid_victory", flash=True),
        event(f"Collected {reward_gold} Gold tips into the till!"),
        event("Ingredients Harvested for the Pantry:"),
    ]
    for item, amount in quest["drops"].items():
        player.pantry[item] += amount
        events.append(event(f"+ {amount}x {item}"))
    if quest["is_boss"]:
        events += advance_zone(player, zones)
    return events

def lose_quest(player):
    player.gold = max(0, player.gold - 15)
    return [
        event("💀 KITCHEN DISASTER! YOUR PARTY WAS OVERWHELMED! 💀", "quest_failed", flash=True),
        event("Your party couldn't stomach all three courses!"),
    ]

# Moves the player to the first zone of the next chapter, if there is one.
def advance_zone(player, zones):
    current_chapter = zones[player.current_zone_nbr]["chapter_nbr"]
    next_zone_nbr = None
    next_chapter = None
    for zone_nbr, zone in zones.items():
        if zone["chapter_nbr"] > current_chapter:
            if next_chapter is None or zone["chapter_nbr"] < next_chapter:
                next_chapter = zone["chapter_nbr"]
                next_zone_nbr = zone_nbr

    if next_zone_nbr is None:
        return [event("🏆 There are no further regions to conquer... yet!", flash=True)]

    player.current_zone_nbr = next_zone_nbr
    return [event(f"🗺️  The road now leads onward to {zones[next_zone_nbr]['name']}!", flash=True)]
