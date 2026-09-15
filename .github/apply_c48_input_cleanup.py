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
"""One-shot source transformer for the C48 input/model-I/O cleanup."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def text(path: str, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def write(path: str, value: str, encoding: str = "utf-8") -> None:
    Path(path).write_text(value, encoding=encoding, newline="\n")


def once(value: str, old: str, new: str, label: str) -> str:
    count = value.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, got {count}")
    return value.replace(old, new)


def section(value: str, start: str, end: str, replacement: str, label: str) -> str:
    a = value.find(start)
    if a < 0:
        raise SystemExit(f"{label}: start anchor missing")
    b = value.find(end, a + len(start))
    if b < 0:
        raise SystemExit(f"{label}: end anchor missing")
    if value.find(start, a + 1) >= 0 and value.find(start, a + 1) < b:
        raise SystemExit(f"{label}: ambiguous start anchor")
    return value[:a] + replacement + value[b:]


# Host read-only object I/O in the ROM-math profile.
p = "compiler/c48/romvm.py"
s = text(p)
s = once(
    s,
    '"""C48 host VM profile with the Sinclair 48K ROM math path enabled."""',
    '"""C48 host VM profile with Sinclair ROM math and read-only object I/O."""',
    "romvm docstring",
)
s = once(
    s,
    "from __future__ import annotations\n\nfrom . import rommath",
    "from __future__ import annotations\n\nfrom pathlib import Path\n\nfrom . import rommath",
    "romvm pathlib import",
)
s = once(s, "from .typesys import FLOAT\n", "from .typesys import FLOAT, INT\n", "romvm INT import")
s = once(
    s,
    '    """C48VM that uses the ROM-derived transcendental implementation."""\n\n',
    '    """C48VM with ROM math and target-shaped read-only object I/O."""\n\n',
    "romvm class docstring",
)
insert = '''    _OBJECT_CHARS = frozenset(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._object_handles: dict[int, list[object]] = {}
        self.builtins["open"] = self._b_open
        self.builtins["close"] = self._b_close
        self.builtins["read"] = self._b_read
        self.builtins["seek"] = self._b_seek

    def _object_root(self) -> Path:
        return Path(self.argv[0]).resolve().parent

    def _object_path(self, raw: bytes) -> Path | None:
        try:
            name = raw.decode("ascii")
        except UnicodeDecodeError:
            return None
        if not 1 <= len(name) <= 10 or name in {".", ".."}:
            return None
        if any(ch not in self._OBJECT_CHARS for ch in name):
            return None
        root = self._object_root()
        path = (root / name).resolve()
        if path.parent != root:
            return None
        return path

    def _b_open(self, args):
        if len(args) != 2 or self._int_math(args[1]) != 1:
            return Value(INT, -1)
        raw = self._read_cstr(self._as_pointer(args[0]))
        path = self._object_path(raw)
        if path is None:
            return Value(INT, -1)
        try:
            if not path.is_file():
                return Value(INT, -1)
            data = path.read_bytes()
        except OSError:
            return Value(INT, -1)
        if len(data) > 65535:
            return Value(INT, -1)
        for handle in range(3, 16):
            if handle not in self._object_handles:
                self._object_handles[handle] = [data, 0]
                return Value(INT, handle)
        return Value(INT, -1)

    def _b_close(self, args):
        if len(args) != 1:
            return Value(INT, -1)
        handle = self._int_math(args[0])
        if handle not in self._object_handles:
            return Value(INT, -1)
        del self._object_handles[handle]
        return Value(INT, 0)

    def _b_read(self, args):
        if len(args) != 3:
            return Value(INT, -1)
        handle = self._int_math(args[0])
        state = self._object_handles.get(handle)
        if state is None:
            return Value(INT, -1)
        count = self._to_unsigned(args[2])
        if count == 0:
            return Value(INT, 0)
        data = state[0]
        pos = state[1]
        assert isinstance(data, bytes) and isinstance(pos, int)
        take = min(count, len(data) - pos)
        if take <= 0:
            return Value(INT, 0)
        ptr = self._as_pointer(args[1])
        self.mem.require_range(ptr, take, write=True)
        self.mem.write_bytes(ptr.address, data[pos:pos + take])
        state[1] = pos + take
        return Value(INT, take)

    def _b_seek(self, args):
        if len(args) != 2:
            return Value(INT, -1)
        handle = self._int_math(args[0])
        state = self._object_handles.get(handle)
        if state is None:
            return Value(INT, -1)
        pos = self._to_unsigned(args[1])
        data = state[0]
        assert isinstance(data, bytes)
        if pos > len(data):
            return Value(INT, -1)
        state[1] = pos
        return Value(INT, 0)

'''
s = once(s, "    def _math1(self, name, args):\n", insert + "    def _math1(self, name, args):\n", "romvm method insertion")
write(p, s)


# GUI console typeahead FIFO.
p = "compiler/c48/gui.py"
s = text(p)
s = once(s, "from __future__ import annotations\n\nimport hashlib", "from __future__ import annotations\n\nfrom collections import deque\n\nimport hashlib", "gui deque import")
start = "    def __post_init__(self) -> None:\n"
frame = "        self._frame_lock = threading.Lock()\n"
a = s.find(start)
b = s.find(frame, a)
if a < 0 or b < 0:
    raise SystemExit("gui init structural anchors missing")
prefix = '''    def __post_init__(self) -> None:
        # Console bytes use a bounded FIFO so normal typeahead survives the
        # presentation gap between adjacent getchar() calls.
        self._key_cond = threading.Condition()
        self._key_waiting = False
        self._key_queue = deque()
'''
s = s[:a] + prefix + s[b:]
methods = '''    def input_char(self) -> int:
        with self._key_cond:
            self._key_waiting = True
            self._probe("input_waiting", queued=len(self._key_queue))
            while not self._key_queue and not self._stop:
                self._key_cond.wait()
            value = -1 if not self._key_queue else self._key_queue.popleft()
            self._key_waiting = False
            self._probe(
                "input_return", value=value, queued=len(self._key_queue)
            )
            return value

    def _offer_key(self, value: int) -> bool:
        """Queue one console byte, preserving bounded typeahead."""
        with self._key_cond:
            if self._stop or len(self._key_queue) >= 256:
                return False
            byte = int(value) & 0xFF
            self._key_queue.append(byte)
            self._probe(
                "key_accepted", value=byte, queued=len(self._key_queue)
            )
            self._key_cond.notify()
            return True

    def _waiting_for_key(self) -> bool:
        with self._key_cond:
            return self._key_waiting and not self._key_queue

'''
s = section(s, "    def input_char(self) -> int:\n", "    def update(self) -> int:\n", methods, "gui input methods")
write(p, s)


# Generic model-object bridge implemented in C48 itself.
p = "usr/src/ailmzx48/aimatch.h"
s = text(p, "ascii")
bridge = '''int open(char *path, int flags);
int close(int h);
int read(int h, unsigned char *p, unsigned int n);
int seek(int h, unsigned int pos);
int ai_mfd;

int ai_mopen(void)
{
    if (ai_mfd >= 3) close(ai_mfd);
    ai_mfd = open("ailm.dat", 1);
    if (ai_mfd < 0) {
        ai_mfd = 0;
        return -1;
    }
    return 0;
}

unsigned int ai_mstat(void)
{
    unsigned int total;
    unsigned int ask;
    int got;
    if (ai_mopen() != 0) return 0;
    total = 0;
    while (1) {
        if (total == 65535) {
            got = read(ai_mfd, ai_mstage, 1);
            if (got != 0) {
                close(ai_mfd);
                ai_mfd = 0;
                return 0;
            }
            break;
        }
        ask = 65535 - total;
        if (ask > 64) ask = 64;
        got = read(ai_mfd, ai_mstage, ask);
        if (got < 0 || (unsigned int)got > ask) {
            close(ai_mfd);
            ai_mfd = 0;
            return 0;
        }
        if (got == 0) break;
        total = total + (unsigned int)got;
    }
    if (seek(ai_mfd, 0) != 0) {
        close(ai_mfd);
        ai_mfd = 0;
        return 0;
    }
    return total;
}

int ai_mseek(unsigned int pos)
{
    if (ai_mfd < 3) return -1;
    return seek(ai_mfd, pos);
}

int ai_mread(unsigned char *p, unsigned int n)
{
    if (ai_mfd < 3) return -1;
    return read(ai_mfd, p, n);
}

'''
s = once(s, "int ai_readfull(unsigned char *p, unsigned int n)\n", bridge + "int ai_readfull(unsigned char *p, unsigned int n)\n", "aimatch bridge insertion")
write(p, s, "ascii")


# Explicit application-side line echo/editing.
p = "usr/src/ailmzx48/ailmzx48.c"
s = text(p, "ascii")
readline = '''int ai_readline(void)
{
    unsigned int n;
    int c;
    int bad;
    n = 0;
    bad = 0;
    while (1) {
        c = getchar();
        if (c < 0) return -1;
        if (ai_drop_lf) {
            ai_drop_lf = 0;
            if (c == 10) continue;
        }
        if (c == 13) {
            ai_drop_lf = 1;
            putchar(10);
            break;
        }
        if (c == 10) {
            putchar(10);
            break;
        }
        if (c == 8 || c == 127) {
            if (n != 0 && !bad) {
                n = n - 1;
                putchar(8);
                putchar(' ');
                putchar(8);
            }
            continue;
        }
        if (c < 32 || c > 126) {
            bad = 1;
            continue;
        }
        if (n < 191 && !bad) {
            ai_in[n] = c;
            n = n + 1;
            putchar(c);
        } else {
            bad = 1;
        }
    }
    ai_in[n] = 0;
    if (bad) return -2;
    return (int)n;
}

'''
s = section(s, "int ai_readline(void)\n", "int ai_isq(void)\n", readline, "ailmzx48 readline")
write(p, s, "ascii")


# Training harness now exercises generic object I/O, with short-read stress only.
p = "usr/src/ailmzx48/tooling/run_iteration.py"
s = text(p)
modelvm = '''class ModelVM(RomMathVM):
    def __init__(self, *args, **kwargs):
        self.model_calls = 0
        self.model_bytes = 0
        self.model_seeks = 0
        self.model_max_request = 0
        self.model_pattern = (1, 7, 3, 64, 2, 11)
        super().__init__(*args, **kwargs)

    def _b_read(self, args):
        count = self._to_unsigned(args[2])
        if count > self.model_max_request:
            self.model_max_request = count
        cap = self.model_pattern[self.model_calls % len(self.model_pattern)]
        self.model_calls += 1
        limited = list(args)
        limited[2] = Value(UINT, min(count, cap))
        result = super()._b_read(limited)
        got = int(result.data)
        if got > 0:
            self.model_bytes += got
        return result

    def _b_seek(self, args):
        result = super()._b_seek(args)
        if int(result.data) == 0:
            self.model_seeks += 1
        return result


'''
s = section(s, "class ModelVM(RomMathVM):\n", "class TraceScreen(ZXScreen):\n", modelvm, "run_iteration ModelVM")
s = once(s, "from c48.typesys import INT, UINT\n", "from c48.typesys import UINT\n", "run_iteration imports")
derived = '''def derived_reply(text: str, prompt: str) -> str:
    if text.endswith("> "):
        text = text[:-2]
    text = text.strip()
    prefix = prompt + "\n"
    if text.startswith(prefix):
        text = text[len(prefix):]
    return text.strip()


'''
s = section(s, "def derived_reply(text: str) -> str:\n", "def main() -> int:\n", derived, "run_iteration reply parser")
s = once(
    s,
    '    run([sys.executable, "-B", str(COMP / "c48.py"),\n         str(SRC), "-o", str(BIN)], remaining)\n',
    '    run([sys.executable, "-B", str(COMP / "c48.py"),\n         str(SRC), "-o", str(BIN)], remaining)\n    (BIN.parent / "ailm.dat").write_bytes(COLD.read_bytes())\n',
    "run_iteration model package copy",
)
s = once(s, "                 model_data=COLD.read_bytes(),\n", "", "run_iteration model_data removal")
s = once(s, '        reply = derived_reply(event["text"])\n', '        reply = derived_reply(event["text"], prompt)\n', "run_iteration reply call")
write(p, s)


# Development header exposes the generic read-only subset.
p = "usr/src/c48host.h"
s = text(p, "ascii")
io = '''int open(char *path, int flags);
int close(int h);
int read(int h, void *p, unsigned int n);
int seek(int h, unsigned int pos);
'''
s = once(s, "int getchar(void);\n", io + "int getchar(void);\n", "c48host I/O prototypes")
write(p, s, "ascii")


# Classify packaged DAT resources.
p = "compiler/check_license_headers.py"
s = text(p)
s = once(
    s,
    '".json", ".bin", ".png", ".c48b", ".docx", ".zip", ".rom"',
    '".json", ".bin", ".dat", ".png", ".c48b", ".docx", ".zip", ".rom"',
    "license DAT suffix",
)
write(p, s)


# GUI regression now requires lossless typeahead.
p = "compiler/tests/test_gui_framebuffer.py"
s = text(p)
test = '''    def test_typeahead_fifo_preserves_rapid_text(self):
        display = TkDisplay(new_screen())
        expected = b"rapid text\\n"
        for value in expected:
            self.assertTrue(display._offer_key(value))
        actual = bytes(display.input_char() for _ in expected)
        self.assertEqual(actual, expected)

'''
s = section(s, "    def test_nonwaiting_key_is_discarded(self):\n", "    def test_close_releases_waiting_getchar(self):\n", test, "GUI typeahead regression")
write(p, s)


# Runtime and exact human-regression coverage.
p = "compiler/tests/test_release_regressions.py"
s = text(p)
s = once(s, "from c48.screen import Font4x8, ZXScreen\nfrom c48.vm import C48VM\n", "from c48.screen import Font4x8, ZXScreen\nfrom c48.romvm import RomMathVM\nfrom c48.vm import C48VM\n", "release regression RomMathVM import")
tests = r'''    def test_rommath_read_only_object_io(self):
        src = (
            "int open(char *p,int f);int close(int h);"
            "int read(int h,unsigned char *p,unsigned int n);"
            "int seek(int h,unsigned int p);"
            "int main(void){unsigned char b[4];int h;"
            "h=open(\"data.dat\",1);if(h<3)return 1;"
            "if(read(h,b,3)!=3)return 2;"
            "if(b[0]!=10||b[1]!=20||b[2]!=30)return 3;"
            "if(seek(h,1)!=0)return 4;"
            "if(read(h,b,4)!=3)return 5;"
            "if(b[0]!=20||b[1]!=30||b[2]!=40)return 6;"
            "if(close(h)!=0)return 7;"
            "if(open(\"../bad\",1)>=0)return 8;return 0;}"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data.dat").write_bytes(bytes((10, 20, 30, 40)))
            program = compile_bytes(
                src.encode("ascii"), source_name="io.c", base_dir=root
            )
            screen = ZXScreen(Font4x8.load(FONT_PATH))
            vm = RomMathVM(program, screen, argv=[str(root / "prog.c48b")])
            self.assertEqual(vm.run(), 0)

    def test_ailmzx48_normal_runner_prompt_and_line_editing(self):
        from c48.format import read

        class TraceScreen(ZXScreen):
            def __init__(self, font):
                super().__init__(font)
                self.trace = bytearray()

            def putchar(self, c):
                self.trace.append(int(c) & 0xFF)
                return super().putchar(c)

        program_path = SDK / "usr/bin/ailmzx48/ailmzx48.c48b"
        program = read(program_path)
        first = iter(b"how popular was the spectrum?\nq\n")
        screen = TraceScreen(Font4x8.load(FONT_PATH))
        vm = RomMathVM(
            program,
            screen,
            argv=[str(program_path)],
            heap_size=0,
            max_steps=4000000,
            input_provider=lambda: next(first, -1),
        )
        self.assertEqual(vm.run(), 0)
        load = lambda name: int(vm._load(vm.global_lvalues[name]).data)
        self.assertEqual(load("ai_error"), 0)
        self.assertEqual(load("ai_turns"), 1)
        self.assertGreater(load("ai_mrecords"), 0)
        self.assertIn(b"how popular was the spectrum?\n", bytes(screen.trace))

        second = iter(b"qq\x08\n")
        screen2 = TraceScreen(Font4x8.load(FONT_PATH))
        vm2 = RomMathVM(
            program,
            screen2,
            argv=[str(program_path)],
            heap_size=0,
            input_provider=lambda: next(second, -1),
        )
        self.assertEqual(vm2.run(), 0)
        self.assertIn(b"qq\x08 \x08\n", bytes(screen2.trace))

'''
s = once(s, '\n\nif __name__ == "__main__":\n', "\n\n" + tests + 'if __name__ == "__main__":\n', "release regression test insertion")
write(p, s)


# Release expectations for two net-new tests and changed development header.
p = "compiler/release_expectations.json"
data = json.loads(text(p, "ascii"))
if data.get("test_count") != 340:
    raise SystemExit(f"unexpected starting test count {data.get('test_count')}")
data["test_count"] = 342
data["host_header_sha256"] = hashlib.sha256(Path("usr/src/c48host.h").read_bytes()).hexdigest()
write(p, json.dumps(data, indent=2) + "\n", "ascii")


# Document target/SDK mapping and terminal responsibility.
p = "usr/src/ailmzx48/AILMZX48-DETAILED-DESIGN.md"
s = text(p)
note = '''### 5.4A Runtime model-object name and SDK mapping

The runtime cold-model basename is frozen as `ailm.dat`. On native ZX-UX it is
a DAT object opened through the ordinary C48 object API with a relative path,
so normal process working-directory semantics apply. The SDK packages the same
logical model bytes beside the C48B1 artifact and its host runner resolves this
bounded read-only packaged-object subset there. This SDK placement is a
convenience mapping only; it does not create a target `/usr` namespace or an
AI-specific runtime ABI. `ailmzx48` obtains model bytes through generic object
I/O and no shipped execution path requires private `ai_m*` host builtins.

Interactive line editing is application-visible behavior: accepted printable
bytes are echoed, Enter emits LF, and destructive backspace is `BS`, space,
`BS`. The SDK GUI preserves bounded typeahead between adjacent `getchar()` calls
rather than discarding characters during framebuffer-presentation gaps.

'''
s = once(s, "### 5.5 Scheduler/process behavior\n", note + "### 5.5 Scheduler/process behavior\n", "design runtime mapping note")
write(p, s)


# Package the exact accepted model bytes beside the SDK executable.
Path("usr/bin/ailmzx48/ailm.dat").write_bytes(
    Path("usr/src/ailmzx48/model/cold-seed.bin").read_bytes()
)

print("C48 INPUT CLEANUP SOURCE TRANSFORM PASS")
