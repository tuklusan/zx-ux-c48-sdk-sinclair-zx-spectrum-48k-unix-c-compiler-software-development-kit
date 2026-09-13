#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def rep(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    if s.count(old) != 1:
        raise RuntimeError(f"bad anchor {path}: {old!r} count={s.count(old)}")
    p.write_text(s.replace(old, new), encoding="utf-8", newline="\n")

rep("verify_gui_desktop.py",
    "from c48.gui import FRAME_HEIGHT, FRAME_WIDTH, footer_text\n",
    "from c48.gui import (\n    FRAME_HEIGHT, FRAME_WIDTH, VISUAL_FRAME_DWELL_MS, footer_text,\n)\n")
rep("verify_gui_desktop.py",
    "def _start(program: Path, probe: Path) -> subprocess.Popen:\n",
    "def _start(program: Path, probe: Path, *args: str) -> subprocess.Popen:\n")
rep("verify_gui_desktop.py",
    "        _launcher_command(str(program)),\n",
    "        _launcher_command(str(program), *args),\n")
visual = '''
def _visual_progression(evidence: Path) -> dict:
    name = "visual-progression"
    probe = evidence / f"probe-{name}.jsonl"
    process = _start(ROOT / "usr/bin/demos/sprites.c48b", probe, "6")
    title = "ZX-UX C48 - sprites.c48b"
    try:
        window = _wait_event(probe, "window_ready", process=process)
        done = _wait_event(
            probe,
            "program_done",
            process=process,
            predicate=lambda r: int(r["status"]) == 0
            and r["error_type"] is None,
        )
        records = [
            r for r in _records(probe)
            if r.get("event") == "frame_presented"
            and r.get("reason") == "yield"
            and int(r["seq"]) < int(done["seq"])
        ]
        if len(records) != 6:
            raise AssertionError(
                f"expected six non-droppable yield frames, got {len(records)}"
            )
        generations = [int(r["generation"]) for r in records]
        if generations != sorted(set(generations)):
            raise AssertionError(
                f"presentation generations are not strictly ordered: {generations}"
            )
        rendered = {
            int(r["generation"]): r for r in _records(probe)
            if r.get("event") == "frame_rendered"
        }
        hashes = []
        for record in records:
            generation = int(record["generation"])
            frame = rendered.get(generation)
            if frame is None or int(frame["seq"]) >= int(record["seq"]):
                raise AssertionError(
                    f"generation {generation} released without prior Tk commit"
                )
            hashes.append(str(frame["frame_sha256"]))
            if int(record["dwell_ms"]) != VISUAL_FRAME_DWELL_MS:
                raise AssertionError(
                    f"generation {generation} used wrong visual dwell"
                )
        if len(set(hashes)) < 5:
            raise AssertionError(
                f"animation exposed too few distinct frames: {hashes}"
            )
        intervals = [
            (int(b["monotonic_ns"]) - int(a["monotonic_ns"])) / 1_000_000.0
            for a, b in zip(records, records[1:])
        ]
        floor = max(1.0, VISUAL_FRAME_DWELL_MS - 10.0)
        if any(value < floor for value in intervals):
            raise AssertionError(
                f"visual-release intervals below dwell floor: {intervals}"
            )
        frame = _latest(probe, "frame_rendered")
        capture = _screenshot(evidence, name, window, frame)
        _send_key(process, title, "space", shift=True)
        stdout, stderr = _finish(process, 0)
        return {
            "capture": capture,
            "generations": generations,
            "frame_sha256": hashes,
            "release_intervals_ms": [round(v, 3) for v in intervals],
            "visual_dwell_ms": VISUAL_FRAME_DWELL_MS,
            "stdout": stdout,
            "stderr": stderr,
        }
    finally:
        if process.poll() is None:
            _terminate_process_tree(process)


'''
rep("verify_gui_desktop.py", "\ndef _forest(evidence: Path) -> dict:\n",
    visual + "def _forest(evidence: Path) -> dict:\n")
rep("verify_gui_desktop.py",
    '    for name, test in (\n        ("forest", _forest),\n',
    '    for name, test in (\n        ("visual-progression", _visual_progression),\n        ("forest", _forest),\n')
rep("verify_gui_desktop.py",
    '    for scratch in evidence.glob("probe-*-frame.ppm"):\n',
    '    for scratch in evidence.glob("probe-*-frame-*.ppm"):\n')
