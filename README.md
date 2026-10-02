# Battles and Barmaids: Enter the Taplands

A turn-based tavern RPG. You play a barmaid running a mobile kitchen-cart in the resistance against the Corporate Wall, a creeping line of franchise-slop fortresses. You buy ingredients, draft a party of 3 adventurer patrons, and fight through quests of 3 "courses," one monster per course. Each round, the barmaid serves or throws an ingredient, and then the patrons and the monster act automatically in speed order.

The game started as a terminal app for my SQL course, with its data in PostgreSQL through SQLAlchemy. **For this portfolio project, I'm putting a Flask REST API in front of the game so it can be played over HTTP, one request per turn.** The app runs as two Docker containers: a Flask web service and a Postgres database.

The full proposal is in [docs/week1-report.txt](docs/week1-report.txt).

## Status

**Working now (Week 2)**

- Flask API with the world catalog and player-save endpoints (listed below)
- `Dockerfile` for the API (gunicorn on `python:3.13-slim`, running as a non-root user)
- `docker-compose.yml` with `web` and `db` services. Postgres loads `schema.sql` (tables and seed data) on first start, and the app reads its connection from `DATABASE_URL`.
- Schema updates for the API: `players.barmaid_class`, plus CHECK constraints on gold, quantities, costs and stats

**Next**

- Week 3: quest-run endpoints (start a quest, draft a party, take combat turns), and pytest tests. This means separating the combat rules from the terminal code (`input()`, `print()` and pygame sound) so the API can call them.
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
     -d '{"barmaid_name": "Bran", "barmaid_class": "Bunhilda"}'

curl -X POST http://localhost:5000/players/Bran/purchases \
     -H "Content-Type: application/json" \
     -d '{"item_nbr": 1, "quantity": 2}'
```

The database is also published on `localhost:5434` (user `postgres`, password `postgres`, database `battles_and_barmaids`) for psql or pgAdmin. These credentials are for local development only.

`schema.sql` only runs when the database volume is empty. After changing the schema, reset the database with:

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

There's no login; the barmaid name identifies the save.

| Method | Path | Description |
|---|---|---|
| POST | `/players` | Create a save. Body: `{"barmaid_name": "Bran", "barmaid_class": "Bunhilda"}`. Class is `Marigold`, `Saffron` or `Bunhilda`. Returns `201`, or `409` if the name is taken. |
| GET | `/players/<barmaid_name>` | Gold, super charge, current zone, class and pantry |
| DELETE | `/players/<barmaid_name>` | Delete the save and its inventory. Returns `204`. |
| GET | `/players/<barmaid_name>/inventory` | Ingredient quantities |
| POST | `/players/<barmaid_name>/purchases` | Buy ingredients. Body: `{"item_nbr": 3, "quantity": 2}`. Returns `422` if the player can't afford it. |
| GET | `/players/<barmaid_name>/adventurers` | Level and gear for each of the 5 adventurer classes |

### Planned: quest runs (Week 3)

| Method | Path | Description |
|---|---|---|
| POST | `/players/<barmaid_name>/runs` | Start a quest |
| GET | `/players/<barmaid_name>/runs` | Run history |
| GET | `/runs/<run_nbr>` | Current state of a run |
| POST | `/runs/<run_nbr>/party` | Draft 3 of the 5 patrons |
| POST | `/runs/<run_nbr>/actions` | Take the barmaid's turn. The server resolves the rest of the round. |
| DELETE | `/runs/<run_nbr>` | Abandon the run |

## Playing the terminal version

The original game still runs in a terminal and uses the same database. It needs Python 3.12+ and a sound device.

```bash
docker compose up -d db
pip install -r requirements-game.txt
python main.py
```

`database.py` connects to the Compose database on `localhost:5434` by default. To use a different server, set `DATABASE_URL`, for example `postgresql+psycopg://user:password@localhost:5432/battles_and_barmaids`.

## Project layout

| File | Purpose |
|---|---|
| `app.py` | Flask API |
| `database.py` | SQLAlchemy models and the database connection, shared by the API and the terminal game |
| `schema.sql` | Table definitions and seed data. This is the source of truth for the schema. |
| `Dockerfile`, `docker-compose.yml` | Container setup |
| `requirements.txt` | API dependencies (installed in the image) |
| `requirements-game.txt` | Adds pygame-ce and rich for the terminal game |
| `main.py`, `entities.py`, `combat.py`, `shop.py`, `data.py` | Terminal game |
| `NARRATIVE.md` | Story, setting and characters |
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
