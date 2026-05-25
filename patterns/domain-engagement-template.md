# Pattern 7 — Domain-Engagement Template (Owner-Commissioned, Domain-Bounded, Position-Taking)

**Status:** proposed (zero validated instances in template; promotion gated on first template-instance engagement following the workflow — see *Governance*)
**Author:** Leroy
**Proposed:** template v1.2.0 (rewritten from PKA-source `investment-evaluation-engagement` as a domain-agnostic shape)
**Approved by:** *pending — promotion to `validated` requires at least one demonstrated instance in template-instance use*

---

## When to use

A domain engagement where the owner commissions the team to move from raw source material to a position-taking deliverable, and the answer requires structured workflow rather than a single brief. Triggers:

- **The question is position-taking shaped** — "should we deepen / partner / proceed / decline / approve" or its domain equivalent. Not a discrete factual lookup; not a neutral research synthesis; a call has to be made.
- **Substantial source material** that doesn't fit in working context. Data rooms, document collections, recorded conversations, primary-source artifacts in mixed media (PDFs, docs, spreadsheets, audio, video).
- **Counterparty or subject-matter information asymmetry.** The owner knows things about their own side that don't live in any document yet — edge, opportunity cost, success picture. The other side (counterparty, candidate, system-under-evaluation, subject) carries information that requires reading, extracting, and synthesizing.
- **The deliverable will inform a real-world decision the owner acts on.** Not academic; not just-in-case; commissioned because the owner has to decide.
- **At least one external conversation or meeting** is part of the engagement arc — pre-briefing it, or transcribing it after.

The pattern is domain-agnostic in *shape* but always domain-bounded in *content*. Example domains where this shape fits:

- Investment evaluation (the PKA-source first instance lived here)
- Consulting engagements with a recommendation deliverable
- Due-diligence work (M&A, vendor selection, partnership evaluation)
- Technical audits where a position-taking summary is required
- Research engagements that end in an actionable recommendation
- Hire-evaluation processes for senior or strategic roles

If the engagement's domain has its own established methodology (financial modeling for investment, security frameworks for tech audits, design rubrics for hire evaluations), this pattern names *where* that methodology slots in but does not specify *what* it contains. The domain methodology is the substance the team or persona supplies; this pattern is the workflow that holds it.

## When NOT to use

This is a heavy-weight engagement pattern. Most domain-adjacent questions don't need it.

- **Discrete factual question.** "What's their track record on X?" is a research-side brief, not a full engagement. Single brief; no framing memo; no thesis.
- **Source material is small enough to read directly.** A short memo and a brochure don't need extraction or framing-memo iteration.
- **The owner already has the framing locked.** If the engagement shape is decided and only execution remains, the pattern is overkill — go straight to brief the executing persona.
- **No real-world decision downstream.** Curiosity-shaped questions are research, not engagement.
- **The subject is already deeply known.** A relationship or system the owner has years of context on does not need re-extraction from documents; the framing pass can be skipped or compressed.

The pattern's cost is real. Reach for it when the *decision* warrants the depth, not when the *question* is intellectually interesting.

## Shape

The engagement proceeds through eight stages. Stages 2-3 run in parallel; stages 5-7 chain sequentially.

1. **Asset intake.** Source material lands in a gitignored location (symlink to a non-persistent share is fine; original-on-host-filesystem is the default). Do not copy into the repo at intake — only what proves needful gets curated into `team_inbox/<engagement_slug>/` after the engagement closes.

2. **Audio/video diarization (parallel)** — every recorded conversation goes through the team's diarization pipeline (or equivalent transcription with speaker labels). Speaker labels stay as `SPEAKER_NN` until the owner maps them; content-based attribution is the practical discipline on long recordings where diarizer drift produces over-counted labels. (See [[empirical-probe-before-design]] for the probe instinct on integration-edge behavior.)

3. **Data-room extraction (parallel with audio)** — a research persona extracts source documents into `pka.db.content` with engagement-slug tagging plus subfolder-derived tags. Deliverable: an inventory mapping the corpus, with signal-density read per document and ranked pointers for the downstream position-taker.

4. **Framing memo (orchestrator-authored, iteratively revised).** The single highest-leverage discipline in the pattern. The memo opens with three framing questions adapted to the domain:
   - **Q1 — Engagement shape:** what does "deepening / partnering / proceeding" mean *concretely* in this domain? (Equity stake? Contract type? Service tier? Role definition? Whatever the domain's equivalents are.)
   - **Q2 — Other-side ask + motivation:** what they want, why now, leverage map.
   - **Q3 — Owner's side:** edge / opportunity cost / success picture at a defined time horizon.

   Three default checks anchor each revision:
   - **Constellation reframe** — if the owner's answers use "we" or "our", check whether the framing assumed solo principal. The engagement may actually involve multiple parties on the owner's side.
   - **Honest weaknesses** — surface what the principal doesn't bring before the position-taking step asks about it.
   - **Operating-shape addendum** — always-parallel vs exclusive: the principal's attention model matters for credibility and flip conditions.

   The memo versions explicitly (v1 → v1.1 → v2 etc.) with a changelog at the bottom so the position-taker can see what landed when.

5. **Pre-meeting prep deliverable** (if an external meeting is part of the engagement) — things to LEARN (gaps in the team's picture) / TEST (calibration questions about the other side's discipline) / SIGNAL (without overcommitting) / AVOID (don't pre-commit). Includes verbatim-droppable questions for the meeting.

6. **Speaker mapping** (for any meeting transcripts) — content-based attribution by the orchestrator, anchor quotes for verification, drift honestly flagged. Locked by the owner. Quote-level citations downstream content-verified per use; the label is a hint, not a guarantee.

7. **Position-taking deliverable.** A position-taking persona — typically a domain analyst paired with a domain critic per [[multi-lens-parallel-critique]] — runs the domain's established methodology against the framing memo. Mandatory: take a position (deepen / partner-at-shape / decline, or the domain equivalent), name the call, structure the supporting case + opposing case + flip conditions + scope + horizon. Sensitivity ranges where open owner-supplied inputs await landing.

   *The domain methodology fills this slot.* This pattern names the slot but does not specify the methodology — that is the position-taking persona's expertise (e.g., investment-thesis architecture, security-audit framework, consulting recommendation rubric).

8. **Re-underwriting contract.** Open inputs awaiting the owner drive re-underwriting per the position-taker's operating contract. The position-taker is structured to absorb new facts cleanly via a v1.1 revision rather than treating v1 as final.

## What protects against failure

- **Framing memo iteration as a discipline.** The memo is never a static input. Each revision incorporates new facts (the data-room read, owner chat answers, meeting transcripts, additional context). Drift-protection lives in the explicit version trail and the inputs-landed-when changelog.
- **Constellation reframe check.** When owner answers use "we" or "our", check whether the framing assumed solo principal. This single check often surfaces a multi-party unit (co-investors, partners, organization layers) that propagates through the rest of the memo and into the position-taking step.
- **Honest weaknesses surfaced before position.** The principal/constellation explicitly names what they don't bring before the position-taker asks about it. Surfaces flip conditions that overclaiming would miss.
- **Operating-shape addendum.** Always-parallel vs exclusive matters for the supporting case's credibility and the opposing case's flip conditions. Mature counterparties run portfolios of engagements; pretending one-engagement focus when reality is parallel-attention is a known mis-shape.
- **Source material indexed and queryable.** `pka.db.content` tagged with engagement slug + subfolder taxonomy is queryable by FTS5; the position-taker cites content_ids back to specific extracted documents. This is the discipline that makes citations auditable.
- **Analyst + critic persona pairing.** The position-taking step pairs a domain analyst with a domain critic (see [[multi-lens-parallel-critique]]). Single-persona position-taking on a high-stakes engagement amplifies whatever blind spots that persona has.
- **Re-underwriting contract.** The position is not final at v1. Open owner-side inputs trigger v1.1 re-underwriting per the position-taker's operating contract. This prevents the position from over-committing on sensitivity ranges that should remain sensitivity ranges until the owner supplies the inputs.

## What the pattern does NOT protect against

(Every pattern names its limits.)

**The other side's information being misleading or incomplete.** The extraction step indexes what's in the data room; the engagement does not audit the data room against external sources. If the counterparty omits material information, the position is sized against partial truth. Mitigation: name what is *not* in the data room as a side observation; treat marketing-register language with appropriate skepticism.

**Diarizer drift on long audio.** Most diarization stacks drift on long recordings — over-count speakers, split one voice across multiple labels. Content-based speaker-mapping is sufficient for downstream internal citation but not sufficient for public citation. If a quote will exit the engagement, acoustic verification by the owner is required.

**The owner's request shape itself being wrong.** This pattern works once the engagement is opened. If the owner opens the engagement on a wrong question entirely, the pattern proceeds against the wrong question. A brief-shaping examination on the engagement-opening brief is the upstream protection (see *Adjacent patterns*).

**Domain-methodology quality issues downstream.** Once the position-taking step is dispatched, the domain methodology's quality is its own concern (the analyst's framework, the critic's checks, the deliverable contract). This pattern shapes the *engagement*; it does not patrol *per-domain* execution.

**Sizing without the owner's open inputs.** The position-taking step is structured to absorb later inputs, but if the engagement closes before the owner supplies them, the position stays at sensitivity ranges rather than committed magnitudes. This is by design — the v1 position is *directional*, not *quantified to commitment*.

**Over-application of the pattern.** Reaching for the full engagement pattern on questions that don't warrant it would burn substantial tokens and owner attention. The precondition gates exist to prevent that.

## Validated instance(s)

*None in template.* This pattern ships at `status='proposed'` with the intent that a forked template-instance owner running a domain engagement against it produces the first validated-instance evidence.

The pattern's PKA-source genealogy (investment-evaluation engagement, one demonstrated instance in PKA's source repo) is *not* validated-instance evidence for the generic version. The generic rewrite has zero direct demonstrated instances at template-ship time; promotion to `validated` requires evidence in template-instance use.

## Adjacent patterns

- **[[sequential-overnight-build]]** (PATTERN-001) — engagements frequently use sequential overnight work between stages, especially when the extraction step produces material for the framing-memo step on a delayed schedule.
- **[[empirical-probe-before-design]]** (PATTERN-006) — speaker mapping on long audio and any integration-edge characterization step fire this pattern. Diarizer behavior under load is an empirical reality documentation rarely characterizes at sufficient resolution.
- **[[audit-then-execute-structural]]** (PATTERN-005) — framing-memo revision arcs (v1 → v2.1) fire this pattern in a stretched definition (the artifact under audit is owner-authored framing rather than an internal structural template). Worth checking on subsequent instances whether the pattern definition widens or whether framing-memo iteration earns its own pattern slot.
- **[[multi-lens-parallel-critique]]** (PATTERN-004) — the analyst-plus-critic persona pairing at the position-taking step is a direct invocation of this pattern.
- **[[persona-gap-triggered-hire]]** (PATTERN-003) — if the engagement's domain reveals the team lacks a needed analyst or critic, this is the upstream hiring trigger.

## Governance

Pattern rewritten as a domain-agnostic shape at template v1.2.0 from PKA-source `investment-evaluation-engagement` (PKA-source genealogy: one demonstrated investment-domain instance in source repo, 2026-05-18). The generic rewrite ships at `status='proposed'` because the engagement-workflow universals extracted from the single source instance are *speculative as universals* until template-instance use produces a second-domain instance.

**Promotion path:** A template-instance owner runs a domain engagement (any domain — investment, consulting, audit, research, hire-eval) through this workflow → AAR review of the run → instance owner promotes to `validated` and adds the instance to *Validated instance(s)* above. Subsequent instances (rule-of-three) calibrate whether the *Shape* generalizes cleanly or whether elements were over-fit to early instances.

**Demotion path:** If two or three template-instance runs surface that the eight-stage shape doesn't fit the engagements they were applied to — the framing-memo step proved unnecessary in their domain, or the analyst/critic pairing was overkill, or the workflow's heavy-weight precondition gates didn't match the engagement frequency — the pattern is refined or moved to `deprecated`. Honest typing.

If a template-instance owner finds that their domain needs a *different* engagement shape entirely (the eight stages don't map), the right move is to fork this pattern into a domain-specific variant rather than force-fitting. The point of the proposed status is to invite that judgment.

---

*Pattern #7 of N — proposed status. See `/patterns/` for the full catalog and [[README]] for the family tree.*
