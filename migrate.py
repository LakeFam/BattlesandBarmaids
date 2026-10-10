# Applies new migrations/*.sql files in filename order, once each, on top of schema.sql.
from pathlib import Path

import psycopg
from sqlalchemy.engine import make_url

from database import DATABASE_URL

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Returns the filenames it applied.
def migrate(database_url=DATABASE_URL):
    libpq_url = make_url(database_url).set(drivername="postgresql").render_as_string(hide_password=False)
    applied = []
    # One transaction: all new migrations apply, or none do.
    with psycopg.connect(libpq_url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('battles_and_barmaids_migrate'))")  # one migrator at a time
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """)
        done = {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))  # multi-statement works without parameters
            conn.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied

if __name__ == "__main__":
    names = migrate()
    if names:
        print(f"Applied: {', '.join(names)}")
    else:
        print("Database is up to date.")
