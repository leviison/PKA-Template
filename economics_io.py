"""
economics_io.py — helper for Phase 1 token-economics capture.

The DB is authoritative. This module owns the contract from agent
task-completion data to (1) the `deliverables.tokens_used` / `tool_uses`
/ `duration_ms` envelope columns and (2) the `economics` row that
carries the Anthropic-specific token breakdown and the USD cost computed
at write time.

Contract (full reasoning in the source deliverable
`owners_inbox/token_economics_phase1_iris.md`, lifted into PKA_Template
from PKA at template-snapshot time):

  - Every agent invocation that produces a `deliverables` row should call
    `write_deliverable_with_economics(...)` instead of bare
    `INSERT INTO deliverables (...)`. The helper inserts the deliverables
    row, looks up the current pricing for the model, computes the USD
    cost, and inserts the matching `economics` row in one transaction.

  - Agents pass what their task-completion notification gives them:
        total_tokens, tool_uses, duration_ms,
        input_tokens, output_tokens,
        cache_creation_tokens, cache_read_tokens,
        model
    Anything an agent cannot report yet (because their host's task
    notification doesn't surface it) defaults to 0 — aggregate queries
    stay numeric-clean and a later post-completion hook can backfill
    via `update_economics(...)`.

  - Pricing is locked in at write time. The `economics.model_pricing_id`
    FK records which pricing snapshot was used. If Anthropic publishes
    new prices, INSERT a new `model_pricing` row — never UPDATE in place.

Capture mechanism — Option A (Phase 1):
  Agents self-populate via this helper. The discipline is centralised in
  one function so each shim doesn't reinvent the SQL. When PKA's scale
  warrants Option C (hybrid post-completion hook), the hook can call the
  same `update_economics()` helper to backfill what the agent didn't
  have access to. The single insert/update point is the architectural
  seam.

Provider note:
  Phase 1 is Anthropic-only. The `provider` argument exists and the
  `model_pricing` table is provider-keyed, so when BACKLOG-006/007/008
  activates multi-provider, non-Anthropic pricing rows drop in without
  schema change. `settings.multi_model_enabled` is consulted only by
  Leroy's routing logic — this helper records whatever provider/model
  the caller passes.

## Demotion criterion

Split criterion. `economics_io.py` lives in the named exception class
(instrumentation) per CLAUDE.md's productization discipline. Its
supporting checks (rule-of-three, stable-interface) are recorded as
deferred-evidence-pending; the retroactive supporting-check evaluation
fires after enough deliverables have been instrumented to assess
whether the value-asymmetry case holds at present-day workflow. The
demotion criterion below is independent of that evaluation — a tool
can be in deferred-evidence-pending status and still have a defined
demotion criterion.

Write-path: retire the write-path when any of:

  (a) Token economics capture moves to a harness-level post-completion
      hook architecture — the seam moves out of the persona-side helper
      into the harness, and `economics_io.py` becomes redundant for new
      captures, OR
  (b) The economics-data shape changes substantively — multi-provider
      routing activates (`multi_model_enabled=true`) and the
      `economics` table requires a different write contract that this
      helper's signature can't accommodate cleanly, OR
  (c) The deferred-evidence-pending supporting checks fail their
      post-deployment evaluation — i.e., the retroactive rule-of-three /
      stable-interface review concludes that economics_io.py shouldn't
      have been built and the instrumentation should have been done
      differently. (This is the discipline's self-corrective path; if
      it fires, it's an instructive case rather than a routine
      retirement.)

Read-path: permanent infrastructure. Historical token-economics data
is interpretable forever — cost trends, model-migration cost analysis,
owner-vs-team economics ratios, productization cost-vs-benefit
projections all depend on it. The `economics` table's read-path
retires only if PKA's economics-instrumentation discipline is
abandoned entirely, which would itself be a separate Intent-layer
decision.

Source: owners_inbox/tool_demotion_criteria_proposal.md (Levi-approved
2026-05-20). Update via Leroy-drafted, Levi-approved deliverable; do not
modify unilaterally.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_DB = Path(__file__).resolve().parent / "pka.db"


def _lookup_pricing_id(
    conn: sqlite3.Connection,
    provider: str,
    model: str,
) -> tuple[int, float, float, float, float]:
    """Return (id, input_price, output_price, cache_write_price, cache_read_price)
    for the most recently effective pricing row for (provider, model).

    Raises ValueError if no pricing row exists — callers must INSERT one
    into `model_pricing` before recording economics for a new model. This
    is by design: silent zero-cost rows for un-priced models would be a
    bug in the audit trail.
    """
    row = conn.execute(
        """
        SELECT id,
               input_price_per_1m,
               output_price_per_1m,
               cache_write_price_per_1m,
               cache_read_price_per_1m
        FROM model_pricing
        WHERE provider = ? AND model = ?
          AND effective_from <= datetime('now')
        ORDER BY effective_from DESC
        LIMIT 1;
        """,
        (provider, model),
    ).fetchone()
    if row is None:
        raise ValueError(
            f"No model_pricing row for provider={provider!r} model={model!r}. "
            f"Add a row to model_pricing before recording economics for this model."
        )
    return row  # type: ignore[return-value]


def compute_cost_usd(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    input_price_per_1m: float,
    output_price_per_1m: float,
    cache_write_price_per_1m: float,
    cache_read_price_per_1m: float,
) -> float:
    """USD cost = sum over rate-classes of (tokens * price_per_1m / 1_000_000).

    Pure function — exposed for tests and for the audit trail (the
    deliverable shows the math).
    """
    return (
        input_tokens * input_price_per_1m
        + output_tokens * output_price_per_1m
        + cache_creation_tokens * cache_write_price_per_1m
        + cache_read_tokens * cache_read_price_per_1m
    ) / 1_000_000.0


def compute_cache_hit_rate(
    input_tokens: int,
    cache_read_tokens: int,
) -> Optional[float]:
    """Cache-read share of input-side tokens.

    Defined as cache_read_tokens / (cache_read_tokens + input_tokens) —
    "what fraction of input we'd otherwise have paid full price for did
    we serve from cache". NULL when denominator is 0 (the deliverable
    section §5 explains why we don't collapse 0/0 to 0.0).
    """
    denom = cache_read_tokens + input_tokens
    if denom <= 0:
        return None
    return cache_read_tokens / denom


def write_deliverable_with_economics(
    conn: sqlite3.Connection,
    *,
    brief_id: int,
    file_path: str,
    created_by: str,
    # Agent task-completion envelope
    total_tokens: int,
    tool_uses: int,
    duration_ms: int,
    # Anthropic API breakdown
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
    # Optional
    provider: str = "anthropic",
    notes: Optional[str] = None,
) -> tuple[int, int]:
    """Insert a deliverables row + matching economics row in one transaction.

    Returns (deliverable_id, economics_id).

    This is the single operational entry point for Phase 1 capture. Each
    agent shim should call this in place of the bare-INSERT pattern in
    the persona deliverable-steps block.
    """
    pricing_id, in_p, out_p, cw_p, cr_p = _lookup_pricing_id(conn, provider, model)
    cost = compute_cost_usd(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        input_price_per_1m=in_p,
        output_price_per_1m=out_p,
        cache_write_price_per_1m=cw_p,
        cache_read_price_per_1m=cr_p,
    )
    hit_rate = compute_cache_hit_rate(input_tokens, cache_read_tokens)

    with conn:  # transaction — both rows commit or neither
        cur = conn.execute(
            """
            INSERT INTO deliverables
                (brief_id, file_path, created_by, notes,
                 tokens_used, tool_uses, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (brief_id, file_path, created_by, notes,
             total_tokens, tool_uses, duration_ms),
        )
        deliverable_id = cur.lastrowid
        cur = conn.execute(
            """
            INSERT INTO economics
                (deliverable_id, provider, model,
                 input_tokens, output_tokens,
                 cache_creation_tokens, cache_read_tokens,
                 estimated_cost_usd, model_pricing_id, cache_hit_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (deliverable_id, provider, model,
             input_tokens, output_tokens,
             cache_creation_tokens, cache_read_tokens,
             cost, pricing_id, hit_rate),
        )
        economics_id = cur.lastrowid
    return deliverable_id, economics_id


def update_economics(
    conn: sqlite3.Connection,
    *,
    deliverable_id: int,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cache_creation_tokens: Optional[int] = None,
    cache_read_tokens: Optional[int] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> None:
    """Backfill or correct an economics row.

    Reserved for the Phase-1.5 / Phase-2 post-completion hook: agents
    write what they can at insert time; the hook fills in cache metadata
    from the API response a moment later. Recomputes cost and hit rate
    against the row's pricing snapshot (or a new pricing snapshot if the
    model changed).
    """
    row = conn.execute(
        """
        SELECT provider, model,
               input_tokens, output_tokens,
               cache_creation_tokens, cache_read_tokens,
               model_pricing_id
        FROM economics
        WHERE deliverable_id = ?;
        """,
        (deliverable_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No economics row for deliverable_id={deliverable_id}")

    cur_provider, cur_model, cur_in, cur_out, cur_cw, cur_cr, _ = row
    new_provider = provider if provider is not None else cur_provider
    new_model = model if model is not None else cur_model
    new_in = input_tokens if input_tokens is not None else cur_in
    new_out = output_tokens if output_tokens is not None else cur_out
    new_cw = cache_creation_tokens if cache_creation_tokens is not None else cur_cw
    new_cr = cache_read_tokens if cache_read_tokens is not None else cur_cr

    pricing_id, in_p, out_p, cw_p, cr_p = _lookup_pricing_id(
        conn, new_provider, new_model
    )
    cost = compute_cost_usd(
        input_tokens=new_in, output_tokens=new_out,
        cache_creation_tokens=new_cw, cache_read_tokens=new_cr,
        input_price_per_1m=in_p, output_price_per_1m=out_p,
        cache_write_price_per_1m=cw_p, cache_read_price_per_1m=cr_p,
    )
    hit_rate = compute_cache_hit_rate(new_in, new_cr)
    with conn:
        conn.execute(
            """
            UPDATE economics
            SET provider = ?, model = ?,
                input_tokens = ?, output_tokens = ?,
                cache_creation_tokens = ?, cache_read_tokens = ?,
                estimated_cost_usd = ?, model_pricing_id = ?,
                cache_hit_rate = ?
            WHERE deliverable_id = ?;
            """,
            (new_provider, new_model, new_in, new_out, new_cw, new_cr,
             cost, pricing_id, hit_rate, deliverable_id),
        )
