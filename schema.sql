-- Run this first, against the "postgres" maintenance database:
CREATE DATABASE python_fundamentals;

-- Then connect to python_fundamentals and run everything below.

CREATE TABLE items (
    item_nbr SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    emoji TEXT NOT NULL,
    cost INTEGER NOT NULL
);

-- Story chapters, per NARRATIVE.md section 5 (The Narrative Arc).
CREATE TABLE chapters (
    chapter_nbr INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL
);

-- Locations, per NARRATIVE.md section 2 (The World & Setting). Each zone
-- belongs to the chapter it's introduced in.
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

-- Every quest board lookup filters by zone_nbr, so it's worth indexing
-- even though it's not the primary key.
CREATE INDEX idx_quests_zone_nbr ON quests (zone_nbr);

CREATE TABLE quest_drops (
    quest_nbr INTEGER NOT NULL REFERENCES quests(quest_nbr),
    item_nbr INTEGER NOT NULL REFERENCES items(item_nbr),
    quantity INTEGER NOT NULL,
    PRIMARY KEY (quest_nbr, item_nbr)
);

CREATE TABLE monsters (
    quest_nbr INTEGER NOT NULL REFERENCES quests(quest_nbr),
    course INTEGER NOT NULL,
    name TEXT NOT NULL,
    hp INTEGER NOT NULL,
    speed INTEGER NOT NULL,
    attack INTEGER NOT NULL,
    emoji TEXT NOT NULL,
    resistant_damage_type TEXT CHECK (resistant_damage_type IN ('fillet', 'skewer', 'tenderize', 'retro')),
    resistant_element TEXT CHECK (resistant_element IN ('spicy', 'frosty', 'tingly', 'umami')),
    PRIMARY KEY (quest_nbr, course)
);

CREATE TABLE players (
    player_nbr SERIAL PRIMARY KEY,
    barmaid_name TEXT NOT NULL UNIQUE,
    gold INTEGER NOT NULL,
    barmaid_super_charge INTEGER NOT NULL,
    current_zone_nbr INTEGER NOT NULL REFERENCES zones(zone_nbr) DEFAULT 1,
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE player_inventory (
    player_nbr INTEGER NOT NULL REFERENCES players(player_nbr) ON DELETE CASCADE,
    item_nbr INTEGER NOT NULL REFERENCES items(item_nbr),
    quantity INTEGER NOT NULL,
    PRIMARY KEY (player_nbr, item_nbr)
);

-- Weapon/armor catalog. tier gates which adventurer levels can roll a given
-- item (mapped to level ranges in Python, not enforced here); rarity is
-- unused for now but will drive drop odds and, for 'shiny', a bonus effect.
CREATE TABLE equipment (
    equipment_nbr SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('weapon', 'armor', 'both')),
    tier TEXT NOT NULL CHECK (tier IN ('novice', 'veteran', 'elite')),
    rarity TEXT NOT NULL CHECK (rarity IN ('common', 'uncommon', 'rare', 'shiny')),
    damage_type TEXT CHECK (damage_type IN ('fillet', 'skewer', 'tenderize', 'retro')),
    element TEXT CHECK (element IN ('spicy', 'frosty', 'tingly', 'umami')),
    power INTEGER NOT NULL,
    cost INTEGER NOT NULL
);

-- Per-player progress for each of the 5 fixed adventurer classes (Paladin,
-- Warrior, Ranger, Rogue, Mage). Weapon/armor are re-rolled at party draft time.
CREATE TABLE player_adventurers (
    player_nbr INTEGER NOT NULL REFERENCES players(player_nbr) ON DELETE CASCADE,
    adventurer_class TEXT NOT NULL CHECK (adventurer_class IN ('Paladin', 'Warrior', 'Ranger', 'Rogue', 'Mage')),
    level INTEGER NOT NULL DEFAULT 1,
    weapon_nbr INTEGER REFERENCES equipment(equipment_nbr),
    armor_nbr INTEGER REFERENCES equipment(equipment_nbr),
    PRIMARY KEY (player_nbr, adventurer_class)
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
(1, 'The Awakening (Prologue)', 'The Corporate Wall is still a distant rumor, but local wildlife is becoming corrupted by synthetic runoff. Master Levain''s starter is failing. Bran ventures into the forbidden spore caves, encountering the Great Boar. After slaying the beast, she harvests the Wild Cave Spores, creating a volatile, powerful new Sourdough Starter. The village is saved, but the vanguard of the Corporate Wall is spotted on the horizon. Bran retrofits a cart into a mobile kitchen and leaves home to meet the threat head-on.'),
(2, 'The Roadside Inn & The Taplands', 'Bran establishes a foothold at a local Taplands tavern. Here, she recruits the Brigade. The plot focuses on liberating local farms from Syndicate buyouts and fighting off waves of processed monsters. The chapter concludes with a fierce "Cook-Off Duel" against Hans von Pretzel, the stubborn Taplands Brewmaster, earning his respect and recruiting him to the Command rather than defeating him as a foe.'),
(3, 'The City of Circuits', 'To upgrade her mobile cart''s heating elements and armor, Bran leads the brigade into the Eastern Dunes. They navigate the ruins of consumerism and recruit Unit Micro-90. The Syndicate ambushes them, led by Shift Supervisor Drake. Bran must out-cook and out-fight Drake''s "efficiency algorithms" using unpredictable, wild fermentation techniques that fry the Syndicate''s sensors.'),
(4, 'The Crashed Titan Sanctuary', 'The Corporate Wall accelerates its march, threatening to swallow the Taplands entirely. Bran seeks out the Crashed Titan in the Lake Crater, hoping to use its geothermal core as the ultimate oven. They are intercepted by Princess Red. A massive, emotional duel ensues between the two princesses (Blue and Red) and the two culinary philosophies.'),
(5, 'Breaking the Wall (The Climax)', 'Using the geothermal energy of the Titan, Bran bakes the Grand Feast of the Taplands, a meal so overflowing with Zest and vitality that it creates a shockwave of pure flavor. The Brigade charges the Corporate Wall, fighting through the sterile cafeterias and boardrooms. In the final confrontation against the Board of Directors (a monolithic AI entity made of ledgers and deep-fryer grease), Bran must prove that chaotic, loving craftsmanship will always overpower soulless optimization.'),
(6, 'A New Vintage (Epilogue)', 'The Wall crumbles, leaving behind fertile soil mixed with steel ruins. The Taplands are safe. Bran''s mobile cart becomes a legendary fixture of the roads, traveling from town to town, teaching the next generation how to keep the wild yeast alive.');

INSERT INTO zones (chapter_nbr, name, description, tavern_name, culinary_theme) VALUES
(1, 'The Village of the Hearth', 'The prologue setting. A quiet, rustic village anchored by Master Levain''s ancient wood-fired stone oven. It is the birthplace of the protagonist''s culinary journey.', 'The Flaming Flagon', 'Rustic Hearth Cooking'),
(2, 'The Taplands', 'A vibrant, chaotic region of amber barley fields, copper fermenting vats, and brave roadside inns. It is a place of authentic culture, slow-cooked meals, and community.', 'The Copper Vat Tavern', 'Wild Fermentation & Brewing'),
(3, 'City of Circuits', 'A fallen commercial monolith half-buried in the sand. Defunct neon signs and solid-state pre-decline electronics await salvage by brave foragers.', 'The Neon Skillet', 'Retro Diner & Salvage Cuisine'),
(4, 'The Crashed Titan Sanctuary', 'A colossal alien war-machine fallen into a lake. Its flooded crater serves as the ultimate future home base for the culinary resistance.', 'The Geothermal Galley', 'Deep-Crater Feasting'),
(5, 'The Corporate Wall', 'A creeping, grey-and-neon border of moving mega-fortresses. The Wall slowly rolls westward, ingesting boutique shops, independent farms, and taverns, only to extrude uniform, sterile franchise chains and endless vats of "pink slime."', 'The Liberated Cafeteria', 'Reclaimed Franchise Slop');

-- The existing 3 quests predate NARRATIVE.md; their boss (The Baconnator, a
-- boar) matches Chapter 1's "Great Boar," so they're placed in the Village
-- of the Hearth for now.
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

INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 1, item_nbr, 4 FROM items WHERE name = 'Mighty Malt';
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 2, item_nbr, 2 FROM items WHERE name = 'Aged Cheddar';
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 2, item_nbr, 3 FROM items WHERE name = 'Chilly Peppers';
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 3, item_nbr, 6 FROM items WHERE name = 'Holy Ham';
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 3, item_nbr, 4 FROM items WHERE name = 'Watery Onion';

INSERT INTO monsters (quest_nbr, course, name, hp, speed, attack, emoji) VALUES
(1, 1, 'Lil Nibbler', 70, 7, 10, '🐭'),
(1, 2, 'Ratta Rogue', 100, 6, 14, '🐀'),
(1, 3, 'Ratta Chewie, the Cellar King', 150, 5, 20, '👑'),
(2, 1, 'Little Gobbler', 120, 10, 16, '🌱'),
(2, 2, 'Greener Goblin', 180, 9, 22, '🥑'),
(2, 3, 'Gobla Cado Grande', 260, 8, 30, '👹'),
(3, 1, 'Braised Bandit', 180, 7, 24, '🥓'),
(3, 2, 'Mutton Chopper', 230, 6, 30, '🍖'),
(3, 3, 'The Baconnator', 320, 5, 38, '🐗');

-- Ratta Chewie is already "grown fat on the stew" - too tender to be tenderized further.
UPDATE monsters SET resistant_damage_type = 'tenderize' WHERE quest_nbr = 1 AND course = 3;
-- The Baconnator is "sizzling and vast" - a frosty attack barely registers.
UPDATE monsters SET resistant_element = 'frosty' WHERE quest_nbr = 3 AND course = 3;

-- Equipment seed data (rolled at party-draft time; see player_adventurers comment above).
-- Every damage_type and every element is covered by exactly one weapon/'both' item.
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
