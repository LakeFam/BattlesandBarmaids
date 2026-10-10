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
    ignore_def BOOLEAN NOT NULL DEFAULT FALSE,
    weapon_nbr INTEGER REFERENCES equipment(equipment_nbr),
    armor_nbr INTEGER REFERENCES equipment(equipment_nbr),
    PRIMARY KEY (run_nbr, slot),
    UNIQUE (run_nbr, adventurer_class),
    CHECK (hp <= max_hp)
);
