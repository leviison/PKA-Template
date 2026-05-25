# Pattern 4 — Multi-Lens Parallel Critique

**Status:** validated (one formal instance — three-lens review of a novel-persona first deliverable, 2026-05-16; informal precedents earlier)
**Author:** Leroy
**Approved by:** owner (2026-05-18)

---

## When to use

When a single artifact warrants critique along multiple **genuinely distinct axes**, and the team has the personas to cover each lane without overlap:

- A **new persona's first deliverable** in a novel domain — trust-build before the persona's output is taken at face value.
- A **new operating pattern's first instance** — validate the pattern is doing what it was designed to do before promoting it on the patterns ladder.
- A **high-stakes artifact** where any single reviewer's blind spots would land hard if uncaught (legal/medical/financial content; architecture decisions with long blast radius).
- The artifact has **multiple legitimate critique axes** that don't collapse into one — e.g., substantive accuracy, persona-execution discipline, pedagogical clarity. If two axes would produce the same critique through different jargon, only one is needed.

## When NOT to use

- **Routine work** in domains the team has already proven out. Multi-lens reviews are calibration tools, not per-deliverable QA. Use sparingly.
- **Single-axis assessment is sufficient.** A typo audit doesn't need a three-lane review.
- **The team can't field genuinely distinct lanes.** If two lenses are going to overlap by 60%, the pattern produces redundant work; either collapse them or run a single deeper review.
- **The artifact is still in flight** and the value is iteration, not validation. Multi-lens reviews are for completed artifacts.

## Shape

1. **Define the lanes.** Each lens is a single critique axis with explicit constraints — what it covers, what it does NOT cover. The constraint matters: without it, lenses drift into each other's territory and the parallel design collapses into duplicated work.

2. **Brief each reviewer independently.** Each lane gets its own brief, naming its constraint explicitly ("stay in your lane — leave the other two angles alone"). The brief specifies the memo structure and the deliverable location.

3. **Reviewers run in parallel and isolated from each other's findings.** Spawn the reviewers as concurrent subagents. None of them sees the other lanes' work-in-progress or completed memos. Independence is what produces non-overlapping critique.

4. **Each reviewer writes a critique memo** to `owners_inbox/critique_<artifact>_<lens>_<reviewer>.md`. Memos stand alone; they don't reference the other lenses.

5. **Leroy synthesizes for the owner.** The synthesis is the unit Leroy produces — at the right altitude, naming each lens's sharpest finding, surfacing where the lenses agree, and naming the meta-finding (often the most valuable output: where lens A and lens B tell different truths about the same artifact).

6. **Action items come from the synthesis, not the individual memos.** What needs to be fixed in the artifact, what needs to be tightened in the upstream design (persona file, shim, brief template), and what pattern observations are worth carrying forward.

## What protects against failure

- **Lane constraints are explicit in each brief.** "Stay in your lane" is a sentence the reviewer must read before starting. Without it, the most thorough reviewer will drift across all three axes and produce a single comprehensive memo that drowns the parallel design's value.
- **Reviewers run in isolation.** No cross-talk during the run. Independence is what produces the non-overlap.
- **The synthesis is honest about disagreement.** When lens A says "clean" and lens B says "partly sound," do not paper over the contradiction. The contradiction IS the finding — it tells the owner that two different checks return different verdicts on the same work, which is often the most actionable insight the pass produces.
- **The pattern is reserved for calibration.** Multi-lens reviews are trust-tuning tools, not routine QA. Three reviewers consume real tokens and team time; deploy on novel-persona firsts and pattern-validation moments, not every deliverable.
- **Three lanes is a healthy default; four needs a real fourth-axis justification.** If you can't articulate why a fourth lane wouldn't overlap with one of the first three, the fourth shouldn't exist.

## What the pattern does NOT protect against

(Discipline added 2026-05-18 per `patterns/README.md` convention — every pattern names its limits so it doesn't get oversold.)

**Lenses can converge despite scope constraints.** Even with "stay in your lane" explicit in each brief, three reviewers may genuinely see the same problem from different angles and produce correlated outputs. When this happens, the calibration value drops — three lenses agreeing tell you about the artifact's quality, but not about the *lens-discipline* the pattern was deployed to calibrate. Mitigation: state the calibration question ex-ante ("we are trying to learn X about this artifact / about the lens design"); if the lenses converge on something other than X, the pass produced an artifact-quality finding, not a calibration finding.

**Sycophancy in lens execution is not enforced against.** If the artifact is from a high-status persona, carries owner endorsement, or sits within a project the reviewer feels invested in, critique softens unconsciously. The pattern doesn't audit each lens's critical posture. Some persona designs enforce this for their lens; not all lens runners have the same discipline baked in. Mitigation: brief each lens with explicit permission to disagree with prior team consensus, and treat "all lenses positive" as a signal worth a second look rather than a confirmation.

**The pattern provides no second-order validation of the lens itself.** The synthesis is Leroy's judgment; if a lens is wrong (misidentifies an issue, misses one that's real, or applies the wrong rubric), the synthesis has to catch it. There is no built-in check that the lens's critique itself is sound. Mitigation: when synthesis surfaces a contradiction between lenses, examine *which lens is wrong* rather than averaging — the contradiction is the most actionable finding (see *What protects against failure*, "synthesis is honest about disagreement").

**The "calibration not routine QA" discipline is guidance, not enforcement.** The pattern says "use sparingly" but doesn't enforce a budget. Risk: pattern gets reached for whenever review feels warranted, burning tokens and team time on per-deliverable QA that a single deeper review would handle. Mitigation: before commissioning, name the calibration purpose (new persona, new pattern, novel domain) explicitly — if no calibration purpose can be named, single-lens deeper review is the right shape.

## Validated instances

- **2026-05-16 — Three-lens review of a novel-persona first deliverable.** Lanes: substantive/doctrinal accuracy, persona-execution discipline, pedagogical/learning value. All three returned in parallel; non-overlapping findings. One lens caught a load-bearing miscitation; another caught a persona-file gap that the persona then turned into a performative footer; the third caught an unsealed principle (the architecture supported a deeper principle than the prose extracted). Meta-finding from the synthesis: **persona discipline can execute perfectly while substantive accuracy fails** — the structural binding is a structural check, not a factual one. That meta-finding directly seeded a design question for the persona's next iteration.

## Relation to other patterns

- **Pairs with [[persona-gap-triggered-hire]]** on new-persona firsts. The hire flow builds the persona; the multi-lens critique validates that the persona's first output deserves the trust the design was built to earn.
- **Distinct from [[sequential-overnight-build]]** — that's a build pattern (upstream/downstream split). This is a review pattern (artifact already exists; multiple reviewers in parallel).
