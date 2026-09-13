<!--
============================================================================
Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
Proprietary rights reserved except as expressly licensed herein.

ZX-UX C48 SDK
This file is governed by the SANYALnet Labs Non-Commercial License in the
root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
for AI/ML model training are prohibited unless separately authorized.

Attribution is required: "Based on original work by Supratim Sanyal of
SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
patent, trademark, and governing-law provisions.
============================================================================
-->
# ailmzx48 Detailed Design

Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.

Status: Design in progress — first measurable model candidate, compressed-context memory plan, and SDK conversation harness established  
Revision: 0.3-draft  
Canonical repository path: `usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md`  
Canonical SDK executable path: `usr/bin/ailmzx48`

## 1. Purpose

`ailmzx48` is a small English conversational language model for ZX-UX. It is written in C48 and is intended to run both on an actual unexpanded Sinclair ZX Spectrum 48K under ZX-UX and in the ZX-UX C48 SDK environment.

The shipped model is trained specifically around the Sinclair ZX Spectrum: its games, history, hardware and software architecture, culture, folklore, personalities, and related subjects. Runtime inference is local to the Spectrum/ZX-UX program. A remote modern language model is not part of the shipped runtime design.

The goal is not to pretend that a 48K Spectrum can run a modern transformer. The goal is to build the most convincing, useful, reproducible local conversational agent that fits the real machine and real ZX-UX/C48 contracts.

The implementation must genuinely contain a learned language-model component. A collection of canned question/answer strings with a prompt around it is not sufficient. Retrieval, compact factual records, deterministic response patterns, and hand-written safety/fallback logic are all permitted, but learned token-continuation statistics must materially participate in normal English response production.

## 2. Explicit project requirements

The following requirements are frozen inputs to the design and are not implementation claims unless a later section explicitly says so:

1. Program name: `ailmzx48`.
2. Implementation language: C48.
3. Runtime targets: actual ZX Spectrum 48K running ZX-UX, and the ZX-UX C48 SDK environment.
4. The release ships with a compact Spectrum-specialist conversational model.
5. The effective conversational context shall substantially exceed the amount of dialogue that can remain as directly addressable live text in the process at once. This is achieved by application-level token/semantic compression and bounded retrieval, not by claiming virtual memory.
6. The user may enter `q` to quit at any time the program is waiting for normal conversational input.
7. Source, design, training/evaluation material, and retained conversation evidence live below `usr/src/ailmzx48/`; the runnable SDK artifact lives at `usr/bin/ailmzx48`.
8. Instrumentation shall support long automated conversations on GitHub-hosted runners, keyboard/input injection into the running SDK session, exact transcript recovery, retained conversation logs, iterative model training/evaluation, and repeat-until-convergence development rather than a fixed training-iteration count.
9. The final documentation shall specify the real-cassette user workflow for booting ZX-UX, loading the native C48 toolchain and `ailmzx48` source/model material from tape, compiling/linking it, saving the resulting executable to tape, reclaiming build-tool memory, and subsequently loading/executing `ailmzx48` without inventing unsupported commands or behaviors.
10. Accuracy and verifiable behavior take priority over implementation convenience.
11. The model and context system must fail within explicit bounds. Corrupt model data, corrupt compressed context, exhausted heap/object space, overlong input, and unavailable optional history must not turn into silent memory corruption.
12. Training/construction may use modern host computers. Normal shipped inference may not depend on a PC, network, Internet service, remote API, or modern remote LM.
13. The design and its retained evidence are durable only after they have been committed to repository `main`; an ephemeral runner or `/mnt/data` copy is not a project checkpoint.

## 3. Canonical authorities

The authority order for this project is frozen as follows.

1. ZX-UX architecture: upstream `docs/01-ZX-UX-ARCHITECTURE-REV12.md` on `main` in `tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project`.
2. ZX-UX implementation/certification plan: upstream `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md` on `main` in the same repository. REV03 explicitly declares itself subordinate to REV12; if the two conflict, REV12 wins.
3. C48 language: `doc/C48 Language Specification Rev 0.11.docx` on `main` in this SDK repository.
4. C48 SDK/compiler/runtime documentation, implementation, examples, tests, and generated artifacts in this repository are implementation evidence and compatibility aids. They do not override the three canonical documents above.
5. This `ailmzx48` design is subordinate to the canonical ZX-UX and C48 contracts.

Design statements that depend on target behavior shall name the authority from which they were derived. Assumptions not yet proved against a canonical authority and/or executable test remain explicitly provisional.

REV03 states that it is subordinate to REV12. That rule is inherited here: implementation convenience, host SDK behavior, this document, or a training result can never silently override REV12 target semantics.

## 4. Repository layout

```text
usr/
├── src/
│   └── ailmzx48/
│       ├── AILMZX48-DETAILED-DESIGN.md
│       ├── ailmzx48.c                 # created when implementation begins
│       ├── model/
│       ├── training/
│       ├── evaluation/
│       ├── conversations/
│       └── tooling/
└── bin/
    └── ailmzx48                       # generated runnable SDK artifact
```

The repository `usr/...` layout is an SDK/repository layout. It must not be confused with the much smaller fixed ZX-UX target namespace defined by REV12. Target-side filenames, object placement, and cassette packaging will be specified separately and must obey the ZX-UX namespace limits.

Git does not preserve empty directories, so the initial scaffold contains small README files in the design subdirectories. They define intended ownership without prematurely freezing file formats.

Expected host-side ownership as the design matures is:

```text
model/          generated target model, format notes, model identity
training/       corpus manifests, deterministic builders, training reports
evaluation/     scenarios, expected facts, scoring configuration
conversations/  selected retained transcripts and convergence evidence
tooling/        host-only build, runner, transcript, scoring and inspection tools
```

Generated bulk CI artifacts need not all be committed. A selected durable evidence set and the metadata needed to reproduce it shall be committed.

## 5. Canonical target constraints that shape this design

### 5.1 Real memory model

REV12 reserves the Spectrum display/ROM-compatibility area below `0x6000` from general allocation and the resident kernel at `0xE000-0xFFFF`. The general ZX-UX arena is therefore the contiguous 32 KiB range `0x6000-0xDFFF`.

That same arena is shared by process image/BSS allocations, process stacks, pipes, mutable RAM-object payloads, compiler/editor working data, and other user allocations. More files mean less process memory and vice versa. `ailmzx48` therefore has no private 48 KiB address space and no license to budget against the headline machine RAM size.

Normal MEX1 image+BSS allocations use `ANY` placement across the arena. Process stacks are `FAST_REQUIRED`. Correctness may not depend on whether ordinary process image/BSS bytes happen to lie in contended or uncontended RAM.

The ordinary launch case must also account for other live ZX-UX allocations. In particular, a foreground external program must not assume that the shell and system resources consume zero arena bytes. The eventual release gate shall measure total simultaneous arena occupancy, not merely `ailmzx48`'s owned process bytes.

ZX-UX has `SYS_EXEC`, which replaces a process image, but this design does not assume that a user-facing shell `exec` command exists until the canonical shell contract or implementation proves one. Ordinary invocation is therefore the conservative memory-budget baseline.

### 5.2 C48 process heap

REV12 section 26 defines no user `SYS_ALLOC`. The C48 heap is a fixed link-time reserve inside the executable BSS. Default `crt0` reserves 1024 bytes unless the linker is given an allowed `-heap` value; the allowed range is an even value from 0 through 8192 bytes.

Consequences for `ailmzx48`:

- the design shall not depend on a growable heap;
- the normal target build should prefer fixed global/static byte arrays and bounded scratch buffers;
- if `malloc` is used at all, its exact purpose and worst-case lifetime must be budgeted before release;
- a zero-heap build is the preferred first target;
- a nonzero heap is accepted only if measurement demonstrates a clear reduction in total memory or complexity without compromising determinism.

### 5.3 C48 language/data-model constraints

The canonical language authority is `C48 Language Specification Rev 0.11.docx`. REV12 section 25 mirrors the target-facing C48 contract used by ZX-UX. The implementation is to be written to the canonical Rev 0.11 language, not to host C extensions.

Important frozen constraints include an 8-bit unsigned plain `char`, 16-bit `short`/`int`/pointers, five-byte Spectrum-native `float`, no `long`, and deliberately limited language facilities. REV12 also defers facilities such as `struct`/`union`, `switch`/`case`, variadic functions, function pointers, the conditional operator, compound assignment, and the comma operator.

The design therefore uses flat byte arrays, parallel arrays where a record would otherwise be tempting, explicit indices, small fixed functions, integer/fixed-point scoring, and direct bounds checks. Floating point is not required for model inference.

Before implementation begins, every C construct introduced into `ailmzx48.c` must be accepted by the canonical C48 specification and the SDK compiler acceptance tests. Host-only tooling may use ordinary contemporary languages and data structures.

### 5.4 I/O and object-storage constraints

REV12 provides ordinary C48 `open`, `read`, `write`, `seek`, `close`, `read_full`, and `write_full` interfaces over ZX-UX objects and devices. The mutable RAM-object table has exactly 32 entries, and ordinary object base names are limited to the ZX-UX fixed namespace contract.

Stored object payloads occupy the same 32 KiB arena as running processes. A separate model/context object is therefore not free merely because it is outside the C48 process image.

REV12 `zxpack`/ZXP1 may compress eligible inactive stored objects. It explicitly does not compress live process image/BSS/heap, stacks, pipes, screen memory, kernel RAM, or pinned runtime resources. `ailmzx48` must never describe ZXP1 as virtual memory or imply that compressed bytes are directly addressable.

A PACKED object is read as its logical byte stream through normal reads. A packed read-only open description requires exactly 272 bytes of COLD-preferred streaming decoder state/history. Packed seeking backward resets the decoder and decodes/discards from logical offset zero. Random backwards probing of one large PACKED object is therefore deliberately expensive and must not be the normal inner inference loop.

Any write-capable open of a PACKED RAM object materializes a private RAW replacement before the writer is returned, except that truncation may create an empty RAW replacement directly. This makes PACKED model/context data safe to transform, but reinforces the rule that archived PACKED data is cold storage rather than a random-access working set.

### 5.5 Scheduler/process behavior

ZX-UX v1 is cooperative. `ailmzx48` must return to kernel boundaries often enough that it does not make the machine feel dead during long scoring/generation loops. The implementation shall define bounded work quanta and call `yield()` at deterministic safe points where measured inference latency warrants it.

A CPU-bound user process is not forcibly preempted merely because it takes too long. Consequently responsiveness is an application responsibility.

The first target implementation shall place yield checkpoints at outer bounded scans rather than deep inside invariants whose partial state would be difficult to validate. Candidate checkpoints include model-record scan intervals, long context-relevance scans, and response-generation token boundaries.

### 5.6 Terminal behavior

ZX-UX exposes a 64-column terminal mode and exact terminal semantics in REV12. `ailmzx48` shall write ordinary terminal text rather than draw its own text renderer. Its wrapping and prompt behavior must be tested against the real tty implementation, including deferred-wrap semantics.

The terminal is part of the behavior contract. Automated evaluation shall capture the logical character stream as well as, for selected cases, the final 6912-byte Spectrum screen. A pretty host transcript cannot substitute for correct target wrapping/scrolling.

## 6. Architectural choice: a host-trained sparse local language agent

A transformer-style neural LM is not the baseline architecture. Its parameter storage, activation memory, multiply-heavy inference, and context machinery are a poor fit for a 3.5 MHz Z80 and the ZX-UX arena.

The working architecture is instead a host-trained, target-inferred sparse statistical language agent with four cooperating pieces:

1. a compact tokenizer/vocabulary;
2. a tiny intent/topic and salient-entity scorer;
3. a compressed Spectrum-domain knowledge/reply store;
4. a variable-order token language model used to rank or generate fluent response continuations under the controller's topic/intent constraints.

This is still a language model: probabilities/weights over token continuations are learned from a corpus and used locally at inference time. The surrounding agent controller supplies conversation state, memory retrieval, topic steering, factual anchoring, uncertainty/fallback behavior, and anti-repetition controls.

The exact release model family is not frozen by this revision. Revision 0.3 does freeze one concrete **Candidate A** so implementation and measurements can begin. Candidate A is a benchmark baseline, not a promise that no better representation will replace it.

### 6.1 No remote inference dependency

A host may train, evaluate, package, inspect, and fuzz the model. GitHub runners may automate those jobs. None of that changes the shipped runtime rule: after the target artifacts are produced, normal `ailmzx48` inference must work with no PC/server/Internet language-model service.

A modern model may be used as a development-time reviewer or synthetic conversational partner only if the evaluation records clearly distinguish its role from target inference and corpus licensing permits the interaction. Target answers must never be silently generated remotely and then presented as Spectrum inference.

### 6.2 No float requirement in the inference core

Training may use floating-point probabilities on the host. The target format shall quantize them into small unsigned integer scores or rank buckets. Runtime comparison/accumulation should use 8- and 16-bit integer operations wherever possible.

If a future candidate genuinely benefits from wider accumulation, it must implement that width explicitly from smaller integer pieces; C48 has no `long` type to casually absorb the problem.

### 6.3 Determinism first

Candidate A uses deterministic decoding. Equal-score choices use a frozen token-ID or record-order tie break. This makes every model build and conversation regression reproducible.

Light stochastic sampling may later be evaluated as an optional conversational-quality feature, but it must accept an explicit seed and must never be required for factual correctness. The first target implementation does not need a random-number generator.

## 7. Token representation — Candidate A

The target tokenizer is deterministic, bounded, and cheaper than carrying raw repeated English text through the whole context engine.

Candidate A uses a mixed-width token byte stream. The candidate wire space is:

```text
0x00        stream terminator / invalid continuation sentinel
0x01        beginning-of-sentence marker
0x02        end-of-sentence marker
0x03        user-turn marker
0x04        assistant-turn marker
0x05        turn-end marker
0x06        newline marker
0x07..0x0F reserved control codes
0x10..0xEF 224 one-byte hot-vocabulary tokens
0xF0        extended-vocabulary escape followed by little-endian u16 token id
0xF1        literal-word escape followed by u8 length 1..31 and ASCII bytes
0xF2        numeric-literal escape followed by u8 length 1..15 and ASCII bytes
0xF3        proper-name literal escape followed by u8 length 1..31 and ASCII bytes
0xF4..0xFF reserved for measured future encodings
```

Extended token IDs are provisionally limited to 0..4095 so host tooling can reject accidental vocabulary growth long before it becomes a 48K-machine problem. This limit is a Candidate-A constraint, not yet a release ABI.

Common punctuation is represented by ordinary hot/extended vocabulary tokens rather than bespoke syntax bytes. Whitespace between word tokens is reconstructed by deterministic detokenization rules. Literal escapes preserve bounded unknown input rather than deleting words the model does not know.

### 7.1 Vocabulary selection

The host builder shall select the 224 hot tokens by measured total byte saving, not raw frequency alone. A token that appears often but has a one-character spelling may save less than a longer Spectrum-domain term.

The extended vocabulary is chosen from the remaining corpus by a score that considers occurrence count, spelling length, domain importance, and whether the token is needed as a factual entity. Candidate builds must report:

- hot token count and coverage;
- extended token count and coverage;
- literal escape rate on training/dev/evaluation corpora;
- mean encoded bytes per lexical token;
- mean encoded bytes per raw input character;
- dictionary storage bytes.

### 7.2 Normalization and case

Matching uses a canonical ASCII normalization suitable for the Spectrum character repertoire. Ordinary English matching is case-normalized, but output spelling is not forced to lower case. Dictionary entries carry enough presentation information to render forms such as `ZX Spectrum`, `Sinclair`, `Manic Miner`, `Z80`, and `ULA` correctly.

Unknown proper names can survive through the proper-name literal escape. The tokenizer must not silently transform a user-supplied unknown name into a known but different token.

### 7.3 Exact recent-token access

A variable-width encoded stream is compact but inconvenient for repeated backwards language-model lookups. Candidate A therefore maintains two recent-history views:

1. a compact encoded L0 exact-turn ring for storage;
2. a 96-entry decoded u16 hot-token ring for fast last-token and n-gram context access.

The decoded ring is a cache of recent canonical token IDs. It is not additional semantic history and may be reconstructed from L0 after reset/debug operations.

## 8. Compressed conversational context

### 8.1 Terminology

`ailmzx48` will deliberately have an **effective conversational context** much larger than its **live exact-token window**.

This is application-level information compression. It is not ZX-UX virtual memory, paging, swapping, or transparent compression of process RAM.

The system is hierarchical. Detail is retained while it is likely to matter and progressively collapsed into cheaper semantic representations as it ages.

### 8.2 Four context levels

The working context has four levels.

**L0 — exact live tail**

The newest dialogue remains as canonical encoded tokens in a fixed circular byte buffer plus a small decoded-token cache. This is the only part treated as exact word-by-word conversational history by the response generator.

L0 contains enough recent user/assistant text to preserve pronouns, immediate corrections, local phrasing, unfinished topic transitions, and short-range linguistic continuity.

**L1 — semantic turn capsules**

When older turns leave L0, they are reduced to compact fixed-format records. A capsule records only information that can influence future conversation: speaker/turn class, topic, salient entities, question/assertion/correction state, selected high-information token IDs, importance, and recency.

Candidate A uses a 16-byte L1 capsule:

```text
+0      flags: speaker/question/correction/polarity/state bits
+1      intent or relation class
+2..3   topic id u16
+4..5   entity A token/entity id u16, 0 if absent
+6..7   entity B token/entity id u16, 0 if absent
+8..9   high-information token A u16, 0 if absent
+10..11 high-information token B u16, 0 if absent
+12..13 value/token/date payload u16 interpreted by flags
+14     importance/confidence rank u8
+15     age/epoch bucket u8
```

No C48 `struct` is required. The implementation may store these as one byte array and symbolic byte offsets.

A capsule is intentionally lossy. Its job is to remember, for example, that the user was discussing `Manic Miner`, had already been told who wrote it, and then compared it with `Jet Set Willy`; it need not retain every article and adjective from the original turns.

**L2 — hierarchical session synopsis**

When the L1 ring fills, a deterministic compaction pass merges selected old capsules into coarser 16-byte synopsis records. These retain durable topics, named entities, user-stated preferences relevant to the conversation, unresolved questions, corrections, and facts already supplied by the agent.

The synopsis is compressed semantic state, not generated prose. No second language model is needed to summarize the conversation on target.

Repeated compaction makes context capacity scale by information density rather than raw character count. Repeated or low-information chatter can collapse aggressively while important corrections and entities remain.

**L3 — optional exact transcript archive**

For reproducibility, debugging, and occasional recovery, exact user/assistant text may also be appended to a transcript object when memory permits. An eligible closed transcript object may benefit from ZX-UX ZXP1 packing.

L3 is not required for every inference step. Normal response planning uses L0/L1/L2. This avoids repeatedly seeking through a large PACKED object, whose backwards seeks are intentionally O(n) in REV12.

On GitHub/SDK evaluation runs, the host harness shall always retain an exact external transcript regardless of whether the target L3 archive is enabled. The external transcript is evidence, not hidden runtime context.

### 8.3 Promotion and compaction

After each completed exchange:

1. tokenize the new user turn and generated response;
2. append exact tokens to L0 and update the decoded 96-token hot cache;
3. if L0 exceeds its fixed capacity, evict whole oldest turn fragments rather than arbitrary half-tokens where practical;
4. derive or update one L1 semantic capsule from the evicted material;
5. if L1 is full, merge selected old capsules into L2 according to a deterministic importance/recency rule;
6. optionally append the exact text to L3 before discarding its live text form;
7. retain counters and guard bytes in instrumented builds to prove that compaction never writes outside assigned buffers.

No stage allocates an unbounded temporary copy of the text being compacted.

### 8.4 Correction and supersession rule

A later explicit correction has priority over an older contradictory capsule when the topic/entity key matches. Candidate A marks the older semantic state superseded or replaces it during compaction; it does not keep both statements with equal authority and hope the generator chooses the newer one.

The rule is intentionally conservative. If two statements cannot be proved to refer to the same topic/entity relation, both may remain and the agent should express uncertainty rather than silently rewriting history.

### 8.5 Retrieval into the active decision context

For each new user turn, the controller computes a cheap integer relevance score against L1/L2 records using features such as:

- exact topic match;
- salient entity match;
- overlap of high-information token IDs;
- unresolved-question marker;
- correction/current-state marker;
- recency;
- importance/confidence.

Only the best small number of records are promoted into current response-planning state. Candidate A initially retains the best four conversational-memory records. That number is a measured knob rather than a user-visible promise.

The response generator receives the recent exact L0 tail, the new user turn, bounded retrieved memory features, current topic/intent state, and any Spectrum-domain knowledge records selected for the question.

This is how a conversation can behave as though it remembers much more text than can physically coexist as raw text in RAM.

### 8.6 What "larger context" does and does not promise

The design promises preservation of useful conversational information across much longer sessions than an all-raw live buffer could hold.

It does not promise perfect verbatim recall after old material has been reduced to L1/L2. If exact quotation of an old turn matters and L3 is unavailable or has been discarded, the agent must not fabricate the wording.

Quality tests therefore distinguish exact recent recall, semantic old-turn recall, topic continuity, entity continuity, contradiction avoidance, correction handling, and unsupported pseudo-verbatim recall.

### 8.7 Candidate-A 3,584-byte conversation/context workspace

Revision 0.3 gives the first context plan a real byte ledger. These values are intentionally easy to alter in generated constants after measurement, but Candidate A shall be implemented and benchmarked against this baseline before tuning.

```text
decoded hot-token ring         192   96 x u16 token ids
L0 encoded exact-turn ring     896   variable-width token bytes
L0 turn directory              128   32 x 4-byte turn descriptors
L1 semantic capsules           768   48 x 16 bytes
L2 synopsis records            384   24 x 16 bytes
input line buffer              192
response text/output buffer    384
retrieval scratch              256
generation/scoring state       256
guards, counters, cursors      128
                              ----
Candidate-A total             3584 bytes
```

This total is BSS/static working memory, not heap. It excludes program code, immutable hot model tables, stack, external model storage, packed-reader state, ZX-UX objects, shell/process overhead, and optional L3 transcript storage.

The first experimental objective is for semantic recall tests to represent source-equivalent history many times larger than the L0 exact ring without increasing this 3,584-byte workspace. No public ratio is claimed until the harness measures it.

### 8.8 Context-compression measurements

Every candidate context implementation shall report at least:

- L0 capacity in encoded bytes, decoded hot tokens, and source-equivalent tokens;
- L1 capsule count and bytes;
- L2 synopsis count and bytes;
- optional L3 logical and physical bytes;
- total target bytes devoted to context;
- source-equivalent raw transcript tokens represented;
- exact-recall horizon;
- semantic-recall accuracy by turn distance;
- correction/supersession accuracy;
- compaction CPU work;
- retrieval CPU work.

The phrase "effective context" in project documentation must be accompanied by those measurements. It must not be presented as a transformer-equivalent context-window number without qualification.

## 9. Model storage and access

Keeping a large immutable model entirely inside the executable image is simple but consumes live process allocation for its whole lifetime. Keeping it as a ZX-UX RAM object still consumes the shared arena, but an eligible inactive model resource may be stored in PACKED form and read as a logical stream.

Candidate A therefore deliberately splits the model into a **hot resident plane** and a **cold sequential plane**.

### 9.1 Hot resident plane

The executable contains only data that must be accessed repeatedly during generation:

- token-control definitions;
- hot-token spelling/presentation metadata;
- compact token class tables;
- intent/topic feature weights or ranks;
- high-frequency variable-order language-model transitions;
- small response-mode and anti-repetition tables;
- model-format reader code and constants.

The hot plane is ordinary executable image/static data and therefore directly addressable. Its byte budget is measured against the compiled artifact. Candidate A begins with an engineering goal of low single-digit KiB for hot tables, but no exact release number is frozen before corpus measurements.

### 9.2 Cold sequential Spectrum knowledge plane

Spectrum-domain knowledge is stored as one or a very small number of external model objects. An eligible object may be ZXP1 PACKED.

The cold plane is designed to be scanned forward once per user turn. It is **not** designed as a desktop random-access database. During the scan, each record's compact trigger/topic/entity header is scored against the user turn. Irrelevant payload tokens are read/discarded; the best few relevant records are copied into bounded retrieval scratch.

This converts the PACKED representation's sequential nature into an intended access pattern rather than a handicap. The design pays bounded CPU time to scan compressed knowledge so it does not have to keep the whole logical knowledge base directly addressable.

The runner shall measure logical bytes scanned, physical bytes occupied, target/VM work, selected-record count, and answer latency for every candidate model size.

### 9.3 Candidate cold-record format

Candidate A uses a length-delimited logical record so corrupt lengths can be rejected before buffers are touched. The provisional record header is:

```text
u8   logical_record_length      complete record, candidate maximum 255
u8   record_type
u16  topic_id
u16  entity_a
u16  entity_b
u8   importance
u8   trigger_count              0..4
u16  trigger[trigger_count]
...  encoded token payload      must fit logical_record_length
```

Host tooling rejects records shorter than their declared header, over 255 logical bytes, with trigger_count above four, with unknown record types, or with token payloads that do not terminate exactly at the record boundary.

Record types are expected to distinguish factual statement, biographical fact, game/software fact, hardware/architecture fact, chronology fact, comparison relation, and conversational/domain phrase material. Exact numeric IDs are not frozen until corpus construction begins.

### 9.4 Candidate model container

The logical cold-model stream begins with a compact header and sequential section directory. Candidate magic is `A48M`; release version numbering and exact integrity polynomial remain to be frozen after the first packer/parser prototype.

The container shall declare at least format version, feature flags, vocabulary identity, record count, logical length, and section lengths. Every declared sum is checked with widened host arithmetic and bounded 16-bit target arithmetic before a section is consumed.

The target model must include a cheap integrity check suitable for the Z80/C48 implementation. Host release tooling also records SHA-256 for reproducibility. SHA-256 is not imposed on the target merely because the host can calculate it cheaply.

### 9.5 Candidate variable-order language model

Candidate A uses pruned variable-order token continuation statistics with maximum order three:

- unigram fallback for general English/token priors;
- bigram transitions for common local syntax;
- trigram transitions only where training evidence and byte/value measurements justify them.

The host trainer quantizes continuation likelihoods into small integer ranks/scores. Low-value transitions are pruned under an explicit byte budget. The target generator backs off deterministically when a higher-order context is absent.

The hot LM is not required to memorize Spectrum facts. Facts are supplied by selected cold records. This separation allows factual knowledge to grow in a compressible sequential representation without making every next-token decision scan the whole model.

### 9.6 Why Candidate A is not merely a template chatbot

A factual record can anchor names, dates and relationships, and a compact response mode may provide sentence boundaries or obligatory fact tokens. Normal wording between/around those anchors is selected using learned token-continuation scores and current conversation state.

A candidate build shall include ablation tests. If replacing the learned continuation table with a fixed deterministic word list produces essentially identical normal responses, the supposed LM is not doing enough work and the candidate fails the project definition.

## 10. Runtime memory budgeting

No release memory claim is frozen until the real compiled C48/MEX1 artifact and model are measured. The budget shall nevertheless be accounted in named categories from the first prototype:

```text
process image/text + immutable hot model tables
process BSS including the 3584-byte Candidate-A workspace
process FAST stack
fixed C48 heap reserve
external cold-model physical storage
272-byte PACKED-reader state if the cold model is packed
optional target transcript object physical storage
shell and other simultaneously resident process allocations
pinned/system arena resources
free-arena safety margin
```

The invariant is:

```text
all simultaneous arena consumers + required safety margin <= 32768 bytes
```

The build/evaluation harness shall reject a candidate whose measured peak violates that equation, even if it appears to work in a host-side simulation.

### 10.1 Candidate-A engineering targets

Before measurement supplies better numbers, Candidate A aims for:

- 3,584 bytes fixed conversation/context workspace;
- zero C48 heap for the initial target implementation;
- 768..1024 bytes target process stack unless measured call depth requires more;
- low-single-digit-KiB hot model tables;
- cold model stored externally and PACKED only when physical bytes are materially reduced;
- exactly one cold-model read handle during normal inference where practical;
- at least several KiB of measured total-arena headroom under the actual ordinary launch configuration.

These are engineering targets, not release promises. A candidate that cannot leave safe arena headroom is rejected or made smaller even if its conversational score is higher.

### 10.2 Memory evidence

Every retained model candidate shall publish a machine-readable memory report containing at least compiled SDK artifact identity, eventual MEX1 image/BSS size when available, configured heap/stack, BSS workspace bytes, external model logical/physical bytes, packed-reader state, observed target/SDK peak, and total system arena headroom.

The phrase "fits in 48K" is not sufficient evidence.

## 11. Response pipeline

A normal turn is a bounded pipeline:

```text
read bounded line
  -> normalize/tokenize
  -> detect q/commands
  -> score topic + intent + salient entities
  -> retrieve L1/L2 conversational memories
  -> sequentially scan cold Spectrum knowledge and retain best records
  -> choose response mode and obligatory factual anchors
  -> seed learned variable-order token generator
  -> select/rank continuation tokens with backoff
  -> apply anti-repeat and factual-anchor checks
  -> detokenize/print
  -> update L0/L1/L2
  -> emit host-side evidence through instrumentation
```

Every stage has a fixed maximum input/output size. A failure in an optional stage falls back to a documented simpler response path rather than overrunning memory.

The controller may choose a direct factual explanation, comparison, historical answer, architecture answer, conversational continuation, clarification request, bounded uncertainty response, or another measured mode. The controller must never invent remote capabilities or hidden access to information outside the shipped model/context.

### 11.1 Candidate knowledge retrieval score

The first retriever uses only integer additions/comparisons. Candidate features include exact topic match, entity match, trigger-token overlap, question/intent compatibility, current conversational-memory reinforcement, and record importance. No runtime floating point is needed.

The host reference implementation calculates the same integer score byte-for-byte. Any future improvement that uses a different host-only formula without a target equivalent is not a valid target model improvement.

### 11.2 Candidate generation policy

Candidate A generates at most 80 canonical output tokens and at most 383 response-buffer bytes excluding the terminating NUL. Earlier termination on a complete sentence is preferred.

At each step the generator evaluates a bounded candidate continuation set. The highest adjusted score wins; ties use ascending canonical token ID. Adjustments include repetition penalties, obligatory fact-anchor progress, response-mode legality, and end-of-sentence preference near the length ceiling.

There is no unbounded beam. A tiny alternative/backtrack slot may be evaluated later if measurements show a quality win, but the baseline is one active output path plus bounded candidate scratch.

## 12. Anti-repetition, uncertainty and conversational quality

Small n-gram-like models can easily loop. The response controller tracks recent output and penalizes or rejects immediate repeated token runs, repeated short phrases, regeneration of the immediately previous answer, pathological punctuation loops, and continuation beyond the hard token/character ceiling.

A response that cannot satisfy its required factual anchors or reaches an invalid model transition must terminate safely. It may fall back to a short uncertainty response rather than manufacture a fact.

The quality target is not merely grammatical-looking noise. Domain factuality, question relevance, continuity with compressed memory, and graceful uncertainty outrank novelty.

### 12.1 Factual anchoring

Cold knowledge records distinguish factual anchor tokens from optional wording where useful. Names, dates, hardware values, authorship, publisher/developer relationships and similar facts selected for an answer must survive the generator unchanged unless an explicit transformation rule exists.

The learned LM is allowed to choose English around facts. It is not allowed to "improve" `48K` into `64K` because a continuation happened to score well.

### 12.2 Unknown material

When retrieval confidence is below the measured threshold or the question is outside shipped knowledge, the agent should say that it does not know enough rather than confidently extrapolate. The exact uncertainty phrases may have learned variation, but their semantics are explicit.

## 13. User interaction

### 13.1 Startup conversation — provisional text

The startup text remains deliberately small and slightly self-aware:

```text
Welcome to SANYALnet Labs ZX-UX AI LM Chat.
© 2006 Supratim Sanyal

I am ailmzx48.
I know a bit about the Sinclair ZX Spectrum —
which is fortunate, because I appear to be living inside one.

48K seemed enormous in 1982. I have opinions about that now.

Ask me about the Spectrum, or just have a chat.
Enter q at any time to quit.

>
```

This wording remains provisional until terminal character repertoire, wrapping, binary size, and startup-memory cost are measured. If the copyright symbol is not in the guaranteed target character repertoire, the target build shall use an ASCII-safe equivalent rather than rely on an accidental host glyph.

### 13.2 Input

`ailmzx48` owns its application input loop after launch. It shall use a bounded line buffer and normal ZX-UX tty services. It shall not depend on the shell retaining the conversation line for it.

Candidate A reserves 192 bytes for the input line including terminator/scratch discipline. The exact accepted user-character maximum will be slightly smaller and will be frozen by implementation. Overlength input must be explicitly rejected or cleanly drained to the next newline; silent semantic truncation is not acceptable.

When waiting for ordinary conversational input, the exact command `q` followed by ENTER terminates cleanly. The matcher ignores the line-ending representation but does not treat an arbitrary sentence containing the letter q as a quit request.

### 13.3 EOF and cancellation

EOF in the host harness and target input errors must produce deterministic clean termination or a documented message; they must not spin forever asking `getchar()` for another byte.

On native ZX-UX, BREAK/cancellation follows the canonical cooperative tty-owner rules. Long model scans shall contain safe yield/kernel boundaries so cancellation is eventually observed.

## 14. SDK instrumentation and automated conversation testing

The project requires a target-visible test path, not only host model scores.

The current SDK already gives the project a useful base:

- `c48run --headless` instantiates the real C48 host VM and Spectrum screen model;
- the VM's default input provider reads host stdin one byte at a time, so C48 `getchar()` can already consume scripted input;
- the VM accepts an injected `input_provider`, allowing a host harness to provide bytes interactively rather than preload one static file;
- C48 `putchar()`/`puts()` update `ZXScreen`, preserving Spectrum terminal semantics;
- `--max-steps` provides a deterministic runaway-execution ceiling;
- the VM exposes globals and memory internally to SDK-host tooling, enabling non-user-visible diagnostic inspection without changing target responses.

The missing feature is exact logical terminal-stream capture. The baseline harness shall add that **outside the C48 program semantics** rather than make the target program print test protocol noise.

### 14.1 Harness architecture

The initial harness lives under:

```text
usr/src/ailmzx48/tooling/
```

The preferred first implementation imports the SDK VM classes directly and supplies:

- a queued byte `input_provider`;
- a tracing `ZXScreen` subclass/wrapper whose `putchar()` records the same logical byte it then passes to the real screen implementation;
- optional VM-global inspection helpers for named `ailmzx48` diagnostic counters;
- deterministic maximum-step and per-turn progress guards.

Conceptually:

```text
scenario / adaptive interlocutor
            |
            v
      queued input bytes
            |
            v
        RomMathVM
            |
      ailmzx48 C48B1
            |
            +----> real ZXScreen semantics ----> .scr evidence
            |
            +----> traced logical characters --> exact transcript
            |
            +----> named debug globals --------> per-turn metrics
```

The tracing wrapper must call the production screen operation rather than reimplement wrapping. A transcript capture bug must therefore not be able to make a bad Spectrum screen look good.

A future general-purpose SDK `--tty-log PATH` option may be useful, but `ailmzx48` does not require changing the public SDK CLI merely to begin testing.

### 14.2 Human-emulation protocol

A conversation runner does not dump hundreds of lines into stdin blindly. It behaves like a user:

1. start the compiled program;
2. observe output until the complete prompt marker is emitted;
3. choose the next input turn from the scenario/adaptive driver;
4. inject its bytes followed by ENTER;
5. observe the complete response and next prompt;
6. score/log that turn;
7. continue for the configured conversation length;
8. inject `q` and prove clean termination.

The driver may choose later turns based on earlier answers. This is the "keyboard access" required for iterative conversations: input is an active callback/queue attached to the running VM, not a fixed redirected text file.

The baseline runner is deterministic. A development-time modern LM may later act as an adaptive human-like interlocutor/reviewer, but deterministic scripted/adversarial suites remain mandatory so a model change can be reproduced without an external service.

### 14.3 Transcript and run identity

Every retained run records:

```text
source commit
C48 compiler/runtime version and relevant hashes
ailmzx48 source hash
model build id and model SHA-256
scenario id/hash
runner/tool hash
exact injected input bytes
exact logical output bytes
exit status
VM step count or bounded work counters
selected screen snapshots/hashes where required
memory/context diagnostic counters
score report
```

Human-readable `.txt` transcripts are paired with a machine-readable metadata record. The exact machine format will be frozen with the tooling; host JSON is acceptable because it never runs on the Spectrum.

Selected regression/convergence transcripts are committed below `conversations/`. Bulk exploration runs may be retained as GitHub Actions artifacts and summarized by committed manifests/reports.

### 14.4 Target-visible diagnostic globals

The C48 program may expose debug-only or always-present small scalar globals such as:

```text
ai_dbg_turns
ai_dbg_l0_bytes
ai_dbg_l1_count
ai_dbg_l2_count
ai_dbg_compactions
ai_dbg_model_records
ai_dbg_model_hits
ai_dbg_output_tokens
ai_dbg_yields
ai_dbg_error
```

The SDK harness can inspect these through the VM's global/memory model after a prompt boundary without printing them to the Spectrum terminal. Native ZX-UX verification can later expose equivalent counters through a diagnostic command/build if needed.

Correctness may not depend on the host being able to inspect these globals. They are instrumentation, not a hidden control channel.

### 14.5 Context-specific long-conversation tests

Long-conversation tests deliberately place important facts at increasing turn distances, push them out of L0, force L1 compaction into L2, and then ask questions whose correct answers depend on those facts.

Tests separately prove that recent exact wording remains available inside the declared L0 horizon; old semantically important facts survive compaction; low-value chatter can be forgotten safely; later corrections supersede older state according to the documented rule; the agent never claims verbatim recall from lossy state; repeated compaction never grows the fixed workspace; and conversations far longer than L0 complete without memory corruption.

### 14.6 Corruption and boundary instrumentation

Host tests surround context/model buffers with guard values where C48 layout permits and verify them at every turn. Model readers receive deliberately truncated headers, oversized lengths, illegal token escapes, bad counts, impossible section totals and malformed record boundaries.

Every malformed case must terminate or fall back deterministically. "It did not crash on this run" is not sufficient evidence; the expected error state and unchanged guards are asserted.

## 15. Training, model construction and iterative improvement

Training/model construction happens on the host from a provenance-recorded Spectrum-domain corpus plus conversational material explicitly approved for this project.

The loop is empirical:

```text
build deterministic corpus snapshot
-> train/build Candidate model
-> package target model
-> run host format/unit tests
-> compile ailmzx48 with C48
-> run short target/SDK regressions
-> run long human-emulated conversations
-> retain transcripts + metrics + artifact identities
-> mine failures by category
-> change corpus/model/controller/context policy
-> repeat
```

There is no arbitrary fixed number of training iterations and no time limit in the design. Development stops when repeated, diverse evaluation rounds show a genuine plateau and remaining failures are primarily hard capacity/model-class limits rather than correctable corpus, pruning, retrieval, context, or controller errors.

### 15.1 Training is not target inference

The host trainer may use memory, disk and computation far beyond a Spectrum. It may calculate full-precision statistics and then quantize/prune them into the target model. That does not violate the project goal because all such machinery disappears from the runtime distribution.

The proof obligation is that the shipped model bytes plus C48 program reproduce the evaluated behavior locally.

### 15.2 Failure mining

Each retained failed/weak turn is assigned one or more categories, for example:

```text
FACT_WRONG
FACT_MISSING
QUESTION_MISREAD
TOPIC_DRIFT
CONTEXT_RECENT_LOSS
CONTEXT_OLD_LOSS
CORRECTION_LOSS
REPETITION
GRAMMAR
TRUNCATION
UNKNOWN_OVERCLAIM
MODEL_FORMAT
LATENCY
MEMORY
HARNESS
```

Training changes should name the failure categories they are intended to improve. A model that gets a higher aggregate score while reintroducing a previously eliminated hard failure does not automatically win.

### 15.3 Adaptive long conversations

In addition to fixed scenarios, the project shall maintain long adaptive conversations whose next question depends on the actual answer. The driver deliberately changes subjects, returns to old facts, corrects itself, supplies new temporary facts, asks comparison questions, introduces unknown names, and revisits old topics after enough chatter to force multiple compaction rounds.

This is the primary way to detect a chatbot that passes isolated questions but loses the thread in actual use.

## 16. Corpus scope, provenance and licensing

The shipped knowledge goal is the Sinclair ZX Spectrum ecosystem, including at least:

- 1982 Spectrum launch/history and Sinclair context;
- 16K/48K hardware architecture, Z80, ULA, ROM, display, keyboard, cassette and sound;
- BASIC/ROM culture and common programming concepts;
- major games, authors, developers/publishers and notable technical facts;
- magazines, bedroom-coder culture, loading screens, tape rituals and folklore;
- notable peripherals and development tools;
- historically important people/companies;
- Spectrum quirks, jokes and culture that make conversation feel machine-specific rather than generic.

The corpus shall distinguish factual source material from conversational style material.

### 16.1 Provenance manifest

Every admitted corpus source receives a host-side record containing source identifier/title, provenance/location, license/authorization basis, acquisition date, source hash where applicable, extraction/transformation version, and which generated fact/training records depend on it.

No arbitrary web scrape is admitted merely because the text is easy to fetch.

### 16.2 Repository-license boundary

The ZX-UX C48 SDK repository and upstream ZX-UX project are canonical **design authorities** for this implementation. Their license text explicitly restricts use for AI/ML model training unless separately authorized. Therefore their prose/source is not automatically part of the `ailmzx48` training corpus.

This design may read those documents to implement correct ZX-UX/C48 behavior. Training the conversational model on their textual content requires a separately recorded authorization or a user-authored/otherwise permitted factual corpus. Design authority and training permission are different questions.

### 16.3 Train/dev/evaluation separation

Factual and conversation tests shall include held-out material. At minimum the tooling must prevent the exact evaluation conversation transcript from simply being reinserted as a training response and then counted as generalization.

Some closed-book facts may deliberately exist in the knowledge store because factual retrieval is part of the model architecture. The evaluation report must distinguish retrieval correctness from linguistic generalization rather than pretend the model was never allowed to know the answer.

## 17. Evaluation and convergence

Evaluation has hard gates and quality scores.

### 17.1 Hard failures

Any of the following rejects a candidate regardless of conversational charm:

- out-of-bounds memory access or guard corruption;
- arena budget overflow;
- model parser accepting a malformed unsafe record;
- infinite/unbounded generation;
- failure to terminate on `q`;
- deterministic regression that cannot be reproduced from retained identities;
- target behavior that requires a remote LM/service;
- false claim of verbatim recall where only lossy context remains;
- known factual anchor mutated into a contradictory value;
- a repository/tooling change that weakens an existing SDK verification gate merely to accept the candidate.

### 17.2 Scored dimensions

The evaluation suite separately reports, rather than hiding behind one number:

- Spectrum-domain factual accuracy;
- answer relevance;
- conversational fluency;
- repetition/degeneration rate;
- recent exact-context recall;
- distant semantic-context recall;
- correction handling;
- uncertainty behavior;
- response diversity across prompts;
- target work/latency;
- model logical and physical bytes;
- total/peak memory and headroom.

A composite score may be useful for ordering experiments, but the component table remains canonical evidence.

### 17.3 Convergence rule

No iteration count is frozen. The project continues while failure mining identifies changes that materially improve important dimensions without violating hard gates.

A provisional plateau detector shall track multiple consecutive accepted candidate rounds and the moving improvement of each important dimension. It may recommend stopping only when new corpus/model/context/controller changes repeatedly fail to produce material gains and manual transcript review agrees that remaining limitations are predominantly capacity/model-class limits.

The exact numerical plateau threshold is deferred until baseline variance exists. Picking `0.5%` today would look scientific without any evidence that it means anything.

## 18. Cassette and real-machine workflow constraints

The final release workflow must be derived from canonical REV12/REV03 cassette, object, compiler, linker and shell behavior. It may not invent a disk-like filesystem or assume the host SDK exists on the physical Spectrum.

Two user-facing cassette roles are planned:

1. a **source/development tape** containing material needed to inspect/build `ailmzx48` using native ZX-UX development tools;
2. a **runtime/distribution tape** containing the ready-to-run executable and model resources arranged for low-memory loading/execution.

The exact physical M48O order is not frozen yet.

### 18.1 What is already known

ZX-UX native C48 compilation and linking are ordinary program activities; the compiler is not architectural permanently resident kernel state. `SYS_EXEC` is a real process-image replacement operation. ZX-UX tape facilities include save/load/verify/scan semantics, and REV12 provides a direct tape-backed MEX1 execution path that can decode a RAW or ZXP1 executable directly into its final process allocation rather than require a second resident executable copy.

Therefore a reboot is **not inherently required merely to "unload the compiler"**. The actual memory problem is the complete set of still-live process allocations and RAM objects after the build: shell/tool processes, source, OBJ1, final executable object, model objects, temporary files and pinned/system state.

### 18.2 Required final proof sequence

Before user documentation claims an exact command sequence, the native implementation must prove the following on a 48K configuration:

1. boot ZX-UX from the canonical system tape;
2. load the native C48 toolchain/source inputs actually required;
3. compile `ailmzx48.c` to the canonical native object form;
4. link the MEX1 executable with measured stack/heap values;
5. save the executable and required model resource(s) to cassette;
6. reclaim build-only RAM objects through supported commands/semantics;
7. return to a state with enough arena space for the runtime configuration;
8. load or directly tape-execute `ailmzx48` using only documented operations;
9. make required model knowledge available without exceeding the arena;
10. hold a multi-turn conversation and quit cleanly.

Every step records `mem`/equivalent evidence where available so the manual can explain why the sequence works.

### 18.3 Compiler/linker lifetime question

The final manual must distinguish process lifetime from stored tool/source objects. A completed `cc` or `ld` process no longer needs to occupy its former process allocation, but resident source/object/executable/model data can still consume the shared arena.

The user should not be told to "unload C48" unless ZX-UX actually has a command with that meaning. The documentation will instead name the real objects/processes to remove or the real process-image transition to perform.

### 18.4 Reboot fallback

If measurement proves that a clean post-build runtime state cannot be reached conveniently without bootstrapping again, the release may document a reboot/reload workflow. Reboot is a valid engineering answer; an invented unload command is not.

The design preference is to avoid reboot if supported cleanup/direct execution makes that unnecessary, but correctness and understandable tape instructions outrank elegance.

## 19. Phased implementation order

Implementation begins only after enough of this design is frozen to prevent incompatible model/context/harness work. The current intended order is:

1. canonical-constraint verifier and host reference tokenizer;
2. corpus provenance format and small hand-audited seed corpus;
3. Candidate-A token statistics and vocabulary builder;
4. host reference L0/L1/L2 compressor/retriever with adversarial long-conversation tests;
5. cold knowledge-record builder and sequential retrieval benchmark;
6. pruned order-1/2/3 hot language-model trainer and quantizer;
7. frozen experimental A48M container plus host packer/verifier;
8. minimal C48 `ailmzx48` shell that prints startup text, reads bounded input and handles `q`;
9. target tokenizer/detokenizer and Candidate-A 3,584-byte context workspace;
10. target L0/L1/L2 compaction/retrieval with debug counters and guards;
11. cold model reader/sequential scorer;
12. hot LM continuation generator and factual-anchor controller;
13. anti-repetition, uncertainty and response-mode integration;
14. SDK active conversation harness with traced output and global telemetry;
15. long GitHub-runner conversation workflow and retained artifacts;
16. repeated corpus/model/controller/context training/evaluation cycles until plateau;
17. native ZX-UX memory/tty/cassette integration and physical-machine verification;
18. final source/runtime tape packaging, exact native build/save/load transcript and certification evidence.

Each phase must preserve a working, testable state. Model sophistication is never allowed to outrun memory-safety and reproducibility evidence.

## 20. Candidate-A implementation interfaces

Revision 0.3 introduces conceptual interfaces so the C48 source can later be split into small functions without depending on unsupported C features. Names are provisional; contracts are more important than spelling.

```text
ai_read_line()              bounded tty line input
ai_tokenize()               ASCII line -> canonical encoded tokens
ai_detokenize()             canonical tokens -> bounded output text
ai_classify()               intent/topic/entity extraction
ai_memory_retrieve()        top L1/L2 semantic records
ai_model_scan()             one forward cold-model scan, top knowledge records
ai_plan_response()          response mode + factual anchors
ai_generate()               deterministic LM continuation
ai_context_commit()         L0 append, eviction, L1/L2 compaction
ai_print_response()         normal tty output
```

C48 functions receive explicit buffer pointers/capacities or operate on named fixed globals. There are no hidden unbounded local arrays.

### 20.1 Error-state discipline

A single small error/status value records the first hard turn failure. Functions return status rather than relying on undefined state after malformed input/model data.

Recoverable cases include no matching knowledge record, literal-token overflow, optional transcript unavailable, or low retrieval confidence. Fatal session cases include model container corruption discovered after startup validation or internal guard failure.

### 20.2 Bounds arithmetic

All target length additions are written so a 16-bit `int` cannot wrap into a passing bounds test. The host model packer/verifier performs the same checks in widened arithmetic and generates only target-safe lengths.

Where a target expression would need a 17-bit intermediate to prove safety, the C48 implementation uses subtraction/reordered comparisons or explicit high/low reasoning rather than relying on nonexistent `long`.

## 21. GitHub-runner iterative conversation cycle

The required long-run development loop is deliberately repository-driven so it survives ephemeral runners.

A normal experiment is:

```text
commit source/corpus/model-tool change to main
        |
        v
GitHub Actions clean runner
        |
        +--> rebuild deterministic model
        +--> compile ailmzx48 with repository C48 compiler
        +--> short conformance/regression suite
        +--> one or more long active conversations
        +--> transcript + metrics + screen evidence artifacts
        |
        v
retrieve artifacts / inspect failures
        |
        v
retain selected evidence in repository
        |
        v
next model/corpus/controller change on main
```

No design/training result exists only in the runner workspace. Model recipes, corpus manifests, scoring rules and selected evidence needed to explain a decision are committed before the next major step.

### 21.1 Conversation lengths

The runner supports short smoke sessions, medium regression sessions, and long stress sessions. Exact counts will be selected from measured runtime, but long sessions must force repeated L0 eviction and L1-to-L2 compaction; otherwise they do not test the feature this project cares about.

A stress scenario may contain hundreds or thousands of turns on the host SDK when runtime permits. The target model is not excused from long logical history merely because no human wants to type a thousand Spectrum questions by hand.

### 21.2 Artifact retrieval

A workflow run retains exact transcript, metadata, scores, and selected `.scr`/rendered evidence as GitHub Actions artifacts. Development tooling must be able to retrieve those artifacts after the runner has exited. Selected convergence/regression artifacts are copied into `usr/src/ailmzx48/conversations/` and committed so runner-retention expiry cannot erase the evidence behind the final model.

### 21.3 Iterative training ownership

The model builder never edits target source during a training run. Training generates candidate model bytes and reports. Deliberate source/controller/context changes are reviewed repository changes, preventing an optimizer from silently teaching around an implementation bug.

## 22. Release model acceptance questions

Before the model format is declared final, the project must answer with retained measurements:

1. What is the compiled C48/target inference code size?
2. What is the exact BSS/stack/heap budget?
3. How many encoded L0 tokens/turns fit in 896 bytes for real conversations?
4. How much source-equivalent history do 48 L1 capsules and 24 L2 records preserve at measured recall quality?
5. What vocabulary size minimizes total hot-table + cold-model + literal cost?
6. What variable-order LM pruning budget gives the best fluency per resident byte?
7. How large is the cold knowledge stream logically and after ZXP1 packing?
8. How long does one complete cold scan take in the SDK and later on real Z80/Fuse evidence?
9. Is one cold scan per turn acceptable, or must a small topic index/cache be added?
10. How much arena remains with the shell/system state and model reader alive?
11. Which Spectrum factual categories remain weak after corpus saturation?
12. Does any quality improvement require enough bytes to make the ordinary runtime configuration unsafe?
13. What is the longest retained semantic dependency demonstrated by an actual transcript, not a synthetic byte count?
14. At convergence, what failures remain and why are they intrinsic or not worth the byte cost to fix?

The final design replaces these questions with measured answers.

## 23. Open design questions after Revision 0.3

The following remain deliberately open until measurement resolves them:

- exact 224-token hot vocabulary contents;
- final extended vocabulary size below the Candidate-A 4096 ceiling;
- final A48M numeric field IDs, section order and integrity algorithm;
- exact cold-record type IDs and trigger weights;
- exact hot LM byte budget and pruning thresholds;
- whether maximum LM order three wins over a smaller order-two model;
- whether the 3,584-byte context split should trade bytes between L0/L1/L2 after real transcripts;
- whether target L3 transcript storage is enabled by default;
- cold model embedded-vs-external split after native MEX1 measurement;
- exact model logical/physical byte budget and ZXP1 ratio;
- final response token ceiling after terminal/latency testing;
- final stack reservation and whether heap remains zero;
- exact target object names and cassette physical ordering;
- ordinary-shell launch versus any proven process-replacement launch option;
- quantitative convergence thresholds after baseline variance is known.

These are measurement questions, not invitations to silently assume desktop defaults.

## 24. Revision and durability discipline

This file is the canonical evolving `ailmzx48` design record within the SDK repository. Each coherent design stage is committed directly to `main`. Conversation text is not an authority when it conflicts with the repository copy.

Before each substantive edit, the latest repository copy shall be read. Canonical ZX-UX/C48 documents shall be rechecked whenever a design statement depends on their contracts. If a later canonical revision changes a relevant contract, this document must be reconciled explicitly rather than carrying an accidental stale assumption forward.

An ephemeral local or runner copy is never considered a durable checkpoint. A design step is complete only after the updated canonical file has been pushed to `main` and read back from GitHub with its new blob/commit identity recorded.