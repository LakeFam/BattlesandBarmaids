import random

import database
from data import FINESSE_FLAVOR, MAGIC_FLAVOR, MELEE_FLAVOR, MONSTER_DEATH_MESSAGES, MONSTER_FLAVOR

INGREDIENTS = database.get_ingredients()

# One line of combat output, plus sound keys to play with it.
def event(text, *sounds, flash=False):
    return {"text": text, "sounds": list(sounds), "flash": flash}

# Death message if the monster just died.
def monster_death_events(monster):
    if monster.is_alive():
        return []
    return [event(random.choice(MONSTER_DEATH_MESSAGES).format(name=monster.name), "monster_death")]

POLISH_LABEL = "🧽 Polish Tumblers: Skip turn, scavenge +1 random ingredient."

def cost_text(cost):
    return ", ".join(f"{amt}x {name}" for name, amt in cost.items())

# A barmaid action the rules won't allow.
class ActionError(Exception):
    def __init__(self, message, sound=None):
        super().__init__(message)
        self.sound = sound

# Base class for the 3 barmaids; each supplies its kit via build_abilities()/build_special().
class Player:
    name = None
    kit_description = None

    def __init__(self):
        self.gold = database.STARTING_GOLD
        self.pantry = {item: database.STARTING_PANTRY_QTY for item in INGREDIENTS}
        self.barmaid_name = self.name
        self.barmaid_class = type(self).__name__  # save key: "Marigold", "Saffron" or "Bunhilda"
        self.barmaid_super_charge = 0
        self.current_zone_nbr = 1
        self.active_party = []
        self.abilities = self.build_abilities()
        self.special = self.build_special()
        # Menu numbers: abilities first, then these two.
        self.polish_choice = len(self.abilities) + 1
        self.special_choice = len(self.abilities) + 2

    def build_abilities(self):
        return []

    def build_special(self):
        return None

    # Applies one action and returns its events. target is only for abilities aimed at one patron.
    def act(self, choice, patrons, monster, target=None):
        if choice == self.polish_choice:
            found = random.choice(list(INGREDIENTS))
            self.pantry[found] += 1
            return [event(f"🧽 You aggressively polish a copper mug on the cart and find 1x {found} hiding underneath!", "barmaid_polish")]

        if 1 <= choice <= len(self.abilities):
            ability = self.abilities[choice - 1]
        elif choice == self.special_choice:
            if self.barmaid_super_charge < 100:
                raise ActionError("❌ Requires 100% Super Charge!", "barmaid_fail")
            ability = self.special
        else:
            raise ActionError(f"Invalid choice. Choose an action from 1 to {self.special_choice}.")

        if not self.check_supplies(ability["cost"]):
            raise ActionError(f"❌ Missing ingredients! Need: {cost_text(ability['cost'])}")

        living = [p for p in patrons if p.is_alive()]
        if ability["target"] == "patron":
            if target is None and len(living) == 1:
                target = living[0]
            if target not in living:
                raise ActionError("Choose a living patron to serve.")
            subject = target
        elif ability["target"] == "party":
            subject = living
        else:
            subject = monster

        self.deduct_supplies(ability["cost"])
        events = ability["effect"](subject)
        if ability is self.special:
            self.barmaid_super_charge = 0
        else:
            self.barmaid_super_charge = min(100, self.barmaid_super_charge + ability["charge"])
        return events

    def check_supplies(self, cost):
        return all(self.pantry.get(item, 0) >= amount for item, amount in cost.items())

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
        target.defense_buff += 3
        target.hp = min(target.max_hp, target.hp + 25)
        return [event(f"🩹 You tend {target.name}'s wounds with warm broth and clean linen! (+3 Defense, +25 HP)", "barmaid_bandage")]

    def round_of_comfort(self, living_patrons):
        for p in living_patrons:
            p.hp = min(p.max_hp, p.hp + 10)
        return [event("🍲 You ladle out a round of hearty soup for everyone! (+10 HP to the whole party)", "combat_heal")]

    def bitter_herb_toss(self, monster):
        monster.attack_power = max(1, monster.attack_power - 2)
        return [event(f"🌿 You toss bitter herbs at {monster.name}! Its Attack Flavor dips to {monster.attack_power}.", "barmaid_haunt")]

    def last_call_miracle(self, living_patrons):
        target = min(living_patrons, key=lambda p: p.hp)
        target.hp = target.max_hp
        target.defense_buff += 5
        return [event(f"✨ LAST CALL MIRACLE! {target.name} is fully healed and fortified!", "barmaid_miracle", flash=True)]

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
        target.ignore_def = True
        return [event(f"🌶️  You pour a flaming shot for {target.name}! Their next strike cuts right through armor!", "barmaid_buff")]

    def rally_cry_ale(self, target):
        target.attack_power += 4
        return [event(f"🍺 You pour {target.name} a Rally Cry Ale! Attack Flavor permanently rises to {target.attack_power}!", "barmaid_rally")]

    def chicory_cure(self, target):
        target.hp = min(target.max_hp, target.hp + 10)
        return [event(f"☕ You slide {target.name} a mug of chicory brew! (+10 HP)", "barmaid_heal")]

    def tavern_anthem(self, living_patrons):
        for p in living_patrons:
            p.ignore_def = True
        return [event("🎺 TAVERN ANTHEM! The whole party's next strikes cut through armor!", "barmaid_anthem", flash=True)]

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
        monster.hp -= 12
        return [event(f"🔥 You hurl a flaming shot straight at {monster.name} for 12 damage!", "barmaid_fireshot")] + monster_death_events(monster)

    def ghost_pepperoni_slice(self, monster):
        monster.attack_power = max(1, monster.attack_power - 4)
        return [event(f"👻🍕 You toss a GHOST PEPPERONI SLICE at {monster.name}! Haunted by the heat, its Attack Flavor drops to {monster.attack_power}!", "barmaid_haunt")]

    def bar_rag_bandage(self, target):
        target.hp = min(target.max_hp, target.hp + 10)
        return [event(f"🩹 You wrap {target.name}'s wound in a bar rag and a shot of courage! (+10 HP)", "barmaid_heal")]

    def holy_ham_grenade(self, monster):
        monster.hp -= 20
        return [event("🍖 KABOOM! HOLY HAM GRENADE DETONATED FOR 20 DAMAGE! 🍖", "combat_grenade", "barmaid_special", flash=True)] + monster_death_events(monster)

Player.classes = [Marigold, Saffron, Bunhilda]

# Shared base for patrons and monsters
class Character:
    def __init__(self, name, hp, speed, attack, aggro):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.speed = speed
        self.attack_power = attack
        self.aggro = aggro
        self.defense_buff = 0
        self.power_meter = 0
        self.ignore_def = False

    def is_alive(self):
        return self.hp > 0

    def execute_special(self, monster, patrons):
        return []

class Patron(Character):
    hp = speed = attack = aggro = 0
    attack_sound = None
    special_sound = None
    attack_emoji = "⚔️"
    name = None
    death_message = None

    def __init__(self, name):
        super().__init__(name, self.hp, self.speed, self.attack, self.aggro)
        self.weapon = None
        self.armor = None

    # Patron-only until monsters get specials.
    def execute_special(self, monster, patrons):
        banner = event(f"🌟 {self.name}'s APPETITE METER IS BURSTING! 🌟", self.special_sound, flash=True)
        return [banner] + self.special_effect(monster, patrons)

    def special_effect(self, monster, patrons):
        return []

class Paladin(Patron):
    hp, speed, attack, aggro = 60, 4, 8, 9
    attack_sound = "paladin_attack"
    special_sound = "paladin_special"
    attack_emoji = "🍳"
    name = "Princess Blue the Natural Leaven Healer"
    flavor_text = MELEE_FLAVOR
    death_message = "🍳💀 Princess Blue collapses, her healing leaven finally spent... 'The bread... still rises...'"

    def special_effect(self, monster, patrons):
        target = min(patrons, key=lambda p: p.hp)
        heal = 20
        target.hp = min(target.max_hp, target.hp + heal)
        target.defense_buff += 3
        return [event(f"🛡️  {self.name} serves a hearty BLESSED STEW! {target.name} recovers {heal} HP and gains +3 Crust Defense!")]

class Warrior(Patron):
    hp, speed, attack, aggro = 50, 6, 11, 7
    attack_sound = "warrior_attack"
    special_sound = "warrior_special"
    attack_emoji = "🔨"
    name = "Grimble the Griddle-Master"
    flavor_text = MELEE_FLAVOR
    death_message = "🔨💀 Grimble the Griddle-Master goes down, his griddle clattering across the floor!"

    def special_effect(self, monster, patrons):
        dmg = self.attack_power * 2
        monster.hp -= dmg
        return [event(f"🥩 {self.name} uses MEAT-HOOK SMASH! Deals {dmg} massive damage to {monster.name}!")] + monster_death_events(monster)

class Ranger(Patron):
    hp, speed, attack, aggro = 40, 7, 10, 4
    attack_sound = "ranger_attack"
    special_sound = "ranger_special"
    attack_emoji = "🍢"
    name = "Willow the Village Pine Scout"
    flavor_text = FINESSE_FLAVOR
    death_message = "🍢💀 Willow falls, her last skewer clattering across the tiles..."

    def special_effect(self, monster, patrons):
        dmg = self.attack_power
        monster.hp -= dmg
        monster.attack_power = max(1, monster.attack_power - 2)
        return [event(f"🏹 {self.name} fires a SKEWERING TOOTHPICK! Deals {dmg} damage and saps the monster's Attack Flavor!")] + monster_death_events(monster)

class Rogue(Patron):
    hp, speed, attack, aggro = 30, 8, 14, 5
    attack_sound = "rogue_attack"
    special_sound = "rogue_special"
    attack_emoji = "🔪"
    name = "Faelen the Fermenter"
    flavor_text = FINESSE_FLAVOR
    death_message = "🔪💀 Faelen the Fermenter slumps over as their fermentation jar shatters on the floor!"

    def special_effect(self, monster, patrons):
        dmg = self.attack_power + 15
        monster.hp -= dmg
        return [event(f"🗡️ {self.name} executes a ZESTY BACKSTAB! Carves past armor for {dmg} vital damage!")] + monster_death_events(monster)

class Mage(Patron):
    hp, speed, attack, aggro = 25, 5, 16, 4
    attack_sound = "robot_attack"
    special_sound = "robot_special"
    attack_emoji = "✨"
    name = "Unit Micro-90 the Vending T-800"
    flavor_text = MAGIC_FLAVOR
    death_message = "✨💀 Unit Micro-90 sparks and slumps, its molten convenience-food core sputtering out..."

    def special_effect(self, monster, patrons):
        dmg = self.attack_power + 5
        monster.hp -= dmg
        monster.speed = max(1, monster.speed - 3)
        return [event(f"❄️  {self.name} casts LIQUID NITROGEN BLAST! Deals {dmg} damage and flash-freezes the monster's speed!")] + monster_death_events(monster)

Patron.classes = [Paladin, Warrior, Ranger, Rogue, Mage]

# Random weapon and armor for each patron, from the equipment catalog's values.
def roll_equipment(patrons, equipment):
    weapon_choices = [item for item in equipment if item["type"] in ("weapon", "both")]
    armor_choices = [item for item in equipment if item["type"] in ("armor", "both")]
    for patron in patrons:
        patron.weapon = random.choice(weapon_choices)
        patron.armor = random.choice(armor_choices)

class Monster(Character):
    attack_sound = "monster_attack"
    flavor_text = MONSTER_FLAVOR

    # Aggro is unused for monsters (kept for later).
    def __init__(self, name, hp, speed, attack, attack_emoji="👹", resistant_damage_type=None, resistant_element=None):
        super().__init__(name, hp=hp, speed=speed, attack=attack, aggro=0)
        self.attack_emoji = attack_emoji
        self.resistant_damage_type = resistant_damage_type
        self.resistant_element = resistant_element

    # From one course of database.get_quests()'s "enemies".
    @classmethod
    def from_enemy(cls, enemy):
        return cls(
            enemy["name"], hp=enemy["hp"], speed=enemy["speed"], attack=enemy["attack"], attack_emoji=enemy["emoji"],
            resistant_damage_type=enemy["resistant_damage_type"], resistant_element=enemy["resistant_element"],
        )
