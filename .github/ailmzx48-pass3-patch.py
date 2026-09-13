# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from pathlib import Path

P = Path("usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md")
t = P.read_text(encoding="utf-8")


def one(old, new):
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit(f"expected one match, got {n}: {old[:80]!r}")
    t = t.replace(old, new, 1)


def section(start, end, body):
    global t
    i = t.find(start)
    if i < 0:
        raise SystemExit(f"missing section start: {start!r}")
    j = t.find(end, i + len(start))
    if j < 0:
        raise SystemExit(f"missing section end: {end!r}")
    t = t[:i] + body.rstrip() + "\n\n" + t[j:]


one("Revision: 0.5-draft", "Revision: 0.6-draft")
one("Revision 0.5 retains it as a corrected benchmark baseline",
    "Revision 0.6 retains it as a corrected benchmark baseline")
one("Revision 0.5 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:",
    "Revision 0.6 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:")
one("## 23. Open design questions after Revision 0.5",
    "## 23. Open design questions after Revision 0.6")

needle = """0xF4..0xFF reserved for measured future encodings
```

Extended token IDs are provisionally limited to 0..4095"""
replacement = """0xF4..0xFF reserved for measured future encodings
```

`0x00` is the scratch-stream terminator/invalid-continuation sentinel. Length-delimited L0 turns and cold records end by declared length plus their framing and do not store or count that sentinel. The 320- and 256-byte scratch buffers therefore retain one final byte for `0x00` after their <=319/<=255 encoded payloads.

Candidate A has one canonical lexical token-ID space, 0..4095. The 224 selected hot tokens receive IDs 0..223 and encode only as byte `0x10 + id`. IDs 224..4095 encode only as `0xF0` followed by the little-endian u16 ID. The decoder rejects `F0` encodings of hot IDs and IDs above 4095, so a lexical token never has two accepted wire encodings.

LM context refs use lexical IDs 0x0000..0x0FFF plus a separate nonlexical range: 0x1000 literal-word, 0x1001 numeric-literal, 0x1002 proper-name, and 0x1003..0x1008 BOS, EOS, user-turn, assistant-turn, turn-end and newline. Literal-class refs are context-only and cannot be detokenized as invented words. Legal control refs map to their wire control codes when emitted. 0x1009..0x10FF remain reserved.

Extended token IDs are provisionally limited to 0..4095"""
one(needle, replacement)

one(
"""Unknown proper names can survive through the proper-name literal escape. The tokenizer must not silently transform a user-supplied unknown name into a known but different token.""",
"""Literal `F1`/`F3` payloads preserve accepted presentation bytes. Case folding is performed during comparison rather than by destroying those bytes. Thus an unknown name such as `McDonald` can survive with its presentation spelling while still participating in the policy-defined case-normalized match. The tokenizer must not silently transform a user-supplied unknown name into a known but different token.""")

one(
"""Persistent model entity/token IDs use semantic-reference bit 15 clear. Bit 15 set denotes a session-literal reference: bits 14..3 contain a 12-bit generation and bits 2..0 select one of eight slots. Candidate A reserves eight 34-byte slots:

```text
+0..1   generation, low 12 bits significant
+2      byte length 0..31
+3..33  exact normalized ASCII bytes, unused tail zero
```""",
"""Semantic-reference value zero is reserved for `absent`. Persistent model entity/token references therefore use bit 15 clear and values 1..0x7FFF; the host builder rejects persistent reference zero. Bit 15 set denotes a session-literal reference: bits 14..3 contain a 12-bit generation and bits 2..0 select one of eight slots. Generation zero is invalid, so live generations are 1..4095. Candidate A reserves eight 34-byte slots:

```text
+0..1   generation, low 12 bits significant
+2      byte length 0..31
+3..33  exact presentation ASCII bytes, unused tail zero
```""")

one(
"""An exact existing literal is reused rather than duplicated. Before a slot is reused, every matching L1/L2 reference is invalidated by a bounded scan and `ai_litloss` is incremented; the new generation makes any missed stale reference fail validation rather than alias a new name. Generation wrap is handled by first invalidating every reference to that slot and restarting its generation from 1. Slot selection is deterministic: prefer an unreferenced slot, otherwise evict the oldest/lowest-retention referenced slot after invalidating it. If exact old literal bytes are lost, the agent may retain the remaining semantic relation but must not pretend it still knows the exact spelling.""",
"""An existing literal is reused when its policy-defined ASCII-folded comparison matches; the retained presentation bytes are not rewritten merely because a later mention uses different case. Before slot reuse, every matching L1/L2 reference is invalidated by a bounded scan and `ai_litloss` is incremented. The new nonzero generation makes a missed stale reference fail validation rather than alias a new name. Generation wrap first invalidates every reference to the slot and restarts at 1. Slot selection is deterministic: prefer an unreferenced slot, otherwise reuse the oldest/lowest-retention referenced slot after invalidation. If old presentation bytes are lost, the agent may retain the remaining semantic relation but must not pretend it still knows the spelling.""")

section(
"### 8.3 Promotion and compaction\n",
"### 8.4 Correction and supersession rule\n",
"""### 8.3 Promotion and compaction

A turn is transactional with respect to conversation memory for every recoverable failure. Classification/retrieval may read the session-literal table but may not allocate, reuse or invalidate a slot before commit. A new literal remains in current-turn scratch for the current answer; persistent session-literal allocation is needed only when an evicted L0 turn is reduced into L1/L2.

Candidate A performs these bounded steps:

1. read and validate the raw user line;
2. tokenize it completely into the 320-byte current-turn scratch, including user-turn/BOS/EOS/turn-end framing; reject without state mutation when framed encoding exceeds 319 bytes;
3. classify/retrieve/generate with current-turn scratch, L0/L1/L2 and read-only session-literal lookup;
4. finish the complete framed response in the 256-byte response-token buffer and validate factual anchors plus token/encoded/printed-byte ceilings;
5. after the cold winners are no longer needed, reuse the 512-byte aim/retrieval scratch to preflight the context commit without mutation: prove required byte/descriptor evictions, validate every L0 descriptor/escape that will be consumed, and prove all fixed L1/L2/session-literal operations are bounded;
6. stream the validated response through the production tty path;
7. apply the preflighted fixed-memory commit: derive at most two ranked capsules from each selected oldest L0 turn, perform deterministic L1-to-L2 compaction and any required session-literal invalidation/reuse, evict complete old turns, then append both complete new speaker turns only after byte and descriptor capacity is available;
8. update the 96-entry decoded LM-context cache and diagnostic counters;
9. in a diagnostic L3 build, append raw accepted input bytes and exact logical output bytes only within its pre-budgeted quota; L3 failure is counted and does not roll back normal conversation state;
10. verify guards before the next prompt.

The preflight overlay is part of the generated Section-8.7 lifetime/layout report. Commit performs no dynamic allocation and no required external I/O, so successful preflight leaves no recoverable capacity failure. An invariant/guard failure is a fatal-session condition, not a promise of rollback from corrupted state.

The 128-byte L0 directory is exactly 32 four-byte descriptors: `u16` ring start plus `u16` encoded byte length. Speaker/turn type remains encoded in the turn stream itself. Ring reads crossing the physical end use bounded modulo copying; a descriptor is accepted only when start/length prove every referenced byte lies within the 896-byte logical ring.

The commit path is tested at both limiting resources: nearly full ring bytes with free descriptors, and free bytes with all descriptors occupied by tiny turns. When L1 needs slots, victim selection is deterministic: weaker protection class first, then lower importance, then greater saturating age, then lower slot index. Explicit corrections and unresolved state outrank ordinary chatter through a frozen protection-class table. Every selected L1 victim is merged into L2 before its slot is reused; if all records are highly protected, the same total order still chooses a victim rather than deadlocking. The host reference freezes/tests that mapping before target implementation.

No stage allocates an unbounded temporary copy of text or semantic records.""")

one("The response generator receives the recent exact L0 tail,",
    "The response generator receives the recent canonical-token L0 tail,")
one("- exact-recall horizon;", "- canonical-token recall horizon;")
one("- recent exact-context recall;", "- recent canonical-token context recall;")
one("4. How many exact L0 turns/tokens fit in 896 bytes for real conversations?",
    "4. How many canonical-token L0 turns/tokens fit in 896 bytes for real conversations?")

one(
"""The first experimental objective remains semantic recall over source-equivalent history many times larger than the L0 exact ring without increasing this 4,336-byte baseline. No public ratio is claimed until the harness measures it.""",
"""The first experimental objective remains semantic recall over source-equivalent history many times larger than the L0 canonical-token ring without increasing this 4,336-byte baseline. The release objective includes a retained long-conversation transcript whose raw source dialogue exceeds the 32 KiB ZX-UX task/object arena while still demonstrating useful distant semantic dependencies. This is a semantic-context claim, not a promise that >32 KiB of verbatim bytes are resident or recoverable. No public ratio is claimed until the harness measures it.""")

one(
"""Every retained model candidate publishes a machine-readable memory report containing at least compiled SDK artifact identity; eventual MEX1 image/text/BSS sizes and symbol/map evidence; configured heap; MEX1 minimum stack and actual +64 allocation; native stack canary/high-water result; ARG1/ENV1 bytes; the 4,336-byte workspace; resident lexicon/hot-table bytes; external model logical/physical/aligned bytes; packed-reader states; optional L3 quota; shell/other process allocations; pinned resources; observed arena peak; FAST and CONTENDED free totals/largest extents; and final total/largest-extent headroom in the actual load/launch order.""",
"""Every retained model candidate publishes a machine-readable memory report containing at least compiled SDK artifact identity; eventual MEX1 image/text/BSS sizes and symbol/map evidence; configured heap; MEX1 minimum stack and actual +64 allocation; native stack canary/high-water result; ARG1/ENV1 bytes; the 4,336-byte workspace; resident lexicon/hot-table bytes; external model logical/physical/aligned bytes; packed-reader states; optional L3 quota; shell/other process allocations; pinned resources; observed arena peak; the address-ordered free-extent map; FAST and CONTENDED free totals; largest legal `ANY` extent including a permitted 0x7FFF/0x8000 crossing; largest `FAST_REQUIRED` extent; actual `COLD_PREFERRED` placement/fallback; and final headroom after replaying the real load/launch allocation sequence.""")

one(
"""  -> validate anchors, repetition, token ceiling and decoded byte ceiling
  -> stream detokenization through the real tty path
  -> commit user/assistant encoded turns to L0 and perform bounded compaction
  -> update diagnostic evidence""",
"""  -> validate anchors, repetition, token ceiling and decoded byte ceiling
  -> preflight bounded no-mutation context commit using scratch overlay
  -> stream detokenization through the real tty path
  -> apply fixed-memory L0/L1/L2/session-literal commit
  -> update diagnostic evidence / optional quota-bounded L3 archive""")

one(
"""© 2006 Supratim Sanyal

I am ailmzx48.""",
"""© 2006 Supratim Sanyal
Based on original work by Supratim Sanyal of SANYALnet Labs.

I am ailmzx48.""")

one(
"""The humor is retained. The exact target bytes remain provisional until the terminal/source character repertoire is proved. **Every non-ASCII glyph in the display draft, including `©` and the em dash, must have an explicitly supported target encoding or an ASCII-safe replacement**; the C48 source must not rely on a host editor/compiler accidentally accepting Unicode. The favorite `48K seemed enormous...` line has no such dependency and remains part of Candidate A.""",
"""The humor is retained. The exact ASCII attribution line `Based on original work by Supratim Sanyal of SANYALnet Labs.` is mandatory because the repository license requires discoverable attribution in user-facing text interfaces; at 60 characters it fits tty64. Decorative target bytes remain provisional until the terminal/source character repertoire is proved. **Every non-ASCII glyph in the draft, including `©` and the em dash, must have an explicitly supported target encoding or an ASCII-safe replacement**; changing a decorative glyph does not remove/alter the mandatory ASCII attribution. The C48 source must not rely on a host editor/compiler accidentally accepting Unicode.""")

one(
'- a queued byte `input_provider` whose invocation is itself an observable "program is asking for input" boundary;',
'- a queued byte `input_provider` that distinguishes queued-byte consumption from a **queue-empty demand** for another byte; only queue-empty demand is a conversational synchronization boundary;')

section(
"### 14.2 Human-emulation protocol\n",
"### 14.3 Transcript and run identity\n",
"""### 14.2 Human-emulation protocol

A conversation runner does not dump hundreds of lines into stdin blindly. It behaves like a user:

1. start the compiled program with the provider queue empty;
2. observe output until `input_provider` reaches its first queue-empty demand for a normal conversation byte;
3. assert the complete expected prompt bytes were emitted before satisfying that demand;
4. choose the next scenario/adaptive turn;
5. enqueue its bytes plus the scenario's canonical ENTER byte; provider calls that merely drain queued bytes are **not** response boundaries;
6. after the turn bytes are consumed, wait for the next queue-empty demand; that demand is the primary response boundary and the harness also asserts the expected prompt suffix;
7. score/log the turn;
8. continue for the configured conversation length;
9. enqueue `q` plus ENTER and prove clean termination without another queue-empty conversational demand.

A queue-empty input demand is the synchronization event. An arbitrary `input_provider` callback is not, because one line causes one callback per consumed byte. Scanning output for `>` alone is likewise insufficient because answers can contain prompt-like bytes. Prompt bytes remain asserted as terminal behavior, but are not the sole framing protocol. Separate input tests cover accepted CR/LF forms so a two-byte host line ending cannot accidentally manufacture a second empty turn.

The baseline runner is deterministic. A development-time modern LM may later act as an adaptive human-like interlocutor/reviewer, but deterministic scripted/adversarial suites remain mandatory so a model change can be reproduced without an external service.""")

one(
"""Correctness may not depend on the host being able to inspect these globals. They are instrumentation, not a hidden control channel, and their bytes are charged to the guards/counters portion of the workspace ledger.""",
"""Correctness may not depend on the host being able to inspect these globals. They are instrumentation, not a hidden control channel, and their bytes are charged to the guards/counters portion of the workspace ledger.

Counter width/epoch is explicit so a long run cannot wrap into fake good news. `ai_l0bytes`, `ai_l1count`, `ai_l2count` and `ai_error` are instantaneous state. `ai_compact`, `ai_l2evict`, `ai_l1drop`, `ai_litloss`, `ai_mrecords`, `ai_mhits`, `ai_otokens`, `ai_yields` and `ai_encfail` are unsigned-16 per-input-attempt counters reset before each attempt; their Candidate-A per-attempt maxima are proved below 65536 and the host aggregates them. `ai_turns` is a saturating unsigned-16 accepted-turn count; the harness transcript count is authoritative beyond saturation.""")

one("ai_classify()     intent/topic/entity/session-literal extraction",
    "ai_classify()     read-only intent/topic/entity/literal lookup")

one(
"16. What is the longest retained semantic dependency demonstrated by an actual transcript, not a synthetic byte count?",
"16. What is the longest retained semantic dependency demonstrated by an actual transcript, not a synthetic byte count, and does a retained stress transcript exceed 32 KiB of raw source dialogue without pretending those raw bytes remain live?")

if "Revision 0.5" in t:
    raise SystemExit("stale Revision 0.5 reference remains")

P.write_text(t, encoding="utf-8", newline="\n")
