-- Quest 1 (Mystery Meat!) was won even if the barmaid only polished tumblers. The rats now hit hard enough
-- that she has to help, and drop a mix of the ingredients she spends instead of only Mighty Malt.

UPDATE monsters SET hp = 110, attack = 20 WHERE quest_nbr = 1 AND course = 1;
UPDATE monsters SET hp = 165, attack = 26 WHERE quest_nbr = 1 AND course = 2;
UPDATE monsters SET hp = 240, attack = 32 WHERE quest_nbr = 1 AND course = 3;

DELETE FROM quest_drops WHERE quest_nbr = 1;
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 1, item_nbr, 2 FROM items
    WHERE name IN ('Mighty Malt', 'Aged Cheddar', 'Watery Onion', 'Chilly Peppers', 'Ghost Pepperoni');
