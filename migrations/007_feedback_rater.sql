-- 007_feedback_rater.sql
-- PKA-Template v1.2.0 baseline — feedback rater + new feedback model.
--
-- Adds the `rater` column to `feedback` so each rating row carries the
-- identity of the rater (owner or orchestrator). This is the substrate
-- change that enables the `leroy_rates_levi_audits` feedback model:
-- Leroy auto-rates routine deliveries; the owner audits a sample at
-- configurable cadence; owner-rated rows always supersede orchestrator-
-- rated rows for the same (brief_ref, team_member) pair via ordering.
--
-- Template note: the model identifier `leroy_rates_levi_audits` retains
-- the historical PKA naming for continuity with PKA's settings rows. A
-- future generic rename to `orchestrator_rates_owner_audits` is a
-- separate productization-discipline call.
--
-- Default 'levi' makes the backfill correct for any future Levi/owner-
-- rated rows. On a fresh template install the feedback table is empty,
-- so no backfill UPDATE is needed (PKA's variant carries an id=175
-- backfill for one historical Leroy-rated row that exists only in
-- PKA-current).
--
-- The CHECK enforces the two-value enum (`levi` | `leroy`).
--
-- Schema change is constant-time on SQLite: ALTER TABLE ADD COLUMN with
-- a default of a constant literal is a metadata-only operation.

-- 1. Add the rater column.
ALTER TABLE feedback ADD COLUMN rater TEXT NOT NULL DEFAULT 'levi'
    CHECK (rater IN ('levi','leroy'));

-- 2. Activate the new feedback model.
UPDATE settings
   SET value='leroy_rates_levi_audits',
       updated_at=datetime('now')
 WHERE key='feedback_model';

-- 3. Insert the audit cadence row (default 7 days).
INSERT OR IGNORE INTO settings (key, value)
VALUES ('audit_cadence_days', '7');


-- +migrate Down

-- DOWN: revert settings first, then drop the column.

UPDATE settings
   SET value='ritual',
       updated_at=datetime('now')
 WHERE key='feedback_model';

DELETE FROM settings WHERE key='audit_cadence_days';

ALTER TABLE feedback DROP COLUMN rater;
