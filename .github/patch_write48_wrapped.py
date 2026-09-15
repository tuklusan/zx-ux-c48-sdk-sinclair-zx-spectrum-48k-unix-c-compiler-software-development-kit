from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "usr/src/apps/write48.c"
BIN = ROOT / "usr/bin/apps/write48.c48b"
EXPECT = ROOT / "compiler/app_expectations.json"


def timed(name: str, payload: bytes, limit: float | None) -> float:
    cmd = ["python", "-B", "compiler/c48run.py", "--headless",
           "usr/bin/apps/write48.c48b"]
    t0 = time.perf_counter()
    try:
        cp = subprocess.run(cmd, cwd=ROOT, input=payload,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, timeout=20)
    except subprocess.TimeoutExpired:
        print(f"{name}: >20s TIMEOUT")
        if limit is not None:
            raise SystemExit(f"{name}: timeout")
        return 20.0
    dt = time.perf_counter() - t0
    print(f"{name}: {dt:.4f}s rc={cp.returncode}")
    if cp.returncode:
        raise SystemExit(cp.stderr.decode(errors="replace"))
    if limit is not None and dt > limit:
        raise SystemExit(f"{name}: too slow {dt:.3f}s > {limit:.3f}s")
    return dt


def patch() -> None:
    s = SRC.read_text(encoding="utf-8")
    pairs = [
        (
            """        if (pos == wr_len) {\n"
            "            if (fresh && col < 60) {\n"
            "                wr_rowsafe[row] = 1;\n"
            "                wr_rowlen[row] = col;\n"
            "            }\n""",
            """        if (pos == wr_len) {\n"
            "            wr_rowlen[row] = col;\n"
            "            if (fresh && col < 60)\n"
            "                wr_rowsafe[row] = 1;\n""",
        ),
        (
            """        if (c == '\\n') {\n"
            "            if (fresh && col < 60) {\n"
            "                wr_rowsafe[row] = 1;\n"
            "                wr_rowlen[row] = col;\n"
            "            }\n""",
            """        if (c == '\\n') {\n"
            "            wr_rowlen[row] = col;\n"
            "            if (fresh && col < 60)\n"
            "                wr_rowsafe[row] = 1;\n""",
        ),
        (
            """            col++;\n"
            "            pos++;\n"
            "            if (col >= 60) {\n""",
            """            col++;\n"
            "            pos++;\n"
            "            wr_rowlen[row] = col;\n"
            "            if (col >= 60) {\n""",
        ),
    ]
    for old, new in pairs:
        if s.count(old) != 1:
            raise SystemExit("write48 row metadata anchor mismatch")
        s = s.replace(old, new)

    start = s.index("int wr_fmove(int d)\n")
    end = s.index("\nint wr_fins(int c)\n", start)
    repl = r'''int wr_fmove(int d)
{
    int old;
    int next;
    int row;
    int col;
    int cc;
    if (!wr_drawn || wr_pcursor < 0)
        return 0;
    old = wr_pcursor;
    row = old / 60;
    col = old % 60;
    if (d > 0) {
        if (wr_cur >= wr_len)
            return 1;
        if (wr_doc[wr_cur] == '\n') {
            if (row >= 18)
                return 0;
            next = (row + 1) * 60;
        } else if (wr_cur + 1 >= wr_len) {
            if (col >= 59) {
                if (row >= 18)
                    return 0;
                next = (row + 1) * 60;
            } else {
                next = old + 1;
            }
        } else if (wr_doc[wr_cur + 1] == '\n') {
            if (col >= 59) {
                if (row >= 18)
                    return 0;
                next = (row + 1) * 60;
            } else {
                next = old + 1;
            }
        } else if (col + 1 >= wr_rowlen[row]) {
            if (row >= 18)
                return 0;
            next = (row + 1) * 60;
        } else {
            next = old + 1;
        }
        wr_cur++;
    } else {
        if (wr_cur <= 0)
            return 1;
        if (wr_doc[wr_cur - 1] == '\n') {
            if (row <= 0)
                return 0;
            next = (row - 1) * 60;
            next = next + wr_rowlen[row - 1];
        } else if (col > 0) {
            next = old - 1;
        } else {
            if (row <= 0 || wr_rowlen[row - 1] <= 0)
                return 0;
            next = (row - 1) * 60;
            next = next + wr_rowlen[row - 1] - 1;
        }
        wr_cur--;
    }
    cc = wr_prev[old];
    inverse(0);
    app_putc(old / 60 + 2, old % 60 + 2, cc);
    cc = wr_prev[next];
    if (cc == ' ')
        cc = '_';
    inverse(1);
    app_putc(next / 60 + 2, next % 60 + 2, cc);
    inverse(0);
    wr_pcursor = next;
    wr_ncursor = next;
    return 1;
}
'''
    s = s[:start] + repl + s[end:]
    bad = [(i, len(line)) for i, line in enumerate(s.splitlines(), 1)
           if len(line) > 64]
    if bad:
        raise SystemExit(f"64-column violations: {bad}")
    SRC.write_text(s, encoding="utf-8", newline="\n")


def update_hashes() -> None:
    data = json.loads(EXPECT.read_text(encoding="ascii"))
    app = data["apps"]["write48"]
    app["source_sha256"] = hashlib.sha256(SRC.read_bytes()).hexdigest()
    app["binary_sha256"] = hashlib.sha256(BIN.read_bytes()).hexdigest()
    EXPECT.write_text(json.dumps(data, indent=2) + "\n",
                      encoding="ascii", newline="\n")
    print("source", app["source_sha256"])
    print("binary", app["binary_sha256"])
    print("screen", app["screen_sha256"])


def test_before() -> None:
    timed("wrapped-before", b"66" + b"8" * 20 + b"q", None)


def test_after() -> None:
    timed("short-row-20", b"8" * 20 + b"q", 2.0)
    timed("wrapped-profile", b"66" + b"8" * 20 + b"q", 4.0)
    timed("deep-wrapped", b"6" * 5 + b"8" * 20 + b"q", 7.0)
    timed("wrapped-roundtrip",
          b"66" + b"8" * 20 + b"5" * 20 + b"q", 4.5)
    timed("typing-20", b"iabcdefghijklmnopqrst\x1bq", 2.0)


def sop() -> None:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = [Path(x.decode("utf-8", "surrogateescape"))
             for x in raw.split(b"\0") if x]
    text = {".py", ".c", ".h", ".md", ".txt", ".json",
            ".yml", ".yaml", ".bat", ".sh"}
    manifests = []
    for pass_no in (1, 2, 3):
        fresh = Path(tempfile.mkdtemp(prefix=f"w48-wrap-{pass_no}-"))
        defects = []
        files = bytes_n = lines_n = 0
        whole = hashlib.sha256()
        for rel in paths:
            dst = fresh / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
            data = dst.read_bytes()
            files += 1
            bytes_n += len(data)
            lines = data.splitlines(keepends=True)
            lines_n += len(lines)
            if data.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                defects.append("LFS pointer: " + rel.as_posix())
            if rel.suffix.lower() in text:
                for lineno, line in enumerate(lines, 1):
                    body = line.rstrip(b"\r\n")
                    if (body.startswith(b"<<<<<<< ") or body == b"=======" or
                            body.startswith(b">>>>>>> ")):
                        defects.append(f"conflict: {rel.as_posix()}:{lineno}")
            rb = rel.as_posix().encode("utf-8", "surrogateescape")
            whole.update(len(rb).to_bytes(4, "big"))
            whole.update(rb)
            whole.update(hashlib.sha256(data).digest())
        manifest = whole.hexdigest()
        manifests.append(manifest)
        print(f"SOP_PASS_{pass_no}: files={files} bytes={bytes_n} "
              f"lines={lines_n} defects={len(defects)} manifest={manifest}")
        if defects:
            raise SystemExit("\n".join(defects))
        shutil.rmtree(fresh)
    if len(set(manifests)) != 1:
        raise SystemExit(f"SoP manifests differ: {manifests}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["patch", "hash", "before", "after", "sop"])
    args = ap.parse_args()
    {"patch": patch, "hash": update_hashes, "before": test_before,
     "after": test_after, "sop": sop}[args.mode]()


if __name__ == "__main__":
    main()
