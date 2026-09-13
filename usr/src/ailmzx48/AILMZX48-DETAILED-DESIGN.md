# ailmzx48 Detailed Design

Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.

Status: Design scaffold — architecture reconstruction in progress  
Revision: 0.1-draft  
Canonical repository path: `usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md`  
Canonical executable path: `usr/bin/ailmzx48`

## 1. Purpose

`ailmzx48` is a small English conversational language model for ZX-UX. It is written in C48 and is intended to run both on an actual unexpanded Sinclair ZX Spectrum 48K under ZX-UX and in the ZX-UX C48 SDK environment.

The shipped model is trained specifically around the Sinclair ZX Spectrum: its games, history, hardware and software architecture, culture, folklore, personalities, and related subjects. Runtime inference must be local to the Spectrum/ZX-UX program; a remote modern language model is not part of the shipped runtime design.

## 2. Explicit project requirements

The following requirements are frozen inputs to the design and are not yet implementation claims:

1. Program name: `ailmzx48`.
2. Implementation language: C48.
3. Runtime targets: actual ZX Spectrum 48K running ZX-UX, and the ZX-UX C48 SDK environment.
4. The release ships with a compact Spectrum-specialist conversational model.
5. The design shall investigate memory/context compression so the effective conversational context can substantially exceed the directly available live runtime memory.
6. The user may enter `q` to quit at any time the program is waiting for normal conversational input.
7. Source, design, training/evaluation material, and retained conversation evidence live below `usr/src/ailmzx48/`; the runnable binary lives at `usr/bin/ailmzx48`.
8. Instrumentation shall support long automated conversations on GitHub-hosted runners, keyboard/input injection into the running SDK session, exact transcript recovery, retained conversation logs, iterative model training/evaluation, and repeat-until-convergence development rather than a fixed training-iteration count.
9. The final documentation shall specify the real-cassette user workflow for booting ZX-UX, loading the native C48 toolchain and `ailmzx48` source from tape, compiling/linking it, saving the resulting executable to tape, reclaiming build-tool memory, and subsequently loading/executing `ailmzx48` without inventing unsupported commands or behaviors.
10. Accuracy and verifiable behavior take priority over implementation convenience.

## 3. Design authorities

For this project, the working authority order is:

1. current disk/repository files on `main` in the ZX-UX C48 SDK repository;
2. C48 language specification and ZX-UX C48 SDK/compiler documentation under `doc/` in that repository;
3. actual compiler/runtime implementation under `compiler/`;
4. shipped C48 examples, demos, applications, and tests under `usr/` and the test/verification trees;
5. upstream ZX-UX architecture documentation only where target-native OS/cassette semantics are not defined locally.

Design statements that depend on target behavior shall cite or name the repository source from which they were derived. Unverified assumptions shall be marked as such until proven.

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
    └── ailmzx48                       # generated runnable artifact
```

Git does not preserve empty directories, so the initial scaffold contains small README files in the design subdirectories. They define intended ownership without prematurely freezing file formats.

## 5. Startup conversation — provisional text

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

This wording is provisional until terminal-width behavior, exact character repertoire, binary size, and startup-memory cost are measured.

## 6. Sections to be completed

The detailed design will be built and committed in small verified stages. Planned sections include: exact C48/SDK constraints; target runtime memory budget; model-family survey and selected model; token/vocabulary representation; inference algorithm; knowledge encoding; context compression and long-conversation state; response generation and anti-repetition behavior; input/editor behavior; deterministic/random behavior; SDK and real-ZX compatibility; instrumentation; automated conversation harness; transcript format; corpus construction and provenance; iterative training and evaluation; convergence criteria; reproducibility; failure handling; cassette distribution and native build/run workflow; verification gates; and phased implementation.

## 7. Revision discipline

This file is the canonical evolving design record. Each coherent design stage is committed directly to `main`. Conversation text is not an authority when it conflicts with the repository copy. Substantive design changes shall be made from the latest disk/repository version rather than reconstructed from chat memory.
