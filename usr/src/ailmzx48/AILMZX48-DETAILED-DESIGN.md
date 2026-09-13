# ailmzx48 Detailed Design

Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.

Status: Design in progress — canonical constraints and compressed-context architecture established  
Revision: 0.2-draft  
Canonical repository path: `usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md`  
Canonical SDK executable path: `usr/bin/ailmzx48`

## 1. Purpose

`ailmzx48` is a small English conversational language model for ZX-UX. It is written in C48 and is intended to run both on an actual unexpanded Sinclair ZX Spectrum 48K under ZX-UX and in the ZX-UX C48 SDK environment.

The shipped model is trained specifically around the Sinclair ZX Spectrum: its games, history, hardware and software architecture, culture, folklore, personalities, and related subjects. Runtime inference is local to the Spectrum/ZX-UX program. A remote modern language model is not part of the shipped runtime design.

The goal is not to pretend that a 48K Spectrum can run a modern transformer. The goal is to build the most convincing, useful, reproducible local conversational agent that fits the real machine and real ZX-UX/C48 contracts.

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

## 3. Canonical authorities

The authority order for this project is frozen as follows.

1. ZX-UX architecture: upstream `docs/01-ZX-UX-ARCHITECTURE-REV12.md` on `main` in `tuklusan/ZX-UX-The-ZX-Spectrum-48K-Unix-Project`.
2. ZX-UX implementation/certification plan: upstream `docs/02-ZX-UX-IMPLEMENTATION-STEPS-REV03.md` on `main` in the same repository. REV03 explicitly declares itself subordinate to REV12; if the two conflict, REV12 wins.
3. C48 language: `doc/C48 Language Specification Rev 0.11.docx` on `main` in this SDK repository.
4. C48 SDK/compiler/runtime documentation, implementation, examples, tests, and generated artifacts in this repository are implementation evidence and compatibility aids. They do not override the three canonical documents above.
5. This `ailmzx48` design is subordinate to the canonical ZX-UX and C48 contracts.

Design statements that depend on target behavior shall name the authority from which they were derived. Assumptions not yet proved against a canonical authority and/or executable test remain explicitly provisional.

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

## 5. Canonical target constraints that shape this design

### 5.1 Real memory model

REV12 reserves the Spectrum display/ROM-compatibility area below `0x6000` from general allocation and the resident kernel at `0xE000-0xFFFF`. The general ZX-UX arena is therefore the contiguous 32 KiB range `0x6000-0xDFFF`.

That same arena is shared by process image/BSS allocations, process stacks, pipes, mutable RAM-object payloads, compiler/editor working data, and other user allocations. More files mean less process memory and vice versa. `ailmzx48` therefore has no private 48 KiB address space and no license to budget against the headline machine RAM size.

Normal MEX1 image+BSS allocations use `ANY` placement across the arena. Process stacks are `FAST_REQUIRED`. Correctness may not depend on whether ordinary process image/BSS bytes happen to lie in contended or uncontended RAM.

### 5.2 C48 process heap

REV12 section 26 defines no user `SYS_ALLOC`. The C48 heap is a fixed link-time reserve inside the executable BSS. Default `crt0` reserves 1024 bytes unless the linker is given an allowed `-heap` value; the allowed range is an even value from 0 through 8192 bytes.

Consequences for `ailmzx48`:

- the design shall not depend on a growable heap;
- the normal target build should prefer fixed global/static byte arrays and bounded scratch buffers;
- if `malloc` is used at all, its exact purpose and worst-case lifetime must be budgeted before release;
- a zero-heap build is a valid optimization target if the final implementation can avoid dynamic allocation cleanly.

### 5.3 C48 language/data-model constraints

The canonical language authority is `C48 Language Specification Rev 0.11.docx`. REV12 section 25 mirrors the target-facing C48 contract used by ZX-UX. The implementation is to be written to the canonical Rev 0.11 language, not to host C extensions.

Important frozen constraints include an 8-bit unsigned plain `char`, 16-bit `short`/`int`/pointers, five-byte Spectrum-native `float`, no `long`, and deliberately limited language facilities. REV12 also defers facilities such as `struct`/`union`, `switch`/`case`, variadic functions, function pointers, the conditional operator, compound assignment, and the comma operator.

The design therefore uses flat byte arrays, parallel arrays where a record would otherwise be tempting, explicit indices, small fixed functions, integer/fixed-point scoring, and direct bounds checks. Floating point is not required for model inference.

Before implementation begins, every C construct introduced into `ailmzx48.c` must be accepted by the canonical C48 specification and the SDK compiler acceptance tests. Host-only tooling may use ordinary contemporary languages and data structures.

### 5.4 I/O and object-storage constraints

REV12 provides ordinary C48 `open`, `read`, `write`, `seek`, `close`, `read_full`, and `write_full` interfaces over ZX-UX objects and devices. The mutable RAM-object table has exactly 32 entries, and ordinary object base names are limited to the ZX-UX fixed namespace contract.

Stored object payloads occupy the same 32 KiB arena as running processes. A separate model/context object is therefore not free merely because it is outside the C48 process image.

REV12 `zxpack`/ZXP1 may compress eligible inactive stored objects. It explicitly does not compress live process image/BSS/heap, stacks, pipes, screen memory, kernel RAM, or pinned runtime resources. `ailmzx48` must never describe ZXP1 as virtual memory or imply that compressed bytes are directly addressable.

A PACKED object is read as its logical byte stream through normal reads. A packed open description requires decoder state/history, and packed seeking may decode/discard from logical offset zero. Random backwards probing of one large PACKED object is therefore deliberately expensive and must not be the normal inner inference loop.

### 5.5 Scheduler/process behavior

ZX-UX v1 is cooperative. `ailmzx48` must return to kernel boundaries often enough that it does not make the machine feel dead during long scoring/generation loops. The implementation shall define bounded work quanta and call `yield()` at deterministic safe points where measured inference latency warrants it.

A CPU-bound user process is not forcibly preempted merely because it takes too long. Consequently responsiveness is an application responsibility.

### 5.6 Terminal behavior

ZX-UX exposes a 64-column terminal mode and exact terminal semantics in REV12. `ailmzx48` shall write ordinary terminal text rather than draw its own text renderer. Its wrapping and prompt behavior must be tested against the real tty implementation, including the deferred-wrap behavior already incorporated into the current architecture baseline.

## 6. Architectural choice: a host-trained sparse local language agent

A transformer-style neural LM is not the baseline architecture. Its parameter storage, activation memory, multiply-heavy inference, and context machinery are a poor fit for a 3.5 MHz Z80 and the ZX-UX arena.

The working architecture is instead a host-trained, target-inferred sparse statistical language agent with four cooperating pieces:

1. a compact tokenizer/vocabulary;
2. a tiny intent/topic and salient-entity scorer;
3. a compressed Spectrum-domain knowledge/reply store;
4. a variable-order token language model used to rank or generate fluent response continuations under the controller's topic/intent constraints.

This is still a language model: probabilities/weights over token continuations are learned from a corpus and used locally at inference time. The surrounding agent controller supplies conversation state, memory retrieval, topic steering, refusal/fallback behavior for unknown material, and anti-repetition controls.

The exact model family and byte format are not frozen by this revision. They shall be selected from measured candidates under the same corpus and evaluation harness. Candidate families may include compact variable-order n-grams, pruned prediction tries, weighted finite-state transitions, retrieval-plus-LM hybrids, or another demonstrably smaller/better target-native representation. A candidate wins on measured target quality per byte and target latency, not on fashionable terminology.

### 6.1 No remote inference dependency

A host may train, evaluate, package, inspect, and fuzz the model. GitHub runners may automate those jobs. None of that changes the shipped runtime rule: after the target artifacts are produced, normal `ailmzx48` inference must work with no PC/server/Internet language-model service.

### 6.2 No float requirement in the inference core

Training may use floating-point probabilities on the host. The target format shall quantize them into small unsigned integer scores or rank buckets. Runtime comparison/accumulation should use 8- and 16-bit integer operations wherever possible.

If a future candidate genuinely benefits from wider accumulation, it must implement that width explicitly from smaller integer pieces; C48 has no `long` type to casually absorb the problem.

## 7. Token representation — working design

The target tokenizer shall be deterministic, bounded, and substantially cheaper than carrying raw repeated English text through the whole context engine.

The current design direction is a mixed-width token stream:

- very common words, punctuation, conversation markers, and Spectrum-domain terms receive one-byte codes;
- less common vocabulary receives an escaped multi-byte token ID;
- unknown words are represented through a bounded spelling/literal escape rather than silently dropped;
- common multi-token phrases may later receive dictionary phrase codes if measurement proves a net byte and quality win.

The exact escape values, vocabulary cardinality, phrase-code rules, and case normalization are not frozen until corpus measurements exist. The encoder must remain single-pass or bounded-lookahead on target.

The important invariant is that the conversation engine stores canonical token IDs wherever possible instead of repeatedly storing the same English strings.

## 8. Compressed conversational context

### 8.1 Terminology

`ailmzx48` will deliberately have an **effective conversational context** much larger than its **live exact-token window**.

This is application-level information compression. It is not ZX-UX virtual memory, paging, swapping, or transparent compression of process RAM.

The system is hierarchical. Detail is retained while it is likely to matter and progressively collapsed into cheaper semantic representations as it ages.

### 8.2 Four context levels

The working context has four levels.

**L0 — exact live tail**

The newest dialogue remains as canonical token IDs in a fixed circular buffer. This is the only part treated as exact word-by-word conversational history by the response generator.

L0 contains enough recent user/assistant text to preserve pronouns, immediate corrections, local phrasing, unfinished topic transitions, and short-range linguistic continuity. Its capacity will be selected from measured quality/bytes, not guessed from a desktop-LM token count.

**L1 — semantic turn capsules**

When older turns leave L0, they are reduced to compact fixed-format records. A capsule records only information that can influence future conversation, for example:

- speaker/turn class;
- topic IDs;
- salient entity IDs;
- question/answer or assertion class;
- small polarity/stance flags;
- selected numbers/dates where representable and important;
- a compact bag or sequence of high-information token IDs;
- recency/turn-distance information;
- a confidence/importance rank.

C48 need not have `struct` support for this. The target representation is a byte record with documented offsets or a set of parallel arrays.

A capsule is intentionally lossy. Its job is to remember that, for example, the user was discussing `Manic Miner`, had already been told who wrote it, and then compared it with `Jet Set Willy`; it need not retain every article and adjective from the original turns.

**L2 — hierarchical session synopsis**

When the L1 ring fills, a deterministic compaction pass merges the least-recent/least-important capsules into one or more coarser synopsis records. These retain durable topics, named entities, user-stated preferences relevant to the conversation, unresolved questions, and facts already supplied by the agent.

The synopsis is therefore a compressed semantic state, not generated prose. No second language model is needed to summarize the conversation on target.

Repeated compaction makes context capacity scale by information density rather than raw character count. A long conversation full of repeated discussion can therefore remain semantically represented with very few bytes.

**L3 — optional exact transcript archive**

For reproducibility, debugging, and occasional recovery, exact user/assistant text may also be appended to a transcript object when memory permits. An eligible closed transcript object may benefit from ZX-UX ZXP1 packing.

L3 is not required for every inference step. Normal response planning uses L0/L1/L2. This avoids repeatedly seeking through a large PACKED object, whose backwards seeks are intentionally O(n) in REV12.

On GitHub/SDK evaluation runs, the host harness shall always retain an exact external transcript regardless of whether the target L3 archive is enabled. The external transcript is evidence, not hidden runtime context.

### 8.3 Promotion and compaction

After each completed exchange:

1. tokenize the new user turn and generated response;
2. append exact tokens to L0;
3. if L0 exceeds its fixed capacity, evict whole oldest turn fragments rather than arbitrary half-tokens where practical;
4. derive or update one L1 semantic capsule from the evicted material;
5. if L1 is full, merge selected old capsules into L2 according to a deterministic importance/recency rule;
6. optionally append the exact text to L3 before discarding its live text form;
7. retain enough counters/checksums in debug builds to prove that compaction never writes outside its assigned buffers.

No stage allocates an unbounded temporary copy of the text being compacted.

### 8.4 Retrieval into the active decision context

For each new user turn, the controller computes a cheap relevance score against L1/L2 records using integer features such as:

- exact topic match;
- salient entity match;
- overlap of high-information token IDs;
- unresolved-question marker;
- recency;
- importance/confidence.

Only the best small number of records are promoted into the current response-planning state. Retrieval therefore costs a bounded scan over compact records instead of reconstructing the entire historical conversation.

The response generator receives:

- the recent exact L0 tail;
- the new user turn;
- a bounded set of retrieved memory features;
- current topic/intent state;
- any Spectrum-domain knowledge records selected for the question.

This is how a conversation can behave as though it remembers much more text than can physically coexist as raw text in RAM.

### 8.5 What "larger context" does and does not promise

The design promises preservation of useful conversational information across much longer sessions than an all-raw live buffer could hold.

It does not promise perfect verbatim recall after old material has been reduced to L1/L2. If exact quotation of an old turn matters and L3 is unavailable or has been discarded, the agent must not fabricate the wording.

Quality tests shall therefore distinguish:

- exact recent recall;
- semantic old-turn recall;
- topic continuity;
- entity continuity;
- contradiction avoidance;
- unsupported pseudo-verbatim recall.

### 8.6 Context-compression measurements

Every candidate context implementation shall report at least:

- L0 capacity in tokens and bytes;
- L1 capsule count and bytes;
- L2 synopsis capacity and bytes;
- optional L3 logical and physical bytes;
- total target bytes devoted to context;
- source-equivalent raw transcript tokens represented;
- exact-recall horizon;
- semantic-recall accuracy by turn distance;
- compaction CPU cost;
- retrieval CPU cost.

The phrase "effective context" in project documentation must be accompanied by those measurements. It must not be presented as a transformer-equivalent context-window number without qualification.

## 9. Model storage and access

Keeping a large immutable model entirely inside the executable image is simple but consumes live process allocation for its whole lifetime. Keeping it as a ZX-UX RAM object still consumes the shared arena, but an eligible inactive model resource may be stored in PACKED form and read as a logical stream.

The initial implementation shall therefore benchmark at least two layouts under identical model contents:

- embedded immutable model bytes linked into the MEX1 image;
- one or a small number of external model objects, including a PACKED representation where ZXP1 materially reduces physical storage.

The external-object design must be laid out for predominantly sequential reads or coarse monotonic sections. It must not assume cheap random seeking inside a PACKED object.

A model split across many tiny objects is disfavored because the ZX-UX mutable object table has only 32 entries and those entries are a system-wide resource.

The final model format shall include a small magic/version header, declared logical sizes/counts, bounded offsets, and an integrity field suitable for target validation. Host release tooling may additionally retain SHA-256 identities; target code does not gain a SHA-256 dependency merely to identify the model.

## 10. Runtime memory budgeting

No release memory claim is frozen until the real compiled C48/MEX1 artifact and model are measured. The budget shall nevertheless be accounted in named categories from the first prototype:

```text
process image/text + static model code/tables
process BSS, including L0/L1/L2 buffers
process FAST stack
fixed C48 heap reserve
external model object physical storage, if used
PACKED-reader decoder state, if used
optional target transcript object physical storage
other simultaneously resident ZX-UX objects/processes
free-arena safety margin
```

The invariant is:

```text
all simultaneous arena consumers + required safety margin <= 32768 bytes
```

The build/evaluation harness shall reject a candidate whose measured peak violates that equation, even if it appears to work in a host-side simulation.

### 10.1 Provisional engineering targets

Before measurement supplies better numbers, the design should aim for:

- a small inference executable rather than a monolithic data-heavy one;
- a 1024-byte or smaller stack unless measured call depth proves otherwise;
- a zero or very small C48 heap;
- context buffers measured in low single-digit KiB, with older conversation compressed rather than retained verbatim;
- enough uncommitted arena headroom for normal ZX-UX bookkeeping and the model/transcript access pattern.

These are engineering targets, not release promises.

## 11. Response pipeline

A normal turn is planned as a bounded pipeline:

```text
read line
  -> normalize/tokenize
  -> detect q/commands
  -> score topic + intent + salient entities
  -> retrieve L1/L2 conversational memories
  -> retrieve Spectrum-domain knowledge/model section
  -> choose response mode/seed
  -> generate/rank token continuation
  -> anti-repeat and sanity checks
  -> detokenize/print
  -> update L0/L1/L2 and transcript evidence
```

Every stage has a fixed maximum input/output size. A failure in an optional stage falls back to a documented simpler response path rather than overrunning memory.

The controller may choose a direct knowledge response, a conversational continuation, a clarification request, a bounded "I don't know" response, or another measured mode. The controller must never invent remote capabilities or hidden access to information outside the shipped model/context.

## 12. Anti-repetition and conversational quality

Small n-gram-like models can easily loop. The response controller shall therefore track a small recent-output fingerprint/token history and penalize or reject:

- immediate repeated token runs;
- repeated short phrases;
- regeneration of the immediately previous answer;
- pathological punctuation loops;
- unbounded sentence generation.

Generation has an exact token/character ceiling and must terminate deterministically even if the model contains malformed cyclic transitions.

The quality target is not merely grammatical-looking noise. Domain factuality, question relevance, continuity with compressed memory, and graceful uncertainty outrank novelty.

## 13. User interaction

### 13.1 Startup conversation — provisional text

The startup text will remain short enough for the target terminal while making the machine's limitations part of the joke rather than hiding them.

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

This wording remains provisional until terminal-width behavior, exact character repertoire, binary size, and startup-memory cost are measured.

### 13.2 Input

`ailmzx48` owns its application input loop after launch. It shall use a bounded line buffer and normal ZX-UX tty services. It shall not depend on the shell retaining the conversation line for it.

The exact maximum conversational input line is not frozen yet. It must be small enough to bound tokenization scratch space and large enough for useful questions. Overlength input must be rejected or cleanly drained with an explicit message; truncation that changes meaning silently is not acceptable.

When waiting for ordinary conversational input, the exact quit command `q` terminates cleanly. Any broader quit syntax will be documented if added later.

## 14. Instrumentation and automated conversation testing

The project requires a target-visible test path, not only host model scores.

The automation architecture shall contain:

- deterministic corpus/model build tooling;
- a host reference implementation for the tokenizer, context compressor, retriever, and model scorer;
- byte-for-byte model-format verification between host output and target reader expectations;
- SDK/emulator keyboard or tty-input injection;
- exact capture of the application's emitted terminal/text stream;
- per-turn timing/progress counters where practical;
- target memory-watermark evidence;
- exact retained host transcript plus model/build identity;
- long scripted conversations that deliberately exceed the raw live-context capacity;
- regression cases for q/EOF/overlong input/corrupt model/out-of-memory paths.

The host reference implementation is an oracle and tooling aid. It is not a runtime dependency.

### 14.1 Context-specific tests

Long-conversation tests shall deliberately place important facts at increasing turn distances, push them out of L0, force L1 compaction into L2, and then ask questions whose correct answers depend on those facts.

Tests must separately prove that:

1. recent exact wording remains available within the declared L0 horizon;
2. old semantically important facts survive compaction;
3. low-value chatter can be forgotten without poisoning later answers;
4. contradictory later corrections supersede older state according to a documented rule;
5. the agent never claims verbatim recall when only a lossy capsule remains;
6. repeated compaction never grows memory usage;
7. a conversation substantially longer than the live exact-token capacity completes without memory corruption.

## 15. Training and convergence

Training/model construction happens on the host from a provenance-recorded Spectrum-domain corpus plus conversational material approved for this project.

The loop is empirical:

```text
build candidate
-> package target model
-> run host unit/evaluation suite
-> run target/SDK conversation suite
-> retain transcripts + metrics + artifact identities
-> inspect failures
-> change corpus/model/controller/context policy
-> repeat
```

There is no arbitrary fixed number of training iterations. Work stops only when the defined quality, memory, latency, reproducibility, and target-correctness gates converge and remain stable over repeated runs.

The final training section will define exact corpus licensing/provenance rules before corpus material is admitted.

## 16. Cassette and real-machine workflow constraints

The final release workflow must be derived from the canonical REV12/REV03 cassette, object, compiler, linker, and shell behavior. It may not invent a disk-like filesystem or assume the development SDK exists on the physical Spectrum.

The intended user story is:

1. boot ZX-UX using its canonical Spectrum cassette sequence;
2. load the required native C48 development objects/source/model material from cassette using supported ZX-UX mechanisms;
3. compile the C48 source with `cc` into OBJ1;
4. link it with `ld` into MEX1 using a measured stack/heap reservation;
5. save the resulting executable/model objects to cassette through supported ZX-UX tape facilities;
6. remove/reclaim compiler, linker, source, and other no-longer-required RAM objects as needed;
7. later load the runnable `ailmzx48` distribution and execute it with the larger runtime memory envelope available after build tools have been reclaimed.

Exact command transcripts are deferred until every command and tape transition has been checked against canonical REV12/REV03 and the implemented SDK/ZX-UX behavior.

## 17. Phased implementation order

Implementation will proceed only after this design is sufficiently frozen. The current intended order is:

1. canonical-constraint verifier and host reference tokenizer;
2. candidate corpus token statistics and token encoding selection;
3. host reference L0/L1/L2 compressor/retriever with adversarial long-conversation tests;
4. candidate sparse-LM/model-family comparison under explicit byte budgets;
5. frozen target model format plus host packer/verifier;
6. minimal C48 target shell that reads input, tokenizes, and emits deterministic test responses;
7. target L0/L1/L2 memory implementation with bounds instrumentation;
8. target model reader/scorer/generator;
9. integrated conversational controller and anti-repetition logic;
10. SDK automated long-conversation harness and convergence loop;
11. real ZX-UX memory/tty/cassette integration and physical-machine verification;
12. release packaging, exact native compile/link/save/load transcript, and final certification evidence.

Each phase must preserve a working, testable state. Model sophistication is never allowed to outrun memory-safety and reproducibility evidence.

## 18. Open design questions

The following remain deliberately open until measurement resolves them:

- exact vocabulary size and token wire format;
- exact L0 token count;
- exact L1 capsule layout/count;
- exact L2 synopsis layout and compaction policy;
- whether target L3 transcript storage is enabled by default;
- winning sparse language-model family and order/depth;
- model embedded-vs-external storage split;
- exact model byte budget and ZXP1 compression ratio;
- exact response token ceiling;
- deterministic versus lightly stochastic sampling policy;
- final stack and heap linker reservations;
- exact target object names and cassette packaging sequence;
- quantitative convergence thresholds for factuality, continuity, repetition, latency, and memory.

These are measurement questions, not invitations to silently assume desktop defaults.

## 19. Revision discipline

This file is the canonical evolving `ailmzx48` design record within the SDK repository. Each coherent design stage is committed directly to `main`. Conversation text is not an authority when it conflicts with the repository copy.

Before each substantive edit, the latest repository copy shall be read. Canonical ZX-UX/C48 documents shall be rechecked whenever a design statement depends on their contracts. If a later canonical revision changes a relevant contract, this document must be reconciled explicitly rather than carrying an accidental stale assumption forward.
