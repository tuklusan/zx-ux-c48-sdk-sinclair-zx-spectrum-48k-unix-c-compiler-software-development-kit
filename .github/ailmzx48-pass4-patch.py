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
        raise SystemExit(f"expected one match, got {n}: {old[:100]!r}")
    t = t.replace(old, new, 1)


one("Revision: 0.6-draft", "Revision: 0.7-draft")
one("Revision 0.6 retains it as a corrected benchmark baseline",
    "Revision 0.7 retains it as a corrected benchmark baseline")
one("Revision 0.6 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:",
    "Revision 0.7 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:")
one("## 23. Open design questions after Revision 0.6",
    "## 23. Open design questions after Revision 0.7")

one(
"""LM context refs use lexical IDs 0x0000..0x0FFF plus a separate nonlexical range: 0x1000 literal-word, 0x1001 numeric-literal, 0x1002 proper-name, and 0x1003..0x1008 BOS, EOS, user-turn, assistant-turn, turn-end and newline. Literal-class refs are context-only and cannot be detokenized as invented words. Legal control refs map to their wire control codes when emitted. 0x1009..0x10FF remain reserved.""",
"""LM context refs use lexical IDs 0x0000..0x0FFF plus a separate nonlexical range: 0x1000 literal-word, 0x1001 numeric-literal, 0x1002 proper-name, 0x1003 BOS, 0x1004 EOS, 0x1005 user-turn, 0x1006 assistant-turn, 0x1007 turn-end and 0x1008 newline. Literal-class refs are context-only and can never be serialized as learned output continuations. Candidate A learned continuation lists may contain lexical IDs, EOS and newline only. BOS plus user/assistant/turn-end framing are controller-owned; reserved refs are rejected. The host builder/verifier enforces this allowlist before target bytes exist. 0x1009..0x10FF remain reserved.""")

one(
"""If a later compact alias index beats the resident sorted lexicon, it is a measured candidate change; Candidate A does not assume such an index for free.""",
"""If a later compact alias index beats the resident sorted lexicon, it is a measured candidate change; Candidate A does not assume such an index for free.

The 16-bit **semantic-reference** namespace used by L1/L2 and cold-record entity fields is deliberately separate from the 0..4095 lexical token-ID namespace. Semantic reference 0 means absent; persistent semantic symbols use 1..0x7FFF; bit-15-set values are session literals. Host tooling owns the mapping from recognized lexical tokens/phrases to persistent semantic symbols and charges that mapping to resident hot-table bytes. A lexical token ID is never copied blindly into a semantic-reference field.""")

one(
"""An existing literal is reused when its policy-defined ASCII-folded comparison matches; the retained presentation bytes are not rewritten merely because a later mention uses different case. Before slot reuse, every matching L1/L2 reference is invalidated by a bounded scan and `ai_litloss` is incremented. The new nonzero generation makes a missed stale reference fail validation rather than alias a new name. Generation wrap first invalidates every reference to the slot and restarts at 1. Slot selection is deterministic: prefer an unreferenced slot, otherwise reuse the oldest/lowest-retention referenced slot after invalidation. If old presentation bytes are lost, the agent may retain the remaining semantic relation but must not pretend it still knows the spelling.""",
"""An existing literal is reused when its policy-defined ASCII-folded comparison matches; the retained presentation bytes are not rewritten merely because a later mention uses different case. Before slot reuse, every matching L1/L2 reference is invalidated by a bounded scan and `ai_litloss` is incremented. The new nonzero generation makes a missed stale reference fail validation rather than alias a new name. Generation wrap first invalidates every reference to the slot and restarts at 1.

Slot selection is a frozen total order. Prefer an unreferenced slot, lowest slot index first. Otherwise scan all L1/L2 references to each slot and derive the slot's strongest live retention tuple: highest record protection class, then highest importance, then youngest (smallest) age. Evict the slot whose strongest tuple is weakest: lower protection, then lower importance, then older age, then lower slot index. This protects a slot when even one live record strongly needs it while still guaranteeing a victim when all eight slots are referenced. Every invalidated reference is cleared/counted before new bytes receive the new generation. If old presentation bytes are lost, the agent may retain the remaining semantic relation but must not pretend it still knows the spelling.""")

one(
"""Age is not a modulo turn counter. The u8 age bucket saturates at 255; bounded maintenance/compaction increments or recomputes it with saturation so wrap can never make ancient state appear new.""",
"""Age is not a modulo turn counter. The u8 bucket is measured in accepted conversational turns and saturates at 255. On every accepted-turn commit, preflight/commit age every already-resident L1/L2 record by one with saturation before victim selection. A capsule newly derived from an evicted L0 speaker turn is initialized to `1 +` the number of newer user-turn descriptors already present after that source turn in the pre-commit L0 directory, saturated to 255; this preserves the time the source already spent in L0 instead of making an old assertion look new when compressed. User and assistant descriptors from the same dialogue turn therefore receive the same initial turn age. L2 coalescing retains the age of the surviving/newest semantic observation selected by the correction/supersession rule. No age path wraps to youth.""")

one("**L3 — optional exact transcript archive**",
    "**L3 — optional exact accepted-turn archive**")
one(
"""The SDK/GitHub harness always retains an exact external transcript. Candidate A keeps target L3 **disabled by default** because an appendable RAW RAM object consumes the same arena as the process/model and reopening a PACKED object for write can materialize a RAW replacement.""",
"""The SDK/GitHub harness always retains the exact external session transcript. Candidate A keeps target L3 **disabled by default**. When enabled, target L3 is only an exact archive of accepted user/assistant turn bytes; startup/prompt traffic and rejected raw lines remain available only in the external harness transcript. A writable RAW archive consumes the same arena as the process/model and reopening a PACKED object for write can materialize a RAW replacement.""")

one(
"""The preflight overlay is part of the generated Section-8.7 lifetime/layout report. Commit performs no dynamic allocation and no required external I/O, so successful preflight leaves no recoverable capacity failure. An invariant/guard failure is a fatal-session condition, not a promise of rollback from corrupted state.""",
"""The preflight overlay is part of the generated Section-8.7 lifetime/layout report. It simulates the same accepted-turn age update, L1/L2 victim/merge order, session-literal invalidations/reuse and L0 evictions that commit will replay. Commit performs no dynamic allocation and no required external I/O, so successful preflight leaves no recoverable capacity failure. An invariant/guard failure is a fatal-session condition, not a promise of rollback from corrupted state.""")

one(
"""- model-format reader code and constants.""",
"""- semantic-symbol lookup/mapping needed by L1/L2;
- model-format reader code and constants.""")

old_fmt = """u8   importance
u8   trigger_count              0..4
u16  trigger[trigger_count]
...  encoded token payload      must fit logical_record_length
```"""
new_fmt = """u8   importance
u8   trigger_count              0..4
u16  trigger[trigger_count]     canonical lexical token IDs
u8   anchor_count               0..2
pair anchor[anchor_count]:
      u8 payload_offset
      u8 encoded_length
...  encoded token payload      must fit logical_record_length
```"""
one(old_fmt, new_fmt)

one(
"""The 192-byte maximum is chosen because two complete winners must coexist inside the 512-byte retrieval scratch with bounded streaming/parser state. Host tooling rejects records shorter than their declared header, over 192 logical bytes, with trigger_count above four, unknown record types, persistent entity IDs using the session-literal high-bit namespace, or token payloads that do not terminate exactly at the record boundary.

Every trigger token/alias must be target-recognizable through the resident lexicon described in Section 7.1. Payload-only wording need not consume resident dictionary bytes.""",
"""The 192-byte maximum is chosen because two complete winners must coexist inside the 512-byte retrieval scratch with bounded streaming/parser state. `entity_a`/`entity_b` use the Section-7.1 semantic-reference namespace: zero is absent and any nonzero cold-model entity must be a persistent 1..0x7FFF symbol. Each trigger is a canonical lexical ID 0..4095 and must be target-recognizable through the resident lexicon.

An anchor pair identifies an exact byte span within the encoded payload. Anchor spans may cover one or more complete lexical/control/literal encodings, have nonzero length, may not overlap, and must begin/end on token boundaries. Candidate A permits at most two spans; factual record types admitted for factual-answer use must carry at least one. The controller copies required anchor sequences byte-for-byte into its anchor plan and never asks the LM to regenerate their content from memory.

Host tooling rejects records shorter than the header implied by their counts, over 192 logical bytes, with trigger_count above four, anchor_count above two, unknown record types, invalid semantic refs, triggers above 4095, illegal/reserved payload controls, malformed literal escapes, anchor spans outside the payload or off token boundaries, overlapping anchors, or payload parsing that does not consume exactly the declared record. Payload-only wording need not consume resident dictionary bytes.""")

one(
"""Literal-class refs from Section 7.3 back off normally when no learned higher-order context exists.""",
"""Literal-class refs from Section 7.3 may appear in lookup context keys and back off normally when no learned higher-order context exists; they are forbidden in learned continuation lists. BOS/user-turn/assistant-turn/turn-end refs are likewise context/controller state rather than learned output candidates.""")

one(
"""The first retriever uses only integer additions/comparisons. Candidate features include exact topic match, entity/session-literal match, trigger-token overlap, question/intent compatibility, current conversational-memory reinforcement, and record importance. No runtime floating point is needed.

The host reference implementation calculates the same integer score byte-for-byte. Any future improvement that uses a different host-only formula without a target equivalent is not a valid target model improvement.""",
"""The first retriever uses only integer additions/comparisons. Candidate features include exact topic match, entity/session-literal match, trigger-token overlap, question/intent compatibility, current conversational-memory reinforcement, and record importance. No runtime floating point is needed.

Candidate-A retrieval and continuation-adjustment arithmetic uses signed 16-bit C48 `int`. Before a model/configuration is emitted, host tooling calculates widened mathematical minima/maxima for every legal feature/candidate combination and rejects weights or penalties whose intermediate or final sum can leave -32768..32767. Target code follows a frozen addition order, so host and target never depend on accidental 16-bit wrap for ranking.

The host reference implementation calculates the same integer score byte-for-byte. Any future improvement that uses a different host-only formula without a target equivalent is not a valid target model improvement.""")

one(
"""Candidate A reserves 192 bytes and accepts at most 191 ASCII input bytes before the terminating NUL. Overlength raw input is cleanly drained/rejected to the next newline. A raw line that fits but violates a literal-span limit from Section 7.4 or expands beyond 319 encoded bytes is likewise rejected before context mutation. Silent text or semantic truncation is not acceptable.""",
"""Candidate A reserves 192 bytes and accepts at most 191 printable ASCII input bytes before the terminating NUL. `ai_readline` tracks an explicit byte count while reading; NUL and other non-line control bytes are rejected **before** they can become C-string content, so neither `strlen` nor tokenization can mistake embedded NUL for a shorter valid line. CR and LF are accepted line terminators. A CR sets a one-byte `drop_lf` state for the next read: if the next byte is LF it is discarded, otherwise that byte begins the next line. This collapses CRLF without a look-ahead read that would create a false harness boundary.

Overlength or control-invalid raw input is drained/rejected to the next line terminator without context mutation. A raw line that fits but violates a literal-span limit from Section 7.4 or expands beyond 319 encoded bytes is likewise rejected before context mutation. Silent text or semantic truncation is not acceptable.""")

one(
"""- arena budget overflow;
- model parser accepting a malformed unsafe record;""",
"""- arena total-byte, placement-class or contiguous-extent allocation proof failure;
- model parser accepting a malformed unsafe record;
- an unadmitted source or source lacking the recorded authorization/license basis contributing to training/model bytes;""")

one(
"""ai_readline()     bounded tty line input
ai_tokenize()     ASCII line -> bounded canonical encoded tokens""",
"""ai_readline()     bounded byte-aware tty line input
ai_tokenize()     accepted ASCII line -> canonical encoded tokens""")
one(
"""ai_generate()     deterministic bounded LM continuation
ai_ctxcommit()    L0 append, eviction, L1/L2 compaction
ai_print()        validated streaming tty output""",
"""ai_generate()     deterministic bounded LM continuation
ai_ctxcheck()     no-mutation bounded context-commit preflight
ai_ctxcommit()    replay preflighted fixed-memory context commit
ai_print()        validated streaming tty output""")

one(
"""13. How much total, FAST and largest-contiguous arena headroom remains with shell/system state, ARG1/ENV1, model object and decoder alive in the real launch order?""",
"""13. What address-ordered free map, largest legal ANY extent, largest FAST_REQUIRED extent and actual COLD_PREFERRED placement/fallback remain with shell/system state, ARG1/ENV1, model object and decoder alive in the real launch order?""")

one("- exact target object names and cassette physical ordering;",
    "- exact target model object names/types/paths and cassette physical ordering;")

if "Revision 0.6" in t:
    raise SystemExit("stale Revision 0.6 reference remains")

P.write_text(t, encoding="utf-8", newline="\n")
