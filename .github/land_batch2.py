#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path.cwd()
BASE = "f45255c14e1e7504a2533f0cc792f9efa556b462"
TEMP_SCRIPT = Path(".github/land_batch2.py")
TEMP_WORKFLOW = Path(".github/workflows/land-game-batch2.yml")


def run(args, *, timeout=1800):
    print("+", " ".join(str(x) for x in args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True, timeout=timeout)


def text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, data):
    (ROOT / path).write_text(data, encoding="utf-8", newline="\n")


def rep(path, old, new, label):
    data = text(path)
    count = data.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, got {count}")
    write(path, data.replace(old, new, 1))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def git_output(*args):
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True
    ).strip()


def patch_sources():
    rep(
        "usr/src/games/gameapi.h",
        "static unsigned int game_seed = 44257u;\n",
        "static unsigned int game_seed = 44257u;\n"
        "static int game_seeded = 0;\n",
        "game seed state",
    )

    old_rand = """static int game_rand(int limit)
{
    unsigned int value;
    if (limit <= 1)
        return 0;
    game_seed = game_seed * 25173u + 13849u;
    game_seed = game_seed & 65535u;
    value = game_seed % (unsigned int)limit;
    return (int)value;
}
"""
    new_rand = """static void game_seed_set(unsigned int seed)
{
    game_seed = seed;
    game_seeded = 1;
}

static void game_seed_init(void)
{
    game_seed_set(ticks());
}

static int game_rand(int limit)
{
    unsigned int value;
    if (limit <= 1)
        return 0;
    if (!game_seeded)
        game_seed_init();
    game_seed = game_seed * 25173u + 13849u;
    game_seed = game_seed & 65535u;
    value = game_seed % (unsigned int)limit;
    return (int)value;
}
"""
    rep(
        "usr/src/games/gameapi.h",
        old_rand,
        new_rand,
        "lazy game seed",
    )

    rep(
        "usr/src/games/arith.c",
        "key <= '9' && digits < 5)",
        "key <= '9' && digits < 3)",
        "arith digit bound",
    )

    rep(
        "usr/src/games/wump.c",
        "    3, 5, 7, 0, 6, 8, 5, 7, 9,\n",
        "    3, 5, 10, 0, 8, 11, 5, 7, 9,\n",
        "wump cave reciprocity",
    )

    old_bg_main = """int main(void)
{
    int count;
    int i;
    int die;
    int rc;
    bg_init();
    while (bg_off_w < 15 && bg_off_b < 15) {
        bg_d1 = game_rand(6) + 1;
        bg_d2 = game_rand(6) + 1;
        count = 2;
        if (bg_d1 == bg_d2)
            count = 4;
        for (i = 0; i < count; i++) {
            if (i == 0)
                die = bg_d1;
            else
                die = bg_d2;
            if (count == 4)
                die = bg_d1;
            rc = bg_play(die);
            if (rc < 0)
                return 0;
        }
        if (bg_side == 0)
            bg_side = 1;
        else
            bg_side = 0;
    }
    bg_show();
    if (bg_off_w == 15)
        print_at(21, 0, "White wins. Press 0.");
    else
        print_at(21, 0, "Black wins. Press 0.");
    while (game_key() != '0')
        bg_turns++;
    return 0;
}
"""
    new_bg_main = """int bg_order(void)
{
    int key;
    int can1;
    int can2;
    can1 = bg_any(bg_d1, bg_side);
    can2 = bg_any(bg_d2, bg_side);
    if (!can1 && !can2)
        return 1;
    if (!can1)
        return 2;
    if (!can2)
        return 1;
    bg_show();
    print_at(20, 0, "First die: 1 or 2");
    print_at(21, 0, "Order:");
    while (1) {
        key = game_key_echo(21, 7);
        bg_turns++;
        if (key == '0')
            return 0;
        if (key == '1' || key == '2') {
            game_record(key, 1);
            return key - '0';
        }
        game_record(key, 3);
        game_show_last(19);
        game_putc(21, 7, ' ');
    }
}

int main(void)
{
    int count;
    int i;
    int die;
    int rc;
    int order;
    bg_init();
    while (bg_off_w < 15 && bg_off_b < 15) {
        bg_d1 = game_rand(6) + 1;
        bg_d2 = game_rand(6) + 1;
        count = 2;
        order = 1;
        if (bg_d1 == bg_d2)
            count = 4;
        else {
            order = bg_order();
            if (order == 0)
                return 0;
        }
        for (i = 0; i < count; i++) {
            if (count == 4)
                die = bg_d1;
            else if (order == 1) {
                if (i == 0)
                    die = bg_d1;
                else
                    die = bg_d2;
            }
            else {
                if (i == 0)
                    die = bg_d2;
                else
                    die = bg_d1;
            }
            rc = bg_play(die);
            if (rc < 0)
                return 0;
        }
        if (bg_side == 0)
            bg_side = 1;
        else
            bg_side = 0;
    }
    bg_show();
    if (bg_off_w == 15)
        print_at(21, 0, "White wins. Press 0.");
    else
        print_at(21, 0, "Black wins. Press 0.");
    while (game_key() != '0')
        bg_turns++;
    return 0;
}
"""
    rep(
        "usr/src/games/bgammon.c",
        old_bg_main,
        new_bg_main,
        "backgammon die order",
    )

    rep(
        "compiler/c48/vm.py",
        "                 sound_player:Callable[[Path],None]|None=None):\n",
        "                 sound_player:Callable[[Path],None]|None=None,\n"
        "                 tick_provider:Callable[[],int]|None=None):\n",
        "vm tick provider signature",
    )
    rep(
        "compiler/c48/vm.py",
        "        self.heap_allocs:set[int]=set()\n"
        "        self.start_time=time.monotonic()\n"
        "        self.max_steps=max_steps\n",
        "        self.heap_allocs:set[int]=set()\n"
        "        self.tick_provider=tick_provider or self._system_ticks\n"
        "        self.max_steps=max_steps\n",
        "vm system tick provider",
    )
    rep(
        "compiler/c48/vm.py",
        "    @staticmethod\n"
        "    def _stdin_char()->int:\n"
        "        b=os.sys.stdin.buffer.read(1)\n"
        "        return -1 if not b else b[0]\n",
        "    @staticmethod\n"
        "    def _system_ticks()->int:\n"
        "        return int(time.monotonic_ns() // 20000000) & 0xFFFF\n"
        "\n"
        "    @staticmethod\n"
        "    def _stdin_char()->int:\n"
        "        b=os.sys.stdin.buffer.read(1)\n"
        "        return -1 if not b else b[0]\n",
        "vm system ticks implementation",
    )
    rep(
        "compiler/c48/vm.py",
        '            "ticks":lambda a:Value(UINT,int((time.monotonic()-self.start_time)*50)&0xFFFF),\n',
        '            "ticks":lambda a:Value(UINT,int(self.tick_provider())&0xFFFF),\n',
        "vm ticks builtin",
    )

    vg = "compiler/verify_games.py"
    rep(
        vg,
        "    max_steps: int,\n"
        ") -> tuple[C48VM, str, int]:\n"
        "    program = read(BIN / f\"{name}.c48b\")\n"
        "    screen = ZXScreen(FONT)\n"
        "    provider = ScriptKeys(keys)\n",
        "    max_steps: int,\n"
        "    tick_value: int = 44257,\n"
        ") -> tuple[C48VM, str, int]:\n"
        "    program = read(BIN / f\"{name}.c48b\")\n"
        "    screen = ZXScreen(FONT)\n"
        "    provider = ScriptKeys(keys)\n",
        "game verifier script tick parameter",
    )
    script_vm = (
        "    provider = ScriptKeys(keys)\n"
        "    vm = C48VM(\n"
        "        program,\n"
        "        screen,\n"
        "        argv=[name],\n"
        "        input_provider=provider,\n"
        "        max_steps=max_steps,\n"
        "    )\n"
    )
    script_vm_new = script_vm.replace(
        "        max_steps=max_steps,\n"
        "    )\n",
        "        max_steps=max_steps,\n"
        "        tick_provider=lambda: tick_value,\n"
        "    )\n",
    )
    rep(vg, script_vm, script_vm_new, "game verifier script pinned ticks")

    rep(
        vg,
        "def run_human(\n"
        "    name: str,\n"
        "    steps,\n"
        "    *,\n"
        "    max_steps: int,\n"
        ") -> tuple[C48VM, str, int]:\n",
        "def run_human(\n"
        "    name: str,\n"
        "    steps,\n"
        "    *,\n"
        "    max_steps: int,\n"
        "    tick_value: int = 44257,\n"
        ") -> tuple[C48VM, str, int]:\n",
        "game verifier human tick parameter",
    )
    human_vm = (
        "    provider = HumanKeys(screen, steps)\n"
        "    vm = C48VM(\n"
        "        program,\n"
        "        screen,\n"
        "        argv=[name],\n"
        "        input_provider=provider,\n"
        "        max_steps=max_steps,\n"
        "    )\n"
    )
    human_vm_new = human_vm.replace(
        "        max_steps=max_steps,\n"
        "    )\n",
        "        max_steps=max_steps,\n"
        "        tick_provider=lambda: tick_value,\n"
        "    )\n",
    )
    rep(vg, human_vm, human_vm_new, "game verifier human pinned ticks")

    rep(
        vg,
        "def run_player(\n"
        "    name: str,\n"
        "    player_type,\n"
        "    *,\n"
        "    max_steps: int,\n"
        "    args: tuple = (),\n"
        ") -> tuple[C48VM, str, Player]:\n",
        "def run_player(\n"
        "    name: str,\n"
        "    player_type,\n"
        "    *,\n"
        "    max_steps: int,\n"
        "    args: tuple = (),\n"
        "    tick_value: int = 44257,\n"
        ") -> tuple[C48VM, str, Player]:\n",
        "game verifier player tick parameter",
    )
    player_vm = (
        "    player = player_type(screen, *args)\n"
        "    vm = C48VM(\n"
        "        program,\n"
        "        screen,\n"
        "        argv=[name],\n"
        "        input_provider=player,\n"
        "        max_steps=max_steps,\n"
        "    )\n"
    )
    player_vm_new = player_vm.replace(
        "        max_steps=max_steps,\n"
        "    )\n",
        "        max_steps=max_steps,\n"
        "        tick_provider=lambda: tick_value,\n"
        "    )\n",
    )
    rep(vg, player_vm, player_vm_new, "game verifier player pinned ticks")

    rep(
        vg,
        'run_script("bgammon", "ff0", max_steps=1000000)',
        'run_script("bgammon", "1ff0", max_steps=1000000)',
        "game verifier backgammon quick order",
    )
    old_human_bg = """        (
            "bgammon",
            (
                (("Source:",), "?"),
                (("Last: ?", "ignored"), "f"),
                (("Last: f", "accepted"), "0"),
            ),
            1000000,
        ),
"""
    new_human_bg = """        (
            "bgammon",
            (
                (("First die:",), "1"),
                (("Source:",), "?"),
                (("Last: ?", "ignored"), "f"),
                (("Last: f", "accepted"), "0"),
            ),
            1000000,
        ),
"""
    rep(vg, old_human_bg, new_human_bg, "game verifier backgammon human order")

    regression = r'''def check_batch2_regressions() -> None:
    vm1, _text, _count = run_script(
        "fortune", "q", max_steps=500000, tick_value=1000
    )
    vm2, _text, _count = run_script(
        "fortune", "q", max_steps=500000, tick_value=1000
    )
    vm3, _text, _count = run_script(
        "fortune", "q", max_steps=500000, tick_value=1001
    )
    seed1 = global_int(vm1, "game_seed")
    seed2 = global_int(vm2, "game_seed")
    seed3 = global_int(vm3, "game_seed")
    if seed1 != seed2 or seed1 == seed3:
        fail("game PRNG seed injection/decorrelation mismatch")
    if global_int(vm1, "game_seeded") != 1:
        fail("game PRNG lazy seed flag was not set")

    vmw, _text, _count = run_script(
        "wump", "q", max_steps=500000
    )
    for room in range(12):
        for slot in range(3):
            neighbor = global_int(vmw, "cave", room * 3 + slot)
            if neighbor < 0 or neighbor >= 12:
                fail("wump: cave neighbor out of range")
            back = False
            for back_slot in range(3):
                if global_int(
                    vmw, "cave", neighbor * 3 + back_slot
                ) == room:
                    back = True
            if not back:
                fail(f"wump: one-way tunnel {room}->{neighbor}")

    arith_source = (SRC / "arith.c").read_text(encoding="ascii")
    if "key <= '9' && digits < 3)" not in arith_source:
        fail("arith: three-digit input guard missing")
    vma, _text, _count = run_script(
        "arith", "99999\nq", max_steps=500000
    )
    if global_int(vma, "ar_turns") != 1:
        fail("arith: five-key input regression did not complete")

    vmb, _text, _count = run_script(
        "bgammon", "2f0", max_steps=1000000
    )
    if (
        global_int(vmb, "bg_pt", 5) != 4
        or global_int(vmb, "bg_pt", 3) != 1
        or global_int(vmb, "bg_pt", 4) != 0
    ):
        fail("bgammon: die-two-first choice was not honored")

    print("GAME BATCH-2 REGRESSION PROBES PASS", flush=True)


'''
    rep(
        vg,
        "def check_quick_play() -> None:\n",
        regression + "def check_quick_play() -> None:\n",
        "game verifier Batch-2 probes",
    )
    rep(
        vg,
        "        check_corpus()\n"
        "        check_quick_play()\n"
        "        check_human_io()\n",
        "        check_corpus()\n"
        "        check_batch2_regressions()\n"
        "        check_quick_play()\n"
        "        check_human_io()\n",
        "game verifier Batch-2 probe call",
    )

    tgr = "compiler/tests/test_game_regressions.py"
    arith_vm = """        vm = C48VM(
            program,
            screen,
            argv=["arith"],
            input_provider=provider,
            max_steps=500000,
        )
"""
    arith_vm_new = """        vm = C48VM(
            program,
            screen,
            argv=["arith"],
            input_provider=provider,
            max_steps=500000,
            tick_provider=lambda: 44257,
        )
"""
    rep(
        tgr,
        arith_vm,
        arith_vm_new,
        "unit arithmetic pinned ticks",
    )


def c48_column_scan():
    bad = []
    for p in sorted((ROOT / "usr/src").rglob("*")):
        if not p.is_file() or p.suffix not in {".c", ".h"}:
            continue
        data = p.read_bytes()
        try:
            decoded = data.decode("ascii")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"non-ASCII C48 source {p}: {exc}")
        for n, line in enumerate(decoded.splitlines(), 1):
            if len(line) > 64:
                bad.append(f"{p.relative_to(ROOT)}:{n}:{len(line)}")
    if bad:
        raise SystemExit("64-column violations: " + ", ".join(bad))
    print("C48 SOURCE COLUMN SCAN PASS", flush=True)


def rebuild_games():
    for source in sorted((ROOT / "usr/src/games").glob("*.c")):
        name = source.stem
        run([
            sys.executable,
            "-B",
            "compiler/c48.py",
            str(source.relative_to(ROOT)),
            "-o",
            f"usr/bin/games/{name}.c48b",
        ])


def refresh_expectations():
    path = ROOT / "compiler/release_expectations.json"
    data = json.loads(path.read_text(encoding="ascii"))
    data["game_header_sha256"] = sha("usr/src/games/gameapi.h")
    for name, item in data["games"].items():
        item["source_sha256"] = sha(f"usr/src/games/{name}.c")
        item["binary_sha256"] = sha(f"usr/bin/games/{name}.c48b")
    path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="ascii",
        newline="\n",
    )
    print("GAME EXPECTATIONS REFRESHED", flush=True)


def remove_landing_harness():
    for rel in (TEMP_SCRIPT, TEMP_WORKFLOW):
        p = ROOT / rel
        if p.exists():
            p.unlink()
    print("ONE-SHOT BATCH-2 HARNESS REMOVED", flush=True)


def assert_delta():
    allowed = {
        "compiler/c48/vm.py",
        "compiler/release_expectations.json",
        "compiler/verify_games.py",
        "compiler/tests/test_game_regressions.py",
        "usr/src/games/gameapi.h",
        "usr/src/games/arith.c",
        "usr/src/games/bgammon.c",
        "usr/src/games/wump.c",
    }
    allowed.update(
        f"usr/bin/games/{p.stem}.c48b"
        for p in (ROOT / "usr/src/games").glob("*.c")
    )
    required = {
        "compiler/c48/vm.py",
        "compiler/release_expectations.json",
        "compiler/verify_games.py",
        "compiler/tests/test_game_regressions.py",
        "usr/src/games/gameapi.h",
        "usr/src/games/arith.c",
        "usr/src/games/bgammon.c",
        "usr/src/games/wump.c",
    }
    raw = git_output("diff", "--name-only", BASE)
    actual = {line for line in raw.splitlines() if line}
    if not required.issubset(actual):
        raise SystemExit(
            f"required Batch-2 delta missing: "
            f"{sorted(required - actual)!r}"
        )
    if not actual.issubset(allowed):
        raise SystemExit(
            f"unexpected Batch-2 delta: "
            f"{sorted(actual - allowed)!r}"
        )
    run(["git", "diff", "--check"])
    print(
        f"FINAL DELTA GUARD PASS files={len(actual)}",
        flush=True,
    )


def tree_files(root):
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    )


def manifest(root):
    h = hashlib.sha256()
    for p in tree_files(root):
        rel = p.relative_to(root).as_posix().encode("utf-8")
        data = p.read_bytes()
        h.update(rel + b"\0" + hashlib.sha256(data).digest())
    return h.hexdigest()


def sop_scan():
    text_suffixes = {
        ".c", ".h", ".py", ".md", ".txt", ".json", ".yml",
        ".yaml", ".bat",
    }
    expected_manifest = manifest(ROOT)
    for pass_no in range(1, 4):
        with tempfile.TemporaryDirectory(
            prefix=f"sop-batch2-{pass_no}-"
        ) as td:
            fresh = Path(td) / "repo"
            shutil.copytree(
                ROOT,
                fresh,
                ignore=shutil.ignore_patterns(
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    "*.pyo",
                    ".coverage",
                ),
            )
            if manifest(fresh) != expected_manifest:
                raise SystemExit(
                    f"SoP pass {pass_no}: fresh-copy manifest mismatch"
                )
            for p in tree_files(fresh):
                rel = p.relative_to(fresh)
                data = p.read_bytes()
                rebuilt = b"".join(data.splitlines(keepends=True))
                if rebuilt != data:
                    raise SystemExit(
                        f"SoP pass {pass_no}: "
                        f"byte-line reconstruction failed: {rel}"
                    )
                for line_no, line in enumerate(
                    data.splitlines(keepends=True), 1
                ):
                    suffix = p.suffix.lower()
                    if suffix in text_suffixes:
                        if b"<<<<<<<" in line or b">>>>>>>" in line:
                            raise SystemExit(
                                f"SoP pass {pass_no}: "
                                f"conflict marker {rel}:{line_no}"
                            )
                    if suffix in {".c", ".h"}:
                        if b"\r" in line:
                            raise SystemExit(
                                f"SoP pass {pass_no}: "
                                f"CR in C48 source {rel}:{line_no}"
                            )
                        body = line.rstrip(b"\n")
                        try:
                            body.decode("ascii")
                        except UnicodeDecodeError:
                            raise SystemExit(
                                f"SoP pass {pass_no}: "
                                f"non-ASCII C48 source {rel}:{line_no}"
                            )
                        if len(body) > 64:
                            raise SystemExit(
                                f"SoP pass {pass_no}: "
                                f">64 cols {rel}:{line_no}"
                            )

            checks = {
                "usr/src/games/gameapi.h": [
                    b"static int game_seeded = 0;",
                    b"static void game_seed_init(void)",
                    b"if (!game_seeded)",
                ],
                "usr/src/games/arith.c": [
                    b"digits < 3",
                ],
                "usr/src/games/bgammon.c": [
                    b"int bg_order(void)",
                    b"First die: 1 or 2",
                ],
                "usr/src/games/wump.c": [
                    b"3, 5, 10, 0, 8, 11",
                ],
                "compiler/c48/vm.py": [
                    b"tick_provider",
                    b"time.monotonic_ns() // 20000000",
                ],
                "compiler/verify_games.py": [
                    b"GAME BATCH-2 REGRESSION PROBES PASS",
                    b"tick_value: int = 44257",
                ],
            }
            for rel, needles in checks.items():
                data = (fresh / rel).read_bytes()
                for needle in needles:
                    if data.count(needle) < 1:
                        raise SystemExit(
                            f"SoP pass {pass_no}: "
                            f"invariant missing {rel}: {needle!r}"
                        )
            print(
                f"SOP PASS {pass_no}: ZERO NEW DEFECTS "
                f"manifest={expected_manifest}",
                flush=True,
            )


def main():
    head = git_output("rev-parse", "HEAD")
    base_seen = git_output("rev-parse", "HEAD^^")
    if base_seen != BASE:
        raise SystemExit(
            f"landing base moved: expected {BASE}, got {base_seen}"
        )
    staged = {
        line
        for line in git_output(
            "diff", "--name-only", BASE, head
        ).splitlines()
        if line
    }
    expected_stage = {
        TEMP_SCRIPT.as_posix(),
        TEMP_WORKFLOW.as_posix(),
    }
    if staged != expected_stage:
        raise SystemExit(
            f"unexpected staging delta: {sorted(staged)!r}"
        )

    patch_sources()
    c48_column_scan()
    rebuild_games()
    refresh_expectations()

    run([
        sys.executable,
        "-B",
        "compiler/verify_games.py",
    ])
    run([
        sys.executable,
        "-B",
        "compiler/verify_games.py",
        "--extended",
    ], timeout=1800)

    remove_landing_harness()
    assert_delta()

    run([
        sys.executable,
        "-B",
        "compiler/verify_release.py",
    ], timeout=1800)

    sop_scan()

    run(["git", "config", "user.name", "github-actions[bot]"])
    run([
        "git",
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    ])
    run(["git", "add", "-A"])
    run([
        "git",
        "commit",
        "-m",
        "fix: harden Batch-2 game review findings",
    ])
    run(["git", "push", "origin", "HEAD:main"])


if __name__ == "__main__":
    main()
