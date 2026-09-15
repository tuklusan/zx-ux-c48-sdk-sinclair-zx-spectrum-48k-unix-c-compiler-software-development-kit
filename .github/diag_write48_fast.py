#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import time

root = Path.cwd()
src = root / "usr/src/apps/write48.c"
original = src.read_text(encoding="utf-8")


def subfunc(pattern: str, replacement: str, text: str) -> str:
    return re.sub(pattern, lambda _m: replacement, text, flags=re.S)


def build(name: str) -> Path:
    out = root / f"usr/bin/apps/{name}.c48b"
    subprocess.run(
        ["python", "-B", "compiler/c48.py", str(src), "-o", str(out)],
        check=True,
    )
    return out


def bench(label: str, binary: Path, data: bytes) -> None:
    t0 = time.perf_counter()
    cp = subprocess.run(
        ["python", "-B", "compiler/c48run.py", "--headless", str(binary)],
        input=data,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    dt = time.perf_counter() - t0
    if cp.returncode:
        raise SystemExit(cp.stderr.decode(errors="replace"))
    print(f"{label}: {dt:.4f}s")


text = original.replace(
    '#include "appapi.h"\n',
    '#include "appapi.h"\nvoid *memset(void *d, int c, unsigned int n);\n',
)
text = text.replace(
    "unsigned char wr_pinv[1140];\nunsigned char wr_ninv[1140];\n",
    "char wr_line[61];\nint wr_pcursor;\nint wr_ncursor;\n"
    "int wr_rowsafe[19];\nint wr_rowlen[19];\nint wr_fast;\n",
)
text = subfunc(
    r"void wr_insert_char\(int c\)\n\{.*?\n\}\n\nvoid wr_delete_at",
    """void wr_insert_char(int c)
{
    int n;
    if (wr_len >= 1899)
        return;
    n = wr_len - wr_cur;
    if (n > 0)
        memmove(wr_doc + wr_cur + 1, wr_doc + wr_cur, (unsigned int)n);
    wr_doc[wr_cur] = (char)c;
    wr_len++;
    wr_cur++;
    wr_doc[wr_len] = 0;
}

void wr_delete_at""",
    text,
)
text = subfunc(
    r"void wr_delete_at\(int pos\)\n\{.*?\n\}\n\nint wr_word_len",
    """void wr_delete_at(int pos)
{
    int n;
    if (pos < 0 || pos >= wr_len)
        return;
    n = wr_len - pos;
    memmove(wr_doc + pos, wr_doc + pos + 1, (unsigned int)n);
    wr_len--;
    if (wr_cur > wr_len)
        wr_cur = wr_len;
}

int wr_word_len""",
    text,
)
text = subfunc(
    r"void wr_blank\(void\)\n\{.*?\n\}",
    """void wr_blank(void)
{
    int i;
    memset(wr_next, ' ', 1140u);
    wr_ncursor = -1;
    for (i = 0; i < 19; i++) {
        wr_rowsafe[i] = 0;
        wr_rowlen[i] = 0;
    }
}""",
    text,
)
text = subfunc(
    r"void wr_build\(void\)\n\{.*?\n\}\n\nvoid wr_diff",
    """void wr_build(void)
{
    int row;
    int col;
    int pos;
    int n;
    int c;
    int cell;
    int fresh;
    wr_blank();
    row = 0;
    col = 0;
    pos = wr_view;
    fresh = (wr_view == 0 || wr_doc[wr_view - 1] == '\\n');
    while (row < 19 && pos <= wr_len) {
        if (pos == wr_len) {
            if (fresh && col < 60) {
                wr_rowsafe[row] = 1;
                wr_rowlen[row] = col;
            }
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            break;
        }
        c = wr_doc[pos];
        if (c == '\\n') {
            if (fresh && col < 60) {
                wr_rowsafe[row] = 1;
                wr_rowlen[row] = col;
            }
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            row++;
            col = 0;
            pos++;
            fresh = 1;
        } else {
            if (c != ' ' && col > 0 &&
                (pos == wr_view || pos == 0 || wr_doc[pos - 1] == ' ' ||
                 wr_doc[pos - 1] == '\\n')) {
                n = wr_word_len(pos);
                if (col + n > 60) {
                    row++;
                    col = 0;
                    fresh = 0;
                    if (row >= 19)
                        break;
                }
            }
            cell = row * 60 + col;
            wr_next[cell] = (char)c;
            if (pos == wr_cur)
                wr_ncursor = cell;
            col++;
            pos++;
            if (col >= 60) {
                row++;
                col = 0;
                fresh = 0;
            }
        }
    }
}

void wr_diff""",
    text,
)
text = subfunc(
    r"void wr_diff\(void\)\n\{.*?\n\}\n\nvoid wr_status",
    """void wr_diff(void)
{
    int row;
    int col;
    int base;
    int dirty;
    int cc;
    for (row = 0; row < 19; row++) {
        base = row * 60;
        dirty = !wr_drawn;
        col = 0;
        while (!dirty && col < 60) {
            if (wr_prev[base + col] != wr_next[base + col])
                dirty = 1;
            col++;
        }
        if (!dirty && wr_pcursor >= base && wr_pcursor < base + 60)
            dirty = 1;
        if (!dirty && wr_ncursor >= base && wr_ncursor < base + 60)
            dirty = 1;
        if (dirty) {
            memmove(wr_line, wr_next + base, 60u);
            wr_line[60] = 0;
            inverse(0);
            print_at(row + 2, 2, wr_line);
            if (wr_ncursor >= base && wr_ncursor < base + 60) {
                cc = wr_next[wr_ncursor];
                if (cc == ' ')
                    cc = '_';
                inverse(1);
                app_putc(row + 2, wr_ncursor - base + 2, cc);
                inverse(0);
            }
        }
    }
    memmove(wr_prev, wr_next, 1140u);
    wr_pcursor = wr_ncursor;
    wr_drawn = 1;
}

void wr_status""",
    text,
)
text = re.sub(
    r"    for \(i = 0; i < 1140; i\+\+\) \{\n"
    r"        wr_prev\[i\] = 0;\n"
    r"        wr_pinv\[i\] = 0;\n"
    r"    \}\n"
    r"    wr_drawn = 0;",
    "    memset(wr_prev, 0, 1140u);\n"
    "    wr_pcursor = -1;\n"
    "    wr_ncursor = -1;\n"
    "    wr_fast = 0;\n"
    "    wr_drawn = 0;",
    text,
)
fast_helpers = """
void wr_draw_fast_row(int row)
{
    int base;
    int cc;
    base = row * 60;
    memmove(wr_line, wr_prev + base, 60u);
    wr_line[60] = 0;
    inverse(0);
    print_at(row + 2, 2, wr_line);
    if (wr_pcursor >= base && wr_pcursor < base + 60) {
        cc = wr_prev[wr_pcursor];
        if (cc == ' ')
            cc = '_';
        inverse(1);
        app_putc(row + 2, wr_pcursor - base + 2, cc);
        inverse(0);
    }
}

int wr_fast_insert_char(int c)
{
    int row;
    int col;
    int base;
    int n;
    int len;
    if (!wr_drawn || wr_pcursor < 0 || wr_len >= 1899)
        return 0;
    row = wr_pcursor / 60;
    col = wr_pcursor % 60;
    if (!wr_rowsafe[row])
        return 0;
    len = wr_rowlen[row];
    if (len >= 59 || col > len)
        return 0;
    n = wr_len - wr_cur;
    if (n > 0)
        memmove(wr_doc + wr_cur + 1, wr_doc + wr_cur, (unsigned int)n);
    wr_doc[wr_cur] = (char)c;
    wr_len++;
    wr_cur++;
    wr_doc[wr_len] = 0;
    base = row * 60;
    if (len > col)
        memmove(wr_prev + base + col + 1,
                wr_prev + base + col,
                (unsigned int)(len - col));
    wr_prev[base + col] = (char)c;
    wr_rowlen[row] = len + 1;
    wr_pcursor = base + col + 1;
    wr_draw_fast_row(row);
    return 1;
}

int wr_fast_backspace(void)
{
    int row;
    int col;
    int base;
    int n;
    int len;
    if (!wr_drawn || wr_pcursor < 0 || wr_cur <= 0)
        return 0;
    row = wr_pcursor / 60;
    col = wr_pcursor % 60;
    if (!wr_rowsafe[row] || col <= 0)
        return 0;
    len = wr_rowlen[row];
    n = wr_len - (wr_cur - 1);
    memmove(wr_doc + wr_cur - 1, wr_doc + wr_cur, (unsigned int)n);
    wr_len--;
    wr_cur--;
    base = row * 60;
    if (len > col)
        memmove(wr_prev + base + col - 1,
                wr_prev + base + col,
                (unsigned int)(len - col));
    wr_prev[base + len - 1] = ' ';
    wr_rowlen[row] = len - 1;
    wr_pcursor = base + col - 1;
    wr_draw_fast_row(row);
    return 1;
}
"""
text = text.replace("\nvoid wr_insert_key(void)\n", fast_helpers + "\nvoid wr_insert_key(void)\n")
text = subfunc(
    r"void wr_insert_key\(void\)\n\{.*?\n\}\n\nint main",
    """void wr_insert_key(void)
{
    int c;
    wr_fast = 0;
    c = getchar();
    if (c == 27) {
        wr_insert = 0;
        return;
    }
    if (c == 8) {
        if (wr_cur > 0) {
            if (wr_fast_backspace())
                wr_fast = 1;
            else {
                wr_cur--;
                wr_delete_at(wr_cur);
            }
        }
        return;
    }
    if (c == 10 || c == 13) {
        wr_insert_char('\\n');
        return;
    }
    if (c >= 32 && c <= 126) {
        if (wr_fast_insert_char(c))
            wr_fast = 1;
        else
            wr_insert_char(c);
    }
}

int main""",
    text,
)
text = text.replace(
    "        if (wr_insert) {\n            wr_insert_key();\n        } else {",
    "        wr_fast = 0;\n"
    "        if (wr_insert) {\n"
    "            wr_insert_key();\n"
    "        } else {",
)
text = text.replace(
    "        wr_ensure();\n        wr_render();\n",
    "        {\n"
    "            int old_view;\n"
    "            old_view = wr_view;\n"
    "            wr_ensure();\n"
    "            if (!wr_fast || wr_view != old_view)\n"
    "                wr_render();\n"
    "        }\n",
)
if "wr_pinv" in text or "wr_ninv" in text:
    raise SystemExit("old inverse arrays remain")
src.write_text(text, encoding="utf-8", newline="\n")
binary = build("write48-fast-diag")
bench("fast-1", binary, b"ia\x1bq")
bench("fast-5", binary, b"iabcde\x1bq")
bench("fast-20", binary, b"iabcdefghijklmnopqrst\x1bq")
subprocess.run(
    ["python", "-B", "compiler/c48run.py", "--headless", str(binary), "verify"],
    check=True,
)
print("fast candidate verify PASS")
