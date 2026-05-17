# PKA Migrations

Lightweight SQL-file migrations for `pka.db`.

## Convention

- One file per migration: `NNN_<slug>.sql`.
- Each file contains **two SQL blocks** separated by a `-- +migrate Down` marker:
  - Everything above the marker is the **UP** block.
  - Everything below is the **DOWN** block.
- Migrations must be **idempotent on UP** (use `CREATE … IF NOT EXISTS`, `INSERT OR IGNORE`, etc.).
- Migrations must be **reversible on DOWN** (use `DROP … IF EXISTS`).
- Run order is filename lex sort. Never renumber existing files; only add new ones.

## Why not Alembic / sqlite-migrate / yoyo

PKA is a single-developer, single-database operating environment. Alembic-style autogen brings ORM coupling we don't have and don't want. Versioned raw-SQL files keep migrations grep-able, diff-able, and obvious — and they live in git next to the schema doc they update.

If/when PKA grows a second database or multi-developer concurrency, revisit. Until then: this is the framework.

## Usage

```bash
# Apply all pending migrations (idempotent)
python3 migrations/migrate.py up

# Apply through a specific migration
python3 migrations/migrate.py up --to 001_memory_table

# Roll back the most recent migration
python3 migrations/migrate.py down

# Roll back to a specific point
python3 migrations/migrate.py down --to 000_baseline

# Show applied migrations
python3 migrations/migrate.py status
```

The runner records applied migrations in the `schema_migrations` table (created on first run).

## Files

- `migrate.py` — the runner.
- `NNN_<slug>.sql` — individual migrations.
