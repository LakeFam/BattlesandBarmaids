-- Seed for a run's dice. The same seed and the same actions replay the same fight.
-- 53 bits, so JavaScript clients could read it exactly.

ALTER TABLE quest_runs ADD COLUMN rng_seed BIGINT;
UPDATE quest_runs SET rng_seed = floor(random() * 9007199254740992)::BIGINT;
ALTER TABLE quest_runs ALTER COLUMN rng_seed SET NOT NULL;
