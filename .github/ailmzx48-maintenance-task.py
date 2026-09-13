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
    "unsigned char ai_hist[6];\n"
    "char ai_in[192];",
    "unsigned char ai_hist[6];\n"
    "unsigned int ai_litgen[8];\n"
    "unsigned char ai_litlen[8];\n"
    "char ai_litbuf[248];\n"
    "unsigned int ai_litset;\n"
    "unsigned int ai_lituse;\n"
    "char ai_in[192];",
    "literal globals",
)
src = once(
    src,
    "int ai_readline(void)\n{\n",
    "int ai_find(char *s)\n"
    "{\n"
    "    unsigned int i;\n"
    "    unsigned int j;\n"
    "    int ok;\n"
    "    i = 0;\n"
    "    while (ai_in[i] != 0) {\n"
    "        j = 0;\n"
    "        ok = 1;\n"
    "        while (s[j] != 0 && ai_in[i + j] != 0) {\n"
    "            if (ai_lower(ai_in[i + j]) != s[j]) ok = 0;\n"
    "            if (!ok) break;\n"
    "            j = j + 1;\n"
    "        }\n"
    "        if (s[j] == 0 && ok) return i;\n"
    "        i = i + 1;\n"
    "    }\n"
    "    return -1;\n"
    "}\n\n"
    "int ai_readline(void)\n{\n",
    "find helper",
)
src = once(
    src,
    "void ai_histpush(unsigned int topic)\n{\n",
    "int ai_namecmd(void)\n"
    "{\n"
    "    if (ai_find(\"my name is \") >= 0) return 1;\n"
    "    if (ai_has(\"what is my name\")) return 2;\n"
    "    if (ai_has(\"remember my name\")) return 2;\n"
    "    return 0;\n"
    "}\n\n"
    "int ai_setname(void)\n"
    "{\n"
    "    int pos;\n"
    "    unsigned int start;\n"
    "    unsigned int n;\n"
    "    unsigned int i;\n"
    "    unsigned int gen;\n"
    "    pos = ai_find(\"my name is \");\n"
    "    if (pos < 0) return 0;\n"
    "    start = pos + 11;\n"
    "    n = 0;\n"
    "    while (ai_in[start + n] != 0 && n < 32) {\n"
    "        n = n + 1;\n"
    "    }\n"
    "    if (n == 0 || n > 31) return 0;\n"
    "    gen = ai_litgen[0] + 1;\n"
    "    if (gen == 0 || gen > 4095) gen = 1;\n"
    "    ai_litgen[0] = gen;\n"
    "    ai_litlen[0] = n;\n"
    "    i = 0;\n"
    "    while (i < n) {\n"
    "        ai_litbuf[i] = ai_in[start + i];\n"
    "        i = i + 1;\n"
    "    }\n"
    "    ai_litset = 1;\n"
    "    return 1;\n"
    "}\n\n"
    "void ai_putraw(char *s)\n"
    "{\n"
    "    unsigned int i;\n"
    "    i = 0;\n"
    "    while (s[i] != 0) {\n"
    "        putchar(s[i]);\n"
    "        i = i + 1;\n"
    "    }\n"
    "}\n\n"
    "void ai_putname(void)\n"
    "{\n"
    "    unsigned int i;\n"
    "    i = 0;\n"
    "    while (i < ai_litlen[0]) {\n"
    "        putchar(ai_litbuf[i]);\n"
    "        i = i + 1;\n"
    "    }\n"
    "}\n\n"
    "void ai_nameack(void)\n"
    "{\n"
    "    ai_putraw(\"I will remember \" );\n"
    "    ai_putname();\n"
    "    puts(\".\");\n"
    "}\n\n"
    "void ai_nameans(void)\n"
    "{\n"
    "    if (ai_litlen[0] == 0) {\n"
    "        puts(\"I do not have your name yet.\");\n"
    "        return;\n"
    "    }\n"
    "    ai_lituse = 1;\n"
    "    ai_putraw(\"I remember your name as \" );\n"
    "    ai_putname();\n"
    "    puts(\".\");\n"
    "}\n\n"
    "void ai_histpush(unsigned int topic)\n{\n",
    "name literal helpers",
)
src = src.replace('ai_putraw("I will remember " );',
                  'ai_putraw("I will remember ");')
src = src.replace('ai_putraw("I remember your name as " );',
                  'ai_putraw("I remember your name as ");')
src = once(
    src,
    "    unsigned int topic;\n"
    "    unsigned int alt;\n",
    "    unsigned int topic;\n"
    "    unsigned int alt;\n"
    "    int namecmd;\n",
    "main name command variable",
)
src = once(
    src,
    "    ai_histuse = 0;\n"
    "    ai_hcount = 0;\n"
    "    ai_drop_lf = 0;",
    "    ai_histuse = 0;\n"
    "    ai_hcount = 0;\n"
    "    ai_litset = 0;\n"
    "    ai_lituse = 0;\n"
    "    ai_drop_lf = 0;",
    "literal init",
)
src = once(
    src,
    "            ai_ctxuse = 0;\n"
    "            ai_altuse = 0;\n"
    "            puts(\"Input rejected.\");",
    "            ai_ctxuse = 0;\n"
    "            ai_altuse = 0;\n"
    "            ai_histuse = 0;\n"
    "            ai_litset = 0;\n"
    "            ai_lituse = 0;\n"
    "            puts(\"Input rejected.\");",
    "literal reject reset",
)
src = once(
    src,
    "        ai_histuse = 0;\n"
    "        topic = ai_pick();",
    "        ai_histuse = 0;\n"
    "        ai_litset = 0;\n"
    "        ai_lituse = 0;\n"
    "        namecmd = ai_namecmd();\n"
    "        if (namecmd != 0) {\n"
    "            ai_otokens = 0;\n"
    "            ai_error = 0;\n"
    "            if (namecmd == 1) {\n"
    "                if (ai_setname()) {\n"
    "                    ai_nameack();\n"
    "                } else {\n"
    "                    puts(\"I could not store that name.\");\n"
    "                }\n"
    "            } else {\n"
    "                ai_nameans();\n"
    "            }\n"
    "            if (ai_turns != 65535) {\n"
    "                ai_turns = ai_turns + 1;\n"
    "            }\n"
    "            ai_yields = 0;\n"
    "            yield();\n"
    "            ai_yields = ai_yields + 1;\n"
    "            continue;\n"
    "        }\n"
    "        topic = ai_pick();",
    "literal main dispatch",
)
srcp.write_text(src, encoding="ascii", newline="\n")

runner = runp.read_text(encoding="utf-8")
runner = once(
    runner,
    '                     "ai_hcount"):',
    '                     "ai_hcount", "ai_litset",\n'
    '                     "ai_lituse"):',
    "literal diagnostics",
)
runner = once(
    runner,
    "    context_hits = 0\n"
    "    context_total = 0\n"
    "    alternate_hits = 0\n"
    "    alternate_total = 0\n"
    "    history_hits = 0\n"
    "    history_total = 0\n",
    "    lit_expect = req.get(\"expected_literal\")\n"
    "    if lit_expect is None:\n"
    "        lit_expect = [None] * len(prompts)\n"
    "    if not isinstance(lit_expect, list):\n"
    "        raise RuntimeError(\"expected_literal must be a list\")\n"
    "    if len(lit_expect) != len(prompts):\n"
    "        raise RuntimeError(\"expected_literal length mismatch\")\n"
    "    for expected in lit_expect:\n"
    "        if expected not in (None, \"none\", \"set\", \"use\"):\n"
    "            raise RuntimeError(\"invalid expected literal mode\")\n"
    "    context_hits = 0\n"
    "    context_total = 0\n"
    "    alternate_hits = 0\n"
    "    alternate_total = 0\n"
    "    history_hits = 0\n"
    "    history_total = 0\n"
    "    literal_hits = 0\n"
    "    literal_total = 0\n",
    "literal expectations",
)
runner = once(
    runner,
    "        if want_hist is not None:\n"
    "            history_total += 1\n"
    "            if hist_hit:\n"
    "                history_hits += 1\n"
    "        turns.append({",
    "        if want_hist is not None:\n"
    "            history_total += 1\n"
    "            if hist_hit:\n"
    "                history_hits += 1\n"
    "        want_lit = lit_expect[i]\n"
    "        if event[\"diag\"].get(\"ai_litset\") == 1:\n"
    "            used_lit = \"set\"\n"
    "        elif event[\"diag\"].get(\"ai_lituse\") == 1:\n"
    "            used_lit = \"use\"\n"
    "        else:\n"
    "            used_lit = \"none\"\n"
    "        lit_hit = want_lit is None or used_lit == want_lit\n"
    "        if want_lit is not None:\n"
    "            literal_total += 1\n"
    "            if lit_hit:\n"
    "                literal_hits += 1\n"
    "        turns.append({",
    "literal scoring",
)
runner = once(
    runner,
    "            \"history_hit\": hist_hit,\n"
    "        })",
    "            \"history_hit\": hist_hit,\n"
    "            \"expected_literal\": want_lit,\n"
    "            \"literal_mode\": used_lit,\n"
    "            \"literal_hit\": lit_hit,\n"
    "        })",
    "literal transcript",
)
runner = once(
    runner,
    "        \"history_ratio\": (\n"
    "            history_hits / history_total\n"
    "            if history_total else 1.0\n"
    "        ),\n"
    "        \"clean_exit\": status == 0,",
    "        \"history_ratio\": (\n"
    "            history_hits / history_total\n"
    "            if history_total else 1.0\n"
    "        ),\n"
    "        \"literal_hits\": literal_hits,\n"
    "        \"literal_total\": literal_total,\n"
    "        \"literal_ratio\": (\n"
    "            literal_hits / literal_total\n"
    "            if literal_total else 1.0\n"
    "        ),\n"
    "        \"clean_exit\": status == 0,",
    "literal score summary",
)
runp.write_text(runner, encoding="utf-8", newline="\n")

design = desp.read_text(encoding="utf-8")
design = once(
    design,
    "Revision: 0.18-draft",
    "Revision: 0.19-draft",
    "design revision",
)
marker = "### 6.1 No remote inference dependency"
note = (
    "Implementation measurement note (Revision 0.19): iteration 6 "
    "validated bounded recovery of earlier topics across intervening "
    "topic changes. The next prototype allocates the full designed "
    "272-byte session-literal storage as parallel C48 arrays (eight "
    "generation values, eight lengths, and 8 x 31 presentation bytes) "
    "while initially using slot 0 only for an exact user-name literal. "
    "Generation advances in the designed 1..4095 range on correction. "
    "This slice tests exact literal retention/correction; semantic refs, "
    "eight-slot eviction and L1/L2 invalidation remain future work.\n\n"
)
design = once(design, marker, note + marker, "design literal note")
desp.write_text(design, encoding="utf-8", newline="\n")

subprocess.run(
    [sys.executable, "-B", "compiler/c48.py",
     "usr/src/ailmzx48/ailmzx48.c", "-o",
     "usr/bin/ailmzx48/ailmzx48.c48b"],
    cwd=root,
    check=True,
)
print("session-literal prototype applied")
