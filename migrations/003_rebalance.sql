-- Rebalance: Saffron's shots now double a patron's next hit, and the boss quest's courses have more HP.

ALTER TABLE quest_run_patrons RENAME COLUMN ignore_def TO double_strike;

UPDATE monsters SET hp = 235 WHERE quest_nbr = 3 AND course = 1;
UPDATE monsters SET hp = 300 WHERE quest_nbr = 3 AND course = 2;
UPDATE monsters SET hp = 415 WHERE quest_nbr = 3 AND course = 3;
