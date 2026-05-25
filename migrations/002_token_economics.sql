-- 002_token_economics.sql
-- BRIEF-127 — Token economics instrumentation (Phase 1: capture)
--
-- Adds two tables:
--   1. `model_pricing` — versioned per-model price table (per-1M-token rates,
--      per-rate-class: input / output / cache_write / cache_read). Rows are
--      immutable snapshots; pricing changes add a new row, never UPDATE.
--   2. `economics` — one row per deliverable (1:1, FK on deliverables.id),
--      capturing the Anthropic-specific breakdown: cache-creation tokens,
--      cache-read tokens, input/output split, model, and the USD cost
--      computed at write time against a specific `model_pricing.id`.
--
-- Design notes (full reasoning in
-- /home/bzadmin/Documents/PKA/owners_inbox/token_economics_phase1_iris.md):
--
--   * Separate `economics` table, not wider `deliverables`. Keeps the
--     Anthropic-specific columns out of `deliverables` so when BACKLOG-006/
--     007/008 lands a non-Anthropic provider, the economics table extends
--     (or a per-provider table joins in) without touching `deliverables`.
--
--   * Cost stored at write time, with `model_pricing_id` FK locking in the
--     pricing snapshot used. Historical accuracy preserved across price
--     changes; auditability requirement satisfied.
--
--   * Pricing table is provider-agnostic in shape — `provider` column
--     anticipates BACKLOG-006/007/008 without implementing it. All seed
--     rows are 'anthropic' today.
--
--   * Existing `deliverables.tokens_used` / `tool_uses` / `duration_ms`
--     columns stay where they are. Those are the agent's self-reported
--     envelope stats; the new economics row carries the API-side breakdown.
--     Both populate from the same task-completion notification.
--
-- Idempotent: every CREATE uses IF NOT EXISTS, every INSERT uses OR IGNORE.
-- Reversible: see the DOWN block.


-- ---------- model_pricing ----------

CREATE TABLE IF NOT EXISTS model_pricing (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    provider                    TEXT NOT NULL,
    model                       TEXT NOT NULL,
    -- All prices in USD per 1,000,000 tokens. Float is acceptable here —
    -- cost is always recomputed at insert time against the snapshot row,
    -- never accumulated by repeated FP arithmetic.
    input_price_per_1m          REAL NOT NULL,
    output_price_per_1m         REAL NOT NULL,
    cache_write_price_per_1m    REAL NOT NULL,
    cache_read_price_per_1m     REAL NOT NULL,
    currency                    TEXT NOT NULL DEFAULT 'USD',
    effective_from              TEXT NOT NULL,
    last_verified_at            TEXT NOT NULL,
    source_url                  TEXT,
    notes                       TEXT,
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),

    -- A given (provider, model, effective_from) triple is unique — we add
    -- a new row when pricing changes, we never UPDATE in place.
    UNIQUE (provider, model, effective_from)
);

CREATE INDEX IF NOT EXISTS model_pricing_lookup_idx
    ON model_pricing (provider, model, effective_from DESC);


-- ---------- economics ----------

CREATE TABLE IF NOT EXISTS economics (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    deliverable_id          INTEGER NOT NULL UNIQUE
                                REFERENCES deliverables(id) ON DELETE CASCADE,
    provider                TEXT NOT NULL DEFAULT 'anthropic',
    model                   TEXT NOT NULL,
    -- Token breakdown. The agent task-completion notification gives us
    -- total_tokens (already in deliverables.tokens_used) and (on recent
    -- Claude Code versions) the cache-creation / cache-read split. Where
    -- the API doesn't surface a rate-class, we record 0 (not NULL) so
    -- aggregations work without coalesce noise.
    input_tokens            INTEGER NOT NULL DEFAULT 0,
    output_tokens           INTEGER NOT NULL DEFAULT 0,
    cache_creation_tokens   INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens       INTEGER NOT NULL DEFAULT 0,
    -- USD cost, computed at write time against model_pricing_id below.
    -- Stored as REAL (sub-cent precision matters when summing across
    -- thousands of small invocations).
    estimated_cost_usd      REAL NOT NULL,
    model_pricing_id        INTEGER NOT NULL
                                REFERENCES model_pricing(id) ON DELETE RESTRICT,
    -- Cache hit rate, pre-computed for query convenience. Defined as
    -- cache_read_tokens / (cache_read_tokens + input_tokens), the share of
    -- input-side tokens served from cache. NULL when denominator is 0.
    cache_hit_rate          REAL,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),

    -- Sanity: non-negative token counts.
    CHECK (input_tokens >= 0),
    CHECK (output_tokens >= 0),
    CHECK (cache_creation_tokens >= 0),
    CHECK (cache_read_tokens >= 0),
    CHECK (estimated_cost_usd >= 0)
);

CREATE INDEX IF NOT EXISTS economics_deliverable_idx
    ON economics (deliverable_id);
CREATE INDEX IF NOT EXISTS economics_model_idx
    ON economics (model);
CREATE INDEX IF NOT EXISTS economics_created_at_idx
    ON economics (created_at DESC);


-- ---------- seed pricing rows ----------
-- Anthropic public pricing as of 2026-05-19, captured from
-- https://www.anthropic.com/pricing (last verified 2026-05-19).
--
-- These are the three tiers PKA routes to today:
--   * claude-opus-4-7         — Opus 4.7 ($15 / $75 per 1M; cache write 1.25×
--                               input, cache read 0.1× input — standard
--                               Anthropic cache pricing convention).
--   * claude-sonnet-4-6       — Sonnet 4.6 ($3 / $15 per 1M).
--   * claude-haiku-4-5-20251001 — Haiku 4.5 ($0.80 / $4 per 1M).
--
-- Convention: cache_write = 1.25× input, cache_read = 0.10× input.
-- See deliverable §3 for the "last verified" capture procedure.

INSERT OR IGNORE INTO model_pricing (
    provider, model,
    input_price_per_1m, output_price_per_1m,
    cache_write_price_per_1m, cache_read_price_per_1m,
    effective_from, last_verified_at, source_url, notes
) VALUES
    ('anthropic', 'claude-opus-4-7',
     15.00, 75.00, 18.75, 1.50,
     '2026-05-19', '2026-05-19',
     'https://www.anthropic.com/pricing',
     'Opus 4.7. Cache write = 1.25x input, cache read = 0.10x input.'),
    ('anthropic', 'claude-sonnet-4-6',
     3.00, 15.00, 3.75, 0.30,
     '2026-05-19', '2026-05-19',
     'https://www.anthropic.com/pricing',
     'Sonnet 4.6. Cache write = 1.25x input, cache read = 0.10x input.'),
    ('anthropic', 'claude-haiku-4-5-20251001',
     0.80, 4.00, 1.00, 0.08,
     '2026-05-19', '2026-05-19',
     'https://www.anthropic.com/pricing',
     'Haiku 4.5. Cache write = 1.25x input, cache read = 0.10x input.');


-- +migrate Down

DROP INDEX IF EXISTS economics_created_at_idx;
DROP INDEX IF EXISTS economics_model_idx;
DROP INDEX IF EXISTS economics_deliverable_idx;
DROP TABLE IF EXISTS economics;
DROP INDEX IF EXISTS model_pricing_lookup_idx;
DROP TABLE IF EXISTS model_pricing;
