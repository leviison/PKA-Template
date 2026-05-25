# PKA Migrations

Lightweight SQL-file migrations for the three PKA database tiers: `pka.db`, `projects.db`, `personal.db`.

## Convention

- One file per migration: `NNN_<slug>.sql`.
- Each file contains **two SQL blocks** separated by a `-- +migrate Down` marker:
  - Everything above the marker is the **UP** block.
  - Everything below is the **DOWN** block.
- Migrations must be **idempotent on UP** (use `CREATE … IF NOT EXISTS`, `INSERT OR IGNORE`, etc.).
- Migrations must be **reversible on DOWN** (use `DROP … IF EXISTS`).
- Run order is filename lex sort. Never renumber existing files; only add new ones.

## Why not Alembic / sqlite-migrate / yoyo

PKA is a single-developer, three-database operating environment. Alembic-style autogen brings ORM coupling we don't have and don't want. Versioned raw-SQL files keep migrations grep-able, diff-able, and obvious — and they live in git next to the schema doc they update.

## Three-tier layout

Each tier has its own migration directory and its own `schema_migrations` table:

- `migrations/` — `pka.db` migrations (Operations tier).
- `migrations/personal/` — `personal.db` migrations (Owner tier).
- `migrations/projects/` — `projects.db` migrations (Projects tier).

The unified `migrate.py` runner targets a single tier per invocation via `--dir` + `--db`.

## Usage

```bash
# pka.db migrations (default — runner targets pka.db, scans migrations/)
python3 migrations/migrate.py up
python3 migrations/migrate.py status
python3 migrations/migrate.py down

# personal.db migrations
python3 migrations/migrate.py up \
    --dir migrations/personal \
    --db ~/PKA-Data/personal.db

# projects.db migrations
python3 migrations/migrate.py up \
    --dir migrations/projects \
    --db projects.db

# Apply through a specific migration
python3 migrations/migrate.py up --to 002_token_economics

# Roll back the most recent migration
python3 migrations/migrate.py down

# Roll back to a specific point
python3 migrations/migrate.py down --to 001_memory_table
```

The runner records applied migrations in each tier's `schema_migrations` table (created on first run).

## v1.2.0 baseline

A fresh `python3 setup.py` install embeds the v1.2.0 baseline DDL directly into the three database files and records the corresponding migrations as already-applied in each tier's `schema_migrations`. The migration files in `migrations/`, `migrations/personal/`, and `migrations/projects/` exist to:

1. Document the canonical DDL for each substrate addition (audit trail + reference).
2. Apply incrementally to evolve the schema after install (new owners add migration `NNN_<slug>.sql` per the convention above).

The baseline migrations recorded as already-applied on a fresh install:

- `pka.db`: `001_memory_table`, `002_token_economics`, `003_split_projects_db`, `004_memory_episodic_view`, `006_briefs_project_slug`, `007_feedback_rater`
- `projects.db`: `003_split_projects_db` (historical bootstrap), `001_projects_memory_substrate`
- `personal.db`: `001_owner_observability`

(No migration `005` in the pka.db baseline — PKA's `005_template_readiness_pka.sql` was a rebuild migration whose effect is baked into the template's `setup.py` directly. There is no historical state to migrate from on a fresh install, so the rebuild would no-op.)

PKA-current uses a longer migration history (the canonical instance ran each delta as a separate migration as it landed). The template ships the consolidated v1.2.0 baseline directly. PKA's longer history is preserved in PKA's repo as audit context; template owners inherit the result.

## Files

- `migrate.py` — the unified runner.
- `NNN_<slug>.sql` — individual migrations, one per tier in its own subdirectory.
