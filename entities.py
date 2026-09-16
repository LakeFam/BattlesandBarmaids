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
# Player is the base class for the 3 selectable barmaids (see Player.classes,
# set after all 3 are defined below). Each barmaid keeps the same turn
# structure (3 costed abilities + a free scavenge + a 100%-charge special)
# but supplies its own kit via build_abilities()/build_special().
class Player:
    name = None
    kit_description = None

    def __init__(self):
        self.gold = 10
        self.pantry = {item: 6 for item in INGREDIENTS}
        self.barmaid_name = self.name
        self.barmaid_super_charge = 0
        self.current_zone_nbr = 1
        self.active_party = []
        self.abilities = self.build_abilities()
        self.special = self.build_special()

    def build_abilities(self):
        return []

    def build_special(self):
        return None

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

            print()
            for i, ability in enumerate(self.abilities, start=1):
                cost_text = ", ".join(f"{amt}x {name}" for name, amt in ability["cost"].items())
                print(f"{i}. {ability['label']} (Cost: {cost_text})")
            print("4. 🧽 Polish Tumblers: Skip turn, scavenge +1 random ingredient.")
            # Only displays option if the barmaid has enough super charge.
            if self.barmaid_super_charge >= 100:
                cost_text = ", ".join(f"{amt}x {name}" for name, amt in self.special["cost"].items())
                print(f"5. {self.special['label']} (Cost: {cost_text})")
            else:
                print("5. (Locked, requires 100% Super Charge)")
            # Selectable actions for Player/Barmaid.
            choice = input("Select hospitality action (1-5): ")
            if choice in ('1', '2', '3'):
                ability = self.abilities[int(choice) - 1]
                # Targets one patron, so uses serve_item for selection.
                if ability["target"] == "patron":
                    if self.serve_item(patrons, ability["cost"], ability["charge"], ability["effect"]):
                        return
                # Targets the whole living party, or the one monster in combat.
                elif self.check_supplies(ability["cost"]):
                    self.deduct_supplies(ability["cost"])
                    if ability["target"] == "party":
                        ability["effect"]([p for p in patrons if p.is_alive()])
                    else:
                        ability["effect"](monster)
                    self.barmaid_super_charge = min(100, self.barmaid_super_charge + ability["charge"])
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
                    if self.check_supplies(self.special["cost"]):
                        self.deduct_supplies(self.special["cost"])
                        if self.special["target"] == "party":
                            self.special["effect"]([p for p in patrons if p.is_alive()])
                        else:
                            self.special["effect"](monster)
                        self.barmaid_super_charge = 0
                        return

            else:
                print("Invalid choice.")

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

class Marigold(Player):
    name = "Marigold the Mender"
    kit_description = "Heavy healing, light offense."

    def build_abilities(self):
        return [
            {
                "label": "🩹 Serve: Tend the Wounds - Bandage & Heal 1 patron",
                "cost": {"🧀 Aged Cheddar": 1, "🌾 Mighty Malt": 1},
                "charge": 25,
                "target": "patron",
                "effect": self.tend_wounds,
            },
            {
                "label": "🍲 Serve: Round of Comfort - Heal the whole party a little",
                "cost": {"🧅 Watery Onion": 1, "🌶️ Chilly Peppers": 1},
                "charge": 30,
                "target": "party",
                "effect": self.round_of_comfort,
            },
            {
                "label": "🌿 Toss: Bitter Herb Toss - Mildly dulls the enemy's Attack",
                "cost": {"🍕 Ghost Pepperoni": 1},
                "charge": 20,
                "target": "monster",
                "effect": self.bitter_herb_toss,
            },
        ]

    def build_special(self):
        return {
            "label": "✨ LAST CALL MIRACLE - Fully heals & fortifies your weakest patron",
            "cost": {"🍖 Holy Ham": 2},
            "target": "party",
            "effect": self.last_call_miracle,
        }

    def tend_wounds(self, target):
        sounds["barmaid_bandage"].play()
        target.defense_buff += 3
        target.hp = min(target.max_hp, target.hp + 25)
        print(f"\n🩹 You tend {target.name}'s wounds with warm broth and clean linen! (+3 Defense, +25 HP)")

    def round_of_comfort(self, living_patrons):
        sounds["combat_heal"].play()
        for p in living_patrons:
            p.hp = min(p.max_hp, p.hp + 10)
        print("\n🍲 You ladle out a round of hearty soup for everyone! (+10 HP to the whole party)")

    def bitter_herb_toss(self, monster):
        sounds["barmaid_haunt"].play()
        monster.attack_power = max(1, monster.attack_power - 2)
        print(f"\n🌿 You toss bitter herbs at {monster.name}! Its Attack Flavor dips to {monster.attack_power}.")

    def last_call_miracle(self, living_patrons):
        sounds["barmaid_miracle"].play()
        target = min(living_patrons, key=lambda p: p.hp)
        target.hp = target.max_hp
        target.defense_buff += 5
        flash_text(f"✨ LAST CALL MIRACLE! {target.name} is fully healed and fortified!")

class Saffron(Player):
    name = "Saffron the Morale-Brewer"
    kit_description = "Big buffs, a splash of healing."

    def build_abilities(self):
        return [
            {
                "label": "🌶️  Serve: Round on the House - Their next strike cuts clean through armor",
                "cost": {"🌶️ Chilly Peppers": 1, "🧅 Watery Onion": 1},
                "charge": 35,
                "target": "patron",
                "effect": self.round_on_the_house,
            },
            {
                "label": "🍺 Serve: Rally Cry Ale - +4 Attack, for the rest of the fight",
                "cost": {"🌾 Mighty Malt": 1, "🧀 Aged Cheddar": 1},
                "charge": 30,
                "target": "patron",
                "effect": self.rally_cry_ale,
            },
            {
                "label": "☕ Serve: Chicory Cure - A quick pick-me-up (+10 HP, no shield)",
                "cost": {"🧀 Aged Cheddar": 1},
                "charge": 20,
                "target": "patron",
                "effect": self.chicory_cure,
            },
        ]

    def build_special(self):
        return {
            "label": "🎺 TAVERN ANTHEM - The whole party's next strikes cut through armor",
            "cost": {"🍖 Holy Ham": 2},
            "target": "party",
            "effect": self.tavern_anthem,
        }

    def round_on_the_house(self, target):
        sounds["barmaid_buff"].play()
        target.ignore_def = True
        print(f"\n🌶️  You pour a flaming shot for {target.name}! Their next strike cuts right through armor!")

    def rally_cry_ale(self, target):
        sounds["barmaid_rally"].play()
        target.attack_power += 4
        print(f"\n🍺 You pour {target.name} a Rally Cry Ale! Attack Flavor permanently rises to {target.attack_power}!")

    def chicory_cure(self, target):
        sounds["barmaid_heal"].play()
        target.hp = min(target.max_hp, target.hp + 10)
        print(f"\n☕ You slide {target.name} a mug of chicory brew! (+10 HP)")

    def tavern_anthem(self, living_patrons):
        sounds["barmaid_anthem"].play()
        flash_text("🎺 TAVERN ANTHEM! The whole party's next strikes cut through armor!")
        for p in living_patrons:
            p.ignore_def = True

class Bunhilda(Player):
    name = "Bunhilda the Brawler"
    kit_description = "Direct damage and debuffs, with just enough healing to get by."

    def build_abilities(self):
        return [
            {
                "label": "🔥 Toss: Flaming Shot to the Face - Direct damage to the enemy",
                "cost": {"🌶️ Chilly Peppers": 1, "🍕 Ghost Pepperoni": 1},
                "charge": 30,
                "target": "monster",
                "effect": self.flaming_shot,
            },
            {
                "label": "👻 Toss: Ghost Pepperoni Slice - Haunt the enemy, lowering their Attack",
                "cost": {"🍕 Ghost Pepperoni": 1},
                "charge": 30,
                "target": "monster",
                "effect": self.ghost_pepperoni_slice,
            },
            {
                "label": "🩹 Serve: Bar Rag Bandage - A quick patch-up (+10 HP)",
                "cost": {"🌾 Mighty Malt": 1},
                "charge": 20,
                "target": "patron",
                "effect": self.bar_rag_bandage,
            },
        ]

    def build_special(self):
        return {
            "label": "🍖 Toss: HOLY HAM GRENADE - Massive damage to enemy!",
            "cost": {"🍖 Holy Ham": 2},
            "target": "monster",
            "effect": self.holy_ham_grenade,
        }

    def flaming_shot(self, monster):
        sounds["barmaid_fireshot"].play()
        deal_damage(monster, 12, "monster_death")
        print(f"\n🔥 You hurl a flaming shot straight at {monster.name} for 12 damage!")
        print_monster_death(monster)

    def ghost_pepperoni_slice(self, monster):
        sounds["barmaid_haunt"].play()
        monster.attack_power = max(1, monster.attack_power - 4)
        print(f"\n👻🍕 You toss a GHOST PEPPERONI SLICE at {monster.name}! Haunted by the heat, its Attack Flavor drops to {monster.attack_power}!")

    def bar_rag_bandage(self, target):
        sounds["barmaid_heal"].play()
        target.hp = min(target.max_hp, target.hp + 10)
        print(f"\n🩹 You wrap {target.name}'s wound in a bar rag and a shot of courage! (+10 HP)")

    def holy_ham_grenade(self, monster):
        sounds["combat_grenade"].play()
        sounds["barmaid_special"].play()
        deal_damage(monster, 20, "monster_death")
        flash_text("🍖 KABOOM! HOLY HAM GRENADE DETONATED FOR 20 DAMAGE! 🍖")
        print_monster_death(monster)

Player.classes = [Marigold, Saffron, Bunhilda]

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
    name = "Princess Blue the Natural Leaven Healer"
    flavor_text = MELEE_FLAVOR
    death_message = "🍳💀 Princess Blue collapses, her healing leaven finally spent... 'The bread... still rises...'"

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
    name = "Willow the Village Pine Scout"
    flavor_text = FINESSE_FLAVOR
    death_message = "🍢💀 Willow falls, her last skewer clattering across the tiles..."

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
    attack_sound = "robot_attack"
    special_sound = "robot_special"
    attack_emoji = "✨"
    name = "Unit Micro-90 the Vending T-800"
    flavor_text = MAGIC_FLAVOR
    death_message = "✨💀 Unit Micro-90 sparks and slumps, its molten convenience-food core sputtering out..."

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

