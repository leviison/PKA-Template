# Pattern 3 — Persona-Gap-Triggered Hire

**Status:** validated (one instance — BRIEF-104, 2026-05-16)
**Author:** Leroy
**Approved by:** owner (2026-05-18)

---

## When to use

When a brief surfaces a real **persona capability gap** in the team — work that no existing team member's operating contract permits, and where the gap is likely to recur:

- The required work violates an existing persona's contract (e.g., opinionated commentary against a "never editorialize" rule).
- The skill space is bounded and well-known in the wider world — the archetype has real practitioners, vocabulary, and discipline.
- The owner has explicitly chosen the hire path over a one-off override.
- The gap is reusable: future work in the domain is plausible enough that building a permanent capability beats burning the override on each instance.

## When NOT to use

- **One-off work** the team will not need again. Use an explicit, documented override on an existing persona's contract for the single brief and revisit only if it recurs.
- **The work fits an existing persona's contract within reasonable stretch.** Don't hire to dodge a stretch goal; hire when the stretch would require violating the contract.
- **The owner is in a hurry and a hire would block the work.** Hires take a session (proposal + build + first deliverable). If the deliverable cannot wait, use the override and queue the hire.
- **The team's name surface is already crowded.** A new persona is intent-layer state — additions should be necessary, not opportunistic.

## Shape

1. **Gap surfaced.** A brief lands that doesn't fit any existing persona's contract. Leroy names the gap explicitly in the routing message rather than silently overriding a persona.

2. **Options presented to the owner.** Three branches: (a) Hire a new persona via Sam — reusable, ~1 session to deliver, builds permanent capacity; (b) one-off override of an existing persona's contract — fast, doesn't build capacity, creates precedent risk; (c) work in a neutral/raw-material shape — honors persona contracts but doesn't satisfy the original ask. Owner picks.

3. **Sam runs the standard hiring flow.** Per `CLAUDE.md` Hiring Process — Sam tasks PAX with a research brief on the archetype; PAX delivers a research report; Sam scans `patterns/` for related validated patterns; Sam writes a hire proposal to `owners_inbox/`. The hire is **gated** on owner approval — no persona file, no shim, no `team_members` row until the owner explicitly approves the proposal.

4. **Owner reviews the proposal and answers any open questions.** Sam's proposal includes a numbered open-questions list (scope, hook, name, operating-contract specifics, default tier, etc.). Owner says "approve as proposed" or names overrides.

5. **Sam builds.** Creates `team/<NAME>.md`, creates `.claude/agents/<slug>.md`, inserts the `team_members` row, marks the hire brief complete. Leroy updates the `CLAUDE.md` roster as the final step.

6. **The original brief now routes to the new persona.** The work that surfaced the gap is the new persona's first deliverable.

## What protects against failure

- **The owner gate.** Hires are not auto-triggered; Leroy proposes options, owner authorizes. This prevents drift where Leroy invents personas to dodge work that should have been done in an existing seat.
- **The persona's operating contract is load-bearing.** Sam's job is not just "make a character." The persona file must include the *discipline that governs the work* (e.g., for an opinionated analyst: structured thesis architecture — bull case, bear case, flip conditions, sizing logic, time horizon). Without that structure, the new persona produces vibes-wearing-a-suit and Sam's design has failed. Binding-at-persona-file, not at brief-level — soft guidance produces ornamental execution.
- **Distinction from adjacent personas is explicit.** The proposal must state how the new persona differs from the closest existing seat. If the distinction is fuzzy, the seats will collide.
- **First deliverable is treated as a trust-build, not a delivery.** Pair this pattern with [[multi-lens-parallel-critique]] on the first run — the persona's output is auditable on substance, persona-discipline, and learning value before trust accrues.

## What the pattern does NOT protect against

(Discipline added 2026-05-18 per `patterns/README.md` convention — every pattern names its limits so it doesn't get oversold.)

**The pattern fires on surfaced gaps only — it does not proactively scan for missing capabilities.** Capabilities the team needs but no brief has yet surfaced remain invisible. The pattern is reactive by design (which is correct — speculative hiring is a different shape and its own failure mode), but the team should not assume the absence of hire triggers means the team is complete.

**A "doesn't fit any persona" brief might be a mis-shaped brief, not a real gap.** The pattern correctly identifies that the work doesn't fit; it does not separately ask whether the *work itself* is well-posed. If the brief is asking the team to do something the team shouldn't be doing, hiring a persona to do it locks in the wrong investment. Mitigation: when a hire-triggering brief surfaces, examine whether the brief is well-posed before commissioning the hire. The persona-gap is real if the work is real.

**The owner-gate is the only enforcement against drift.** The pattern lists "owner in a hurry" as a disqualifier in *When NOT to use*, but the disqualifier is owner-applied, not pattern-enforced. Under time pressure, even a well-meaning owner may approve a hire that should have been a one-off override. Mitigation: when proposing the three options, Leroy should explicitly name which option is fastest and which is most reusable — the tradeoff has to be visible at the decision point.

## Validated instances

- **BRIEF-104 (2026-05-16) — opinionated-strategist hire.** Trigger: a follow-up brief requested an opinionated thesis on a special-situations investment vehicle, which violated PAX's "never editorialize" contract. Three options presented; owner chose hire. Sam ran the full flow, dispatched PAX inline for research, produced a hire proposal with a structured thesis-architecture operating contract. Owner approved as proposed. Build delivered the persona file, shim, and `team_members` row. The new persona's first deliverable shipped the same session; a multi-lens critique pass on that first deliverable validated both the persona design and this pattern.

## Failure mode worth naming

The strongest temptation when this pattern is the right call: *"just brief the existing persona harder."* Routing an opinionated piece to a neutral-synthesis persona with explicit instructions to take positions violates the persona's contract and produces output that is neither neutral (the persona's value) nor opinionated (the original ask). Don't override a persona's contract by stuffing more instructions into a brief.
