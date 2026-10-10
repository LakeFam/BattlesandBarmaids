# Battles and Barmaids: Enter the Taplands
# Python 3.12+ with pygame-ce. Best in a dark terminal.
import random
import time

from rich import print

import combat
import database
import shop
from audio import sounds
from data import FLAGON_ART, TITLE_FLAVOR
from entities import Monster, Patron, Player
from terminal import clear_screen, flash_text, run_course

QUESTS = database.get_quests()
ZONES = database.get_zones()
EQUIPMENT = database.get_equipment()

# True if lst has no duplicates.
def is_unique(lst):
    return len(lst) == len(set(lst))

# Random weapon and armor for each patron.
def roll_equipment(bar_pool):
    weapon_choices = []
    armor_choices = []
    for item in EQUIPMENT.values():
        if item["type"] == "weapon" or item["type"] == "both":
            weapon_choices.append(item)
        if item["type"] == "armor" or item["type"] == "both":
            armor_choices.append(item)

    for patron in bar_pool:
        patron.weapon = random.choice(weapon_choices)
        patron.armor = random.choice(armor_choices)

class GameEngine:
    def __init__(self):
        print("\n--- CHOOSE YOUR BARMAID ---")
        for i, cls in enumerate(Player.classes, start=1):
            print(f"[{i}] {cls.name} - {cls.kit_description}")

        count = len(Player.classes)
        while True:
            choice = input(f"Select your barmaid (1-{count}): ").strip()
            if choice in map(str, range(1, count + 1)):
                break
            print("Invalid choice.")

        self.player = Player.classes[int(choice) - 1]()

        saved = database.get_player(self.player.barmaid_class)
        if saved is None:
            database.create_player(self.player)
        else:
            self.player.gold = saved["gold"]
            self.player.barmaid_super_charge = saved["barmaid_super_charge"]
            self.player.current_zone_nbr = saved["current_zone_nbr"]
            self.player.pantry = saved["pantry"]
            print(f"\nWelcome back, {self.player.barmaid_name}! Loaded your saved tavern.")

    # Main game loop
    def run(self):
        self.show_title_screen()
        quest_nbr = self.phase_1_hub()
        while quest_nbr is not None:
            victory, drops = self.phase_2_dungeon(quest_nbr)
            self.phase_3_resolution(victory, drops, quest_nbr)
            quest_nbr = self.phase_1_hub()

    # Title screen
    def show_title_screen(self):
        sounds["title"].play()
        time.sleep(.2)
        print("\n" + "="*65)
        print("\n⚔️  🍺 🍗  BATTLES AND BARMAIDS: ENTER THE TAPLANDS 🍗 🍺 ⚔️")
        print("\n" + "="*65)
        time.sleep(3)
        print(f"\n{random.choice(TITLE_FLAVOR)}\n")
        print("-" * 65)
        time.sleep(2.6)
        print()
        flash_text("Press [ENTER] to open the tavern doors and start the game...", flashes=0, delay=0.1)
        input()
        print("... Entering the Taplands...")
        sounds["title"].fadeout(6000)
        sounds["quest_combat"].fadeout(6000)
        sounds["tavern_ambience"].play(loops=-1, fade_ms=4000)
        sounds["press_enter"].play()
        sounds["tavern_music"].play(loops=-1)
        time.sleep(6.5)

    # Phase 1: tavern hub (shop, quests, party draft)
    def phase_1_hub(self):
        while True:
            zone = ZONES[self.player.current_zone_nbr]
            clear_screen()
            print(FLAGON_ART)
            print("\n" + "="*50)
            print(f"=== 🍺 🐀 🍖 Enter {zone['tavern_name']} 🍖 🐀 🍺 ===")
            print("="*50)
            print(f"\n📍 {zone['name']} — {zone['culinary_theme']}")
            print(f"\n💰 Gold in Till: {self.player.gold} 💰")

            pantry_summary = " | ".join(f"{k}: {v}" for k, v in self.player.pantry.items())
            print(f"\nPantry Stock: [{pantry_summary}]")
            print("\n1. Visit the Pantry Market (Buy Ingredients)")
            print("2. Review Tonight's Special Menu & Make Reservations.")
            print("3. Lock up the Tavern & Quit")
            choice = input("\nChoose activity (1-3): ")

            if choice == '1':
                sounds["shop_enter"].play()
                shop.shop(self.player, sounds)
            elif choice == '2':
                sounds["menu_select"].play()
                quest_nbr = self.select_quest()
                if quest_nbr is None:
                    continue
                self.draft_party()
                return quest_nbr
            elif choice == '3':
                database.save_player(self.player)
                break
            else:
                print("Invalid choice.")
                time.sleep(1.5)  # readable before the hub redraws

    # Quest board for the current zone
    def select_quest(self):
        print("\n--- TODAY'S SPECIALS (QUEST BOARD) ---")
        zone_quests = {}
        for q_id, quest in QUESTS.items():
            if quest["zone_nbr"] == self.player.current_zone_nbr:
                zone_quests[q_id] = quest

        if not zone_quests:
            print("The kitchen has nothing new to serve in this region yet. Check back soon!")
            input("\nPress [ENTER] to return to the hub.")
            return None

        for q_id, quest in zone_quests.items():
            print(f"{q_id}. {quest['name']} (Boss: {quest['enemies'][3]['name']} - 3 Courses)")
            print(f"   📜 {quest['description'].replace('\n', '\n   ')}\n")
        print("0. Return to Hub")

        q_choice = input("\nSelect a Dinner Course: ")
        if q_choice not in map(str, zone_quests):
            if q_choice != '0':
                print("Invalid choice. Returning to hub.")
                time.sleep(1.5)
            return None

        selected_quest = zone_quests[int(q_choice)]
        print(f"\nRecipe Report: You Selected '{selected_quest['name']}' (3 courses, ending with {selected_quest['enemies'][3]['name']})!")
        return int(q_choice)

    # Draft 3 patrons from the bar pool
    def draft_party(self):
        print("\n--- BAR ROOM: SELECT YOUR PARTY OF 3 ---")
        bar_pool = []
        for cls in Patron.classes:
            bar_pool.append(cls(cls.name))
        roll_equipment(bar_pool)

        for i, c in enumerate(bar_pool, start=1):
            print(f"[{i}] {c.name} ({type(c).__name__}) - HP: {c.hp} | Atk: {c.attack_power} | Aggro: {c.aggro}")
            print(f"     🗡️ Weapon: {c.weapon['name']} (+{c.weapon['power']}) | 🛡️ Armor: {c.armor['name']} (+{c.armor['power']})")

        print("\nChoose 3 patrons from the bar pool (e.g., enter numbers space-separated like '1 3 4'):")
        while True:
            party = self.read_party_choice(bar_pool)
            if party is not None:
                self.player.active_party = party
                break
            print(f"Invalid selection. Please enter exactly 3 different numbers between 1 and {len(bar_pool)}.")

        print("\nParty Reserved! Preparing the kitchen-cart...")

    # Returns the 3 chosen patrons, or None for invalid input.
    def read_party_choice(self, bar_pool):
        raw_choices = input(f"Your party draft (1-{len(bar_pool)}): ").split()

        if len(raw_choices) != 3:
            return None

        indices = []
        for text in raw_choices:
            if text not in map(str, range(1, len(bar_pool) + 1)):
                return None
            indices.append(int(text) - 1)

        if not is_unique(indices):
            return None

        party = []
        for idx in indices:
            party.append(bar_pool[idx])
        return party

    # Phase 2: fight through 3 courses
    def phase_2_dungeon(self, quest_nbr):
        sounds["tavern_ambience"].fadeout(1500)
        sounds["press_enter"].fadeout(1500)
        sounds["tavern_music"].fadeout(1500)
        sounds["quest_start"].play()
        sounds["quest_combat"].play(loops=-1)
        print("\n" + "="*50)
        print("=== QUEST: THE DUNGEON BASEMENT (3 COURSES) ===")
        print("="*50)

        quest = QUESTS[quest_nbr]
        patrons = self.player.active_party

        print("The dinner party staggers away from the bar counter.")
        print(f"\n{self.player.barmaid_name} securely locks down the tavern, grabbing the handles of her rolling kitchen-cart...")
        print(f"You descend into the tavern's damp dungeon tunnels to serve up {quest['name']}...")
        time.sleep(2)
        for course in range(1, 4):
            enemy = quest['enemies'][course]
            monster = Monster(
                enemy['name'], hp=enemy['hp'], speed=enemy['speed'], attack=enemy['attack'], attack_emoji=enemy['emoji'],
                resistant_damage_type=enemy['resistant_damage_type'], resistant_element=enemy['resistant_element'],
            )
            flash_text(f"🍽️  --- COURSE {course} OF 3: {monster.name} IS SERVED! --- 🍽️")
            time.sleep(1)

            if not run_course(course, patrons, monster, self.player):
                return False, None

            print(f"\n✨ Course {course} cleared!")
            if course < 3:
                print("You quickly toss a healing snack to your patrons as the next course arrives...")
                combat.heal_between_courses(patrons)
                sounds["next_course"].play()
                time.sleep(2)

        return True, quest['drops']

    # Phase 3: rewards or penalties
    def phase_3_resolution(self, victory, drops, quest_nbr):
        sounds["quest_combat"].fadeout(6000)
        print("\n" + "="*50)
        print("=== LAST CALL! SETTLE THE TAB ===")
        print("="*50)
        if victory:
            sounds["quest_victory"].play()
            sounds["barmaid_victory"].play()
            reward_gold = random.randint(30, 60)
            self.player.gold += reward_gold
            flash_text("🎉 ALL 3 COURSES CLEARED! THE MEAL ENDS IN VICTORY! 🎉")
            print(f"Collected {reward_gold} Gold tips into the till!")
            print("Ingredients Harvested for the Pantry:")
            for item, amount in drops.items():
                self.player.pantry[item] += amount
                print(f"+ {amount}x {item}")
            if QUESTS[quest_nbr]["is_boss"]:
                self.advance_zone()
        else:
            sounds["quest_failed"].play()
            flash_text("💀 KITCHEN DISASTER! YOUR PARTY WAS OVERWHELMED! 💀")
            print("Your party couldn't stomach all three courses!")
            self.player.gold = max(0, self.player.gold - 15)
        # Return-to-tavern ambience
        print("\nDragging the kitchen-cart back to the Tavern Hub...")
        sounds["cart_return"].play()
        sounds["tavern_ambience"].play(loops=-1, fade_ms=4000)
        time.sleep(3)
        sounds["tavern_music"].play(loops=-1)
        time.sleep(3)
        database.save_player(self.player)

    # After a boss: move to the next chapter's zone.
    def advance_zone(self):
        current_chapter = ZONES[self.player.current_zone_nbr]["chapter_nbr"]
        next_zone_nbr = None
        next_chapter = None
        for zone_nbr, zone in ZONES.items():
            if zone["chapter_nbr"] > current_chapter:
                if next_chapter is None or zone["chapter_nbr"] < next_chapter:
                    next_chapter = zone["chapter_nbr"]
                    next_zone_nbr = zone_nbr

        if next_zone_nbr is None:
            flash_text("🏆 There are no further regions to conquer... yet!")
            return

        self.player.current_zone_nbr = next_zone_nbr
        flash_text(f"🗺️  The road now leads onward to {ZONES[next_zone_nbr]['name']}!")

if __name__ == "__main__":
    time.sleep(.1)  # cleaner audio start
    GameEngine().run()