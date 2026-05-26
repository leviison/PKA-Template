# Pattern 11 — Probe-Validity Discipline

**Status:** proposed (zero validated instances in template; promotion gated on first template-instance firing — see *Governance*)
**Author:** Leroy
**Proposed:** template v1.2.1 (rewritten from PKA-source `probe-validity-discipline` as an owner-neutral shape)
**Approved by:** *pending — promotion to `validated` requires at least one demonstrated instance in template-instance use*

---

## When to use

A debugging or characterization moment where:

- The system being probed has **multiple interacting layers** — kernel/driver/userspace, distributed processes, network protocols with timeouts, container/host boundaries, hardware virtualization / mediator boundaries — and a probe at one layer can return a clean answer while the actual constraint sits at another.
- The "obvious" hypothesis matches a **plausible-but-not-yet-confirmed** root cause, OR the probe's *shape* may not match the question's *shape* even without a stated hypothesis.
- A probe returns a **clean affirmative or negative** that closes a hypothesis — fast, decisive, unambiguous-looking. *Especially* when the result confirms what the prober expected.
- The **brief or upstream spec prescribed the probe** based on theoretical analysis without empirical confirmation — the prober was handed a probe shape from above, not one they constructed from the question.
- The downstream cost of acting on a wrong verdict is **destructive, expensive to reverse, or prone to producing misleading downstream artifacts** — uninstalling a working driver, rebooting hardware, restructuring a container, abandoning an architectural recommendation, reporting wrong numbers that propagate into decisions.

In short: when the **probe's output is being trusted to close a hypothesis**, the probe itself becomes the discipline's surface — not the result.

## When NOT to use

- **Single-layer failures with one obvious cause.** A null-pointer dereference doesn't need probe-validation; the stack trace is the probe.
- **Probes that are themselves the contract** — running the test suite to verify a fix is not "probing the system"; the suite IS the system's contract.
- **Time-critical emergency unblocks where rigor is impossible.** When production is down, fix-then-validate is the right shape; probe-validity discipline applies to the post-mortem.
- **Probes whose *question-fit* has been validated at first use.** Once a probe is known-reliable in a given domain *for a given question*, repeating the probe-the-probe step is cost without payoff. **Note the question-fit qualifier:** mechanical validity (the probe runs and returns clean data) is not sufficient — the probe must reliably answer *the question being asked*. A mechanically-reliable probe can answer a question different from the one being asked while looking like it answered correctly. Mechanical validity without question-fit produces probes that are reliable-but-blind.

## Shape

This is a discipline applied *to probe-runners*, not a workflow shape per se. Five steps fire when the discipline is in play. **Note: once internalized, the discipline collapses to Step 2 plus a habit.** Explicit five-step expression is for teaching, for high-cost-of-wrong moments, and for codification purposes — not for every probe.

1. **Probe → observe result.** The first instinct: run the probe, note the result. Standard.

2. **Audit the probe against four question-frames.** Before trusting the result, the discipline requires asking — explicitly — each of four diagnostic questions. These are not optional sub-bullets; they are required checklist items. Step-skipping (the prober asks one of the four and declares Step 2 done) defeats the discipline.

   - **2a — Environment match.** Was the probe's environment the same as the failure's environment? (User context vs. root context; container interior vs. host; load-time vs. runtime.) Probes that ran "near" the failure but not "in" the failure environment lie silently.

   - **2b — Path traversal.** Did the probe traverse the path the failure traverses? (A `strings` test for a dlopen'd plugin returns nothing — the plugin doesn't link the symbols statically, regardless of capability. The probe didn't traverse the path the failure traverses.)

   - **2c — Success-condition match.** Does the probe's success condition match the system's success condition? (Driver loads doesn't mean driver binds; binds doesn't mean operates. The probe's pass condition has to match the system's working condition.)

   - **2d — State-not-under-the-probe.** What state-not-under-the-probe could be silently mediating? (Kernel module parameter, missing config file, env stripping, latent permission, secure-boot signing.)

3. **Layer the probe.** Run alternative probe shapes that should give *consistent* answers if the first probe was honest. The probe-the-probe step is itself a probe. If layers agree, confidence rises; if layers diverge, the first probe was lying.

   **Reasoning-audit (Step 2) comes before re-probing (Step 3) because reasoning is cheap and re-probing is not always cheap.** When re-probing is itself cheap, the two steps can interleave.

   **Two operational modes of layering, both valid, with different power:**
   - *(a) Different-shape layering.* Run a probe of a structurally different shape that should converge on the same answer if probe 1 was honest. This is the discipline's primary power — it catches assumption-blind-spots that a same-shape re-run cannot.
   - *(b) Same-shape varied-condition layering.* Re-run the same probe under varied conditions (different user, different time, different environment) to see if the result is stable. This is the cheaper retry; useful for catching transient or context-dependent artifacts but weaker against shared assumptions.

4. **If divergence shows: the probe was wrong, not the system.** The hypothesis was probably wrong too, but the discipline catches a more important failure mode — the probe-as-trusted-instrument was deceiving. Resist the urge to declare the *system* mysterious; first interrogate the *probe*.

   **Meta-characterization clause:** if multiple layered probes diverge *among themselves* rather than from the verdict, the move is to characterize "I have N probes giving M different answers," not to pick a side. Three-way disagreement is its own data — usually pointing at a state-not-under-any-of-the-probes that the next round of probing needs to explicitly target.

5. **Only after probe-validation: accept the verdict and act.** The discipline's value is in the gate before action, not in the action itself. The action sequence is the same whether the discipline was applied or not — the difference is whether the action is taken against the actual cause or a probe-artifact.

## What protects against failure

- **Protection 1 — Multiple independent probes are the default, not the exception.** A single clean probe result is suspicious by itself. Two probes from different angles converging on the same answer is the minimum confidence threshold for high-cost actions.

- **Protection 2 — Probe-result-affirming-my-hypothesis warrants *extra* suspicion, not less.** Confirmation bias is a probe's worst enemy. When the probe agrees with what I expected, the discipline says: layer another probe specifically designed to *falsify* the hypothesis. This protection fires unevenly in practice — some probe moments exhibit it explicitly, others don't. The discipline names the move; the prober has to exercise it.

- **Protection 3 — Explicit "what could make this probe lie?" question** before declaring a verdict. The question is sometimes uncomfortable (the prober has emotional investment in the probe), which is exactly when it matters most.

- **Protection 4 — (cross-reference)** Brief-author discipline against prescribing the HOW from theoretical analysis without empirical grounding is a separate discipline that fires upstream. When that upstream discipline fails (a brief over-prescribes a probe shape from theory), probe-validity must fire downstream as the prober catches the mismatch. Cross-reference, not internal protection.

- **Protection 5 — "Stop and characterize, don't cascade."** This is the *operational expression* of the entire pattern. When a probe fails, the discipline says: stop, run the probe-the-probe step, characterize the actual wall. Don't pivot architecturally on a probe verdict that hasn't been validated.

- **Protection 6 — Angle-diversity, not just shape-diversity.** Two probes that share a hidden assumption can be wrong-in-the-same-way regardless of how different their shapes look. The discipline requires probes from genuinely different *angles* (different layer, different observer, different time-frame, different domain model) — not just different syntactic shapes. Shared-blind-spot risk is real and named explicitly in *what this pattern does NOT protect against*; angle-diversity is the active defense.

## What the pattern does NOT protect against

(Discipline borrowed from [[audit-then-execute-structural]] — every pattern names its limits.)

1. **Probes that don't exist yet.** The discipline applies once a probe has been run; it doesn't tell you which probe to run first when you walk into an unknown system. [[empirical-probe-before-design]] (PATTERN-006) covers the *which-probe-to-run* question; probe-validity covers the *did-the-probe-honestly-answer* question.

2. **Cognitive cost overhead.** Layering probes carries time and effort cost. The discipline applies where the cost of acting on a wrong verdict is high; routine debugging doesn't need it. Mis-application produces over-rigorous slow work that resembles paralysis.

3. **Systemic measurement gaps.** If the right probe simply cannot be constructed (no observability, sealed system, side-channel only), the discipline cannot rescue you. The probe-the-probe step fails because the probe-the-probe is the same probe.

4. **Adversarial / actively-deceiving systems.** Probe-validity assumes the system is honest-but-noisy, not malicious. A system intentionally returning misleading answers (security context, deceptive monitoring environment) requires a different discipline.

5. **Probes that pass for the wrong reason (shared blind spot).** If a probe and a probe-the-probe step share a hidden assumption, both can be wrong-in-the-same-way. Protection 6 (angle-diversity) is the active defense, but the risk cannot be fully eliminated.

6. **Probes whose validity depends on the prober's domain expertise.** The discipline works when the prober knows *what could make this probe lie*. A junior prober may not have the domain knowledge to ask the right four questions in Step 2. The pattern silently assumes domain competence; in lower-competence contexts, the discipline reduces to "be careful," which is not operational.

7. **Non-stationary systems.** If the system being probed changes between probe and probe-the-probe, divergence may mean "system moved," not "probe lied." The pattern assumes stationarity at the probe-and-validate timescale; for systems that don't satisfy that assumption, layered probes' disagreement is ambiguous between "probe was wrong" and "system moved."

## Validated instance(s)

*None in template.* This pattern ships at `status='proposed'` with the intent that a forked template-instance owner running a high-stakes debugging or characterization engagement against it produces the first validated-instance evidence.

The pattern's PKA-source genealogy (seven instances within a single multi-day engagement in the source repo) is *not* validated-instance evidence for the template-instance version — the single-engagement empirical base is one of the load-bearing concerns the source repo itself named on promotion, and a template-instance install starts that empirical base from zero. The generic version has zero direct demonstrated instances at template-ship time; promotion to `validated` requires evidence in template-instance use.

## Adjacent patterns

- **[[empirical-probe-before-design]]** (PATTERN-006) — **closest cousin.** PATTERN-006 governs *which probe to run first when designing*; PATTERN-011 governs *did the probe honestly answer when validating*. Same family (*Characterize before you commit*), different decision points. The two patterns can co-fire on the same brief (probe to characterize, then validate the probe's verdict against the brief's prescription).

- **[[audit-then-execute-structural]]** (PATTERN-005) — **Family 1 sibling.** Same family (*Characterize before you commit*), different territory: audit characterizes internal *structural* artifacts (templates, schemas, repo surfaces) where the source of truth is the file system; probe-validity governs *runtime* characterization where the source of truth is system behavior. The family-instinct is the same; the operational expression differs by territory.

- **[[multi-lens-parallel-critique]]** (PATTERN-004) — related when the probe's question warrants multiple independent reviewers from genuinely distinct angles. Multi-lens-parallel-critique is a coordination pattern for *deliberate* multi-angle review of an artifact; probe-validity layering at Step 3 is the same instinct applied to runtime characterization.

## Governance

Pattern rewritten as an owner-neutral shape at template v1.2.1 from PKA-source `probe-validity-discipline` (PKA-source genealogy: seven demonstrated instances within a single multi-day engagement in the source repo, all from one prober). The generic rewrite ships at `status='proposed'` because the discipline's content generalizes in principle while the empirical evidence does not — the source-repo single-prober / single-engagement empirical base is exactly the kind of evidence that template-instance use is needed to widen.

**Promotion path to `validated`:** A template-instance owner runs a high-stakes debugging or characterization engagement against this pattern → instance documented in *Validated instance(s)* above → instance owner promotes to `validated`. Subsequent instances calibrate whether the discipline holds across personas and engagement classes, or whether the early instances were over-fit.

**Demotion conditions** (per pattern discipline):
- If three consecutive probe-validity applications in a template-instance produce no meaningful divergence — every probe was honest the first time — the discipline has been internalized; codifying it as a pattern is unnecessary ceremony. Promote-out by retiring.
- If amendment-fatigue compounds — every probe spawns probe-the-probe spawns probe-the-probe-the-probe recursively — the cost exceeds the benefit and the pattern downgrades.
- If the discipline is consistently misapplied to single-layer simple bugs (where it's overkill per *When NOT to use*), the pattern's signal-to-noise problem warrants either tighter scope or retirement.

---

*Pattern #11 of N — proposed status. See `/patterns/` for the full catalog and [[README]] for the family tree.*
