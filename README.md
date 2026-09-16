# Battles and Barmaids: Enter the Taplands

## Description

A terminal-based RPG built as a Python fundamentals project. You play a rogue chef building a mobile kitchen-cart resistance against a creeping, franchise-slop Corporate Wall — buying ingredients, drafting a party of patrons, and cooking your way through dungeon-style quests.

Built with:
Python 3.11+
PostgreSQL via SQLAlchemy ORM
pygame for audio playback.

## API Reference

This project has no HTTP layer — `database.py` is the boundary between game logic and persistence, so it's documented here as the project's "API."

Function | Description

`get_ingredients()` | Ingredient name to cost, for the pantry and shop. |
`get_quests()` | Quest catalog, including drops and enemies. |
`get_zones()` | Zone catalog, for the tavern hub and zone progression. |
`get_player(barmaid_name)` | Saved state for a barmaid, or none. |
`create_player(player)` | Saves a new player and starting pantry. |
`save_player(player)` | Updates an existing save. |

## Retrospective

### How did the project's design evolve over time?

The schema started as set of tables mirroring the initial data.py file. From there, it went through several rounds of revision:

# Every _id column was renamed to a _nbr convention as that was I'm accustomed to.

# An equipment catalog was added ahead of the gameplay code that will use it. A planned "roll random gear by adventurer level" feature.

# chapters and zones tables were added to give the flat quest list real structure (each zone has its own tavern name and culinary theme)

# items.emoji was split out of items.name into its own column, so a "🌾 Mighty Malt"-style display string could keep being used in code while data stayed structured.

# The game's lore document went through a second draft. Both the lore and chapters document were updated to match.

# A pass focused on correctness/speed/memory/indexing tightened up issues that'd accumulated across that growth

Did you choose to use an ORM or raw SQL? Why?

# ORM. Simply put, I've been writing SQL for 10 years. ORM was the new content for me.
