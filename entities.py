import random
import sys
import time

import database
from data import FINESSE_FLAVOR, MAGIC_FLAVOR, MELEE_FLAVOR, MONSTER_DEATH_MESSAGES, MONSTER_FLAVOR, sounds

INGREDIENTS = database.get_ingredients()

# Moved dealing damage to a function to allow for death check, death sound.
def deal_damage(target, dmg, death_sound):
    target.hp -= dmg
    if not target.is_alive():
        sounds[death_sound].play()
# Random death message for monsters
def print_monster_death(monster):
    if not monster.is_alive():
        print(random.choice(MONSTER_DEATH_MESSAGES).format(name=monster.name))

# Some handy flashing text function for dramatic effect.
def flash_text(text, flashes=3, delay=0.2):
    for _ in range(flashes):
        sys.stdout.write(f"\r\033[1;33m{text}\033[0m")
        sys.stdout.flush()
        time.sleep(delay)
        sys.stdout.write("\r" + " " * len(text) + "\r")
        sys.stdout.flush()
        time.sleep(delay)
    print(f"\033[1;33m{text}\033[0m")
# There's the Player, and NPCs (Patrons and Monsters). Player details here.
class Player:
    def __init__(self):
        self.gold = 10
        self.pantry = {item: 6 for item in INGREDIENTS}
        self.barmaid_name = "Bunhilda the Brawler"
        self.barmaid_super_charge = 0
        self.current_zone_nbr = 1
        self.active_party = []


    def take_turn(self, patrons, monster):
        while True:
            print("\n" + "="*40)
            print(f"--- {self.barmaid_name.upper()}'S MOBILE KITCHEN-CART ---")
            print(f"Barmaid Super Charge: {self.barmaid_super_charge}%")
            # Display stocked pantry items
            in_stock = []
            for k, v in self.pantry.items():
                if v > 0:
                    in_stock.append(f"{k}: {v}")
            pantry_display = " | ".join(in_stock)
            print(f"Pantry Stock: [{pantry_display}]")

            print("\n1. 🧀 Serve: Gouda Guard (Cost: 1 Cheddar, 1 Malt) - Shield & Heal 1 patron")
            print("2. 🌶️  Serve: Dragon's Breath Shot (Cost: 1 Chilly Peppers, 1 Watery Onion) - Buff 1 patron attack")
            print("3. 🍕 Toss: GHOST PEPPERONI SLICE (Cost: 1 Ghost Pepperoni) - Haunt the enemy, lowering their Attack")
            print("4. 🧽 Polish Tumblers: Skip turn, scavenge +1 random ingredient.")
            # Only displays option if the barmaid has enough super charge.
            if self.barmaid_super_charge >= 100:
                print("5. 🍖 Toss: HOLY HAM GRENADE (Cost: 2 Holy Ham) - Massive damage to enemy!")
            else:
                print("5. (Locked, requires 100% Super Charge)")
            # Selectable actions for Player/Barmaid.
            choice = input("Select hospitality action (1-5): ")
            # Targets one player so uses serve_item for selection.
            if choice == '1':
                cost = {"🧀 Aged Cheddar": 1, "🌾 Mighty Malt": 1}
                if self.serve_item(patrons, cost, 25, self.apply_gouda_guard):
                    return
            # Targets one player so uses serve_item for selection.
            elif choice == '2':
                cost = {"🌶️ Chilly Peppers": 1, "🧅 Watery Onion": 1}
                if self.serve_item(patrons, cost, 35, self.apply_dragons_breath):
                    return
            # Targets the one monster in combat, and applies a debuff.
            elif choice == '3':
                cost = {"🍕 Ghost Pepperoni": 1}
                if self.check_supplies(cost):
                    self.deduct_supplies(cost)
                    sounds["barmaid_haunt"].play()
                    monster.attack_power = max(1, monster.attack_power - 4)
                    self.barmaid_super_charge = min(100, self.barmaid_super_charge + 30)
                    print(f"\n👻🍕 You toss a GHOST PEPPERONI SLICE at {monster.name}! Haunted by the heat, its Attack Flavor drops to {monster.attack_power}!")
                    time.sleep(.5)
                    return
            # Freebie action if pantry is empty, gives a random ingredient to the barmaid's pantry.
            elif choice == '4':
                found = random.choice(list(INGREDIENTS))
                self.pantry[found] += 1
                print(f"\n🧽 You aggressively polish a copper mug on the cart and find 1x {found} hiding underneath!")
                return
            # Only available if the barmaid has full super charge.
            elif choice == '5':
                if self.barmaid_super_charge < 100:
                    sounds["barmaid_fail"].play()
                    print("❌ Requires 100% Super Charge!")
                else:
                    cost = {"🍖 Holy Ham": 2}
                    if self.check_supplies(cost):
                        self.deduct_supplies(cost)
                        sounds["combat_grenade"].play()
                        sounds["barmaid_special"].play()
                        deal_damage(monster, 20, "monster_death")
                        flash_text("🍖 KABOOM! HOLY HAM GRENADE DETONATED FOR 20 DAMAGE! 🍖")
                        print_monster_death(monster)
                        self.barmaid_super_charge = 0
                        return

            else:
                print("Invalid choice.")

    def apply_gouda_guard(self, target):
        sounds["barmaid_heal"].play()
        target.defense_buff += 5
        target.hp = min(target.max_hp, target.hp + 15)
        print(f"\n🧀 You slide a hardened cheese shield to {target.name}! (+5 Defense, +15 HP)")
        time.sleep(.5)

    def apply_dragons_breath(self, target):
        sounds["barmaid_buff"].play()
        target.ignore_def = True
        print(f"\n🌶️  You pour a flaming shot for {target.name}! Their next strike cuts right through armor!")

    def serve_item(self, patrons, cost, charge_gain, apply_effect):
        if not self.check_supplies(cost):
            return False
        # Who can be targeted? Only the living.
        living = [p for p in patrons if p.is_alive()]
        if len(living) == 1:
            target = living[0]
        else:
            print("\nWho will you slide this across the cart to?")
            for i, p in enumerate(living):
                print(f"{i+1}. {p.name} ({p.hp}/{p.max_hp} HP) [Appetite Meter: {p.power_meter}%]")

            while True:
                try:
                    choice = int(input("Select patron number: ")) - 1
                    if 0 <= choice < len(living):
                        target = living[choice]
                        break
                except ValueError:
                    pass
                print("Invalid choice. Try again.")
        # Spend, and apply.
        self.deduct_supplies(cost)
        apply_effect(target)
        # Adds super charge to Barmaid, but prevents super charge from exceeding 100%
        self.barmaid_super_charge = min(100, self.barmaid_super_charge + charge_gain)
        return True

    def check_supplies(self, cost):
        for item, amount in cost.items():
            if self.pantry.get(item, 0) < amount:
                needed = ", ".join(f"{amt}x {name}" for name, amt in cost.items())
                print(f"❌ Missing ingredients! Need: {needed}")
                return False
        return True

    def deduct_supplies(self, cost):
        for item, amount in cost.items():
            self.pantry[item] -= amount

# Patrons and Monsters were merged to a single NPC_Class as primary class.

class NPC_Class:
    
    def __init__(self, name, hp, speed, attack, aggro, style, is_player=False):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.speed = speed
        self.attack_power = attack
        self.aggro = aggro
        self.combat_style = style
        self.defense_buff = 0
        self.power_meter = 0
        self.is_player = is_player
        self.ignore_def = False

    def is_alive(self):
        return self.hp > 0

    def execute_special(self, monster, patrons):
        pass

class Patron(NPC_Class):
    hp = speed = attack = aggro = 0
    style = "Melee"
    attack_sound = None
    special_sound = None
    attack_emoji = "⚔️"
    name = None
    death_message = None

    def __init__(self, name):
        super().__init__(name, self.hp, self.speed, self.attack, self.aggro, self.style, is_player=True)
        self.weapon = None
        self.armor = None

    # Patron-specific, for now. Will be moved up to NPC_Class when monsters get specials.
    def execute_special(self, monster, patrons):
        sounds[self.special_sound].play()
        flash_text(f"🌟 {self.name}'s APPETITE METER IS BURSTING! 🌟")
        self.special_effect(monster, patrons)

    def special_effect(self, monster, patrons):
        pass

class Paladin(Patron):
    hp, speed, attack, aggro, style = 60, 4, 8, 9, "Melee"
    attack_sound = "paladin_attack"
    special_sound = "paladin_special"
    attack_emoji = "🍳"
    name = "Sir Galaham the Gourmet"
    flavor_text = MELEE_FLAVOR
    death_message = "🍳💀 Sir Galaham the Gourmet collapses, his apron finally stained... 'A noble... sear...'"

    def special_effect(self, monster, patrons):
        target = min((p for p in patrons if p.is_alive()), key=lambda p: p.hp)
        heal = 20
        target.hp = min(target.max_hp, target.hp + heal)
        target.defense_buff += 3
        print(f"🛡️  {self.name} serves a hearty BLESSED STEW! {target.name} recovers {heal} HP and gains +3 Crust Defense!")

class Warrior(Patron):
    hp, speed, attack, aggro, style = 50, 6, 11, 7, "Melee"
    attack_sound = "warrior_attack"
    special_sound = "warrior_special"
    attack_emoji = "🔨"
    name = "Grimble the Griddle-Master"
    flavor_text = MELEE_FLAVOR
    death_message = "🔨💀 Grimble the Griddle-Master goes down, his griddle clattering across the floor!"

    def special_effect(self, monster, patrons):
        dmg = self.attack_power * 2
        deal_damage(monster, dmg, "monster_death")
        print(f"🥩 {self.name} uses MEAT-HOOK SMASH! Deals {dmg} massive damage to {monster.name}!")
        print_monster_death(monster)

class Ranger(Patron):
    hp, speed, attack, aggro, style = 40, 7, 10, 4, "Finesse"
    attack_sound = "ranger_attack"
    special_sound = "ranger_special"
    attack_emoji = "🍢"
    name = "Lyra the Line-Cook"
    flavor_text = FINESSE_FLAVOR
    death_message = "🍢💀 Lyra the Line-Cook falls, her skewers scattering across the tiles..."

    def special_effect(self, monster, patrons):
        dmg = self.attack_power
        deal_damage(monster, dmg, "monster_death")
        monster.attack_power = max(1, monster.attack_power - 2)
        print(f"🏹 {self.name} fires a SKEWERING TOOTHPICK! Deals {dmg} damage and saps the monster's Attack Flavor!")
        print_monster_death(monster)

class Rogue(Patron):
    hp, speed, attack, aggro, style = 30, 8, 14, 5, "Finesse"
    attack_sound = "rogue_attack"
    special_sound = "rogue_special"
    attack_emoji = "🔪"
    name = "Faelen the Fermenter"
    flavor_text = FINESSE_FLAVOR
    death_message = "🔪💀 Faelen the Fermenter slumps over as their fermentation jar shatters on the floor!"

    def special_effect(self, monster, patrons):
        dmg = self.attack_power + 15
        deal_damage(monster, dmg, "monster_death")
        print(f"🗡️ {self.name} executes a ZESTY BACKSTAB! Carves past armor for {dmg} vital damage!")
        print_monster_death(monster)

class Mage(Patron):
    hp, speed, attack, aggro, style = 25, 5, 16, 4, "Magic"
    attack_sound = "mage_attack"
    special_sound = "mage_special"
    attack_emoji = "✨"
    name = "Elara the Sous-Sorceress"
    flavor_text = MAGIC_FLAVOR
    death_message = "✨💀 Elara the Sous-Sorceress crumples as her spellbook smolders to ash..."

    def special_effect(self, monster, patrons):
        dmg = self.attack_power + 5
        deal_damage(monster, dmg, "monster_death")
        monster.speed = max(1, monster.speed - 3)
        print(f"❄️  {self.name} casts LIQUID NITROGEN BLAST! Deals {dmg} damage and flash-freezes the monster's speed!")
        print_monster_death(monster)

Patron.classes = [Paladin, Warrior, Ranger, Rogue, Mage]

class Monster(NPC_Class):
    attack_sound = "monster_attack"
    flavor_text = MONSTER_FLAVOR

    # Note: Aggro is irrelevant in this version, but is kept for future use.
    def __init__(self, name, hp, speed, attack, attack_emoji="👹", resistant_damage_type=None, resistant_element=None):
        super().__init__(name, hp=hp, speed=speed, attack=attack, aggro=0, style="Monster", is_player=False)
        self.attack_emoji = attack_emoji
        self.resistant_damage_type = resistant_damage_type
        self.resistant_element = resistant_element

