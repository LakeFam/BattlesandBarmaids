# Terminal client: screen helpers and the combat prompts.
import sys
import time

import combat
from audio import sounds
from entities import POLISH_LABEL, ActionError, cost_text

# Simple way to clear the screen
def clear_screen():
    print("\n" * 100)

# Flashing text for dramatic effect
def flash_text(text, flashes=3, delay=0.2):
    for _ in range(flashes):
        sys.stdout.write(f"\r\033[1;33m{text}\033[0m")
        sys.stdout.flush()
        time.sleep(delay)
        sys.stdout.write("\r" + " " * len(text) + "\r")
        sys.stdout.flush()
        time.sleep(delay)
    print(f"\033[1;33m{text}\033[0m")

# "hp/max HP" in green above 50%, yellow down to 25%, red below.
def hp_text(character):
    left = character.hp / character.max_hp
    if left > 0.5:
        color = "32"
    elif left >= 0.25:
        color = "33"
    else:
        color = "31"
    return f"\033[{color}m{character.hp}/{character.max_hp} HP\033[0m"

# Plays and prints events from the rules.
def show_events(events):
    for e in events:
        for key in e["sounds"]:
            sounds[key].play()
        if e["flash"]:
            flash_text(e["text"])
        else:
            print(e["text"])

# One course. True if the monster dies, False if the party does.
def run_course(course, patrons, monster, player):
    round_num = 1
    while monster.is_alive():
        if combat.party_defeated(patrons):
            return False

        print(f"\n--- BATTLE ROUND {round_num} (Course {course}) ---")
        print(f"Monster: {monster.name} ({monster.hp}/{monster.max_hp} HP)")
        print("Patron Status:")
        for p in patrons:
            if p.is_alive():
                print(f"  - {p.name}: {hp_text(p)} [Appetite Meter: {p.power_meter}%]")
        time.sleep(1)

        barmaid_turn(player, patrons, monster)
        for turn in combat.play_round(patrons, monster):
            show_events(turn)
            time.sleep(1)
        round_num += 1

    return True

# Menu loop until the barmaid takes a valid action.
def barmaid_turn(player, patrons, monster):
    while True:
        print("\n" + "="*40)
        print(f"--- {player.barmaid_name.upper()}'S MOBILE KITCHEN-CART ---")
        print(f"Barmaid Super Charge: {player.barmaid_super_charge}%")
        in_stock = " | ".join(f"{k}: {v}" for k, v in player.pantry.items() if v > 0)
        print(f"Pantry Stock: [{in_stock}]")

        print()
        for i, ability in enumerate(player.abilities, start=1):
            print(f"{i}. {ability['label']} (Cost: {cost_text(ability['cost'])})")
        print(f"{player.polish_choice}. {POLISH_LABEL}")
        if player.barmaid_super_charge >= 100:
            print(f"{player.special_choice}. {player.special['label']} (Cost: {cost_text(player.special['cost'])})")
        else:
            print(f"{player.special_choice}. (Locked, requires 100% Super Charge)")

        raw_choice = input(f"Select hospitality action (1-{player.special_choice}): ")
        if not raw_choice.isdigit():
            print("Invalid choice.")
            continue
        choice = int(raw_choice)

        # Only ask for a target once the ingredients are there.
        target = None
        if 1 <= choice <= len(player.abilities):
            ability = player.abilities[choice - 1]
            if ability["target"] == "patron" and player.check_supplies(ability["cost"]):
                target = choose_patron(patrons)

        try:
            events = player.act(choice, patrons, monster, target)
        except ActionError as err:
            if err.sound:
                sounds[err.sound].play()
            print(err)
            continue

        print()
        show_events(events)
        time.sleep(.5)
        return

def choose_patron(patrons):
    living = [p for p in patrons if p.is_alive()]
    if len(living) == 1:
        return living[0]

    print("\nWho will you slide this across the cart to?")
    for i, p in enumerate(living, start=1):
        print(f"{i}. {p.name} ({hp_text(p)}) [Appetite Meter: {p.power_meter}%]")
    while True:
        choice = input("Select patron number: ")
        if choice in map(str, range(1, len(living) + 1)):
            return living[int(choice) - 1]
        print("Invalid choice. Try again.")
