# Pattern 2 — Single-Consumer Event-Stream Architecture

**Status:** validated (one instance — BRIEF-079, 2026-05-15)
**Author:** Sam
**Approved by:** owner (2026-05-15)

---

## When to use

A system where:

- **A single upstream event source emits each event exactly once.** The source is a true iterator: asyncio SSE stream, asyncio.Queue, Redis pub/sub channel subscribed once, or any other single-consumption event iterator.
- **Multiple internal components need to receive all events** — or overlapping subsets of the same stream. Two or more downstream consumers have distinct responsibilities (e.g., one assembles the result; one proxies events to the browser).
- **Splitting source reads across consumers is not possible without loss.** The source does not support fan-out natively; it hands each event to whichever reader resolves next.

## When NOT to use

- **Truly single consumer.** If only one component will ever read from the source, there is nothing to fan out. No buffer needed; connect directly.
- **Broadcast semantics are already at the source.** Redis pub/sub with properly separated channel names gives each subscriber its own copy. If the source already fans out, don't add an intermediary buffer that duplicates the mechanism.
- **Pull-once semantics.** A single request-response (one message, no replay, no streaming) does not need this pattern. The pattern addresses continuous streams, not single-payload fetches.
- **The source supports multiple simultaneous consumers natively** (e.g., Kafka consumer groups with distinct group IDs). Let the infrastructure carry the fan-out; don't build a buffer layer on top.

## Shape

1. **Designate one reader.** A single component — named explicitly in the design — opens the source connection and owns it for the life of the stream. No other component may open a second connection to the same source for the same job.

2. **Reader writes to a local buffer.** As events arrive, the reader appends each raw event to a per-job local buffer (e.g., `list[str]`). The buffer is shared by reference with downstream consumers. The reader also signals stream termination (e.g., a `threading.Event` or async flag set when a terminal event arrives).

3. **Fan-out via async polling.** Downstream consumers read from the local buffer, not from the source. They poll the buffer at a short interval and yield buffered events they haven't yet processed. They stop when the termination signal is set and the buffer is exhausted.

4. **Terminal events propagate to all consumers.** Terminal events (`done`, `error`) are written to the buffer like any other event, so every downstream consumer receives them in order. The termination signal is set *after* the terminal event is appended — not before.

## What protects against failure

- **Single-consumer eliminates the race.** With one reader at the source, there is no contention over which `await` resolves first. The failure mode — terminal events landing in the wrong consumer, causing silent data loss — cannot occur.
- **Local buffer isolates consumer pace.** Each downstream consumer reads from the buffer at its own rate. A slow consumer (browser SSE proxy) does not starve a fast consumer (result-assembly task); neither blocks the other.
- **Terminal events are in-band.** Putting `done`/`error` into the same buffer guarantees every consumer receives the terminal event in correct sequence. Out-of-band signaling (setting a flag before writing the event) risks a consumer stopping before it reads the terminal payload.
- **Late-connecting consumers see the full history.** Because the buffer accumulates all events since stream open, a consumer that connects after the stream has already been running receives the complete event history immediately, then transitions to real-time polling.

## What the pattern does NOT protect against

(Discipline added 2026-05-18 per `patterns/README.md` convention — every pattern names its limits so it doesn't get oversold.)

**The buffer is unbounded by default.** The pattern accumulates every event for the life of the stream. Long-running streams or many concurrent jobs grow buffers linearly in memory; the pattern does not prescribe eviction. Mitigation: pair the per-job buffer with a high-water mark + eviction strategy. If buffer history is non-load-bearing for replay, drop-oldest; if late-connecting consumers depend on full history, cap concurrent jobs instead. Either way, decide explicitly — don't ship an unbounded list as production state.

**The pattern is push-from-source, pull-from-buffer — backpressure to the upstream source is lost.** Downstream consumers can be slow without blocking the reader (intended). But if the reader itself needs to slow the *source* down (rare, but possible with high-volume sources that support backpressure), the buffer interposes and the source never sees the consumer pace. Mitigation: not relevant for sources that don't support backpressure (most asyncio queues, SSE streams). If the source does support backpressure and you care, this isn't the right pattern.

**Buffer lifetime tied to job lifetime requires explicit cleanup.** Dead buffers from jobs that crashed or stalled accumulate if no cleanup hook fires. The pattern relies on per-job lifecycle being honored; it doesn't enforce it. Mitigation: register cleanup at job-creation time, not at completion (completion may never arrive).

## Validated instance

**BRIEF-079** — SSE-frontend implementation (2026-05-15)

During implementation, the naive design would have had two asyncio tasks connecting independently to the upstream's `GET /v1/jobs/{id}/events` SSE endpoint: a result-assembly task (needing the `done` payload to assemble structured output) and the SSE proxy endpoint `GET /api/jobs/{job_id}/events` (forwarding all events to the browser). Because the upstream's asyncio.Queue delivers each event once to whichever reader's `await` resolves first, the terminal `done` event would land in the wrong consumer roughly half the time — silent data loss, broken output assembly, no exception raised.

The pattern was applied before shipping:

- A single reader function (`consume_stream()`) is the sole reader from the upstream SSE stream. It appends each raw SSE frame as a string to `event_sink` (a `list[str]` per job, registered in a per-job map), and sets `done_event` when the stream terminates.
- The SSE proxy endpoint reads from the local `event_sink` buffer with 100ms async polling. It never opens a connection to the upstream. It waits for `done_event` and yields all remaining buffered events before closing.

The two-consumer race was caught and corrected during implementation, before any testing. The fix required no changes to the upstream's contract. BRIEF-079 was delivered 5/5.

## Adjacent patterns

**Broadcast channels with explicit channel ownership** (e.g., Redis pub/sub with named channels) — the right tool when the infrastructure itself fans out. Each subscriber gets its own copy; no intermediary buffer needed. Distinct from this pattern: the source does the work, not the reader.

**Message queues with consumer groups** (e.g., Kafka with group IDs) — fan-out via group semantics. Each group gets a full copy of the stream; consumers within a group partition the stream. Use when horizontal scale across multiple processes is required. This pattern addresses a single-process, multiple-consumer shape; consumer groups are overkill and add operational complexity.

**Sequential Overnight Build** ([[sequential-overnight-build]]) — the upstream/downstream handoff pattern that produced this incident. The two-consumer race was caught *because* the downstream brief specified building against the live upstream, not a mock — which forced the correct consumption architecture to be designed explicitly rather than assumed.

## Governance

Patterns are part of the Intent layer (alongside `CLAUDE.md` and `team/*.md`). New pattern entries require owner approval before merge. Leroy proposes; the owner accepts.

Pattern status values: `proposed` (one instance observed, awaiting approval) → `validated` (approved with at least one instance) → `deprecated` (superseded or no longer applicable).

---

*Pattern #2 of N. See `/patterns/` for the full set.*
