<!--
ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com

SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
-->

# `c48run --multitask` frozen host contract

## Native semantic reference

Phase 2 is pinned to read-only ZX-UX commit
`69348ee366c48b436aa0d07237ae2e7473e55327`. The host implementation was
frozen from the following upstream contracts at that commit:

- `v1/src/kernel/process.asm`
- `v1/src/kernel/scheduler.asm`
- `v1/src/kernel/syscall.asm`
- `v1/include/syscall.inc`
- `tools/p11-prerelease/sdk_multitask_run.py`

The native process table has eight fixed slots. PID0 is the idle process. PID1
is the permanent shell/init process. User process slots are PID2 through PID7.
The scheduler is cooperative and round-robin: ordinary instructions do not
preempt a process. Scheduling occurs only at an admitted scheduling service,
a blocking service, process termination, or cancellation. A positive sleep
moves the caller to SLEEPING until its wake tick. A zero-duration sleep returns
success without yielding. A normal user-process exit publishes ZOMBIE state
and wakes a waiting parent. PID1 is protected from normal exit. Native wait
reaps a matching child; native kill protects PID0/PID1 and delivers
cancellation to an eligible child at a safe restore boundary. Terminal input
ownership is restored to live PID1, or PID0 if PID1 is unavailable.

The upstream concurrent Hanoi/8-Queens proof launches PID2 and PID3 and
switches only through the admitted cooperative yield boundary. That proof is
the semantic model for the SDK-side recursive workload proof; the SDK does not
claim that host execution is native kernel execution.

## Host process model

`c48run --multitask` reserves the same eight identities. PID0 is synthetic idle
state, PID1 is a synthetic session supervisor, and directly listed programs
are assigned PID2 through PID7 in command-line order. The host therefore
accepts one through six direct programs. Each direct process has its own VM
memory, globals, local scopes, call/continuation frames, heap, argument block,
object handles, terminal status, and accounting. The ZX screen is shared.

The host session intentionally does not implement native spawn, wait, or kill
as C48 services in Phase 2. Those surfaces are deferred rather than partially
emulated. Directly launched children remain represented as terminal ZOMBIE
records until the synthetic supervisor observes final session status. This is
a host orchestration detail, not a claim about native child reaping.

A process runtime failure terminates that process with status 1 while unrelated
runnable processes continue. After all direct processes are terminal, overall
status is zero only if every process ended with zero; otherwise the first
nonzero status in ascending PID order is returned. A global BREAK returns 130.
A session-wide step or wall-clock safety ceiling returns 1 and cancels every
still-live direct process.

## Command-line contract

The admitted form is:

```text
c48run --multitask PROGRAM1.c48b PROGRAM2.c48b [PROGRAM3.c48b ...]
```

In this mode every positional token is a program path. Per-process extra
arguments are not admitted. Each process receives exactly its supplied program
token as `argv[0]`. An empty list and a list longer than six programs are
errors. Outside this mode the established single-program `program [args ...]`
contract remains unchanged.

`--heap` is an independent per-process heap ceiling. `--max-steps` is one
session-wide deterministic semantic-step ceiling. `--time-quota` is one
session-wide wall-clock ceiling. `ticks()` reads one shared session tick source.
The font, ROM-math profile, display scale, and dump options are session-wide.
Screen dumps and PPM outputs are taken from the final shared screen.

Headless execution uses the same cooperative scheduler. It never performs a
blocking host stdin read for a C48 process. A headless process that calls
`getchar()` without an injected deterministic event source fails explicitly,
while proof tests may inject a non-blocking PID-aware input source. GUI input
is likewise polled without allowing an input wait to stall unrelated runnable
processes.

## Scheduling and device contract

One C48 process executes at a time. No host thread chooses C48 execution order.
A process can hand control to the session only at `yield()`, positive
`sleep()`, blocking `getchar()`, termination, cancellation, or a configured
session safety ceiling. Zero-duration `sleep()` returns immediately without a
handoff. A CPU-bound process that never reaches one of those boundaries may
starve peers until a configured safety ceiling intervenes, matching the
cooperative native model.

Runnable direct processes are selected round-robin by PID. If none is runnable,
PID0 represents the idle path while sleepers or input waiters are serviced.
Positive sleep uses the shared nondecreasing tick source. Deterministic proof
runs inject their tick and input streams; identical programs, options, and
injected events must produce identical schedule traces and final screen bytes.
Live wall-clock and human input timings are external events and are not claimed
to be repeatable.

Graphics, text, border, and sound calls are serialized by cooperative execution
order against the shared session devices. If multiple processes wait for
keyboard input, an existing owner is retained; otherwise the lowest waiting PID
becomes owner. One delivered byte wakes only that owner, then ownership is
released for the next waiter.

## GUI completion contract

The GUI worker runs one complete session target; it is not a C48 scheduler.
The final completion footer is suppressed while any direct process remains
runnable, sleeping, or input-blocked. When one process exits, the others keep
running. Only after the final direct process reaches terminal state may the
final framebuffer and `Press Shift+Space to exit` footer be exposed.

Shift+Space before final completion is a global BREAK request and cancels the
session. Shift+Space after final completion only closes the retained final
display.
