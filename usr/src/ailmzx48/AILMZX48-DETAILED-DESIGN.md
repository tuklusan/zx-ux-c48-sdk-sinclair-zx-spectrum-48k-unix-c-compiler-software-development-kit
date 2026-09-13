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

Status: SDK implementation profile qualified; full native-release profile blocked on upstream ZX-UX implementation
Revision: 0.26-draft
Canonical repository path: `usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md`  
Canonical SDK executable path: `usr/bin/ailmzx48/ailmzx48.c48b`

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
    └── ailmzx48/
        └── ailmzx48.c48b              # generated SDK C48B1 artifact
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

Forensic Review Pass 1 re-extracted the actual DOCX from repository bytes rather than inferring it from the Python compiler. The reviewed DOCX has SHA-256 `bc371718637b1ffe840bb220c6fff6421982a05337e30cafdbf05497b202268d`. It directly confirms an unsigned 8-bit plain `char`, 16-bit `short`/`int`/pointers, five-byte Spectrum-compatible `float`, no `long`, a 15-character identifier limit, and the absence of function pointers, variadic functions, `struct`/`union`, `switch`/`case`, compound assignment, the conditional operator and the comma-expression operator.

The design therefore uses flat byte arrays, parallel arrays where a record would otherwise be tempting, explicit indices, small fixed functions, integer/fixed-point scoring, and direct bounds checks. Floating point is not required for model inference. Target identifiers in this document are kept at or below the canonical 15-character limit.

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

ZX-UX and the ZX-UX SDK expose a 64-character by 24-line text terminal. `ailmzx48` shall write ordinary terminal text rather than draw its own text renderer. Its wrapping, scrolling, and prompt behavior must be tested against the real tty implementation, including deferred-wrap semantics.

The terminal is part of the behavior contract. Automated evaluation shall capture the logical character stream as well as, for selected cases, the final 6912-byte Spectrum screen. A pretty host transcript cannot substitute for correct target wrapping/scrolling.

### 5.7 SDK repository/release-gate constraints

`ailmzx48` lives inside an already certified SDK repository, so repository rules are part of implementation feasibility rather than clerical cleanup.

For every repository change associated with this project:

- every new or modified `usr/src/**/*.c` or `usr/src/**/*.h` artifact must obey the SDK's current <=64-character source-line release contract;
- target C/H identifiers must obey the C48 15-character identifier limit;
- new header-eligible project files must carry the repository-required license/attribution header;
- a new artifact suffix or exceptional format must be classified by the existing license/release tooling rather than bypassed;
- `MANIFEST.sha256` must be regenerated from the exact repository bytes using the repository's established normalization rule;
- `python -B compiler/verify_release.py` must pass on the complete candidate tree before that repository state is accepted;
- no test, manifest, license, deterministic expectation, source-line gate or release verifier may be weakened merely to admit `ailmzx48`.

The host SDK's passing behavior is useful evidence, but its documented non-claims remain in force: it does not by itself certify native Z80 stack use, allocator fragmentation, OBJ1/MEX1 behavior, ZX-UX syscalls, scheduler behavior or cassette semantics.

## 6. Architectural choice: a host-trained sparse local language agent

A transformer-style neural LM is not the baseline architecture. Its parameter storage, activation memory, multiply-heavy inference, and context machinery are a poor fit for a 3.5 MHz Z80 and the ZX-UX arena.

The working architecture is instead a host-trained, target-inferred sparse statistical language agent with four cooperating pieces:

1. a compact tokenizer/vocabulary;
2. a tiny intent/topic and salient-entity scorer;
3. a compressed Spectrum-domain knowledge/reply store;
4. a variable-order token language model used to rank or generate fluent response continuations under the controller's topic/intent constraints.

This is still a language model: probabilities/weights over token continuations are learned from a corpus and used locally at inference time. The surrounding agent controller supplies conversation state, memory retrieval, topic steering, factual anchoring, uncertainty/fallback behavior, and anti-repetition controls.

The exact release model family is not frozen by this revision. Revision 0.3 introduced concrete **Candidate A**; Revision 0.11 retains it as a corrected benchmark baseline so implementation and measurements can begin without pretending the representation is already optimal. Candidate A is not a promise that no better representation will replace it.

Implementation measurement note (Revision 0.15): the first two bootstrap iterations used one global learned first-order transition graph. Iteration 2 showed cross-topic sentence splicing when shared lexical tokens connected otherwise unrelated training records. The bootstrap implementation therefore moves to topic-conditioned learned transition tables selected by the controller. This remains a measured prototype, not a freeze of the release model family; it is also closer to the architecture above, where topic/intent constraints condition language-model continuation scoring.

Implementation measurement note (Revision 0.16): iteration 3 reached 12/12 keyword expectations on regression and fresh paraphrase prompts with coherent topic-conditioned replies. The next bootstrap measurement therefore adds one bounded previous-response topic register solely to test immediate follow-up continuity. Explicit topic cues always win; only the fixed phrases `tell me more`, `what about that`, and `same topic` may inherit the preceding response topic. `ai_ctxuse` records use per accepted turn. This three-word state is not claimed as Candidate-A L0/L1/L2 implementation and contributes no large-context evidence; it is a controller prototype used to establish harness semantics before the fixed context engine is implemented.

Implementation measurement note (Revision 0.17): iteration 4 reached 14/14 answer expectations and 14/14 expected context-use decisions. Immediate topic inheritance therefore works as an instrumented controller primitive. Repeated same-topic answers still duplicated the same learned path, so the bootstrap generator now alternates deterministically between the learned primary and secondary continuation from the topic seed when a topic repeats. `ai_altuse` reports whether the secondary path was actually taken. This is anti-repetition measurement over learned statistics, not a canned response table and not stochastic sampling.

Implementation measurement note (Revision 0.18): iteration 5 validated deterministic learned secondary continuations without breaking immediate topic context. The next bounded prototype adds a six-entry recent-distinct-topic history so explicit `go back` requests can recover prior topics across intervening topic changes. This is instrumentation for conversational-history behavior only; it is not the final L0/L1/L2 representation and makes no expanded context-window claim until the designed compressor is implemented and stress-tested.

Implementation measurement note (Revision 0.19): iteration 6 validated bounded recovery of earlier topics across intervening topic changes. The next prototype allocates the full designed 272-byte session-literal storage as parallel C48 arrays (eight generation values, eight lengths, and 8 x 31 presentation bytes) while initially using slot 0 only for an exact user-name literal. Generation advances in the designed 1..4095 range on correction. This slice tests exact literal retention/correction; semantic refs, eight-slot eviction and L1/L2 invalidation remain future work.

Implementation measurement note (Revision 0.21): the target C48 program now contains the first fixed-size semantic-context slice rather than relying only on the six-topic controller history. It allocates the 896-byte L0 ring, exact 128-byte 32-entry descriptor directory, 48 x 16-byte L1 capsules, and 24 x 16-byte L2 capsules as fixed arrays, ages capsules saturating at 255, promotes evicted L0 user turns into L1, and compacts L1 victims into mergeable L2 summaries. An explicit `remember this topic` controller operation is retained as a high-importance semantic capsule and `return to the remembered topic` retrieves it after L0 eviction. This slice deliberately stores normalized printable turn bytes in L0 rather than the final Section-7 token wire and currently commits ordinary model-answer turns rather than every controller-only turn. It is therefore a target-resident compaction/retrieval prototype, not yet a claim that Candidate-A canonical tokenization or the complete 4,336-byte workspace is implemented. The runner records L0/L1/L2 occupancy, per-turn compaction/eviction counters and semantic-retrieval use so a >32-KiB source-equivalent actual SDK conversation can prove bounded distant semantic recall before the final tokenizer wire replaces the temporary L0 byte representation.

Implementation measurement note (Revision 0.22): iteration 11 is the first retained actual-SDK long semantic-context endurance result. The real C48 program accepted 500 turns plus the terminating `q`, emitted 501 turn-start beeps, processed 48,820 source-equivalent dialogue bytes, performed 443 L1-to-L2 compactions, reached the fixed 48-record L1 and five L2 records while keeping L0 at or below 884 of 896 bytes, and then recovered the memory topic pinned at turn 2 on turn 500 after 497 intervening turns. The final answer was `Memory matters because every byte deserves care.` The active SDK run took 275.815 seconds and remained inside the 1,200-second session limit. This is distinct from the earlier host-only 500-dialogue/51,000-byte context-reference stress. It proves bounded target-resident semantic retention in the SDK VM, while the L0 representation in that iteration was still the temporary normalized printable-byte prototype.

Implementation measurement note (Revision 0.23): the target L0 slice now stores the Section-7 control/lexical/literal wire shape instead of raw turn text. Known resident lexical IDs use the one-byte hot form (and the extended form remains implemented for IDs >=224); unknown alphanumeric spans use bounded F1/F2/F3 literals; user/assistant framing and turn-end controls are stored explicitly. A 96-entry u16 decoded LM-context ring is maintained simultaneously with lexical IDs, literal-class refs and speaker framing refs. Pin state is now descriptor metadata rather than a raw-text search during L0 eviction, so semantic promotion remains valid after wire encoding. Printable punctuation that is not yet resident in the starter vocabulary is retained through the F1 literal fallback; therefore the starter tokenizer still does not satisfy the final preference that common punctuation have ordinary lexical IDs. Encoding is two-pass (size/preflight then direct ring write), so an oversized encoded speaker turn is rejected before L0/L1/L2 mutation. The next measurement must re-run long semantic endurance on this encoded target state before the temporary raw-L0 evidence is superseded.
Implementation measurement note (Revision 0.24): iteration 12 repeated the retained 500-turn actual-SDK endurance scenario after replacing the temporary printable L0 with the Section-7 token/literal wire. The C48 program again accepted 500 turns plus `q`, emitted 501 beeps, processed 48,820 source-equivalent dialogue bytes, recovered the turn-2 memory topic at turn 500, and completed in 266.794 seconds. The encoded L0 peak fell from iteration 11's 884 bytes to 830 of 896 bytes; L1 reached 48 records, L2 reached five, 436 L1-to-L2 compactions occurred, and the decoded 96-entry u16 LM-context ring reached its exact capacity without exceeding it. This supersedes the raw-L0 endurance evidence for the implemented wire slice while leaving punctuation-token coverage and richer semantic capsules as open work.

Implementation measurement note (Revision 0.25): the target session-literal prototype now uses all eight designed 31-byte presentation slots with 1..4095 generations and bit-15 session references. User-name corrections rotate deterministically through the eight slots. Name state is stored in the value field of relation-3 L1/L2 capsules rather than recalled directly from slot zero; recall generation-checks the reference before resolving bytes. A correction marks older name capsules superseded, and reusing a slot scans both semantic tiers for the old generation reference, clears it and increments `ai_litloss`. L2 merging preserves a current relation-3 capsule over superseded history. This is the first target-side generation-checked session-reference slice, but it is still specialized to the user-name relation rather than the complete Candidate-A semantic relation schema. The next retained conversation must force slot reuse, observe stale-reference loss, compact across a long dialogue and recover only the newest name.

Implementation measurement note (Revision 0.26): the SDK-target
implementation now closes the context/literal gaps identified after the
training convergence checkpoint.  Target code performs an explicit no-mutation
capacity/descriptor preflight before an accepted dialogue pair is committed,
uses protection/importance/age/slot ordering for semantic-record eviction,
uses generation-checked session-literal reuse with the designed preference for
an unreferenced slot and otherwise the weakest strongest live-retention tuple,
and invalidates schema-declared semantic-reference fields before slot reuse.
Name assignment/recall turns now pass through the same bounded L0/L1/L2
conversation commit path rather than living only in a side channel.  The added
logic was split into C48 headers rather than raising the compiler's 32768-byte
source-object safety ceiling.

The retained post-repair SDK conformance case contains 70 accepted turns.  It
scores 70/70 expected keywords, performs 15 L1-to-L2 compactions, reaches two
L2 records, fills the 96-entry decoded LM-context ring, records exactly one
deliberate stale-generation invalidation after the ninth distinct name, and
recalls only the newest name at the end.  Independent post-change replays of
final regression suites A, B and C each remain 12/12 with clean exit and zero
literal-reference losses.  These measurements supersede the open-work sentence
at the end of Revision 0.25 for the implemented SDK profile.

The SDK profile is not a substitute for native certification.  As of this
revision the read-only upstream ZX-UX repository main identity checked for the
native dependency is `cb8e4ea0b68df693e5d4133fc906ed46234427b6`; its latest
inspected durable certification item is Phase-1 `P1.25`.  That upstream state
does not yet provide the native C48/OBJ1/MEX1 build, allocator/stack/Fuse, and
physical-cassette execution path required by Sections 18, 19 and 22.  Those
native-only obligations therefore remain explicitly `BLOCKED_EXTERNAL`; they
are neither silently waived nor counted as SDK zero-gap evidence.


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

`0x00` is the scratch-stream terminator/invalid-continuation sentinel. Length-delimited L0 turns and cold records end by declared length plus their framing and do not store or count that sentinel. The 320- and 256-byte scratch buffers therefore retain one final byte for `0x00` after their <=319/<=255 encoded payloads.

Candidate A has one canonical lexical token-ID space, 0..4095. The 224 selected hot tokens receive IDs 0..223 and encode only as byte `0x10 + id`. IDs 224..4095 encode only as `0xF0` followed by the little-endian u16 ID. The decoder rejects `F0` encodings of hot IDs and IDs above 4095, so a lexical token never has two accepted wire encodings.

LM context refs use lexical IDs 0x0000..0x0FFF plus a separate nonlexical range: 0x1000 literal-word, 0x1001 numeric-literal, 0x1002 proper-name, 0x1003 BOS, 0x1004 EOS, 0x1005 user-turn, 0x1006 assistant-turn, 0x1007 turn-end and 0x1008 newline. Literal-class refs are context-only and can never be serialized as learned output continuations. Candidate A learned continuation lists may contain lexical IDs, EOS and newline only. BOS plus user/assistant/turn-end framing are controller-owned; reserved refs are rejected. The host builder/verifier enforces this allowlist before target bytes exist. 0x1009..0x10FF remain reserved.

Extended token IDs are provisionally limited to 0..4095 so host tooling can reject accidental vocabulary growth long before it becomes a 48K-machine problem. This limit is a Candidate-A constraint, not yet a release ABI.

Common punctuation is represented by ordinary hot/extended vocabulary tokens rather than bespoke syntax bytes. Whitespace between word tokens is reconstructed by deterministic detokenization rules. Literal escapes preserve bounded unknown input rather than deleting words the model does not know.

### 7.1 Vocabulary selection

The host builder shall select the 224 one-byte hot wire tokens by measured total byte saving, not raw frequency alone. A token that appears often but has a one-character spelling may save less than a longer Spectrum-domain term.

The extended token-ID space is provisionally limited to 0..4095, but **4096 IDs are an address-space ceiling, not a promise to keep 4096 spellings resident**. Any token that the target tokenizer must recognize by spelling, any token the hot LM may emit, and every token/alias used as a cold-record trigger must have a directly usable resident recognition/presentation entry or another separately measured resident lookup representation. Candidate A initially uses one resident sorted recognition/presentation lexicon rather than hiding a random-access dictionary inside a PACKED object.

Cold-record payload wording that is not needed for target-side recognition may remain literal bytes inside the cold sequential stream. A word must not be assigned a compact extended ID if reconstructing or matching that ID would require an unbudgeted random seek through cold storage.

The resident lexicon is chosen from the remaining corpus by a score that considers occurrence count, spelling length, domain importance, factual-entity/trigger use, LM-output use and total table bytes. Candidate builds must report:

- one-byte hot token count and coverage;
- resident extended token count and coverage;
- resident recognition/presentation table bytes;
- literal escape rate on training/dev/evaluation corpora;
- mean encoded bytes per lexical token;
- mean encoded bytes per raw input character;
- total dictionary/index storage bytes.

If a later compact alias index beats the resident sorted lexicon, it is a measured candidate change; Candidate A does not assume such an index for free.

The 16-bit **semantic-reference** namespace used by L1/L2 and cold-record entity fields is deliberately separate from the 0..4095 lexical token-ID namespace. Semantic reference 0 means absent; persistent semantic symbols use 1..0x7FFF; bit-15-set values are session literals. Host tooling owns the mapping from recognized lexical tokens/phrases to persistent semantic symbols and charges that mapping to resident hot-table bytes. A lexical token ID is never copied blindly into a semantic-reference field.

Topic IDs are a third namespace. Candidate A reserves topic ID 0 for generic/unknown and assigns 1..65535 only through the generated model's frozen topic-ID map. L1/L2 topic fields, classifier outputs and cold-record `topic_id` values all use that same map. The map is a hot/cold compatibility input, not an incidental trainer ordering.

### 7.2 Normalization and case

Matching uses a canonical ASCII normalization suitable for the Spectrum character repertoire. Ordinary English matching is case-normalized, but output spelling is not forced to lower case. Dictionary entries carry enough presentation information to render forms such as `ZX Spectrum`, `Sinclair`, `Manic Miner`, `Z80`, and `ULA` correctly.

Literal `F1`/`F3` payloads preserve accepted presentation bytes. Case folding is performed during comparison rather than by destroying those bytes. Thus an unknown name such as `McDonald` can survive with its presentation spelling while still participating in the policy-defined case-normalized match. The tokenizer must not silently transform a user-supplied unknown name into a known but different token.

### 7.3 Exact recent-token access

A variable-width encoded stream is compact but inconvenient for repeated backwards language-model lookups. Candidate A therefore maintains two recent-history views:

1. a compact encoded L0 exact-turn ring for storage;
2. a 96-entry decoded u16 **LM-context reference** ring for fast recent n-gram access.

Known vocabulary tokens use their canonical target token IDs. Literal-word, numeric-literal and proper-name escapes are represented in the decoded LM ring by three fixed synthetic class references outside the 0..4095 vocabulary-ID range; their exact literal bytes remain in the encoded current-turn/L0 storage. Synthetic literal classes are context features only and can never be detokenized as invented words.

The decoded ring is therefore a cache of recent LM context, not an independent exact transcript. It may be reconstructed from L0 after reset/debug operations.

### 7.4 Lexical and encoded-turn bounds

Literal escapes are bounded format records, not licenses to truncate input. Candidate A applies these rules before any conversation state is mutated:

- `F1` literal-word payload: 1..31 ASCII bytes;
- `F2` numeric-literal payload: 1..15 ASCII bytes;
- `F3` proper-name payload: 1..31 ASCII bytes; a detected multi-word proper-name span may include its internal ASCII spaces;
- a lexical item/span that exceeds its applicable bound is rejected for that turn with a bounded user-visible error rather than silently shortened or changed;
- malformed embedded NUL/control bytes are rejected by the tokenizer input contract;
- the complete user turn must fit the separate current-turn encoded scratch limit defined in Section 8.7 after token expansion.

These are Candidate-A bounds. Later measurements may change them only together with the wire-format and workspace accounting.

## 8. Compressed conversational context

### 8.1 Terminology

`ailmzx48` will deliberately have an **effective conversational context** much larger than its **live exact-token window**.

This is application-level information compression. It is not ZX-UX virtual memory, paging, swapping, or transparent compression of process RAM.

The system is hierarchical. Detail is retained while it is likely to matter and progressively collapsed into cheaper semantic representations as it ages.

### 8.2 Four context levels

The working context has four levels plus one small session-literal table used by the semantic levels.

**L0 — exact canonical-token live tail**

The newest dialogue remains as canonical encoded tokens in a fixed circular byte buffer plus a small decoded LM-context cache. This is the only part treated as exact canonical-token conversational history by the response generator. Because tokenization normalizes presentation such as ordinary case/spacing, L0 is not a byte-perfect transcript of what the user typed.

L0 contains enough recent user/assistant text to preserve pronouns, immediate corrections, local phrasing, unfinished topic transitions, and short-range linguistic continuity.

**L1 — semantic turn capsules**

When older turns leave L0, they are reduced to compact fixed-format records. A capsule records only information that can influence future conversation: speaker/source class, topic, salient entities, question/assertion/correction state, selected high-information references, importance and bounded recency.

Candidate A uses a 16-byte L1 capsule. Before target implementation, each intent/relation-class ID also freezes a small host/target schema saying which semantic-reference fields are meaningful and whether bytes +12..13 hold a raw numeric/date/token payload or a semantic reference. The same schema drives validation, correction keys, session-literal invalidation and host/target differential tests; a field is never guessed to be a reference from its bit pattern alone.

```text
+0      flags
+1      intent or relation class
+2..3   topic id u16
+4..5   entity A semantic ref u16, 0 if absent
+6..7   entity B semantic ref u16, 0 if absent
+8..9   high-information semantic ref A u16, 0 if absent
+10..11 high-information semantic ref B u16, 0 if absent
+12..13 value/token/date payload u16 interpreted by flags/relation
+14     importance/confidence rank u8
+15     saturating age bucket u8
```

The Candidate-A flag byte is:

```text
bit 0     speaker: 0 user, 1 assistant
bit 1     question
bit 2     explicit correction
bit 3     negative/polarity marker
bit 4     unresolved/open state
bit 5     superseded state
bits 6-7 source class:
00 user/session assertion
01 assistant fact grounded by selected cold knowledge
10 assistant conversational/unverified state
11 reserved/system state
```

No C48 `struct` is required. The implementation stores these as byte arrays and symbolic byte offsets.

A capsule is intentionally lossy. Its job is to remember, for example, that the user was discussing `Manic Miner`, had already been told who wrote it, and then compared it with `Jet Set Willy`; it need not retain every article and adjective from the original turns.

**Session literal table — bounded exact names/values used by L1/L2**

Semantic-reference value zero is reserved for `absent`. Persistent model entity/token references therefore use bit 15 clear and values 1..0x7FFF; the host builder rejects persistent reference zero. Bit 15 set denotes a session-literal reference: bits 14..3 contain a 12-bit generation and bits 2..0 select one of eight slots. Generation zero is invalid, so live generations are 1..4095. Candidate A reserves eight 34-byte slots:

```text
+0..1   generation, low 12 bits significant
+2      byte length 0..31
+3..33  exact presentation ASCII bytes, unused tail zero
```

An existing literal is reused when its policy-defined ASCII-folded comparison matches; the retained presentation bytes are not rewritten merely because a later mention uses different case. Before slot reuse, every matching L1/L2 reference is invalidated by a bounded scan and `ai_litloss` is incremented. The new nonzero generation makes a missed stale reference fail validation rather than alias a new name. Generation wrap first invalidates every reference to the slot and restarts at 1.

Slot selection is a frozen total order. Prefer an unreferenced slot, lowest slot index first. Otherwise scan all L1/L2 references to each slot and derive the slot's strongest live retention tuple: highest record protection class, then highest importance, then youngest (smallest) age. Evict the slot whose strongest tuple is weakest: lower protection, then lower importance, then older age, then lower slot index. This protects a slot when even one live record strongly needs it while still guaranteeing a victim when all eight slots are referenced. Every invalidated reference is cleared/counted before new bytes receive the new generation. If old presentation bytes are lost, the agent may retain the remaining semantic relation but must not pretend it still knows the spelling.

This table is what lets a user-supplied unknown name or short temporary string survive L0 eviction without pretending that an arbitrary new word magically acquired a permanent model token ID.

**L2 — hierarchical session synopsis**

Candidate A uses 24 x 16-byte L2 records with the same physical field skeleton as L1. An L2 record is a merged semantic fact/state record, not generated prose. L2 compaction uses a deterministic relation key containing source class, relation class, topic and applicable entity refs. Matching keys are coalesced; correction/supersession state and the newest bounded value are preserved according to Section 8.4.

When no existing L2 key can absorb an incoming record and all 24 slots are occupied, Candidate A deterministically evicts the lowest-retention record using protection class, importance, saturating age and slot index as the tie-break tuple. It increments `ai_l2evict`. Corrections, unresolved questions and current user/session facts receive stronger retention than repeated low-information chatter, but **L2 is still finite**: unrelated high-information facts can eventually be lost and the evaluation must measure that loss honestly.

Age is not a modulo turn counter. The u8 bucket is measured in accepted conversational turns and saturates at 255. On every accepted-turn commit, preflight/commit age every already-resident L1/L2 record by one with saturation before victim selection. A capsule newly derived from an evicted L0 speaker turn is initialized to `1 +` the number of newer user-turn descriptors already present after that source turn in the pre-commit L0 directory, saturated to 255; this preserves the time the source already spent in L0 instead of making an old assertion look new when compressed. User and assistant descriptors from the same dialogue turn therefore receive the same initial turn age. L2 coalescing retains the age of the surviving/newest semantic observation selected by the correction/supersession rule. No age path wraps to youth.

**L3 — optional exact accepted-turn archive**

The SDK/GitHub harness always retains the exact external session transcript. Candidate A keeps target L3 **disabled by default**. When enabled, target L3 is only an exact archive of accepted user/assistant turn bytes; startup/prompt traffic and rejected raw lines remain available only in the external harness transcript. A writable RAW archive consumes the same arena as the process/model and reopening a PACKED object for write can materialize a RAW replacement.

A diagnostic build may enable target L3 only with an explicit fixed logical/physical quota included in the arena budget. When that quota is reached, archival stops with a diagnostic counter; it never grows opportunistically until memory fails. After a closed archive becomes eligible for packing, any later reopen-for-write peak must still be budgeted as a RAW materialization. L3 is not normal inference context and cannot be used to inflate the claimed live context window.

### 8.3 Promotion and compaction

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

The preflight overlay is part of the generated Section-8.7 lifetime/layout report. It simulates the same accepted-turn age update, L1/L2 victim/merge order, session-literal invalidations/reuse and L0 evictions that commit will replay. Commit performs no dynamic allocation and no required external I/O, so successful preflight leaves no recoverable capacity failure. An invariant/guard failure is a fatal-session condition, not a promise of rollback from corrupted state.

The 128-byte L0 directory is exactly 32 four-byte descriptors: `u16` ring start plus `u16` encoded byte length. Speaker/turn type remains encoded in the turn stream itself. Ring reads crossing the physical end use bounded modulo copying; a descriptor is accepted only when start/length prove every referenced byte lies within the 896-byte logical ring.

The commit path is tested at both limiting resources: nearly full ring bytes with free descriptors, and free bytes with all descriptors occupied by tiny turns. When L1 needs slots, victim selection is deterministic: weaker protection class first, then lower importance, then greater saturating age, then lower slot index. Explicit corrections and unresolved state outrank ordinary chatter through a frozen protection-class table. Every selected L1 victim is merged into L2 before its slot is reused; if all records are highly protected, the same total order still chooses a victim rather than deadlocking. The host reference freezes/tests that mapping before target implementation.

No stage allocates an unbounded temporary copy of text or semantic records.

Implementation measurement note (Revision 0.20): a deterministic host reference for the Candidate-A L0/L1/L2/session-literal context machinery now exists in `tooling/context_reference.py`. It models the 896-byte L0 ring and 32-descriptor limit, complete-dialogue eviction, 48 fixed L1 records, 24 fixed L2 records, saturating ages, deterministic L1-to-L2 compaction/L2 eviction, four-record bounded retrieval, generation-checked session literals, and transactional preflight by clone-and-apply. Host-only descriptor metadata is an oracle sidecar; the target descriptor remains exactly four bytes. The retained stress report covers 500 dialogue pairs and 51,000 raw source-equivalent bytes while all modeled target context capacities remain fixed. This is a host correctness oracle, not yet proof that the C48 target implements the same state machine or native memory layout.

### 8.4 Correction and supersession rule

Conversation memory records **who asserted what**; they do not mutate the shipped cold knowledge base.

A later explicit user correction may supersede an older contradictory **user/session assertion** when the source class, topic/entity references and relation key establish that the statements describe the same semantic relation. The older session record is marked superseded or replaced during compaction.

A user assertion does not silently overwrite an assistant fact that was grounded by a cold knowledge record, and neither L1 nor L2 ever rewrites cold model bytes. If a user-supplied correction conflicts with grounded shipped knowledge, both provenance states may be retained: response planning can state the conflict, ask for clarification, or prefer the grounded fact according to measured policy. If identity/relation equivalence cannot be established, the system retains uncertainty rather than merging by guesswork.

This prevents compressed context from becoming either a fossilized contradiction pile or an easy route for a conversational assertion to poison the model's persistent factual state.

### 8.5 Retrieval into the active decision context

For each new user turn, the controller computes a bounded integer relevance score against L1/L2 records using features such as exact topic match, persistent/session entity match, overlap of high-information references, unresolved-question marker, correction/current-state marker, saturating recency and importance/confidence.

Every semantic-reference-bearing field identified by the frozen relation schema—including +12..13 when that relation declares it a semantic ref—is validated before use. A session-literal ref must match its slot and generation; a stale ref is cleared/treated as absent and counted, never resolved to newly reused bytes. Slot invalidation scans exactly the same schema-declared fields, so no hidden semantic-ref position can escape generation checking.

Candidate A retains the best four conversational-memory records as **indices plus scores**, not four copied 16-byte records. The original L1/L2 arrays remain the storage. This avoids spending retrieval scratch on data already resident and leaves the scratch budget for cold-model winners and streaming state.

The response generator receives the recent canonical-token L0 tail, the current encoded user turn, the bounded selected L1/L2 indices, current topic/intent state, and at most the two cold knowledge records selected in Section 9.

This is how a conversation can behave as though it remembers much more text than can physically coexist as raw text in RAM, while stale/lost semantic information remains observable rather than silently re-created.

### 8.6 What "larger context" does and does not promise

The design promises preservation of useful conversational information across much longer sessions than an all-raw live buffer could hold.

L0 preserves the exact **canonical token sequence** that survived tokenization. It does not by itself preserve byte-for-byte source spelling, capitalization or whitespace that normalization discarded. Perfect verbatim quotation is therefore promised only when the exact source bytes are still available from the current raw line, the external SDK transcript, or an enabled exact L3 archive.

After old material has been reduced to L1/L2, even canonical token wording is no longer promised. If exact quotation matters and no exact transcript source is available, the agent must not fabricate the wording.

Quality tests therefore distinguish canonical-token recent recall, source-byte/verbatim transcript recall, semantic old-turn recall, topic continuity, entity continuity, contradiction avoidance, correction handling, and unsupported pseudo-verbatim recall.

### 8.7 Candidate-A 4,336-byte conversation/context workspace

Forensic Review Pass 1 found that the Revision-0.3 ledger omitted simultaneous encoded current-turn state, had no bounded representation for unknown names after L0, and treated one 384-byte decoded response buffer as though it also solved canonical response-token retention. Candidate A therefore uses the following corrected static/BSS ledger:

```text
decoded LM-context ring        192   96 x u16 context refs
L0 encoded exact-turn ring     896
L0 turn directory              128   32 x 4-byte descriptors
L1 semantic capsules           768   48 x 16 bytes
L2 synopsis records            384   24 x 16 bytes
session literal slots          272   8 x 34 bytes
input line buffer              192   at most 191 bytes + NUL
current-turn encoded scratch   320   <=319 bytes incl. turn framing
response encoded-token buffer  256   <=255 bytes incl. turn framing
aim/retrieval scratch          512
generation/scoring state       256
guards, counters, cursors      160
                    ----
Candidate-A total             4336 bytes
```

The 512-byte retrieval scratch is explicitly partitionable as two 192-byte cold-record winner slots, up to 64 bytes of bounded streaming read/parser staging, and up to 64 bytes of scores/indices/header state. Conversational-memory winners remain indices into L1/L2 and are not copied here.

There is deliberately no second 384-byte decoded response buffer. Generation completes and validates the canonical encoded response first; detokenization then streams through the real tty one bounded token/literal at a time. Before printing, the generator proves the decoded output will satisfy the Section-11 character ceiling.

The 4,336-byte total is static/BSS working memory, not heap. It excludes program code, immutable resident lexicon/hot model tables, native process stack, ARG1/ENV1 allocation, external cold-model storage, PACKED-reader state, shell/system allocations and optional pre-budgeted target L3 storage.

All phase overlays inside the named scratch regions require a generated lifetime/layout report. A local C48 array, parser buffer or model-header copy that is not represented in this ledger is a memory-accounting defect rather than "compiler overhead".

The first experimental objective remains semantic recall over source-equivalent history many times larger than the L0 canonical-token ring without increasing this 4,336-byte baseline. The release objective includes a retained long-conversation transcript whose raw source dialogue exceeds the 32 KiB ZX-UX task/object arena while still demonstrating useful distant semantic dependencies. This is a semantic-context claim, not a promise that >32 KiB of verbatim bytes are resident or recoverable. No public ratio is claimed until the harness measures it.

### 8.8 Context-compression measurements

Every candidate context implementation shall report at least:

- L0 capacity in encoded bytes, decoded hot tokens, and source-equivalent tokens;
- L1 capsule count and bytes;
- L2 synopsis count and bytes;
- optional L3 logical and physical bytes;
- total target bytes devoted to context;
- source-equivalent raw transcript tokens represented;
- canonical-token recall horizon;
- semantic-recall accuracy by turn distance;
- correction/supersession accuracy;
- compaction CPU work;
- retrieval CPU work;
- session-literal slot evictions/stale-reference losses;
- L2 semantic evictions and dropped L1 candidates.

The phrase "effective context" in project documentation must be accompanied by those measurements. It must not be presented as a transformer-equivalent context-window number without qualification.

## 9. Model storage and access

Keeping a large immutable model entirely inside the executable image is simple but consumes live process allocation for its whole lifetime. Keeping it as a ZX-UX RAM object still consumes the shared arena, but an eligible inactive model resource may be stored in PACKED form and read as a logical stream.

Candidate A therefore deliberately splits the model into a **hot resident plane** and a **cold sequential plane**.

### 9.1 Hot resident plane

The executable contains only data that must be accessed repeatedly during generation:

- token-control definitions;
- resident hot + extended recognition/spelling/presentation lexicon;
- compact token class tables;
- intent/topic feature weights or ranks;
- high-frequency variable-order language-model transitions;
- small response-mode and anti-repetition tables;
- semantic-symbol lookup/mapping needed by L1/L2;
- model-format reader code and constants.

The hot plane is ordinary executable image/static data and therefore directly addressable. Its byte budget is measured against the compiled artifact. Candidate A begins with an engineering goal of low single-digit KiB for hot tables, but no exact release number is frozen before corpus measurements.

### 9.2 Cold sequential Spectrum knowledge plane

Spectrum-domain knowledge is stored as one or a very small number of external model objects. In Candidate A, **external means a separate resident ZX-UX RAM object during conversation**, not a magic tape-backed random-access file. An eligible resident object may be ZXP1 PACKED when the measured physical saving justifies the 272-byte read-state cost and decompression latency.

The baseline cold plane is scanned forward exactly once per user turn. At model-open time the program obtains the object's actual logical length through the canonical object metadata/stat path and requires it to equal the A48M declared logical length before any record can be accepted. With one persistent handle, the scanner seeks to logical offset zero at the start of the next turn; on a PACKED object REV12 therefore resets the decoder and the subsequent scan decodes forward again.

The scanner requests logical chunks no larger than 64 bytes but never assumes one `read` returns the whole request. It uses `read_full` where the exact remaining byte count is known, or an equivalent bounded loop that accepts legal positive short reads and treats zero/premature EOF before the declared end as model corruption. It never reads past the declared/actual equal logical length. `yield()`/kernel boundaries occur at measured chunk or record intervals rather than asking one syscall to decompress the entire model.

Each record header is scored as it streams past. Candidate A retains **at most two complete winning cold records**, each at most 192 logical bytes, in the two fixed winner slots inside retrieval scratch. A later better match replaces the lower-ranked slot deterministically. Irrelevant payload is validated/read and discarded; no backwards probe is needed to recover a winner.

A tiny index at the front of one PACKED object cannot by itself make the object random access: seeking to a later logical position still requires decoder work through the preceding logical stream, and returning backwards resets to zero. If one full scan per turn is too slow, the next candidates are measured alternatives such as a RAW indexed object, a small number of independently PACKED topic shards opened one at a time, or a larger resident topic/cache plane. Each alternative must account for physical bytes, extra handles/272-byte decoder states, fragmentation and latency.

The runner shall measure logical bytes scanned, resident physical bytes occupied, bounded read count, yields, VM work, selected-record count and answer latency. Host wall-clock time is not presented as Z80 latency; release latency requires Fuse/cycle evidence and ultimately real-machine evidence.

### 9.3 Candidate cold-record format

Candidate A uses a length-delimited logical record so corrupt lengths can be rejected before buffers are touched. The provisional record header is:

```text
u8   logical_record_length      complete record, Candidate-A maximum 192
u8   record_type
u16  topic_id
u16  entity_a
u16  entity_b
u8   importance
u8   trigger_count              0..4
u16  trigger[trigger_count]     canonical lexical token IDs
u8   anchor_count               0..2
pair anchor[anchor_count]:
      u8 payload_offset
      u8 encoded_length
...  encoded token payload      must fit logical_record_length
```

The 192-byte maximum is chosen because two complete winners must coexist inside the 512-byte retrieval scratch with bounded streaming/parser state. `entity_a`/`entity_b` use the Section-7.1 semantic-reference namespace: zero is absent and any nonzero cold-model entity must be a persistent 1..0x7FFF symbol. Each trigger is a canonical lexical ID 0..4095 and must be target-recognizable through the resident lexicon.

An anchor pair identifies an exact byte span within the encoded payload. Anchor spans may cover one or more complete lexical or literal encodings, have nonzero length, may not overlap, and must begin/end on token boundaries. BOS, EOS, newline and every other control byte are forbidden **inside anchor spans**: anchors represent factual content, not sentence/turn framing. Candidate A permits at most two spans; factual record types admitted for factual-answer use must carry at least one. The anchor plan does **not** copy those bytes: it stores only bounded `(winner_slot, payload_offset, encoded_length, progress)` descriptors inside generation/scoring state. The two complete winner slots remain live until response generation finishes, and required anchor bytes are copied directly from the referenced winner into the response buffer. This preserves anchors without inventing an unbudgeted duplicate buffer.

Cold payloads use the same canonical lexical/literal encodings as conversation text. Candidate-A payload controls are limited to BOS, EOS and newline; user-turn, assistant-turn, turn-end, `0x00`, reserved wire controls and unknown escapes are forbidden inside a knowledge-record payload.

Host tooling rejects records shorter than the header implied by their counts, over 192 logical bytes, with trigger_count above four, anchor_count above two, unknown record types, invalid semantic refs, triggers above 4095, forbidden/reserved payload controls, malformed literal escapes, anchor spans outside the payload or off token boundaries, control bytes inside anchors, overlapping anchors, or payload parsing that does not consume exactly the declared record. Payload-only wording need not consume resident dictionary bytes.

Record types are expected to distinguish factual statement, biographical fact, game/software fact, hardware/architecture fact, chronology fact, comparison relation, and conversational/domain phrase material. Exact numeric IDs are not frozen until corpus construction begins.

### 9.4 Candidate model container

The logical cold-model stream begins with a compact header and sequential section directory. Candidate magic is `A48M`; release version numbering and the exact target integrity algorithm remain to be frozen after the first packer/parser prototype.

ZX-UX v1 exposes RAM-object logical/storage lengths and seek offsets as u16 values. Consequently each Candidate-A cold model object has a hard logical length of at most 65535 bytes. If later measurements require sharding, **each shard** independently obeys that bound and its resident physical allocation is budgeted. A PACKED resident object must also satisfy REV12's requirement that physical `storage_length` is strictly smaller than its logical length and must fit the real arena allocation.

The container shall declare at least format version, feature flags, resident-vocabulary identity, a fixed-size hot/cold **interface identity**, record count, logical length and section lengths. The interface identity is generated from the canonical lexical-ID map, topic-ID map, semantic-symbol map, relation/record schemas and scoring-feature schema; target code compares the fixed bytes before accepting records. This prevents a cold object from a different build from being interpreted under merely similar vocabulary. Host provenance additionally records SHA-256 of the full interface description; the exact compact target identity width is frozen with A48M. Host tooling validates all sums/counts in widened arithmetic, rejects any stream whose mathematical layout exceeds the u16 target object/seek domain, and only then emits narrowed fields. Target validation uses subtraction/reordered comparisons so 16-bit wrap cannot turn an invalid layout into a valid one.

The target model includes an incremental integrity check suitable for the Z80/C48 implementation. Before record scoring, the target validates the A48M header/version/declared lengths, requires actual object logical length == declared logical length, and checks resident-vocabulary plus hot/cold-interface identities. Every complete cold scan then validates section boundaries, exact declared record count, structural bounds and the requirement that the last declared section/record ends exactly at logical length while accumulating the integrity check over the canonical protected bytes. No selected cold record may reach response generation until the scan has reached the declared logical end and the integrity result matches. Thus the first question also performs full model validation without requiring an extra unbudgeted startup copy/scan; later scans retain the same fail-closed check unless a separately proved immutable-object optimization replaces it. Host release tooling also records SHA-256 for reproducibility. SHA-256 is not imposed on the target merely because the host can calculate it cheaply.

### 9.5 Candidate variable-order language model

Candidate A uses pruned variable-order token continuation statistics with maximum order three:

- unigram fallback for general English/token priors;
- bigram transitions for common local syntax;
- trigram transitions only where training evidence and byte/value measurements justify them.

The host trainer quantizes continuation likelihoods into small integer ranks/scores. Low-value transitions are pruned under an explicit byte budget. **Every serialized continuation context, including the unigram fallback, carries at most 12 learned continuation candidates in Candidate A.** The controller may inject at most two obligatory legal factual-anchor candidates, so one generation step evaluates no more than 14 candidates.

Hot transition contexts are sorted and directly addressable. Candidate A uses bounded binary lookup rather than scanning the complete transition table for every output token. A trigram key is compared lexicographically as two u16 context refs; it is never packed into a nonexistent C48 `long`. Literal-class refs from Section 7.3 may appear in lookup context keys and back off normally when no learned higher-order context exists; they are forbidden in learned continuation lists. BOS/user-turn/assistant-turn/turn-end refs are likewise context/controller state rather than learned output candidates.

The hot LM is not required to memorize Spectrum facts. Facts are supplied by selected cold records. This separation allows factual knowledge to grow in a compressible sequential representation without making every next-token decision scan the whole cold model.

Candidate reports include total hot-transition bytes, number of contexts by order, maximum/mean continuation fanout, lookup-comparison counts, fallback frequency and quality/latency ablations. The 12-candidate cap is a Candidate-A measurement point, not a frozen release ABI.

### 9.6 Why Candidate A is not merely a template chatbot

A factual record can anchor names, dates and relationships, and a compact response mode may provide sentence boundaries or obligatory fact tokens. Normal wording between/around those anchors is selected using learned token-continuation scores and current conversation state.

A candidate build shall include ablation tests. If replacing the learned continuation table with a fixed deterministic word list produces essentially identical normal responses, the supposed LM is not doing enough work and the candidate fails the project definition.

## 10. Runtime memory budgeting

No release memory claim is frozen until the real compiled C48/MEX1 artifact and model are measured. The budget is nevertheless accounted in named simultaneous categories from the first prototype:

```text
process image/text + immutable resident lexicon/hot model tables
process BSS total, including workspace and any fixed C48 heap reserve
MEX1 minimum_stack_size plus REV12's additional 64 bootstrap bytes
ARG1 + ENV1 process bootstrap allocation and alignment
external cold-model resident physical storage + allocator alignment
272-byte PACKED-reader state for each independent packed model handle
optional pre-budgeted target L3 physical storage
shell and other simultaneously resident process allocations/stacks
pinned/system arena resources
allocator fragmentation / placement-class safety margin
```

The workspace and configured heap are reported as BSS subdivisions and are never added a second time on top of measured total BSS. The simple total is a **necessary but not sufficient** invariant:

```text
all simultaneous arena consumers + required safety margin <= 32768 bytes
```

REV12 also requires placement classes and contiguous extents. Release evidence must therefore prove the actual allocation sequence succeeds with image+BSS `ANY`, process stack `FAST_REQUIRED`, object-store placement, two-byte alignment and the measured fragmented free map. Total free bytes cannot rescue a required allocation when the largest legal extent is too small or FAST space is exhausted.

The build/evaluation harness rejects a candidate that violates either the total-byte equation or the class/extent allocation proof, even if a host-side simulation with a flat byte counter appears to work.

### 10.1 Candidate-A engineering targets

Before measurement supplies better numbers, Candidate A aims for:

- 4,336 bytes fixed conversation/context workspace;
- zero C48 heap for the initial target implementation;
- no arbitrary release stack target: begin measurement from the canonical linker default `minimum_stack_size` of 512 bytes, test native high-water/canaries and call-depth stress, then select the smallest safe even value in REV12's 64..4096 range with an explicitly justified safety margin; the allocator always consumes that chosen value plus REV12's mandatory 64 bootstrap bytes;
- low-single-digit-KiB resident lexicon/hot model tables only if measured tables really meet that goal;
- one or a very small number of separately resident cold model objects, PACKED only when physical bytes are materially reduced;
- exactly one cold-model read handle during normal Candidate-A inference;
- target L3 disabled by default;
- several KiB of measured total-arena headroom **and** safe largest-extent/FAST headroom under the actual ordinary launch configuration.

These are engineering targets, not release promises. A candidate that cannot leave safe allocator headroom is rejected or made smaller even if its conversational score is higher.

### 10.2 Memory evidence

Every retained model candidate publishes a machine-readable memory report containing at least compiled SDK artifact identity; eventual MEX1 image/text/BSS sizes and symbol/map evidence; configured heap; MEX1 minimum stack and actual +64 allocation; native stack canary/high-water result; ARG1/ENV1 bytes; the 4,336-byte workspace; resident lexicon/hot-table bytes; external model logical/physical/aligned bytes; packed-reader states; optional L3 quota; shell/other process allocations; pinned resources; observed arena peak; the address-ordered free-extent map; FAST and CONTENDED free totals; largest legal `ANY` extent including a permitted 0x7FFF/0x8000 crossing; largest `FAST_REQUIRED` extent; actual `COLD_PREFERRED` placement/fallback; and final headroom after replaying the real load/launch allocation sequence.

The host C48 VM is not evidence for native Z80 stack high-water or ZX-UX allocator fragmentation. Those claims require the native/Fuse path and, for final hardware claims, a physical 48K run.

The phrase "fits in 48K" is not sufficient evidence.

## 11. Response pipeline

A normal turn is a bounded transactional pipeline:

```text
read bounded line
  -> normalize/tokenize completely into current-turn encoded scratch
  -> reject lexical/encoded overflow before mutating context
  -> detect q/commands
  -> score topic + intent + salient entities
  -> retrieve L1/L2 conversational-memory indices
  -> seek cold model to zero and perform one bounded forward scan
  -> retain at most two complete cold records
  -> choose response mode and obligatory factual anchors
  -> generate complete canonical response into encoded response buffer
  -> validate anchors, repetition, token ceiling and decoded byte ceiling
  -> preflight bounded no-mutation context commit using scratch overlay
  -> stream detokenization through the real tty path
  -> apply fixed-memory L0/L1/L2/session-literal commit
  -> update diagnostic evidence / optional quota-bounded L3 archive
```

Every stage has a fixed maximum input/output size. Optional-stage failure falls back to a documented simpler response path rather than overrunning memory. A response-generation overflow is detected before partial answer text is printed; the controller may substitute a known-small bounded uncertainty/error response.

The controller may choose a direct factual explanation, comparison, historical answer, architecture answer, conversational continuation, clarification request, bounded uncertainty response, or another measured mode. The controller must never invent remote capabilities or hidden access to information outside the shipped model/context.

### 11.1 Candidate knowledge retrieval score

The first retriever uses only integer additions/comparisons. Candidate features include exact topic match, entity/session-literal match, trigger-token overlap, question/intent compatibility, current conversational-memory reinforcement, and record importance. No runtime floating point is needed.

Candidate-A retrieval and continuation-adjustment arithmetic uses signed 16-bit C48 `int`. Before a model/configuration is emitted, host tooling calculates widened mathematical minima/maxima for every legal feature/candidate combination and rejects weights or penalties whose intermediate or final sum can leave -32768..32767. Target code follows a frozen addition order, so host and target never depend on accidental 16-bit wrap for ranking.

The host reference implementation calculates the same integer score byte-for-byte. Any future improvement that uses a different host-only formula without a target equivalent is not a valid target model improvement.

### 11.2 Candidate generation policy

Candidate A generates at most 80 canonical output tokens, at most 255 encoded response bytes inside the 256-byte buffer, and at most 383 printed ASCII bytes for one answer. All three ceilings apply independently. Before accepting a token/literal, the generator proves that its encoded bytes and eventual spelling/literal bytes still fit the remaining limits.

At each step the generator evaluates no more than the Section-9.5 bound of 12 learned candidates plus two controller-injected factual-anchor candidates. The highest adjusted score wins; ties use ascending canonical token/reference order. Adjustments include repetition penalties, obligatory fact-anchor progress, response-mode legality, and end-of-sentence preference near the length ceiling.

There is no unbounded beam. A tiny alternative/backtrack slot may be evaluated later if measurements show a quality win, but its byte and candidate-count ceiling must be added explicitly before adoption. The baseline is one active encoded output path plus bounded candidate scratch.

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
Copyright (c) 2026 Supratim Sanyal

I am ailmzx48.
I know a bit about the Sinclair ZX Spectrum —
which is fortunate, because I appear to be living inside one.

48K seemed enormous in 1982. I have opinions about that now.

Ask me about the Spectrum, or just have a chat.
Enter q at any time to quit.

>
```

The humor is retained. The interactive startup does not print the repository's source/document attribution sentence. The project license requires that attribution in source-level documentation instead. Startup text uses an ASCII copyright line; any future decorative non-ASCII glyph must have an explicitly supported target encoding or an ASCII-safe replacement. The C48 source must not rely on a host editor/compiler accidentally accepting Unicode.

At the start of every normal conversational input turn, immediately before the prompt becomes input-ready, `ailmzx48` emits a short approximately 0.5-second `beep()` cue. Candidate-A bootstrap uses pitch offset `0.0`; exact release pitch may change after terminal/audio testing. Audio-backend unavailability in the host SDK is non-fatal and is never used as the conversation framing signal. The harness records the target-visible beep-call counter separately from logical tty bytes.

### 13.2 Input

`ailmzx48` owns its application input loop after launch. It uses a bounded line buffer and normal ZX-UX tty services; it does not depend on the shell retaining the conversation line for it.

Candidate A reserves 192 bytes and accepts at most 191 printable ASCII input bytes before the terminating NUL. `ai_readline` tracks an explicit byte count while reading; NUL and other non-line control bytes are rejected **before** they can become C-string content, so neither `strlen` nor tokenization can mistake embedded NUL for a shorter valid line. CR and LF are accepted line terminators. A CR sets a one-byte `drop_lf` state for the next read: if the next byte is LF it is discarded, otherwise that byte begins the next line. This collapses CRLF without a look-ahead read that would create a false harness boundary.

Overlength or control-invalid raw input is drained/rejected to the next line terminator without context mutation. A raw line that fits but violates a literal-span limit from Section 7.4 or expands beyond 319 encoded bytes is likewise rejected before context mutation. Silent text or semantic truncation is not acceptable.

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
- C48 `putchar()`/`puts()` update `ZXScreen`, preserving the SDK Spectrum terminal semantics;
- `--max-steps` provides a deterministic runaway-execution ceiling;
- the VM exposes globals and memory internally to SDK-host tooling, enabling diagnostic inspection without changing target responses.

Forensic Review Pass 1 also found an important current-SDK limitation: the host VM builtin surface does **not** yet expose the ZX-UX `open`/`read`/`seek`/`close` object-I/O path needed by Candidate A's external cold model. Therefore a host conversation that only embeds the cold model in Python or directly pokes VM memory is not an end-to-end test of the target storage interface.

Before external-model SDK conversations count as target-interface regressions, the SDK/harness must gain a reviewed, tested read-only object-I/O adapter that lets the same C48 source call the canonical interfaces against registered model fixture bytes. It must fail with target-like bounds/errors, support deterministic positive short-read injection and premature-EOF/error cases, expose the fixture's actual logical length to the C48 path, and must not become a hidden alternate inference path. A RAW fixture adapter can validate parser/retriever logic; claims about ZXP1 decoder state, packed seek cost, allocator placement or cassette behavior still require their native/architecture-specific tests.

The other missing feature is exact logical terminal-stream capture. The baseline harness adds that **outside the C48 program semantics** rather than making the target program print test protocol noise.

### 14.1 Harness architecture

The initial harness lives under:

```text
usr/src/ailmzx48/tooling/
```

It imports the SDK VM classes directly and supplies:

- a queued byte `input_provider` that distinguishes queued-byte consumption from a **queue-empty demand** for another byte; only queue-empty demand is a conversational synchronization boundary;
- a tracing `ZXScreen` subclass/wrapper whose `putchar()` records the same logical byte it then passes to the real screen implementation;
- the reviewed read-only model-object adapter required above before external-model runs are called end-to-end SDK tests;
- an explicit VM heap setting equal to the candidate configuration (`heap_size=0` for the initial zero-heap target), never the host VM's convenient default; this catches accidental `malloc` dependence even though it does not certify native BSS placement;
- optional VM-global inspection helpers for named `ailmzx48` diagnostic counters;
- deterministic maximum-step, per-turn progress and output-size guards.

Because SDK `puts()` ultimately calls the same `ZXScreen.putchar()` path, the tracer observes both output routes while still exercising production wrapping/scrolling. The tracing layer must never reimplement the terminal renderer.

A future general-purpose SDK `--tty-log PATH` option may be useful, but `ailmzx48` does not require changing the public SDK CLI merely to begin testing.

### 14.2 Human-emulation protocol

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

The baseline runner is deterministic. A development-time modern LM may later act as an adaptive human-like interlocutor/reviewer, but deterministic scripted/adversarial suites remain mandatory so a model change can be reproduced without an external service.

### 14.3 Transcript and run identity

Every retained run records:

```text
source commit
C48 compiler/runtime version and relevant hashes
ailmzx48 source hash and compiled C48B1 artifact hash
model build-manifest hash plus SHA-256 of every generated hot/cold model artifact
compact hot/cold interface identity embedded in the tested artifacts
configured SDK heap value and target heap/link settings
scenario id/hash
runner/tool hash
upstream ZX-UX authority commit and hashes of REV12/REV03 bytes
C48 Rev-0.11 DOCX SHA-256
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

The C48 program may expose small diagnostic scalar globals. All target names obey the Rev-0.11 15-character identifier limit; Candidate-A names include:

```text
ai_turns
ai_l0bytes
ai_l1count
ai_l2count
ai_compact
ai_l2evict
ai_l1drop
ai_litloss
ai_mrecords
ai_mhits
ai_otokens
ai_yields
ai_encfail
ai_error
```

The SDK harness can inspect these through the VM's global/memory model after an input-request boundary without printing them to the Spectrum terminal. Native ZX-UX verification can later expose equivalent counters through a diagnostic build if needed.

Correctness may not depend on the host being able to inspect these globals. They are instrumentation, not a hidden control channel, and their bytes are charged to the guards/counters portion of the workspace ledger.

Counter width/epoch is explicit so a long run cannot wrap into fake good news. `ai_l0bytes`, `ai_l1count`, `ai_l2count` and `ai_error` are instantaneous state. `ai_compact`, `ai_l2evict`, `ai_l1drop`, `ai_litloss`, `ai_mrecords`, `ai_mhits`, `ai_otokens`, `ai_yields` and `ai_encfail` are unsigned-16 per-input-attempt counters reset before each attempt; their Candidate-A per-attempt maxima are proved below 65536 and the host aggregates them. `ai_turns` is a saturating unsigned-16 accepted-turn count; the harness transcript count is authoritative beyond saturation.

### 14.5 Context-specific long-conversation tests

Long-conversation tests deliberately place important facts at increasing turn distances, push them out of L0, force L1 compaction into L2, and then ask questions whose correct answers depend on those facts.

Tests separately prove that the recent canonical token sequence remains available inside the declared L0 horizon; source-byte quotation is claimed only when an exact transcript source exists; old semantically important facts survive compaction; low-value chatter can be forgotten safely; later corrections supersede older state according to the documented rule; repeated compaction never grows the fixed workspace; and conversations far longer than L0 complete without memory corruption.

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
CONTEXT_LITERAL_LOSS
L2_EVICTION
EVAL_LEAKAGE
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

Every admitted corpus source receives a host-side record containing at least source identifier/title, exact provenance/location, license/authorization basis and scope, acquisition date, source-byte hash where applicable, extraction/transformation tool version, normalized-output hash, train/dev/evaluation split assignment, and the generated fact/training records that depend on it.

The manifest also records exclusions/withdrawals so a later rebuild can prove that disallowed material no longer contributes to a generated model. Derived facts or conversational records retain source-lineage IDs through aggregation; a final packed target record need not carry bulky citations, but the host build graph must be able to trace it back to admitted sources.

No arbitrary web scrape is admitted merely because the text is easy to fetch.

### 16.2 Repository-license boundary

The ZX-UX C48 SDK repository and upstream ZX-UX project are canonical **design authorities** for this implementation. Their license text explicitly restricts use for AI/ML model training unless separately authorized. Therefore their prose/source is not automatically part of the `ailmzx48` training corpus.

This design may read those documents to implement correct ZX-UX/C48 behavior. Training the conversational model on their textual content requires the separate express written authorization required by the repository license or a user-authored/otherwise permitted factual corpus. Merely placing text, generated conversations, extracts, or model-building inputs under `usr/src/ailmzx48/training/` does not grant training permission: every admitted item still needs an independent manifest basis that permits the intended AI/ML use, and any item whose only governing permission is the root SDK license is excluded from training. Design authority, repository location and training permission are three different questions.

### 16.3 Train/dev/evaluation separation

The tooling maintains explicit, content-addressed partitions for training, development/tuning, deterministic regression and blind evaluation. Exact transcript exclusion alone is not enough: near-duplicate prompts, paraphrased fact templates and source-derived question/answer pairs are grouped so one semantic item cannot casually leak across a claimed blind boundary.

Regression cases are allowed to become known to developers and are used to prevent old failures returning. Blind-evaluation cases are different: once a blind result is inspected closely enough to motivate a corpus, controller, pruning or prompt-specific change, that case is retired from the blind set and a new held-out case replaces it. A score repeatedly optimized against the same inspected set is development evidence, not blind generalization evidence.

Some closed-book facts deliberately exist in the knowledge store because factual retrieval is part of the model architecture. Evaluation therefore labels retrieval/fact availability separately from linguistic generation and asks held-out phrasings/relations rather than pretending the system was never allowed to know a shipped fact.

### 16.4 Synthetic/generated conversation material

If a modern model or scripted generator creates development conversations, every generated batch records generator/model identity, version where available, exact prompt/configuration or deterministic seed, generation date, license/authorization basis for using its output, review/admission status and corpus split. Synthetic conversations used for failure mining or tuning cannot later be reported as untouched blind evaluation.

Generated material is never silently promoted into factual truth. Factual records require their own admitted provenance or explicit user-authored authority.

## 17. Evaluation and convergence

Evaluation has hard gates and quality scores.

### 17.1 Hard failures

Any of the following rejects a candidate regardless of conversational charm:

- out-of-bounds memory access or guard corruption;
- arena total-byte, placement-class or contiguous-extent allocation proof failure;
- model parser accepting a malformed unsafe record;
- an unadmitted source or source lacking the recorded authorization/license basis contributing to training/model bytes;
- infinite/unbounded generation;
- failure to terminate on `q`;
- deterministic regression that cannot be reproduced from retained identities;
- target behavior that requires a remote LM/service;
- false claim of verbatim/source-byte recall where exact source bytes are not retained;
- known factual anchor mutated into a contradictory value;
- a repository/tooling change that weakens an existing SDK verification gate merely to accept the candidate.

### 17.2 Scored dimensions

The evaluation suite separately reports, rather than hiding behind one number:

- Spectrum-domain factual accuracy;
- answer relevance;
- conversational fluency;
- repetition/degeneration rate;
- recent canonical-token context recall;
- distant semantic-context recall;
- correction handling;
- uncertainty behavior;
- response diversity across prompts;
- target work/latency;
- model logical and physical bytes;
- total/peak memory and headroom.

A composite score may be useful for ordering experiments, but the component table remains canonical evidence.

### 17.3 Convergence rule

No iteration count or numerical plateau threshold is invented before baseline evidence exists. After baseline variance and target runtime are measured, the project freezes a convergence protocol **before** using it to declare success. That protocol names the primary dimensions, allowed regression margins, minimum number of consecutive accepted no-material-gain rounds, blind-evaluation cadence and target memory/latency ceilings.

A candidate round is accepted only if all hard gates pass and no predeclared critical dimension regresses beyond its frozen allowance. Improvement is assessed on the component table rather than a single composite score. Deterministic suites must reproduce byte-for-byte under the same identities; adaptive/generated suites record their seed/model/configuration so variance is explicit rather than mysterious.

Blind evaluation is used as milestone evidence, not an endlessly tuned scoreboard. If its failures drive the next change, those cases become regression/development cases and fresh blind cases replace them.

Development continues while failure mining identifies changes that materially improve important dimensions within the byte/latency budget. Convergence may be declared only after the frozen consecutive-round rule is met, manual transcript review agrees, and remaining failures are documented as capacity/model-class/byte-cost limitations rather than obvious unfixed corpus, retrieval, context or controller defects. The numerical values remain open until baseline measurement can justify them.

## 18. Cassette and real-machine workflow constraints

The final release workflow must be derived from canonical REV12/REV03 cassette, object, compiler, linker and shell behavior. It may not invent a disk-like filesystem or assume the host SDK exists on the physical Spectrum.

Two user-facing cassette roles are planned:

1. a **source/development tape** containing material needed to inspect/build `ailmzx48` using native ZX-UX development tools;
2. a **runtime/distribution tape** containing the ready-to-run executable and model resources arranged for low-memory loading/execution.

The exact physical M48O order is not frozen yet.

### 18.1 What is already known

ZX-UX native C48 compilation and linking are ordinary program activities; the compiler is not architectural permanently resident kernel state. `SYS_EXEC` is a real process-image replacement operation. ZX-UX tape facilities include save/load/verify/scan semantics, and REV12 provides a direct tape-backed MEX1 execution path that can decode a RAW or ZXP1 executable directly into its final process allocation rather than require a second resident executable copy.

That direct tape-backed path solves an **executable-copy** problem. It does not turn Candidate A's repeatedly scanned cold knowledge into a random-access cassette resource. In the baseline runtime, the cold model must already exist as one or a few resident ZX-UX RAM objects before normal inference, optionally PACKED. Their physical bytes and any 272-byte decoder states consume the same arena as the running process.

Therefore a reboot is not inherently required merely to "unload the compiler". The actual memory problem is the complete set of still-live process allocations and RAM objects after the build: shell/tool processes, source, OBJ1, final executable object, model objects, temporary files and pinned/system state. A future proposal to stream knowledge from cassette during every answer would be a different, heavily blocking sequential-storage design and requires separate proof rather than being smuggled into the word "external".

### 18.2 Operator Build Overview

The release operator has two conceptual build paths. Both begin from an exact accepted source/model identity and both must preserve the same runtime interfaces, memory limits, provenance records and release gates.

For the **host/SDK build**, the operator starts from a clean repository `main` plus an admitted, content-addressed corpus/provenance snapshot. Deterministic host tooling builds the resident vocabulary/topic/semantic maps, bounded hot LM tables, cold A48M knowledge object(s), interface identity and model manifest. The portable repository C48 toolchain compiles `ailmzx48.c` into the deterministic SDK C48B1/VM form and produces the runnable SDK artifact under `usr/bin/ailmzx48/ailmzx48.c48b`. That host artifact is explicitly not OBJ1, MEX1 or Z80 machine code. Host tooling also emits the accepted model resources/manifests that feed native packaging. Host format tests, active SDK conversations, model/interface checks, `MANIFEST.sha256`, `git diff --check` and the complete SDK release verifier must all pass before those identities can feed the native release build.

For the **native-on-ZX-UX build**, model training is not repeated on the Spectrum. The operator boots canonical ZX-UX, loads the source/development tape containing the native C48 toolchain, `ailmzx48` source and already-generated accepted model resources, compiles the source to the canonical native object form, links the MEX1 image with measured heap/stack settings, verifies the resulting executable/model objects using documented target facilities, and saves the accepted runtime objects to cassette. Build-only source/tool/intermediate RAM objects are then reclaimed through supported ZX-UX semantics before runtime memory proof. Host and native builds must use the same frozen source/model/interface contracts; byte-identical executables are claimed only if measurement proves them, otherwise retained hashes plus behavioral/native verification identify each accepted build.

Packaging is the final operator step, not an inference step: the accepted native MEX1 executable from the native build path and the required accepted model resource(s) form the runtime/distribution tape, while source, native build inputs and development tools belong on the source/development tape. The SDK C48B1 artifact remains a host/SDK deliverable and is never mislabeled as a Spectrum executable. Exact M48O order, target object names and final commands remain subject to the proof sequence below rather than being invented here.

### 18.3 Independent Installation Overview

Ordinary installation/use starts from a clean 48K-compatible machine that can boot the canonical ZX-UX system tape and from an accepted `ailmzx48` runtime/distribution tape. The user does **not** need the C48 compiler, source/development tape, host SDK, training corpus or model-building tools merely to install and run the released program.

The runtime tape contains the prebuilt MEX1 executable plus every required cold-model/resource object and the release identity information needed by the documented verification flow. After boot, the user enters the normal ZX-UX shell session, scans/loads or directly executes the runtime objects only through the cassette/object operations actually provided by ZX-UX, and verifies the loaded objects with documented tape/object metadata checks. The normal launch path must leave the required model object(s) resident in the form expected by `ailmzx48`; launch-time A48M length/interface/integrity validation remains mandatory before model records can influence an answer. Exact target names, directories, commands and tape ordering are deliberately deferred until native proof freezes them.

A successful launch presents the normal startup conversation. Entering exact `q` at a normal input prompt terminates the program cleanly and returns control according to the proven ZX-UX launch path; no hidden daemon or background model service remains resident. Process allocations, stack and open-description/decoder state are released by normal close/exit semantics.

"Uninstall" on ZX-UX primarily means reclaiming the volatile runtime objects after `ailmzx48` has exited and all relevant handles are closed. Mutable executable/model RAM objects are removed only through supported object-removal semantics; pinned/system resources are never treated as application files. Removing RAM objects does not erase their cassette copies, because cassette is sequential persistent media rather than an in-place deletable filesystem. A distribution tape that should no longer contain `ailmzx48` is replaced/recreated without those objects rather than being described as having an in-place uninstall operation. Memory/extent evidence after reclaim must show that the application's arena allocations are actually gone.

### 18.4 Required final proof sequence

Before user documentation claims an exact command sequence, the native implementation must prove the following on a 48K configuration:

1. boot ZX-UX from the canonical system tape;
2. load the native C48 toolchain/source inputs actually required;
3. compile `ailmzx48.c` to the canonical native object form;
4. link the MEX1 executable with measured stack/heap values;
5. save the executable and required model resource(s) to cassette;
6. reclaim build-only RAM objects through supported commands/semantics;
7. return to a state with enough total, FAST and contiguous arena space for the runtime configuration;
8. load the model resource(s) into resident RAM-object form, packing only through documented ZX-UX behavior when it improves the measured physical budget;
9. load or directly tape-execute the MEX1 executable using only documented operations;
10. open the model in the exact normal read configuration and prove process + shell/system state + model physical bytes + every decoder state coexist with required allocator headroom;
11. hold a multi-turn conversation that performs repeated model scans, exercises context compaction and quits cleanly.

Every stage records `mem`/equivalent evidence including FAST/CONTENDED totals and largest extents where available. The final manual explains not only that the sequence worked once, but why its allocation order is valid.

### 18.5 Compiler/linker lifetime question

The final manual must distinguish process lifetime from stored tool/source objects. A completed `cc` or `ld` process no longer needs to occupy its former process allocation, but resident source/object/executable/model data can still consume the shared arena.

The user should not be told to "unload C48" unless ZX-UX actually has a command with that meaning. The documentation will instead name the real objects/processes to remove or the real process-image transition to perform.

### 18.6 Reboot fallback

If measurement proves that a clean post-build runtime state cannot be reached conveniently without bootstrapping again, the release may document a reboot/reload workflow. Reboot is a valid engineering answer; an invented unload command is not.

The design preference is to avoid reboot if supported cleanup/direct execution makes that unnecessary, but correctness and understandable tape instructions outrank elegance.

## 19. Phased implementation order

Implementation begins only after enough of this design is frozen to prevent incompatible model/context/harness work. The current intended order is:

1. canonical-authority identity/extraction verifier for REV12, REV03 and the actual C48 Rev-0.11 DOCX, plus repository release-gate checks;
2. corpus provenance/split format and small hand-audited seed corpus;
3. Candidate-A tokenizer, resident recognition/presentation lexicon and token statistics;
4. host reference L0/L1/L2/session-literal compressor/retriever with adversarial long-conversation tests;
5. cold knowledge-record builder, frozen relation/semantic-reference schemas, anchor-span validation and sequential two-winner retrieval benchmark;
6. pruned bounded-fanout order-1/2/3 hot language-model trainer, quantizer and widened score-bound proof;
7. frozen experimental A48M container plus host packer/verifier with u16 target-limit and hot/cold-interface-identity mismatch tests, including changed topic-ID assignments;
8. reviewed SDK read-only object-I/O adapter/conformance tests needed for the external model fixture;
9. minimal C48 `ailmzx48` program that prints startup text, reads bounded input and handles `q`;
10. target tokenizer/detokenizer, 4,336-byte workspace and session-literal logic;
11. target L0/L1/L2 compaction/retrieval with counters, guards and loss instrumentation;
12. cold model reader/sequential scorer using bounded short-read-safe reads/yields, exact object-vs-header length/count validation and at most two winners;
13. hot LM lookup/generator and factual-anchor controller;
14. anti-repetition, uncertainty and response-mode integration;
15. SDK active conversation harness with traced output, input-request framing, object fixture and global telemetry;
16. long GitHub-runner conversation workflow and retained artifacts;
17. repeated corpus/model/controller/context training/evaluation cycles under frozen split/convergence rules;
18. native ZX-UX memory/stack/allocator/tty integration and Fuse evidence;
19. physical 48K cassette/runtime verification;
20. final source/runtime tape packaging, exact native build/save/load transcript and certification evidence.

Each phase preserves a working, release-verifiable repository state on `main`. New target C/H files obey the <=64-column and <=15-character-identifier rules from the moment they are introduced. Model sophistication is never allowed to outrun memory-safety, provenance and reproducibility evidence.


### 19.1 Bootstrap vertical slice and runner bound

Implementation is allowed to cross several later phases with a deliberately
tiny smoke implementation before claiming those phases complete. The first
vertical slice may embed a learned micro-model in generated C48 data solely to
prove deterministic model construction, C48 compilation, SDK conversation
framing, telemetry and durable transcript retention. It is not the release
substitute for the external A48M cold-object path; the read-only object-I/O
adapter and normal hot/cold split remain required before external-model SDK
regressions count as target-interface evidence.

Every individual GitHub-hosted ailmzx48 active training/evaluation
session is bounded to at most 20 minutes (1,200 seconds). The enclosing runner
job has separate bounded finalization headroom; the baseline workflow uses a
30-minute job timeout so a full 20-minute session can still finalize artifacts,
regenerate `MANIFEST.sha256`, run the full SDK release verifier and
`git diff --check`, and commit/push the result. A completed iteration is not
disposable runner state: its model candidate, exact conversation transcript,
run metadata and score report form one atomic iteration checkpoint and must be
committed together to `main` before a later iteration begins.

## 20. Candidate-A implementation interfaces

Revision 0.12 keeps conceptual target interfaces deliberately within the C48 Rev-0.11 identifier limit:

```text
ai_readline()     bounded byte-aware tty line input
ai_tokenize()     accepted ASCII line -> canonical encoded tokens
ai_detok()        one canonical token/literal -> tty bytes
ai_classify()     read-only intent/topic/entity/literal lookup
ai_memget()       top L1/L2 record indices
ai_modelscan()    one forward cold scan, at most two winners
ai_plan()         response mode + factual anchors
ai_generate()     deterministic bounded LM continuation
ai_ctxcheck()     no-mutation bounded context-commit preflight
ai_ctxcommit()    replay preflighted fixed-memory context commit
ai_print()        validated streaming tty output
```

Exact signatures are not frozen. Every target function remains within the canonical argument-count/type rules, receives explicit buffer pointers/capacities where needed, and uses no function pointers or unsupported aggregate types. Candidate A uses no recursion in the inference path. Large automatic arrays are prohibited; persistent and sizeable scratch arrays are named globals charged to Section 8.7. Every shipped C/H source line remains <=64 characters.

### 20.1 Error-state discipline

A single small error/status value records the first hard turn failure. Functions return status rather than relying on undefined state after malformed input/model data.

Recoverable cases include no matching knowledge record, raw/encoded input rejection, optional transcript unavailable, low retrieval confidence, exhausted/reused session-literal capacity, or a safely degraded stale semantic reference. Fatal session cases include model container corruption discovered during validated access or internal guard failure.

A recoverable semantic loss is counted and must never be repaired by reading uninitialized/stale bytes or inventing the missing spelling.

### 20.2 Bounds arithmetic

All target length additions are written so a 16-bit `int` cannot wrap into a passing bounds test. The host model packer/verifier performs the same checks in widened arithmetic and generates only target-safe lengths.

Where a target expression would need a 17-bit intermediate to prove safety, the C48 implementation uses subtraction/reordered comparisons or explicit high/low reasoning rather than relying on nonexistent `long`. Model-object/seek offsets never exceed the u16 domain established in Section 9.4.

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

1. What are the compiled C48 and native MEX1 image/text/BSS sizes?
2. What is the exact 4,336-byte workspace map, BSS total/subdivision accounting, heap reserve, measured MEX1 minimum stack, actual +64 stack allocation and native stack high-water?
3. What raw-input patterns hit the 191-byte, lexical-span or 319-byte encoded-turn rejection bounds, and are all rejected without state mutation?
4. How many canonical-token L0 turns/tokens fit in 896 bytes for real conversations?
5. How much source-equivalent history do 48 L1 capsules, 24 L2 records and eight generation-checked session-literal slots preserve at measured recall quality?
6. How often are session literals/L2 facts evicted and how does that affect old-name/correction recall?
7. What resident recognition/presentation vocabulary minimizes total lexicon + hot-LM + cold-literal cost while still covering every retrieval trigger?
8. What variable-order pruning/fanout budget gives the best fluency per resident byte and per target lookup cost?
9. How large is each cold knowledge object logically and physically after ZXP1 packing, within the u16 object limit, and do object/header length mismatches, short/premature reads and mismatched hot/cold interface identities—including changed topic-ID maps—fail before record use?
10. How long does one complete cold scan take in SDK work units, Fuse/cycle evidence and a real 48K run?
11. Is one full scan per turn acceptable, or does RAW indexing, topic sharding or a resident cache win after all byte/decoder/fragmentation costs are counted?
12. Does the SDK object-I/O adapter produce the same logical parser/retrieval results as the native RAW path, without being misrepresented as PACKED/cassette certification?
13. What address-ordered free map, largest legal ANY extent, largest FAST_REQUIRED extent and actual COLD_PREFERRED placement/fallback remain with shell/system state, ARG1/ENV1, model object and decoder alive in the real launch order?
14. Which Spectrum factual categories remain weak after corpus saturation?
15. Does any quality improvement require enough bytes or latency to make the ordinary runtime configuration unsafe or unpleasant?
16. What is the longest retained semantic dependency demonstrated by an actual transcript, not a synthetic byte count, and does a retained stress transcript exceed 32 KiB of raw source dialogue without pretending those raw bytes remain live?
17. What frozen train/dev/regression/blind split and convergence protocol supports the final model-selection claim?
18. At convergence, what failures remain and why are they intrinsic or not worth the byte/latency cost to fix?

The final design replaces these questions with measured answers.

### 22.1 Revision-0.26 measured SDK answers and release-profile boundary

The acceptance questions above are now classified by evidence scope rather
than left as an undifferentiated to-do list.  The durable machine-readable
source of this classification is
`evaluation/DESIGN-COMPLIANCE-STATUS.json`.

For the **SDK implementation profile**, retained measurements establish the
following: the shipped SDK artifact is C48B1 and is never mislabeled as native
OBJ1/MEX1/Z80 code; the active runner uses zero C48 heap; L0 is bounded to 896
bytes/32 descriptors, L1 to 48 x 16-byte capsules, L2 to 24 x 16-byte records,
the session-literal store to 272 bytes/eight generation-checked slots, and the
decoded LM-context ring to 96 u16 entries; the cold A48M object is 8432 logical
bytes with 69 records, a 64-byte maximum read request and a 192-byte maximum
record; the host context oracle has retained a 500-dialogue/51000-source-byte
stress while fixed capacities remained bounded; the post-repair target-SDK
literal/context conversation retained 70/70 expected answers with real
compaction and stale-reference invalidation; and post-repair final regression
A/B/C remain 12/12 each.  The repository release verifier and `git diff
--check` are mandatory for the exact committed tree.

Questions that require **native ZX-UX evidence** remain intentionally open:
final MEX1 image/text/BSS and stack high-water, ARG1/ENV1 and real allocator
extent maps, RAW/PACKED native object placement, cycle/Fuse latency, native tty
and syscall equivalence, native compiler/linker lifetime, cassette save/load
ordering, physical 48K coexistence/headroom, and the Section-18.4 eleven-step
real-machine proof.  The upstream dependency is currently only at Phase-1
durable certification (`P1.25` at the inspected upstream main identity above),
so fabricating answers for those questions would violate the accuracy-first
rule.  Full native-release compliance becomes eligible for its own three-pass
zero-gap certificate only after those upstream facilities exist and the native
proof is retained.

The current compliance certificate therefore has two independent fields:
`SDK_PROFILE = PASS (3/3 zero-gap review passes)` and
`FULL_NATIVE_RELEASE = BLOCKED_EXTERNAL`.  A PASS in the first field must never
be rendered or summarized as a PASS in the second.

## 23. Open design questions after Revision 0.12

The following remain deliberately open until measurement resolves them:

- exact 224-token one-byte hot vocabulary contents;
- final resident extended-vocabulary/recognition-lexicon size below the 4096 ID ceiling;
- final A48M numeric field IDs, section order, compact hot/cold interface-identity width and integrity algorithm;
- exact cold-record type IDs and trigger weights;
- exact hot LM byte budget, pruning thresholds and whether the Candidate-A 12-continuation cap should move;
- whether maximum LM order three wins over a smaller order-two model;
- whether the 4,336-byte context split should trade bytes among L0/L1/L2/session literals/retrieval scratch after real transcripts;
- whether eight session-literal slots is the best byte/recall trade after measured unknown-name conversations;
- whether any target L3 archival mode is worth its explicitly reserved arena bytes; it remains off by default in Candidate A;
- cold model embedded-vs-separate-object split after native MEX1 measurement;
- one PACKED scan versus RAW indexing, a few PACKED shards or a larger resident cache;
- exact model logical/physical byte budget and ZXP1 ratio within the u16 object limit;
- final response token/encoded/printed-byte ceilings after terminal and latency testing;
- final MEX1 minimum stack reservation, selected from measured native high-water rather than a guessed range, and whether heap remains zero;
- exact target model object names/types/paths and cassette physical ordering;
- ordinary-shell launch versus any proven process-replacement launch option;
- final turn-start beep pitch/cue behavior after real-machine audio/usability testing;
- quantitative convergence thresholds/consecutive-round count after baseline variance is known.

These are measurement questions, not invitations to silently assume desktop defaults.

## 24. Revision and durability discipline

This file is the canonical evolving `ailmzx48` design record within the SDK repository. Each coherent design stage is committed directly to `main`. Conversation text is not an authority when it conflicts with the repository copy.

Before each substantive edit, the latest repository copy shall be read. Canonical ZX-UX/C48 documents shall be rechecked whenever a design statement depends on their contracts. If a later canonical revision changes a relevant contract, this document must be reconciled explicitly rather than carrying an accidental stale assumption forward.

Because this SDK release gate covers repository bytes, a design edit is not complete merely when this Markdown file changes. The exact edited tree must regenerate `MANIFEST.sha256`, pass `python -B compiler/verify_release.py`, and preserve every existing license/header/source-line/deterministic verification rule. A failing gate is investigated and corrected; the gate is not relaxed for design convenience.

An ephemeral local or runner copy is never considered a durable checkpoint. A design step is complete only after the updated canonical file and matching manifest have been pushed to `main`, read back from GitHub, and their new blob/commit identities recorded.
