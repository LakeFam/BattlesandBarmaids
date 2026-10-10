# Battles and Barmaids: Enter the Taplands

A turn-based tavern RPG. You play a barmaid running a mobile kitchen-cart in the resistance against the Corporate Wall, a creeping line of franchise-slop fortresses. You buy ingredients, draft a party of 3 adventurer patrons, and fight through quests of 3 "courses," one monster per course. Each round, the barmaid serves or throws an ingredient, and then the patrons and the monster act automatically in speed order.

The game started as a terminal app for my SQL course, with its data in PostgreSQL through SQLAlchemy. **For this portfolio project, I'm putting a Flask REST API in front of the game so it can be played over HTTP, one request per turn.** The app runs as two Docker containers: a Flask web service and a Postgres database.

The full proposal is in [docs/week1-report.txt](docs/week1-report.txt). One change since then: saves are now one per barmaid class instead of a player-chosen `barmaid_name`, so the proposal's `/players/<barmaid_name>` paths are `/players/<barmaid_class>`.

## Status

**Week 2**

- Flask API with the world catalog and player-save endpoints (listed below)
- `Dockerfile` for the API (gunicorn on `python:3.13-slim`, running as a non-root user)
- `docker-compose.yml` with `web` and `db` services. Postgres loads `schema.sql` (tables and seed data) on first start, and the app reads its connection from `DATABASE_URL`.
- Schema updates for the API: `players.barmaid_class`, plus CHECK constraints on gold, quantities, costs and stats

**Week 3**

- pytest tests: integration tests for the API (using pytest-flask) and unit tests for the combat rules. See [Running the tests](#running-the-tests).
- Combat rules separated from the terminal code. `entities.py` and `combat.py` return an event log (text plus sound names) and raise `ActionError` for invalid barmaid actions, instead of calling `print()`, `input()` or pygame. `terminal.py` prints and plays the events, and only `audio.py` loads pygame.
- Quest-run tables (`quest_runs` and `quest_run_patrons`) from the proposal, added as the first migration. They also store the monster's current attack and speed and each patron's current attack, because abilities change those mid-fight.
- Migrations: `migrate.py` applies new files in `migrations/` on top of `schema.sql`, so schema changes no longer mean deleting the database.

**Next**

- Quest-run endpoints (start a quest, draft a party, take combat turns) that call the combat rules directly and keep a run's state in the quest-run tables.
- Week 4: deploy to a cloud provider and/or add a GitHub Actions workflow that builds and tests the app.

## Running it with Docker

You need Docker Desktop (or another Docker engine with Compose).

```bash
docker compose up --build
```

The API is then at http://localhost:5000. Try:

```bash
curl http://localhost:5000/zones
curl http://localhost:5000/quests/3

curl -X POST http://localhost:5000/players \
     -H "Content-Type: application/json" \
     -d '{"barmaid_class": "Bunhilda"}'

curl -X POST http://localhost:5000/players/Bunhilda/purchases \
     -H "Content-Type: application/json" \
     -d '{"item_nbr": 1, "quantity": 2}'
```

The database is also published on `localhost:5434` (user `postgres`, password `postgres`, database `battles_and_barmaids`) for psql or pgAdmin. These credentials are for local development only.

`schema.sql` only runs when the database volume is empty. Later schema changes go in numbered files in `migrations/`, and `migrate.py` applies the ones a database hasn't had yet, recording each in a `schema_migrations` table. The `web` container runs it on every start. To start over from scratch instead, which deletes your saves:

```bash
docker compose down -v
docker compose up --build
```

## API endpoints

All bodies are JSON. Errors come back as `{"error": "..."}` with `404` (not found), `409` (conflicts with current state) or `422` (invalid input).

### World catalog (read-only)

| Method | Path | Description |
|---|---|---|
| GET | `/chapters` | All story chapters |
| GET | `/zones` | All zones. Optional `?chapter_nbr=2` |
| GET | `/zones/<zone_nbr>` | One zone, with its tavern name and culinary theme |
| GET | `/zones/<zone_nbr>/quests` | The quests in a zone |
| GET | `/quests/<quest_nbr>` | One quest, with its 3 monsters (one per course) and item drops |
| GET | `/items` | The ingredient catalog with prices |
| GET | `/equipment` | Weapons and armor. Optional `?type=weapon\|armor\|both`, `?tier=novice\|veteran\|elite`, `?rarity=common\|uncommon\|rare\|shiny` |

### Players

There's no login. Each barmaid has one save, shared with the terminal game.

| Method | Path | Description |
|---|---|---|
| POST | `/players` | Create a save. Body: `{"barmaid_class": "Bunhilda"}`. Class is `Marigold`, `Saffron` or `Bunhilda`. Returns `201`, or `409` if that barmaid already has a save. |
| GET | `/players/<barmaid_class>` | Gold, super charge, current zone, class and pantry |
| DELETE | `/players/<barmaid_class>` | Delete the save and its inventory. Returns `204`. |
| GET | `/players/<barmaid_class>/inventory` | Ingredient quantities |
| POST | `/players/<barmaid_class>/purchases` | Buy ingredients. Body: `{"item_nbr": 3, "quantity": 2}`. Returns `422` if the player can't afford it. |
| GET | `/players/<barmaid_class>/adventurers` | Level and gear for each of the 5 adventurer classes |

### Planned: quest runs

| Method | Path | Description |
|---|---|---|
| POST | `/players/<barmaid_class>/runs` | Start a quest |
| GET | `/players/<barmaid_class>/runs` | Run history |
| GET | `/runs/<run_nbr>` | Current state of a run |
| POST | `/runs/<run_nbr>/party` | Draft 3 of the 5 patrons |
| POST | `/runs/<run_nbr>/actions` | Take the barmaid's turn. The server resolves the rest of the round. |
| DELETE | `/runs/<run_nbr>` | Abandon the run |

## Playing the terminal version

The original game still runs in a terminal and uses the same database. It needs Python 3.12+ and a sound device.

```bash
docker compose up -d db
pip install -r requirements-game.txt
python migrate.py      # after pulling schema changes
python main.py
```

`database.py` connects to the Compose database on `localhost:5434` by default. To use a different server, set `DATABASE_URL`, for example `postgresql+psycopg://user:password@localhost:5432/battles_and_barmaids`.

## Running the tests

The tests use [pytest](https://docs.pytest.org/) and [pytest-flask](https://pytest-flask.readthedocs.io/). They need Python 3.12+ and the Compose database.

```bash
docker compose up -d db
python -m venv .venv
.venv\Scripts\activate          # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
```

The tests run against their own database, `battles_and_barmaids_test`. pytest rebuilds it from `schema.sql` at the start of every run, so your saved games are never touched. To run the tests against another server, set `TEST_DATABASE_URL`. Its database name must end in `_test`, because that database gets dropped and recreated.

| File | What it tests |
|---|---|
| `tests/test_catalog_api.py` | Integration: the read-only catalog endpoints return the seed data, filter correctly, and send JSON errors |
| `tests/test_players_api.py` | Integration: creating, reading and deleting saves, and buying ingredients, including rejected input |
| `tests/test_combat.py` | Unit: weapon resistance, attack and armor math, barmaid actions (including rejected ones) and combat rounds. Also checks that the rules never load pygame. |
| `tests/test_quest_runs_schema.py` | Integration: the quest-run tables' constraints (one unfinished run per player, consistent status, valid patron state) and that migrations only apply once |
| `tests/test_app_helpers.py` | Unit: input validation helper in `app.py` |
| `tests/conftest.py` | Shared setup: builds the test database from `schema.sql` plus migrations, and provides the `app` fixture that pytest-flask's `client` fixture uses |

## Project layout

| File | Purpose |
|---|---|
| `app.py` | Flask API |
| `database.py` | SQLAlchemy models and the database connection, shared by the API and the terminal game |
| `schema.sql` | Starting table definitions and seed data |
| `migrations/`, `migrate.py` | Schema changes since `schema.sql`, and the script that applies them |
| `Dockerfile`, `docker-compose.yml` | Container setup |
| `requirements.txt` | API dependencies (installed in the image) |
| `requirements-game.txt` | Adds pygame-ce and rich for the terminal game |
| `requirements-dev.txt` | Adds pytest and pytest-flask for the tests. The tests don't need pygame. |
| `tests/`, `pytest.ini` | Tests and pytest settings |
| `entities.py`, `combat.py`, `data.py` | Game rules and text: barmaids, patrons, monsters and combat. No terminal or sound code, so the API can use them. |
| `main.py`, `terminal.py`, `shop.py`, `audio.py` | Terminal game: menus, prompts, screen output and pygame sound |
| `NARRATIVE.md` | This game's world, characters and how it plays |
| `docs/story-plans.md` | The full story, planned for a future game |
| `project.drawio` | Design diagram |
| `docs/week1-report.txt` | Project proposal |

## Background: SQL course retrospective

### How did the project's design evolve over time?

The schema started as a set of tables mirroring the original `data.py` file. From there, it went through several rounds of revision:

1. Every `_id` column was renamed to a `_nbr` convention, since that's what I'm used to.
2. An equipment catalog was added ahead of the gameplay code that will use it, for a planned "roll random gear by adventurer level" feature.
3. `chapters` and `zones` tables were added to give the flat quest list real structure. Each zone has its own tavern name and culinary theme.
4. `items.emoji` was split out of `items.name` into its own column, so the code could keep using "🌾 Mighty Malt"-style display strings while the data stayed structured.
5. The game's lore document went through a second draft, and the chapters data was updated to match.
6. A final pass on correctness, speed, memory and indexing cleaned up issues that had built up along the way.

### Did you choose to use an ORM or raw SQL? Why?

ORM. I've been writing SQL for 10 years, so the ORM was the new material for me.
