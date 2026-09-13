#!/usr/bin/env python3
from pathlib import Path

ROOT = Path.cwd()
A = ROOT / "usr" / "src" / "ailmzx48"

def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(
            f"anchor mismatch {path}: {old!r} count={text.count(old)}"
        )
    path.write_text(
        text.replace(old, new, 1), encoding="utf-8", newline="\n"
    )


def main() -> int:
    design = A / "AILMZX48-DETAILED-DESIGN.md"
    replace_once(
        design,
        "corrected BASIC RUN and Hobbit sales claims remain within the\n"
        "  measured 8,458-byte A48M envelope;",
        "corrected BASIC RUN and Hobbit sales claims remain within the\n"
        "  measured 8,538-byte A48M envelope;",
    )

    checker = A / "evaluation" / "check_design_compliance.py"
    anchor = (
        '    require(a48m.get("logical_length") == 8538, '
        '"A48M logical length mismatch")\n'
    )
    insertion = anchor + (
        '    require("measured 8,458-byte A48M envelope" not in design,\n'
        '            "stale current A48M envelope remains in design")\n'
        '    require("measured 8,538-byte A48M envelope" in design,\n'
        '            "current factual A48M envelope marker missing")\n'
    )
    replace_once(checker, anchor, insertion)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
