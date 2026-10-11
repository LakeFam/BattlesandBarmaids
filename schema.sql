-- Run against an empty battles_and_barmaids database (Compose does this on first start).

CREATE TABLE items (
    item_nbr SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    emoji TEXT NOT NULL,
    cost INTEGER NOT NULL CHECK (cost >= 0)
);

-- Story chapters for this game (NARRATIVE.md). The Bran arc stays in docs/story-plans.md.
CREATE TABLE chapters (
    chapter_nbr INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

-- Locations (NARRATIVE.md section 2), each in the chapter that introduces it
CREATE TABLE zones (
    zone_nbr SERIAL PRIMARY KEY,
    chapter_nbr INTEGER NOT NULL REFERENCES chapters(chapter_nbr),
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    tavern_name TEXT NOT NULL,
    culinary_theme TEXT NOT NULL
);

CREATE TABLE quests (
    quest_nbr INTEGER PRIMARY KEY,
    zone_nbr INTEGER NOT NULL REFERENCES zones(zone_nbr),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    is_boss BOOLEAN NOT NULL DEFAULT FALSE
);

-- The quest board filters by zone.
CREATE INDEX idx_quests_zone_nbr ON quests (zone_nbr);

CREATE TABLE quest_drops (
    quest_nbr INTEGER NOT NULL REFERENCES quests(quest_nbr),
    item_nbr INTEGER NOT NULL REFERENCES items(item_nbr),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (quest_nbr, item_nbr)
);

CREATE TABLE monsters (
    quest_nbr INTEGER NOT NULL REFERENCES quests(quest_nbr),
    course INTEGER NOT NULL CHECK (course BETWEEN 1 AND 3),
    name TEXT NOT NULL,
    hp INTEGER NOT NULL CHECK (hp > 0),
    speed INTEGER NOT NULL CHECK (speed > 0),
    attack INTEGER NOT NULL CHECK (attack > 0),
    emoji TEXT NOT NULL,
    resistant_damage_type TEXT CHECK (resistant_damage_type IN ('fillet', 'skewer', 'tenderize', 'retro')),
    resistant_element TEXT CHECK (resistant_element IN ('spicy', 'frosty', 'tingly', 'umami')),
    PRIMARY KEY (quest_nbr, course)
);

CREATE TABLE players (
    player_nbr SERIAL PRIMARY KEY,
    barmaid_class TEXT NOT NULL UNIQUE CHECK (barmaid_class IN ('Marigold', 'Saffron', 'Bunhilda')),
    gold INTEGER NOT NULL DEFAULT 10 CHECK (gold >= 0),
    barmaid_super_charge INTEGER NOT NULL DEFAULT 0 CHECK (barmaid_super_charge BETWEEN 0 AND 100),
    current_zone_nbr INTEGER NOT NULL REFERENCES zones(zone_nbr) DEFAULT 1,
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE player_inventory (
    player_nbr INTEGER NOT NULL REFERENCES players(player_nbr) ON DELETE CASCADE,
    item_nbr INTEGER NOT NULL REFERENCES items(item_nbr),
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    PRIMARY KEY (player_nbr, item_nbr)
);

-- Weapons and armor. tier maps to adventurer levels in Python; rarity is reserved for drop odds.
CREATE TABLE equipment (
    equipment_nbr SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('weapon', 'armor', 'both')),
    tier TEXT NOT NULL CHECK (tier IN ('novice', 'veteran', 'elite')),
    rarity TEXT NOT NULL CHECK (rarity IN ('common', 'uncommon', 'rare', 'shiny')),
    damage_type TEXT CHECK (damage_type IN ('fillet', 'skewer', 'tenderize', 'retro')),
    element TEXT CHECK (element IN ('spicy', 'frosty', 'tingly', 'umami')),
    power INTEGER NOT NULL CHECK (power >= 0),
    cost INTEGER NOT NULL CHECK (cost >= 0)
);

-- Per-player progress for the 5 adventurer classes. Gear is re-rolled at draft time.
CREATE TABLE player_adventurers (
    player_nbr INTEGER NOT NULL REFERENCES players(player_nbr) ON DELETE CASCADE,
    adventurer_class TEXT NOT NULL CHECK (adventurer_class IN ('Paladin', 'Warrior', 'Ranger', 'Rogue', 'Mage')),
    level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    weapon_nbr INTEGER REFERENCES equipment(equipment_nbr),
    armor_nbr INTEGER REFERENCES equipment(equipment_nbr),
    PRIMARY KEY (player_nbr, adventurer_class)
);

-- Quest runs: one attempt at a quest, saved between API requests.
-- Ingredients and super charge stay on player_inventory and players.
CREATE TABLE quest_runs (
    run_nbr SERIAL PRIMARY KEY,
    player_nbr INTEGER NOT NULL REFERENCES players(player_nbr) ON DELETE CASCADE,
    quest_nbr INTEGER NOT NULL REFERENCES quests(quest_nbr),
    status TEXT NOT NULL DEFAULT 'drafting' CHECK (status IN ('drafting', 'in_combat', 'won', 'lost', 'abandoned')),
    course INTEGER NOT NULL DEFAULT 1 CHECK (course BETWEEN 1 AND 3),
    round_nbr INTEGER NOT NULL DEFAULT 1 CHECK (round_nbr >= 1),
    -- Current monster stats; abilities lower attack and speed mid-fight.
    monster_hp INTEGER CHECK (monster_hp >= 0),
    monster_attack INTEGER CHECK (monster_attack > 0),
    monster_speed INTEGER CHECK (monster_speed > 0),
    started_at TIMESTAMP NOT NULL DEFAULT now(),
    ended_at TIMESTAMP,
    -- Seed for the run's dice. The same seed and the same actions replay the same fight.
    rng_seed BIGINT NOT NULL,
    CHECK ((status IN ('won', 'lost', 'abandoned')) = (ended_at IS NOT NULL)),
    CHECK (status <> 'in_combat' OR (monster_hp IS NOT NULL AND monster_attack IS NOT NULL AND monster_speed IS NOT NULL))
);

-- Run history by player.
CREATE INDEX idx_quest_runs_player_nbr ON quest_runs (player_nbr);

-- One unfinished run per player.
CREATE UNIQUE INDEX uq_quest_runs_one_open_per_player ON quest_runs (player_nbr)
    WHERE status IN ('drafting', 'in_combat');

-- The 5-patron draft pool and the party's live combat state.
CREATE TABLE quest_run_patrons (
    run_nbr INTEGER NOT NULL REFERENCES quest_runs(run_nbr) ON DELETE CASCADE,
    slot INTEGER NOT NULL CHECK (slot BETWEEN 1 AND 5),
    adventurer_class TEXT NOT NULL CHECK (adventurer_class IN ('Paladin', 'Warrior', 'Ranger', 'Rogue', 'Mage')),
    is_drafted BOOLEAN NOT NULL DEFAULT FALSE,
    hp INTEGER NOT NULL CHECK (hp >= 0),
    max_hp INTEGER NOT NULL CHECK (max_hp > 0),
    -- Rally Cry Ale raises it mid-fight.
    attack_power INTEGER NOT NULL CHECK (attack_power > 0),
    power_meter INTEGER NOT NULL DEFAULT 0 CHECK (power_meter BETWEEN 0 AND 100),
    defense_buff INTEGER NOT NULL DEFAULT 0 CHECK (defense_buff >= 0),
    -- Saffron's Round on the House: the next hit deals double damage.
    double_strike BOOLEAN NOT NULL DEFAULT FALSE,
    weapon_nbr INTEGER REFERENCES equipment(equipment_nbr),
    armor_nbr INTEGER REFERENCES equipment(equipment_nbr),
    PRIMARY KEY (run_nbr, slot),
    UNIQUE (run_nbr, adventurer_class),
    CHECK (hp <= max_hp)
);

-- Seed data, migrated from data.py

INSERT INTO items (name, emoji, cost) VALUES
    ('Mighty Malt', '🌾', 5),
    ('Aged Cheddar', '🧀', 8),
    ('Chilly Peppers', '🌶️', 10),
    ('Watery Onion', '🧅', 12),
    ('Holy Ham', '🍖', 15),
    ('Ghost Pepperoni', '🍕', 20);

INSERT INTO chapters (chapter_nbr, name, description) VALUES
(1, 'The Village of the Hearth', 'The Corporate Wall is still a distant rumor, but local wildlife is turning strange on synthetic runoff. The barmaid''s first nights at The Flaming Flagon are spent clearing what has crawled into the village: cellar rats, a larder raid, and The Baconnator, the village''s Great Boar. She drafts three patrons, fights three courses at a time from the kitchen-cart, and opens the road to the Taplands if the boar goes down.'),
(2, 'The Taplands', 'The last frontier of authentic cooking: amber barley fields, copper fermenting vats, and roadside inns that still serve slow food. From The Copper Vat Tavern the barmaid stocks wild fermentation into the cart and holds the line as franchise-slop creeps in from the east.'),
(3, 'City of Circuits', 'A fallen commercial monolith half-buried in the Eastern Dunes. Defunct neon and pre-decline electronics wait to be salvaged into supper. The Neon Skillet is home base for retro diner cooking while the cart forages the ruins.'),
(4, 'The Crashed Titan Sanctuary', 'A colossal alien war-machine lies in a flooded lake crater. Its geothermal heart could become the resistance''s greatest oven. The Geothermal Galley serves deep-crater feasts while the Corporate Wall accelerates its westward march.'),
(5, 'The Corporate Wall', 'A grey-and-neon border of moving mega-fortresses, ingesting farms and taverns and extruding sterile franchise chains. If the cart reaches The Liberated Cafeteria, the fight leaves cellars behind and charges into reclaimed slop.'),
(6, 'A New Vintage', 'If the Wall ever crumbles, it will leave fertile soil mixed with steel. The Taplands stay wild. The kitchen-cart keeps to the roads, one tavern at a time, teaching the next generation how to keep the wild yeast alive.');

INSERT INTO zones (chapter_nbr, name, description, tavern_name, culinary_theme) VALUES
(1, 'The Village of the Hearth', 'The prologue setting. A quiet, rustic village anchored by Master Levain''s ancient wood-fired stone oven. It is the birthplace of the protagonist''s culinary journey.', 'The Flaming Flagon', 'Rustic Hearth Cooking'),
(2, 'The Taplands', 'A vibrant, chaotic region of amber barley fields, copper fermenting vats, and brave roadside inns. It is a place of authentic culture, slow-cooked meals, and community.', 'The Copper Vat Tavern', 'Wild Fermentation & Brewing'),
(3, 'City of Circuits', 'A fallen commercial monolith half-buried in the sand. Defunct neon signs and solid-state pre-decline electronics await salvage by brave foragers.', 'The Neon Skillet', 'Retro Diner & Salvage Cuisine'),
(4, 'The Crashed Titan Sanctuary', 'A colossal alien war-machine fallen into a lake. Its flooded crater serves as the ultimate future home base for the culinary resistance.', 'The Geothermal Galley', 'Deep-Crater Feasting'),
(5, 'The Corporate Wall', 'A creeping, grey-and-neon border of moving mega-fortresses. The Wall slowly rolls westward, ingesting boutique shops, independent farms, and taverns, only to extrude uniform, sterile franchise chains and endless vats of "pink slime."', 'The Liberated Cafeteria', 'Reclaimed Franchise Slop');

-- The Baconnator is Chapter 1's Great Boar (NARRATIVE.md section 6).
INSERT INTO quests (quest_nbr, zone_nbr, name, description, is_boss) VALUES
(1, (SELECT zone_nbr FROM zones WHERE name = 'The Village of the Hearth'), 'Mystery Meat! Clearing the Cellar Rats', 'Ratta Chewie, the Cellar King, holds his throne,
A hulking rat lord with a crown made of bone,
He''s grown fat on the stew
And the cellar all knew
That none but three courses could topple him alone.', FALSE),
(2, (SELECT zone_nbr FROM zones WHERE name = 'The Village of the Hearth'), 'Goblin Raid on the Larder', 'Gobla Cado Grande, grown massive and green,
The largest guac-goblin the Larder has seen,
He crushes the cheese
And hoards with such ease,
So three courses must topple this guacamole machine.', FALSE),
(3, (SELECT zone_nbr FROM zones WHERE name = 'The Village of the Hearth'), 'The Bored King (BOSS)', 'The Baconnator, a boar built of bacon,
Wears a crooked crown he''s proud to be shakin'',
He''s sizzling and vast,
Bored stiff on his cast,
Bring three courses, his rule we''ll be breakin''!', TRUE);

-- Quest 1 drops a mix of what the barmaid spends; quest 2 pays more for a harder fight.
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 1, item_nbr, 2 FROM items
    WHERE name IN ('Mighty Malt', 'Aged Cheddar', 'Watery Onion', 'Chilly Peppers', 'Ghost Pepperoni');
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 2, item_nbr, 4 FROM items WHERE name IN ('Aged Cheddar', 'Chilly Peppers');
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 2, item_nbr, 3 FROM items WHERE name = 'Ghost Pepperoni';
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 3, item_nbr, 6 FROM items WHERE name = 'Holy Ham';
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 3, item_nbr, 4 FROM items WHERE name = 'Watery Onion';

INSERT INTO monsters (quest_nbr, course, name, hp, speed, attack, emoji) VALUES
(1, 1, 'Lil Nibbler', 110, 7, 20, '🐭'),
(1, 2, 'Ratta Rogue', 165, 6, 26, '🐀'),
(1, 3, 'Ratta Chewie, the Cellar King', 240, 5, 32, '👑'),
(2, 1, 'Little Gobbler', 130, 10, 23, '🌱'),
(2, 2, 'Greener Goblin', 195, 9, 29, '🥑'),
(2, 3, 'Gobla Cado Grande', 280, 8, 37, '👹'),
(3, 1, 'Braised Bandit', 235, 7, 24, '🥓'),
(3, 2, 'Mutton Chopper', 300, 6, 30, '🍖'),
(3, 3, 'The Baconnator', 415, 5, 38, '🐗');

-- Ratta Chewie is already "grown fat on the stew" - too tender to be tenderized further.
UPDATE monsters SET resistant_damage_type = 'tenderize' WHERE quest_nbr = 1 AND course = 3;
-- The Baconnator is "sizzling and vast" - a frosty attack barely registers.
UPDATE monsters SET resistant_element = 'frosty' WHERE quest_nbr = 3 AND course = 3;

-- Each damage_type and element appears on exactly one weapon or 'both' item.
INSERT INTO equipment (name, type, tier, rarity, damage_type, element, power, cost) VALUES
('Cast-Iron Skillet',        'weapon', 'novice', 'common',   'tenderize', NULL,      6, 14),
('Red-Hot Poker',            'weapon', 'novice', 'common',   'skewer',    NULL,      7, 16),
('Fillet Knife',             'weapon', 'novice', 'uncommon', 'fillet',    NULL,      8, 20),
('Salvaged Toaster Fork',    'both',   'novice', 'uncommon', 'retro',     NULL,      7, 22),
('Chili Pepper Cleaver',     'weapon', 'novice', 'uncommon', NULL,        'spicy',   8, 20),
('Frosted Ice Tongs',        'weapon', 'novice', 'uncommon', NULL,        'frosty',  8, 20),
('Numbing Peppercorn Mace',  'both',   'novice', 'rare',     NULL,        'tingly',  9, 26),
('Umami Bone-Broth Cleaver', 'both',   'novice', 'rare',     NULL,        'umami',   7, 24),
('Quilted Oven Mitts',       'armor',  'novice', 'common',   NULL,        NULL,      5, 12),
('Reinforced Apron',         'armor',  'novice', 'common',   NULL,        NULL,      6, 14);
