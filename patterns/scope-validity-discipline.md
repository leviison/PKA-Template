# Pattern 13 — Scope-Validity Discipline (verify the discipline's scope matches its proper surface before declaring it applied)

**Status:** proposed (zero validated instances in template; promotion gated on first template-instance firing — see *Governance*)
**Author:** Leroy
**Proposed:** template v1.2.1 (rewritten from PKA-source `scope-validity-discipline` as an owner-neutral shape)
**Approved by:** *pending — promotion to `validated` requires at least one demonstrated instance in template-instance use*

---

## When to use

When applying a discipline, protocol, or pattern, ask: *what is the proper scope of this discipline — and does my application of it match that scope?* The pattern fires when the answer is no — when a discipline is applied at a narrower scope than the surface it should cover, leaving the broader surface unprotected even though the local application looks correct.

This is the sibling pattern to [[probe-validity-discipline]] (PATTERN-011). PATTERN-011 asks *is the probe valid for its target?*; this pattern asks *is the scope of what's being probed (or audited, or verified, or preserved) matched to the surface that the discipline is meant to protect?*

Triggers:

- **A discipline named, then applied at a localizable level** (a specific probe, a specific test, a specific artifact), while the surface the discipline is supposed to protect is broader (the system, the engagement, the cross-stream behavior, the multi-surface artifact).
- **Local application reads correctly in isolation**, but a broader read reveals that the application covers a subset of what the discipline was meant to cover.
- **Multi-surface or multi-instance artifacts** where the discipline must apply across the surface, but its application has been instantiated against one instance.
- **"Preserve-prod" / "verify-clean" / "probe-before-design"** applied at the artifact level when the system level is the proper scope.

## When NOT to use

- **Single-scope work.** The discipline's proper scope and its application scope coincide naturally.
- **Genuine scope-limit calls.** The discipline's scope is *deliberately* narrow for cost-asymmetry reasons (e.g., probe-validity for a specific probe doesn't require probing the entire system — it requires probing the specific probe's specific interface). The pattern fires only when the scope mismatch is unintentional or unconsidered, not when it's deliberate.
- **The discipline doesn't have a meaningful broader scope.** Some disciplines are inherently artifact-local — there's no "broader scope" to check against.

The pattern is stakes-gated by the discipline's surface. If the surface the discipline could protect is small, the pattern adds cost without benefit.

## Shape

The pattern operates at brief-design and discipline-application time, not at execution time. The protective work happens when the discipline is named, before it's applied.

1. **Name the discipline being applied.** Explicit: *"this work applies PATTERN-011 / preserve-prod / verification-surface-matches-failure-surface / etc."*

2. **Name the discipline's proper scope.** Where should this discipline operate to deliver its full value? At the brief level? The engagement level? The system level? The multi-surface artifact level?

3. **Name the actual application scope.** Where is the discipline being applied concretely? At which specific probe / artifact / surface?

4. **If the scopes differ, name the gap.** Either (a) extend the application to the proper scope, OR (b) declare the deliberate scope limit and the cost-asymmetry that justifies it, OR (c) commission additional work to cover the gap at the proper scope.

5. **The verification artifact captures the scope.** Not just *"PATTERN-011 applied"* but *"PATTERN-011 applied at probe-level X, deliberately not at engagement-level Y because Z."*

## What protects against failure

- **Scope-naming at discipline-application time.** Engineers under time pressure default to applying disciplines at the most-local available scope (the artifact in front of them); the brief and the deliverable are the only places that force the question of *is this the right scope?*
- **Brief framing names the discipline's expected scope.** When commissioning work that should apply a discipline, the brief names the operating scope — not just *apply PATTERN-011* but *apply PATTERN-011 at engagement-level, covering all probes the engagement runs.*
- **Multi-instance or multi-surface enumeration discipline.** When the artifact or system has multiple instances/surfaces, the discipline-application enumerates each instance and either covers it or names the deliberate skip.
- **Deliverable artifacts capture scope explicitly.** *"PATTERN-011 instance #N at probe-level X"* rather than just *"PATTERN-011 instance #N."*

## What the pattern does NOT protect against

**Disciplines we forgot to name.** The pattern fires on disciplines being applied; it doesn't surface disciplines that should be applied but aren't named at all. That's a separate gap.
*Mitigation:* Pattern catalog review at brief-design time — does this brief touch a class of work where any pattern should automatically fire? Standing protocols (`protocols/`) are the dispatch-tier counterpart to patterns; they fire on triggers without requiring brief-time discovery.

**Wrong-discipline application.** A discipline applied at the right scope but inappropriate to the work shape (e.g., probe-validity applied to a synthesis-shape brief where the load-bearing failure mode is elsewhere). The pattern checks scope, not appropriateness.
*Mitigation:* Brief-shaping discipline operates at the upstream point — choosing which disciplines apply to the work shape.

**Scope-expansion-creep.** Naming the proper scope as broader than necessary, requiring application at a scope that's not load-bearing for the work. The pattern can be wielded too aggressively, expanding scope past what the work warrants.
*Mitigation:* Stakes-gate. If the work doesn't have a meaningful broader scope or the broader scope is low-stakes, the pattern doesn't fire.

**The scope-naming itself being wrong.** Naming the "proper scope" requires judgment; that judgment can be miscalibrated. The pattern surfaces the question but doesn't guarantee the answer.
*Mitigation:* Cross-persona review on high-stakes scope-judgment calls. [[multi-lens-parallel-critique]] (PATTERN-004) is the closest discipline.

## Validated instance(s)

*None in template.* This pattern ships at `status='proposed'` with the intent that a forked template-instance owner running discipline-applying work against it produces the first validated-instance evidence.

The pattern's PKA-source genealogy (seven convergent instances within a single multi-day engagement in the source repo, spanning four personas and four distinct disciplines whose scope was mis-matched) is suggestive of the discipline's portability — but a template-instance install starts the empirical base from zero, and the source repo's clustering-in-one-engagement was itself a load-bearing concern at promotion. The generic version has zero direct demonstrated instances at template-ship time; promotion to `validated` requires evidence in template-instance use.

## Adjacent patterns

- **[[probe-validity-discipline]]** (PATTERN-011) — **sibling pattern.** PATTERN-011 asks *is the probe valid for its target?*; PATTERN-013 asks *is the scope of what's being probed matched to the surface this discipline is meant to protect?* The two patterns operate at adjacent points: PATTERN-011 protects against bad-probe-of-correct-scope; PATTERN-013 protects against good-probe-of-wrong-scope.
- **[[empirical-probe-before-design]]** (PATTERN-006) — **cousin.** PATTERN-006's *"characterize at the surface where reality lives"* instinct generalizes: the scope of characterization must match the scope of the failure mode that downstream work is being shaped against.
- **[[audit-then-execute-structural]]** (PATTERN-005) — **cousin.** The audit step's coverage scope is itself a scope-validity concern; an audit scoped to a subset of the structural surface protects the audited subset but leaves the unaudited surface exposed.
- **[[multi-lens-parallel-critique]]** (PATTERN-004) — relevant when cross-persona review on high-stakes scope-judgment is warranted.

## Governance

Pattern rewritten as an owner-neutral shape at template v1.2.1 from PKA-source `scope-validity-discipline` (PKA-source genealogy: seven convergent instances within a single multi-day engagement in the source repo, spanning four personas and four distinct disciplines). The generic rewrite ships at `status='proposed'` because the empirical evidence — though strong in its source-repo clustering — has not yet been observed across multiple engagements or across template-instance use, and the clustering-in-one-engagement concern was itself named at source-repo promotion.

**Promotion path to `validated`:** A template-instance owner runs work that explicitly applies a discipline → the scope-naming + application-scope check + scope-gap-named-if-different sequence is exercised → the resulting work confirms the discipline held against a scope mis-match risk → instance documented in *Validated instance(s)* above → instance owner promotes to `validated`.

**Demotion / deprecation path:** If over time the pattern's template-instance instance count stays at zero — engagements never warrant scope-discipline naming — the pattern is a candidate for retirement (the discipline being already-internalized in normal brief-shaping). If a future PATTERN-N supersedes it by covering its discipline as one of several concerns (a discipline-application meta-pattern covering scope-matching, appropriateness-matching, and triggering-condition-matching), this pattern is a candidate for absorption-by-supersession.

---

*Pattern #13 of N — proposed status. See `/patterns/` for the full catalog and [[README]] for the family tree.*
