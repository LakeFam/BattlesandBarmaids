# Balance simulator: plays many seeded quests through the game rules with a simple AI barmaid.
# Reads the catalog from the database but never writes to it.
#   python simulate.py              # both reports
#   python simulate.py --runs 500   # more runs per row, slower but steadier
import argparse
import itertools
import random
from statistics import mean

import combat
import database
from entities import INGREDIENTS, ActionError, Monster, Patron, Player, roll_equipment

QUESTS = database.get_quests()
ZONES = database.get_zones()
EQUIPMENT = database.get_equipment()
BOSS_QUEST = next(nbr for nbr, q in QUESTS.items() if q["is_boss"])
FARM_QUESTS = [nbr for nbr, q in QUESTS.items() if not q["is_boss"] and q["zone_nbr"] == QUESTS[BOSS_QUEST]["zone_nbr"]]
PARTIES = list(itertools.combinations(range(len(Patron.classes)), 3))
RESTOCK_COST = 50
MAX_ROUNDS = 300  # a fight this long counts as lost

def party_name(party):
    return "/".join(Patron.classes[i].__name__ for i in party)

def hurt(patron, below):
    return patron.hp < patron.max_hp * below

# --- AI barmaid: tries each (action, target) in order and takes the first the rules allow ---
# Orders were picked by simulation, and checked to never do worse with more ingredients.

def options(player, patrons, monster):
    living = [p for p in patrons if p.is_alive()]
    weakest = min(living, key=lambda p: p.hp / p.max_hp)
    special = (player.special_choice, None)
    name = type(player).__name__

    if name == "Marigold":
        opts = []
        if hurt(weakest, 0.5):
            opts += [special, (1, weakest)]
        if sum(hurt(p, 0.75) for p in living) >= 2:
            opts.append((2, None))
        if monster.attack_power > 6:
            opts.append((3, None))
        return opts

    if name == "Saffron":
        unrallied = [p for p in living if p.attack_power == type(p).attack]
        hitter = max(living, key=lambda p: p.attack_power)
        opts = [special]
        if hurt(weakest, 0.3):
            opts.append((3, weakest))
        if unrallied:
            opts.append((2, max(unrallied, key=lambda p: p.attack)))
        if hurt(weakest, 0.9):
            opts.append((3, weakest))
        return opts + [(1, hitter)]

    # Bunhilda: lower the monster's attack first, then patch up and attack.
    opts = [special]
    if monster.attack_power >= 12:
        opts.append((2, None))
    if hurt(weakest, 0.6):
        opts.append((3, weakest))
    opts.append((1, None))
    if hurt(weakest, 0.9):
        opts.append((3, weakest))
    return opts

# Farming: polish for ingredients unless a patron is in danger.
def thrifty_options(player, patrons, monster):
    if any(hurt(p, 0.3) for p in patrons if p.is_alive()):
        return options(player, patrons, monster)
    return []

def barmaid_turn(player, patrons, monster, rng, plan=options):
    for choice, target in plan(player, patrons, monster):
        try:
            return player.act(choice, patrons, monster, target, rng)
        except ActionError:
            continue
    return player.act(player.polish_choice, patrons, monster, rng=rng)

# --- One quest, following the same flow as the terminal game and the API ---

# Returns (won, course reached).
def play_quest(player, quest_nbr, party, rng, plan=options):
    quest = QUESTS[quest_nbr]
    pool = [cls(cls.name) for cls in Patron.classes]
    roll_equipment(pool, EQUIPMENT.values(), rng)
    patrons = [pool[i] for i in party]

    for course in range(1, 4):
        monster = Monster.from_enemy(quest["enemies"][course])
        rounds = 0
        while monster.is_alive():
            if combat.party_defeated(patrons) or rounds >= MAX_ROUNDS:
                combat.lose_quest(player)
                return False, course
            barmaid_turn(player, patrons, monster, rng, plan)
            combat.play_round(patrons, monster, rng)
            rounds += 1
        combat.clear_course(course, patrons)

    combat.win_quest(player, quest, ZONES, rng)
    return True, 3

# Spends gold on +2-of-everything restocks.
def restock(player):
    while player.gold >= RESTOCK_COST:
        player.gold -= RESTOCK_COST
        for item in INGREDIENTS:
            player.pantry[item] += 2

# --- Reports ---

def fresh_save_report(runs, seed):
    print(f"\nFRESH SAVE: 10 gold, 6 of each ingredient. {runs} runs per party, all 10 parties.")
    print(f"{'Barmaid':<10}{'Quest':<34}{'Win':>6}  {'Best party':<28}{'Worst party':<28}")
    best_boss_party = {}
    for cls in Player.classes:
        for quest_nbr, quest in QUESTS.items():
            rates = {}
            for party in PARTIES:
                wins = 0
                for i in range(runs):
                    rng = random.Random(f"{seed}:{cls.__name__}:{quest_nbr}:{party}:{i}")
                    wins += play_quest(cls(), quest_nbr, party, rng)[0]
                rates[party] = wins / runs
            best = max(rates, key=rates.get)
            worst = min(rates, key=rates.get)
            if quest_nbr == BOSS_QUEST:
                best_boss_party[cls] = best
            label = f"{quest_nbr}. {quest['name']}"[:32]
            print(f"{cls.__name__:<10}{label:<34}{mean(rates.values()):>6.0%}  "
                  f"{party_name(best) + f' {rates[best]:.0%}':<28}{party_name(worst) + f' {rates[worst]:.0%}':<28}")
    return best_boss_party

def farming_report(runs, seed, best_boss_party, farm_counts=(0, 1, 2, 3, 4, 6)):
    print(f"\nBOSS AFTER FARMING: quests {' and '.join(map(str, FARM_QUESTS))} in turn, polishing for ingredients unless "
          f"a patron is in danger, all gold spent on restocks (+2 of each for {RESTOCK_COST}), then the boss.")
    print(f"Each barmaid uses her best boss party from above. {runs} runs per cell.")
    print(f"{'Barmaid':<10}" + "".join(f"{f'{n} farmed':>10}" for n in farm_counts) + f"{'gold/farm':>11}")
    for cls in Player.classes:
        party = best_boss_party[cls]
        cells = []
        gold_per_farm = []
        for n in farm_counts:
            wins = 0
            for i in range(runs):
                rng = random.Random(f"{seed}:farm:{cls.__name__}:{n}:{i}")
                player = cls()
                for f in range(n):
                    before = player.gold
                    play_quest(player, FARM_QUESTS[f % len(FARM_QUESTS)], party, rng, thrifty_options)
                    gold_per_farm.append(player.gold - before)
                    restock(player)
                wins += play_quest(player, BOSS_QUEST, party, rng)[0]
            cells.append(f"{wins / runs:>10.0%}")
        avg_gold = f"{mean(gold_per_farm):.0f}" if gold_per_farm else "-"
        print(f"{cls.__name__:<10}" + "".join(cells) + f"{avg_gold:>11}")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=200, help="runs per row or cell (default 200)")
    parser.add_argument("--seed", default="balance", help="change it for a fresh sample (default 'balance')")
    args = parser.parse_args()

    best_boss_party = fresh_save_report(args.runs, args.seed)
    farming_report(args.runs, args.seed, best_boss_party)

if __name__ == "__main__":
    main()
