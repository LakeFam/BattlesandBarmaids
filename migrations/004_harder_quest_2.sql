-- Quest 2 (Goblin Raid on the Larder) was a guaranteed win. The goblins now hit almost as hard as the boss,
-- and richer drops make the risk worth it.

UPDATE monsters SET hp = 130, attack = 23 WHERE quest_nbr = 2 AND course = 1;
UPDATE monsters SET hp = 195, attack = 29 WHERE quest_nbr = 2 AND course = 2;
UPDATE monsters SET hp = 280, attack = 37 WHERE quest_nbr = 2 AND course = 3;

UPDATE quest_drops SET quantity = 4
    WHERE quest_nbr = 2 AND item_nbr IN (SELECT item_nbr FROM items WHERE name IN ('Aged Cheddar', 'Chilly Peppers'));
INSERT INTO quest_drops (quest_nbr, item_nbr, quantity)
    SELECT 2, item_nbr, 3 FROM items WHERE name = 'Ghost Pepperoni';
