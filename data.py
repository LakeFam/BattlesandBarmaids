from pygame import mixer
# Initialize the mixer module
mixer.init()
# Load sound files and create a dictionary of sounds
def sound(filename):
    return mixer.Sound(f"sounds/{filename}")
# Loads all the sounds to be used by mixer.
sounds = {
    "title": sound("title_theme.mp3"),
    "tavern_ambience": sound("tavern_ambience.mp3"),
    "press_enter": sound("press_enter.mp3"),
    "tavern_music": sound("tavern_music.mp3"),
    "quest_start": sound("quest_start.mp3"),
    "quest_combat": sound("quest_combat.mp3"),
    "quest_victory": sound("quest_victory.mp3"),
    "quest_failed": sound("quest_failed.mp3"),
    "menu_select": sound("menu_select.mp3"),
    "shop_enter": sound("shop_enter.mp3"),
    "shop_restock": sound("shop_restock.mp3"),
    "shop_broke": sound("shop_broke.mp3"),
    "purchase": sound("purchase.mp3"),
    "cart_return": sound("cart_return.mp3"),
    "next_course": sound("next_course.mp3"),
    "combat_heal": sound("combat_heal.mp3"),
    "combat_grenade": sound("combat_grenade.mp3"),
    "barmaid_victory": sound("barmaid_victory.mp3"),
    "barmaid_haunt": sound("barmaid_haunt.mp3"),
    "barmaid_fail": sound("barmaid_fail.mp3"),
    "barmaid_special": sound("barmaid_special.mp3"),
    "barmaid_heal": sound("barmaid_heal.mp3"),
    "barmaid_buff": sound("barmaid_buff.mp3"),
    "paladin_attack": sound("paladin_attack.mp3"),
    "paladin_special": sound("paladin_special.mp3"),
    "warrior_attack": sound("warrior_attack.mp3"),
    "warrior_special": sound("warrior_special.mp3"),
    "ranger_attack": sound("ranger_attack.mp3"),
    "ranger_special": sound("ranger_special.mp3"),
    "rogue_attack": sound("rogue_attack.mp3"),
    "rogue_special": sound("rogue_special.mp3"),
    "mage_attack": sound("mage_attack.mp3"),
    "mage_special": sound("mage_special.mp3"),
    "monster_attack": sound("monster_attack1.mp3"),
    "patron_death": sound("patron_death.mp3"),
    "monster_death": sound("monster_death.mp3"),
}
# Flavor text and game data
TITLE_FLAVOR = (
    "If you drop your fork, don't reach through the knots in the wood\nto grab it. The kitchen staff isn't responsible for missing\nfingers, and the basement rats down there have terrible manners.",
    "The floor gets slick with spilled gravy after the second round,\nso mind your step near the fire pit. Patrons who complained about\nthe smell were quietly reassigned to the cellar.",
    "Complaints about portion size should be directed to the kitchen\nrats, who handle inventory personally. We are not responsible for\nfingers lost during especially enthusiastic seasoning.",
)
# Flavor text for combat and attacks
MELEE_FLAVOR = ("tenderizes with a cast-iron skillet", "mashes aggressively into", "carves a hefty slice out of", "batters with a heavy rolling pin", "skewers with a red-hot poker", "clobbers senseless with a stockpot lid", "slams a rolling pin down on", "grinds mercilessly into")
FINESSE_FLAVOR = ("peels the armor off", "slices cleanly through the crust of", "juliennes a neat wound into", "marinates with a flurry of strikes on", "minces a path straight through", "bastes a searing glaze onto", "flambés with a quick flick of the wrist", "skins a thin cut off")
MAGIC_FLAVOR = ("flash-frys with a burst of arcane heat", "deep-freezes in a sudden frost", "broils with mystical convection", "simmers the air around", "microwaves with a chaotic pulse", "steams with a scalding hex", "caramelizes under a shower of sparks", "peppers with arcane shrapnel")
MONSTER_FLAVOR = ("savagely gnaws on", "tenders a brutal bite into", "crumbles the defenses of", "smashes raw into", "claws hungrily at", "lashes a filthy tail into", "drools menacingly over", "chomps down hard on")
# Flavor text for monster deaths
MONSTER_DEATH_MESSAGES = (
    "💀 {name} collapses into a smoking heap of gravy and bone!",
    "💀 {name} lets out one final greasy shriek before going still!",
    "💀 {name} crumbles apart like an overcooked crust, defeated!",
    "💀 {name} keels over, finally done to a well-done crisp!",
)
