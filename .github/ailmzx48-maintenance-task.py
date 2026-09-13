#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
a = root / "usr" / "src" / "ailmzx48"
srcp = a / "ailmzx48.c"
runp = a / "tooling" / "run_iteration.py"
desp = a / "AILMZX48-DETAILED-DESIGN.md"


def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected 1 match, found {n}")
    return text.replace(old, new, 1)

src = srcp.read_text(encoding="ascii")
src = once(
    src,
    "unsigned int ai_altstate;\nchar ai_in[192];",
    "unsigned int ai_altstate;\n"
    "unsigned int ai_histuse;\n"
    "unsigned int ai_hcount;\n"
    "unsigned char ai_hist[6];\n"
    "char ai_in[192];",
    "source globals",
)
src = once(
    src,
    "unsigned int ai_pick(void)\n{\n",
    "void ai_histpush(unsigned int topic)\n"
    "{\n"
    "    unsigned int i;\n"
    "    if (ai_hcount < 6) {\n"
    "        ai_hist[ai_hcount] = topic;\n"
    "        ai_hcount = ai_hcount + 1;\n"
    "        return;\n"
    "    }\n"
    "    i = 1;\n"
    "    while (i < 6) {\n"
    "        ai_hist[i - 1] = ai_hist[i];\n"
    "        i = i + 1;\n"
    "    }\n"
    "    ai_hist[5] = topic;\n"
    "}\n\n"
    "unsigned int ai_pick(void)\n{\n",
    "history push function",
)
src = once(
    src,
    "    if (ai_has(\"computer\")) return ai_t_spec;\n"
    "    if (ai_havectx) {",
    "    if (ai_has(\"computer\")) return ai_t_spec;\n"
    "    if (ai_hcount != 0 && ai_has(\"go back\")) {\n"
    "        ai_ctxuse = 1;\n"
    "        ai_histuse = 1;\n"
    "        return ai_hist[ai_hcount - 1];\n"
    "    }\n"
    "    if (ai_havectx) {",
    "history selection",
)
src = once(
    src,
    "    ai_altuse = 0;\n"
    "    ai_altstate = 0;\n"
    "    ai_drop_lf = 0;",
    "    ai_altuse = 0;\n"
    "    ai_altstate = 0;\n"
    "    ai_histuse = 0;\n"
    "    ai_hcount = 0;\n"
    "    ai_drop_lf = 0;",
    "history init",
)
src = once(
    src,
    "        ai_ctxuse = 0;\n"
    "        ai_altuse = 0;\n"
    "        topic = ai_pick();",
    "        ai_ctxuse = 0;\n"
    "        ai_altuse = 0;\n"
    "        ai_histuse = 0;\n"
    "        topic = ai_pick();",
    "history turn reset",
)
src = once(
    src,
    "        ai_generate(topic, alt);\n"
    "        puts(ai_out);\n"
    "        ai_lasttop = topic;",
    "        ai_generate(topic, alt);\n"
    "        puts(ai_out);\n"
    "        if (ai_histuse) {\n"
    "            if (ai_hcount != 0) {\n"
    "                ai_hcount = ai_hcount - 1;\n"
    "            }\n"
    "        } else {\n"
    "            if (!ai_ctxuse && ai_havectx) {\n"
    "                if (topic != ai_lasttop) {\n"
    "                    ai_histpush(ai_lasttop);\n"
    "                }\n"
    "            }\n"
    "        }\n"
    "        ai_lasttop = topic;",
    "history commit",
)
srcp.write_text(src, encoding="ascii", newline="\n")

runner = runp.read_text(encoding="utf-8")
runner = once(
    runner,
    '                     "ai_altstate"):',
    '                     "ai_altstate", "ai_histuse",\n'
    '                     "ai_hcount"):',
    "runner diagnostics",
)
runner = once(
    runner,
    "    context_hits = 0\n"
    "    context_total = 0\n"
    "    alternate_hits = 0\n"
    "    alternate_total = 0\n",
    "    hist_expect = req.get(\"expected_history\")\n"
    "    if hist_expect is None:\n"
    "        hist_expect = [None] * len(prompts)\n"
    "    if not isinstance(hist_expect, list):\n"
    "        raise RuntimeError(\"expected_history must be a list\")\n"
    "    if len(hist_expect) != len(prompts):\n"
    "        raise RuntimeError(\"expected_history length mismatch\")\n"
    "    for expected in hist_expect:\n"
    "        if expected is not None and not isinstance(expected, bool):\n"
    "            raise RuntimeError(\"expected history must be bool or null\")\n"
    "    context_hits = 0\n"
    "    context_total = 0\n"
    "    alternate_hits = 0\n"
    "    alternate_total = 0\n"
    "    history_hits = 0\n"
    "    history_total = 0\n",
    "runner history expectations",
)
runner = once(
    runner,
    "        want_alt = alt_expect[i]\n"
    "        used_alt = event[\"diag\"].get(\"ai_altuse\") == 1\n"
    "        alt_hit = want_alt is None or used_alt == want_alt\n"
    "        if want_alt is not None:\n"
    "            alternate_total += 1\n"
    "            if alt_hit:\n"
    "                alternate_hits += 1\n",
    "        want_alt = alt_expect[i]\n"
    "        used_alt = event[\"diag\"].get(\"ai_altuse\") == 1\n"
    "        alt_hit = want_alt is None or used_alt == want_alt\n"
    "        if want_alt is not None:\n"
    "            alternate_total += 1\n"
    "            if alt_hit:\n"
    "                alternate_hits += 1\n"
    "        want_hist = hist_expect[i]\n"
    "        used_hist = event[\"diag\"].get(\"ai_histuse\") == 1\n"
    "        hist_hit = want_hist is None or used_hist == want_hist\n"
    "        if want_hist is not None:\n"
    "            history_total += 1\n"
    "            if hist_hit:\n"
    "                history_hits += 1\n",
    "runner history scoring",
)
runner = once(
    runner,
    "            \"alternate_hit\": alt_hit,\n"
    "        })",
    "            \"alternate_hit\": alt_hit,\n"
    "            \"expected_history\": want_hist,\n"
    "            \"history_used\": used_hist,\n"
    "            \"history_hit\": hist_hit,\n"
    "        })",
    "runner history transcript",
)
runner = once(
    runner,
    "        \"alternate_ratio\": (\n"
    "            alternate_hits / alternate_total\n"
    "            if alternate_total else 1.0\n"
    "        ),\n"
    "        \"clean_exit\": status == 0,",
    "        \"alternate_ratio\": (\n"
    "            alternate_hits / alternate_total\n"
    "            if alternate_total else 1.0\n"
    "        ),\n"
    "        \"history_hits\": history_hits,\n"
    "        \"history_total\": history_total,\n"
    "        \"history_ratio\": (\n"
    "            history_hits / history_total\n"
    "            if history_total else 1.0\n"
    "        ),\n"
    "        \"clean_exit\": status == 0,",
    "runner history score summary",
)
runp.write_text(runner, encoding="utf-8", newline="\n")

design = desp.read_text(encoding="utf-8")
design = once(
    design,
    "Revision: 0.17-draft",
    "Revision: 0.18-draft",
    "design revision",
)
marker = "### 6.1 No remote inference dependency"
note = (
    "Implementation measurement note (Revision 0.18): iteration 5 "
    "validated deterministic learned secondary continuations without "
    "breaking immediate topic context. The next bounded prototype adds "
    "a six-entry recent-distinct-topic history so explicit `go back` "
    "requests can recover prior topics across intervening topic changes. "
    "This is instrumentation for conversational-history behavior only; "
    "it is not the final L0/L1/L2 representation and makes no expanded "
    "context-window claim until the designed compressor is implemented "
    "and stress-tested.\n\n"
)
design = once(design, marker, note + marker, "design history note")
desp.write_text(design, encoding="utf-8", newline="\n")

subprocess.run(
    [sys.executable, "-B", "compiler/c48.py",
     "usr/src/ailmzx48/ailmzx48.c", "-o",
     "usr/bin/ailmzx48/ailmzx48.c48b"],
    cwd=root,
    check=True,
)
print("bounded topic-history prototype applied")
