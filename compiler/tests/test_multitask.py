# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
"""Cooperative multi-program runtime regressions."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
COMPILER = HERE.parent
sys.path.insert(0, str(COMPILER))

from c48.compiler import compile_bytes
from c48.errors import RuntimeC48Error
from c48.multitask import CooperativeSession, SLEEPING, WAIT_INPUT, ZOMBIE
from c48.screen import Font4x8, ZXScreen

FONT = Font4x8.load(COMPILER / "assets" / "SANYALnet-Labs-4x8-font-FINAL.bin")


def compile_text(source: str, name: str = "mt.c"):
    return compile_bytes(
        source.encode("ascii"),
        source_name=name,
        base_dir=Path.cwd(),
    )


def new_screen() -> ZXScreen:
    return ZXScreen(FONT)


class TickSource:
    def __init__(self, value: int = 10):
        self.value = value

    def now(self) -> int:
        return self.value

    def advance_to(self, deadline: int | None) -> None:
        if deadline is not None and deadline > self.value:
            self.value = deadline
        else:
            self.value += 1


class MultitaskRuntimeTests(unittest.TestCase):
    def test_session_rejects_zero_and_more_than_six_programs(self):
        with self.assertRaisesRegex(RuntimeC48Error, "at least one"):
            CooperativeSession([], [], new_screen())
        program = compile_text("int main(void){return 0;}\n")
        with self.assertRaisesRegex(RuntimeC48Error, "at most six"):
            CooperativeSession(
                [program] * 7,
                [str(i) for i in range(7)],
                new_screen(),
            )

    def test_pid_assignment_uses_slots_two_through_seven(self):
        source = "int getpid(void);int main(void){return getpid();}\n"
        programs = [compile_text(source, f"p{i}.c") for i in range(6)]
        session = CooperativeSession(
            programs,
            [f"p{i}" for i in range(6)],
            new_screen(),
        )
        self.assertEqual(session.run(), 2)
        self.assertEqual(
            [session.descriptors[i].exit_status for i in range(2, 8)],
            [2, 3, 4, 5, 6, 7],
        )

    def test_round_robin_switches_only_at_explicit_yield(self):
        source = (
            "int yield(void);"
            "int main(void){yield();yield();return 0;}\n"
        )
        program = compile_text(source)
        session = CooperativeSession(
            [program, program],
            ["left", "right"],
            new_screen(),
        )
        self.assertEqual(session.run(), 0)
        dispatches = [event for event in session.trace if event[0] == "dispatch"]
        self.assertEqual(
            dispatches,
            [
                ("dispatch", 2),
                ("dispatch", 3),
                ("dispatch", 2),
                ("dispatch", 3),
                ("dispatch", 2),
                ("dispatch", 3),
            ],
        )

    def test_zero_sleep_does_not_handoff(self):
        source = (
            "int sleep(unsigned int t);int yield(void);"
            "int main(void){sleep(0);yield();return 0;}\n"
        )
        program = compile_text(source)
        session = CooperativeSession(
            [program, program],
            ["left", "right"],
            new_screen(),
        )
        self.assertEqual(session.run(), 0)
        self.assertFalse(any(event[0] == "sleep" for event in session.trace))
        self.assertEqual(
            [event for event in session.trace if event[0] == "dispatch"][:2],
            [("dispatch", 2), ("dispatch", 3)],
        )

    def test_positive_sleep_blocks_and_wakes_on_shared_ticks(self):
        ticks = TickSource()
        sleeper = compile_text(
            "int sleep(unsigned int t);"
            "int main(void){sleep(5);return 0;}\n",
            "sleeper.c",
        )
        finisher = compile_text("int main(void){return 0;}\n", "done.c")
        session = CooperativeSession(
            [sleeper, finisher],
            ["sleeper", "done"],
            new_screen(),
            tick_provider=ticks.now,
            idle_wait=ticks.advance_to,
        )
        self.assertEqual(session.run(), 0)
        self.assertIn(("sleep", 2, 5, 15), session.trace)
        self.assertIn(("wake", 2, 15), session.trace)
        self.assertEqual(session.descriptors[2].state, ZOMBIE)

    def test_recursive_continuations_survive_repeated_handoffs(self):
        source = (
            "int yield(void);"
            "int walk(int n){if(n==0)return 0;yield();return walk(n-1)+1;}"
            "int main(void){if(walk(6)!=6)return 1;return 0;}\n"
        )
        program = compile_text(source)
        session = CooperativeSession(
            [program, program],
            ["a", "b"],
            new_screen(),
        )
        self.assertEqual(session.run(), 0)
        self.assertEqual(session.descriptors[2].exit_status, 0)
        self.assertEqual(session.descriptors[3].exit_status, 0)

    def test_globals_and_heaps_are_process_private(self):
        first = compile_text(
            "void *malloc(unsigned int n);int yield(void);int g;"
            "int main(void){char *p;g=7;p=(char*)malloc(2);"
            "if(p==0)return 2;*p=11;yield();"
            "if(g!=7)return 3;if(*p!=11)return 4;return 0;}\n",
            "first.c",
        )
        second = compile_text(
            "void *malloc(unsigned int n);int yield(void);int g;"
            "int main(void){char *p;g=9;p=(char*)malloc(2);"
            "if(p==0)return 2;*p=13;yield();"
            "if(g!=9)return 3;if(*p!=13)return 4;return 0;}\n",
            "second.c",
        )
        session = CooperativeSession(
            [first, second],
            ["first", "second"],
            new_screen(),
            heap_size=64,
        )
        self.assertEqual(session.run(), 0)

    def test_each_process_receives_only_its_program_token(self):
        source_a = (
            "int main(int argc,char **argv){"
            "if(argc!=1)return 2;if(argv[0][0]!='L')return 3;return 0;}\n"
        )
        source_b = (
            "int main(int argc,char **argv){"
            "if(argc!=1)return 2;if(argv[0][0]!='R')return 3;return 0;}\n"
        )
        session = CooperativeSession(
            [compile_text(source_a), compile_text(source_b)],
            ["LeftToken", "RightToken"],
            new_screen(),
        )
        self.assertEqual(session.run(), 0)

    def test_input_wait_does_not_block_unrelated_process(self):
        input_calls: list[int] = []
        first_poll = True

        def poll(pid: int) -> int | None:
            nonlocal first_poll
            input_calls.append(pid)
            if first_poll:
                first_poll = False
                return None
            return 65

        reader = compile_text(
            "int getchar(void);"
            "int main(void){int c;c=getchar();if(c!=65)return 2;return 0;}\n",
            "reader.c",
        )
        peer = compile_text(
            "int yield(void);int main(void){yield();return 0;}\n",
            "peer.c",
        )
        session = CooperativeSession(
            [reader, peer],
            ["reader", "peer"],
            new_screen(),
            input_poll=poll,
        )
        self.assertEqual(session.run(), 0)
        self.assertIn(("input_wait", 2), session.trace)
        self.assertIn(("dispatch", 3), session.trace)
        self.assertIn(("input", 2, 65), session.trace)
        self.assertTrue(input_calls)
        self.assertTrue(all(pid == 2 for pid in input_calls))

    def test_headless_input_fails_that_process_and_peer_finishes(self):
        reader = compile_text(
            "int getchar(void);int main(void){getchar();return 0;}\n"
        )
        peer = compile_text("int main(void){return 0;}\n")
        session = CooperativeSession(
            [reader, peer],
            ["reader", "peer"],
            new_screen(),
        )
        self.assertEqual(session.run(), 1)
        self.assertEqual(session.descriptors[2].exit_status, 1)
        self.assertEqual(session.descriptors[3].exit_status, 0)
        self.assertTrue(any(e[:2] == ("exit", 3) for e in session.trace))

    def test_process_runtime_exit_does_not_stop_peer(self):
        bad = compile_text("int main(void){return 7;}\n", "bad.c")
        peer = compile_text("int main(void){return 0;}\n", "peer.c")
        session = CooperativeSession(
            [bad, peer],
            ["bad", "peer"],
            new_screen(),
        )
        self.assertEqual(session.run(), 7)
        self.assertEqual(session.descriptors[2].exit_status, 7)
        self.assertEqual(session.descriptors[3].exit_status, 0)

    def test_session_step_ceiling_stops_starving_process(self):
        spinner = compile_text(
            "int main(void){int x;x=0;while(1){x=x+1;}return 0;}\n",
            "spin.c",
        )
        peer = compile_text("int main(void){return 0;}\n", "peer.c")
        session = CooperativeSession(
            [spinner, peer],
            ["spin", "peer"],
            new_screen(),
            max_steps=100,
        )
        self.assertEqual(session.run(), 1)
        self.assertEqual(
            [e for e in session.trace if e[0] == "dispatch"],
            [("dispatch", 2)],
        )
        self.assertTrue(session.descriptors[2].cancelled)
        self.assertTrue(session.descriptors[3].cancelled)


if __name__ == "__main__":
    unittest.main()
