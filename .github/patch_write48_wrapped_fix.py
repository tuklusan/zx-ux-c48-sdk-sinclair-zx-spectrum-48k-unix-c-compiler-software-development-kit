from pathlib import Path

p = Path('usr/src/apps/write48.c')
s = p.read_text(encoding='utf-8')

pairs = [
    (
        "        if (pos == wr_len) {\n"
        "            if (fresh && col < 60) {\n"
        "                wr_rowsafe[row] = 1;\n"
        "                wr_rowlen[row] = col;\n"
        "            }\n",
        "        if (pos == wr_len) {\n"
        "            wr_rowlen[row] = col;\n"
        "            if (fresh && col < 60)\n"
        "                wr_rowsafe[row] = 1;\n",
    ),
    (
        "        if (c == '\\n') {\n"
        "            if (fresh && col < 60) {\n"
        "                wr_rowsafe[row] = 1;\n"
        "                wr_rowlen[row] = col;\n"
        "            }\n",
        "        if (c == '\\n') {\n"
        "            wr_rowlen[row] = col;\n"
        "            if (fresh && col < 60)\n"
        "                wr_rowsafe[row] = 1;\n",
    ),
    (
        "            col++;\n"
        "            pos++;\n"
        "            if (col >= 60) {\n",
        "            col++;\n"
        "            pos++;\n"
        "            wr_rowlen[row] = col;\n"
        "            if (col >= 60) {\n",
    ),
]
for old, new in pairs:
    if s.count(old) != 1:
        raise SystemExit('write48 row metadata anchor mismatch')
    s = s.replace(old, new)

start = s.index('int wr_fmove(int d)\n')
end = s.index('\nint wr_fins(int c)\n', start)
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
    raise SystemExit('64-column violations: ' + repr(bad))
p.write_text(s, encoding='utf-8', newline='\n')
