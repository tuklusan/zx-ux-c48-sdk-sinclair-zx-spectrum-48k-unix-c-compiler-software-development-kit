#!/usr/bin/env python3
# Maintenance task intentionally performs no source edits.
# The stable maintenance workflow removes this file, regenerates
# MANIFEST.sha256, runs the full release verifier, and checkpoints main.
from pathlib import Path

root = Path(__file__).resolve().parents[1]
required = root / ".github" / "workflows" / "ailmzx48-maintenance.yml"
if not required.is_file():
    raise SystemExit("stable maintenance workflow missing")
for retired in (
    root / ".github" / "workflows" / "ailmzx48-bootstrap.yml",
    root / ".github" / "workflows" / "ailmzx48-bootstrap-retry.yml",
):
    if retired.exists():
        raise SystemExit("obsolete bootstrap workflow still present")
print("ailmzx48 maintenance topology clean")
