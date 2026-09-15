from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPI = ROOT / "usr/src/apps/appapi.h"
WRSRC = ROOT / "usr/src/apps/write48.c"
WRBIN = ROOT / "usr/bin/apps/write48.c48b"
SHSRC = ROOT / "usr/src/apps/sheet48.c"
SHBIN = ROOT / "usr/bin/apps/sheet48.c48b"
EXPECT = ROOT / "compiler/app_expectations.json"

sys.path.insert(0, str(ROOT / "compiler"))
from c48.format import read
from c48.screen import Font4x8, ZXScreen
from c48.vm import C48VM


def rep(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label}: expected one anchor, got {text.count(old)}")
    return text.replace(old, new)


def patch_appapi() -> None:
    s = APPI.read_text(encoding="ascii")
    s = rep(
        s,
        "/* Shared helpers for interactive C48 applications. */\n",
        "/* Shared helpers for interactive C48 applications. */\n"
        "/* C48 has no include guards: include this once per app. */\n"
        "/* Runtime declarations are intentional. Normal SDK builds */\n"
        "/* do not inject declarations through <c48.h>. */\n",
        "appapi contract comment",
    )
    s = rep(
        s,
        "void *memmove(void *d, void *s, unsigned int n);\n",
        "void *memmove(void *d, void *s, unsigned int n);\n"
        "void *memset(void *d, int c, unsigned int n);\n",
        "appapi memset declaration",
    )
    s = rep(
        s,
        "        if (c == 27)\n            return 0;\n",
        "        if (c == 11 || c == 27)\n            return 0;\n",
        "appapi cancel key",
    )
    APPI.write_text(s, encoding="ascii", newline="\n")


def patch_write48() -> None:
    s = WRSRC.read_text(encoding="ascii")
    s = rep(
        s,
        '#include "appapi.h"\n'
        'void *memset(void *d, int c, unsigned int n);\n',
        '#include "appapi.h"\n',
        "remove local memset",
    )
    s = rep(
        s,
        "int wr_rowsafe[19];\nint wr_rowlen[19];\nint wr_fast;\n",
        "int wr_rowsafe[19];\nint wr_rowlen[19];\n"
        "int wr_rowpos[19];\nint wr_after;\nint wr_fast;\n",
        "row metadata globals",
    )

    old = '''void wr_blank(void)
{
    int i;
    memset(wr_next, ' ', 1140u);
    wr_ncursor = -1;
    for (i = 0; i < 19; i++) {
        wr_rowsafe[i] = 0;
        wr_rowlen[i] = 0;
    }
}

void wr_build(void)
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
            wr_rowlen[row] = col;
            if (fresh && col < 60)
                wr_rowsafe[row] = 1;
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            break;
        }
        c = wr_doc[pos];
        if (c == '\\n') {
            wr_rowlen[row] = col;
            if (fresh && col < 60)
                wr_rowsafe[row] = 1;
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            row++;
            col = 0;
            pos++;
            fresh = 1;
        } else {
            if (c != ' ' && col > 0 &&
                (pos == wr_view || pos == 0 ||
                 wr_doc[pos - 1] == ' ' ||
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
            wr_rowlen[row] = col;
            if (col >= 60) {
                row++;
                col = 0;
                fresh = 0;
            }
        }
    }
}
'''
    new = '''void wr_blank(void)
{
    int i;
    memset(wr_next, ' ', 1140u);
    wr_ncursor = -1;
    wr_after = wr_view;
    for (i = 0; i < 19; i++) {
        wr_rowsafe[i] = 0;
        wr_rowlen[i] = 0;
        wr_rowpos[i] = -1;
    }
}

void wr_layout(int first, int pos)
{
    int row;
    int col;
    int n;
    int c;
    int cell;
    int fresh;
    row = first;
    col = 0;
    fresh = (pos == 0 || wr_doc[pos - 1] == '\\n');
    if (row < 19)
        wr_rowpos[row] = pos;
    while (row < 19 && pos <= wr_len) {
        if (pos == wr_len) {
            wr_rowlen[row] = col;
            if (fresh && col < 60)
                wr_rowsafe[row] = 1;
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            break;
        }
        c = wr_doc[pos];
        if (c == '\\n') {
            wr_rowlen[row] = col;
            if (fresh && col < 60)
                wr_rowsafe[row] = 1;
            if (pos == wr_cur)
                wr_ncursor = row * 60 + col;
            row++;
            col = 0;
            pos++;
            fresh = 1;
            if (row < 19)
                wr_rowpos[row] = pos;
        } else {
            if (c != ' ' && col > 0 &&
                (pos == 0 || wr_doc[pos - 1] == ' ' ||
                 wr_doc[pos - 1] == '\\n')) {
                n = wr_word_len(pos);
                if (col + n > 60) {
                    row++;
                    col = 0;
                    fresh = 0;
                    if (row >= 19)
                        break;
                    wr_rowpos[row] = pos;
                }
            }
            cell = row * 60 + col;
            wr_next[cell] = (char)c;
            if (pos == wr_cur)
                wr_ncursor = cell;
            col++;
            pos++;
            wr_rowlen[row] = col;
            if (col >= 60) {
                row++;
                col = 0;
                fresh = 0;
                if (row < 19)
                    wr_rowpos[row] = pos;
            }
        }
    }
    wr_after = pos;
}

void wr_build(void)
{
    wr_blank();
    wr_layout(0, wr_view);
}
'''
    s = rep(s, old, new, "layout refactor")

    anchor = '''    memmove(wr_prev, wr_next, 1140u);
    wr_pcursor = wr_ncursor;
    wr_drawn = 1;
}

void wr_status(void)
'''
    replacement = '''    memmove(wr_prev, wr_next, 1140u);
    wr_pcursor = wr_ncursor;
    wr_drawn = 1;
}

void wr_diff_from(int first)
{
    int row;
    int col;
    int base;
    int dirty;
    int cc;
    int count;
    for (row = first; row < 19; row++) {
        base = row * 60;
        dirty = !wr_drawn;
        col = 0;
        while (!dirty && col < 60) {
            if (wr_prev[base + col] != wr_next[base + col])
                dirty = 1;
            col++;
        }
        if (!dirty && wr_pcursor >= base &&
            wr_pcursor < base + 60)
            dirty = 1;
        if (!dirty && wr_ncursor >= base &&
            wr_ncursor < base + 60)
            dirty = 1;
        if (dirty) {
            memmove(wr_line, wr_next + base, 60u);
            wr_line[60] = 0;
            inverse(0);
            print_at(row + 2, 2, wr_line);
            if (wr_ncursor >= base &&
                wr_ncursor < base + 60) {
                cc = wr_next[wr_ncursor];
                if (cc == ' ')
                    cc = '_';
                inverse(1);
                app_putc(row + 2,
                         wr_ncursor - base + 2, cc);
                inverse(0);
            }
        }
    }
    base = first * 60;
    count = 1140 - base;
    memmove(wr_prev + base, wr_next + base,
            (unsigned int)count);
    wr_pcursor = wr_ncursor;
    wr_drawn = 1;
}

void wr_status(void)
'''
    s = rep(s, anchor, replacement, "suffix diff")

    s = rep(
        s,
        '        print_at(21, 1, "INSERT: ESC CMD  BS DEL  ENTER NL");\n',
        '        print_at(21, 1, "INSERT: CAPS+7 CMD  BS DEL  ENTER NL");\n',
        "insert status",
    )

    status_end = '''    print_at(23, 1, "1992 DEMO CV - EDITABLE IN MEMORY");
    wr_stat = wr_insert;
}

int wr_down_view(void)
'''
    tail_code = '''    print_at(23, 1, "1992 DEMO CV - EDITABLE IN MEMORY");
    wr_stat = wr_insert;
}

int wr_tail(int first)
{
    int i;
    int base;
    int count;
    int start;
    if (first < 0)
        first = 0;
    if (first >= 19 || wr_rowpos[first] < 0)
        return 0;
    start = wr_rowpos[first];
    base = first * 60;
    if (base > 0)
        memmove(wr_next, wr_prev, (unsigned int)base);
    count = 1140 - base;
    memset(wr_next + base, ' ', (unsigned int)count);
    wr_ncursor = -1;
    for (i = first; i < 19; i++) {
        wr_rowsafe[i] = 0;
        wr_rowlen[i] = 0;
        wr_rowpos[i] = -1;
    }
    wr_layout(first, start);
    if (wr_ncursor < 0)
        return 0;
    wr_diff_from(first);
    wr_status();
    return 1;
}

int wr_down_view(void)
'''
    s = rep(s, status_end, tail_code, "suffix layout")

    old = '''int wr_down_view(void)
{
    int next;
    next = wr_view + wr_rowlen[0];
    if (next < wr_len && wr_doc[next] == '\\n')
        next++;
    if (next <= wr_view && wr_view < wr_len)
        next = wr_view + 1;
    if (next > wr_len)
        next = wr_len;
    if (next <= wr_view)
        return 0;
    wr_view = next;
    return 1;
}
'''
    new = '''int wr_down_view(void)
{
    int next;
    next = wr_rowpos[1];
    if (next < 0 || next <= wr_view)
        next = wr_view + wr_rowlen[0];
    if (next < wr_len && wr_doc[next] == '\\n')
        next++;
    if (next <= wr_view && wr_view < wr_len)
        next = wr_view + 1;
    if (next > wr_len)
        next = wr_len;
    if (next <= wr_view)
        return 0;
    wr_view = next;
    return 1;
}
'''
    s = rep(s, old, new, "down view")

    ensure_anchor = '''void wr_ensure(void)
{
    if (wr_cur < wr_view) {
        wr_view = wr_cur - 120;
        if (wr_view < 0)
            wr_view = 0;
    }
    if (wr_cur > wr_view + 850) {
        wr_view = wr_cur - 400;
        if (wr_view < 0)
            wr_view = 0;
    }
}

int wr_match(int pos, char *q)
'''
    page_code = '''void wr_ensure(void)
{
    if (wr_cur < wr_view) {
        wr_view = wr_cur - 120;
        if (wr_view < 0)
            wr_view = 0;
    }
    if (wr_cur > wr_view + 850) {
        wr_view = wr_cur - 400;
        if (wr_view < 0)
            wr_view = 0;
    }
}

int wr_nextrow(int pos)
{
    int col;
    int n;
    int c;
    col = 0;
    while (pos < wr_len) {
        c = wr_doc[pos];
        if (c == '\\n')
            return pos + 1;
        if (c != ' ' && col > 0 &&
            (pos == 0 || wr_doc[pos - 1] == ' ' ||
             wr_doc[pos - 1] == '\\n')) {
            n = wr_word_len(pos);
            if (col + n > 60)
                return pos;
        }
        col++;
        pos++;
        if (col >= 60)
            return pos;
    }
    return pos;
}

void wr_page(int down)
{
    int p;
    int rows;
    int goal;
    if (down) {
        if (wr_after < wr_len) {
            wr_view = wr_after;
            wr_cur = wr_view;
        } else {
            wr_cur = wr_len;
        }
        return;
    }
    if (wr_view <= 0) {
        wr_view = 0;
        wr_cur = 0;
        return;
    }
    p = 0;
    rows = 0;
    while (p < wr_view && p < wr_len) {
        p = wr_nextrow(p);
        rows++;
    }
    goal = rows - 19;
    if (goal < 0)
        goal = 0;
    p = 0;
    while (goal > 0 && p < wr_len) {
        p = wr_nextrow(p);
        goal--;
    }
    wr_view = p;
    wr_cur = p;
}

int wr_match(int pos, char *q)
'''
    s = rep(s, ensure_anchor, page_code, "page helpers")

    old = '''    if (p >= wr_len) {
        p = 0;
        while (p < wr_cur && !wr_match(p, q))
            p++;
    }
    if (p < wr_len)
        wr_cur = p;
'''
    new = '''    if (p >= wr_len) {
        p = 0;
        while (p <= wr_cur && p < wr_len &&
               !wr_match(p, q))
            p++;
        if (p > wr_cur)
            p = wr_len;
    }
    if (p < wr_len)
        wr_cur = p;
'''
    s = rep(s, old, new, "find wrap position zero")
    s = rep(
        s,
        '    print_at(23, 1, "FIND> ");\n'
        '    if (!app_readline(23, 7, q, 24)) {\n',
        '    print_at(23, 1, "FIND CAPS+7 CANCEL> ");\n'
        '    if (!app_readline(23, 21, q, 24)) {\n',
        "find cancel prompt",
    )

    old = '''int wr_fins(int c)
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
        memmove(wr_doc + wr_cur + 1,
                wr_doc + wr_cur, (unsigned int)n);
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
    wr_frow(row);
    return 1;
}
'''
    new = '''int wr_fins(int c)
{
    int row;
    int col;
    int base;
    int n;
    int len;
    int end;
    int i;
    if (!wr_drawn || wr_pcursor < 0 || wr_len >= 1899)
        return 0;
    row = wr_pcursor / 60;
    col = wr_pcursor % 60;
    len = wr_rowlen[row];
    end = wr_rowpos[row] + len;
    if (col > len)
        return 0;
    if (end >= wr_len || wr_doc[end] == '\\n') {
        if (len >= 59)
            return 0;
    } else if (len >= 60) {
        return 0;
    }
    n = wr_len - wr_cur;
    if (n > 0)
        memmove(wr_doc + wr_cur + 1,
                wr_doc + wr_cur, (unsigned int)n);
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
    for (i = row + 1; i < 19; i++) {
        if (wr_rowpos[i] >= 0)
            wr_rowpos[i]++;
    }
    wr_after++;
    wr_pcursor = base + col + 1;
    wr_ncursor = wr_pcursor;
    wr_frow(row);
    return 1;
}
'''
    s = rep(s, old, new, "wrapped insert fast path")

    old = '''int wr_fbs(void)
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
    memmove(wr_doc + wr_cur - 1,
            wr_doc + wr_cur, (unsigned int)n);
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
    wr_frow(row);
    return 1;
}
'''
    new = '''int wr_fbs(void)
{
    int row;
    int col;
    int base;
    int n;
    int len;
    int end;
    int start;
    int firstlen;
    int nextlen;
    int i;
    if (!wr_drawn || wr_pcursor < 0 || wr_cur <= 0)
        return 0;
    row = wr_pcursor / 60;
    col = wr_pcursor % 60;
    if (col <= 0)
        return 0;
    len = wr_rowlen[row];
    start = wr_rowpos[row];
    end = start + len;
    if (!wr_rowsafe[row] && row > 0 && start > 0 &&
        wr_doc[start - 1] == ' ') {
        firstlen = wr_word_len(start);
        if (wr_cur - 1 < start + firstlen &&
            wr_rowlen[row - 1] + firstlen - 1 <= 60)
            return 0;
    }
    if (end < wr_len && wr_doc[end] != '\\n') {
        if (len >= 60)
            return 0;
        nextlen = wr_word_len(end);
        if (len - 1 + nextlen <= 60)
            return 0;
    }
    n = wr_len - (wr_cur - 1);
    memmove(wr_doc + wr_cur - 1,
            wr_doc + wr_cur, (unsigned int)n);
    wr_len--;
    wr_cur--;
    base = row * 60;
    if (len > col)
        memmove(wr_prev + base + col - 1,
                wr_prev + base + col,
                (unsigned int)(len - col));
    wr_prev[base + len - 1] = ' ';
    wr_rowlen[row] = len - 1;
    for (i = row + 1; i < 19; i++) {
        if (wr_rowpos[i] >= 0)
            wr_rowpos[i]--;
    }
    wr_after--;
    wr_pcursor = base + col - 1;
    wr_ncursor = wr_pcursor;
    wr_frow(row);
    return 1;
}
'''
    s = rep(s, old, new, "wrapped backspace fast path")

    old = '''void wr_insert_key(void)
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
            if (wr_fbs())
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
        if (wr_fins(c))
            wr_fast = 1;
        else
            wr_insert_char(c);
    }
}
'''
    new = '''void wr_insert_key(void)
{
    int c;
    int row;
    int first;
    wr_fast = 0;
    c = getchar();
    if (c == 11 || c == 27) {
        wr_insert = 0;
        return;
    }
    row = 0;
    if (wr_pcursor >= 0)
        row = wr_pcursor / 60;
    if (c == 8) {
        if (wr_cur > 0) {
            if (wr_fbs()) {
                wr_fast = 1;
            } else {
                first = row;
                if (first > 0)
                    first--;
                wr_cur--;
                wr_delete_at(wr_cur);
                if (wr_tail(first))
                    wr_fast = 1;
            }
        }
        return;
    }
    if (c == 10 || c == 13) {
        wr_insert_char('\\n');
        if (wr_tail(row))
            wr_fast = 1;
        return;
    }
    if (c >= 32 && c <= 126) {
        if (wr_fins(c)) {
            wr_fast = 1;
        } else {
            wr_insert_char(c);
            if (wr_tail(row))
                wr_fast = 1;
        }
    }
}
'''
    s = rep(s, old, new, "insert mode cancel and suffix reflow")

    old = '''            if (key == '6') {
                wr_cur = wr_cur + 60;
                if (wr_cur > wr_len)
                    wr_cur = wr_len;
            }
            if (key == '7') {
                wr_cur = wr_cur - 60;
                if (wr_cur < 0)
                    wr_cur = 0;
            }
'''
    new = '''            if (key == '6')
                wr_page(1);
            if (key == '7')
                wr_page(0);
'''
    s = rep(s, old, new, "true page movement")

    bad = [
        (n, len(line), line)
        for n, line in enumerate(s.splitlines(), 1)
        if len(line) > 64
    ]
    if bad:
        raise SystemExit("write48 64-column violations: " + repr(bad))
    WRSRC.write_text(s, encoding="ascii", newline="\n")


def patch() -> None:
    patch_appapi()
    patch_write48()
    for path in (APPI, WRSRC):
        bad = [
            (n, len(line))
            for n, line in enumerate(path.read_text("ascii").splitlines(), 1)
            if len(line) > 64
        ]
        if bad:
            raise SystemExit(f"{path.name}: 64-column violations {bad}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def startup_hash(path: Path, name: str) -> str:
    font = Font4x8.load(ROOT / "compiler/assets/font4x8-tasword.bin")
    screen = ZXScreen(font)
    vm = C48VM(
        read(path), screen, argv=[name, "verify"],
        max_steps=10000000,
    )
    status = vm.run()
    if status != 0:
        raise SystemExit(f"{name}: startup status {status}")
    return hashlib.sha256(screen.bytes()).hexdigest()


def update_expect() -> None:
    data = json.loads(EXPECT.read_text(encoding="ascii"))
    data["helper_sha256"] = sha(APPI)
    for name, src, binary in (
        ("sheet48", SHSRC, SHBIN),
        ("write48", WRSRC, WRBIN),
    ):
        item = data["apps"][name]
        item["source_sha256"] = sha(src)
        item["binary_sha256"] = sha(binary)
        item["screen_sha256"] = startup_hash(binary, name)
        print(
            name,
            item["source_sha256"],
            item["binary_sha256"],
            item["screen_sha256"],
        )
    EXPECT.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="ascii", newline="\n",
    )
    print("helper", data["helper_sha256"])


def run_state(payload: bytes) -> tuple[float, dict[str, int]]:
    font = Font4x8.load(ROOT / "compiler/assets/font4x8-tasword.bin")
    screen = ZXScreen(font)
    keys = iter(payload)

    def key() -> int:
        return next(keys, -1)

    vm = C48VM(
        read(WRBIN), screen, argv=[str(WRBIN)],
        input_provider=key, max_steps=50000000,
    )
    begin = time.monotonic()
    status = vm.run()
    elapsed = time.monotonic() - begin

    def gv(name: str) -> int:
        lv = vm.global_lvalues[name]
        return vm.mem.load_integer(lv.pointer.address, lv.ctype)

    state = {
        "status": status,
        "len": gv("wr_len"),
        "cur": gv("wr_cur"),
        "view": gv("wr_view"),
        "pcursor": gv("wr_pcursor"),
    }
    return elapsed, state


def before() -> None:
    elapsed, state = run_state(b"8" * 120 + b"iabcde\x1bq")
    print("BEFORE_WRAPPED", f"{elapsed:.4f}", state)
    if state["status"] != 0 or state["len"] != 802:
        raise SystemExit(f"unexpected wrapped baseline: {state}")

    _, state = run_state(b"6q")
    print("BEFORE_PAGE", state)
    if state["cur"] != 60:
        raise SystemExit(f"old byte-page behavior not reproduced: {state}")

    _, state = run_state(b"i\x0bq\x1bq")
    print("BEFORE_CANCEL", state)
    if state["len"] != 798:
        raise SystemExit(f"old ESC-only behavior not reproduced: {state}")


def after() -> None:
    elapsed, state = run_state(b"8" * 120 + b"iabcde\x0bq")
    print("AFTER_WRAPPED_5", f"{elapsed:.4f}", state)
    if state["status"] != 0 or state["len"] != 802:
        raise SystemExit(f"wrapped insert failed: {state}")
    if elapsed > 2.0:
        raise SystemExit(f"wrapped insert remains too slow: {elapsed:.4f}s")

    elapsed, state = run_state(b"8" * 120 + b"iabcdefghijklmnop\x0bq")
    print("AFTER_WRAP_EDGE", f"{elapsed:.4f}", state)
    if state["status"] != 0 or state["len"] != 813:
        raise SystemExit(f"wrap-edge insert failed: {state}")
    if state["pcursor"] < 0:
        raise SystemExit(f"wrap-edge cursor invisible: {state}")

    elapsed, state = run_state(b"8" * 125 + b"i\x08\x08\x08\x08\x08\x0bq")
    print("AFTER_WRAPPED_BS", f"{elapsed:.4f}", state)
    if state["status"] != 0 or state["len"] != 792:
        raise SystemExit(f"wrapped backspace failed: {state}")
    if state["pcursor"] < 0:
        raise SystemExit(f"backspace cursor invisible: {state}")

    _, state = run_state(b"6q")
    print("AFTER_PAGE_DOWN", state)
    if state["cur"] < 400 or state["view"] != state["cur"]:
        raise SystemExit(f"page down is not visual-page based: {state}")
    if state["pcursor"] < 0:
        raise SystemExit(f"page-down cursor invisible: {state}")

    _, state = run_state(b"67q")
    print("AFTER_PAGE_ROUNDTRIP", state)
    if state["cur"] != 0 or state["view"] != 0:
        raise SystemExit(f"page roundtrip failed: {state}")

    _, state = run_state(b"i\x0bq\x1bq")
    print("AFTER_CANCEL", state)
    if state["len"] != 797 or state["status"] != 0:
        raise SystemExit(f"native cancel key failed: {state}")

    _, state = run_state(b"f\x0bq")
    print("AFTER_FIND_CANCEL", state)
    if state["status"] != 0 or state["len"] != 797:
        raise SystemExit(f"find cancel failed: {state}")

    source = WRSRC.read_text(encoding="ascii")
    if "while (p <= wr_cur && p < wr_len &&" not in source:
        raise SystemExit("position-zero FIND wrap fix is absent")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: review_write48.py MODE")
    modes = {
        "before": before,
        "patch": patch,
        "hash": update_expect,
        "after": after,
    }
    fn = modes.get(sys.argv[1])
    if fn is None:
        raise SystemExit("unknown mode")
    fn()


if __name__ == "__main__":
    main()
