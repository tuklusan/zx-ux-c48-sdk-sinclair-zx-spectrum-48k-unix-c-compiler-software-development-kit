// ============================================================
// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and AI/ML
// model training prohibited unless separately authorized.
//
// Attribution required: Based on original work by Supratim
// Sanyal of SANYALnet Labs. See root LICENSE for full terms.
// ============================================================
#include "appapi.h"
void *memset(void *d, int c, unsigned int n);

char wr_doc[1900];
char wr_prev[1140];
char wr_next[1140];
char wr_line[61];
int wr_pcursor;
int wr_ncursor;
int wr_rowsafe[19];
int wr_rowlen[19];
int wr_fast;
int wr_len;
int wr_cur;
int wr_view;
int wr_insert;
int wr_drawn;
int wr_stat;

void wr_append(char *s)
{
    int i;
    i = 0;
    while (s[i] != 0 && wr_len < 1899) {
        wr_doc[wr_len] = s[i];
        wr_len++;
        i++;
    }
    wr_doc[wr_len] = 0;
}

void wr_seed(void)
{
    wr_len = 0;
    wr_append("SIR CLIVE SINCLAIR\n");
    wr_append("Cambridge, England - Resume, 1992\n\n");
    wr_append("PROFILE\n");
    wr_append("British inventor and entrepreneur focused ");
    wr_append("on making electronics and home computers ");
    wr_append("affordable and widely accessible.\n\n");
    wr_append("EXPERIENCE\n");
    wr_append("SINCLAIR RESEARCH LTD, Cambridge\n");
    wr_append("Founder and Chairman, 1979-present\n");
    wr_append("Led development and marketing of low-cost ");
    wr_append("home computers: ZX80 (1980), ZX81 (1981), ");
    wr_append("ZX Spectrum (1982) and Sinclair QL (1984).\n\n");
    wr_append("SINCLAIR RADIONICS LTD\n");
    wr_append("Founder, 1961-1979\n");
    wr_append("Developed compact electronics including ");
    wr_append("amplifier kits, calculators, watches and ");
    wr_append("portable television products.\n\n");
    wr_append("SELECTED MILESTONES\n");
    wr_append("1982  ZX Spectrum launched.\n");
    wr_append("1983  Awarded a knighthood.\n");
    wr_append("1985  Sinclair C5 electric vehicle launched.\n");
    wr_append("1986  Computer business sold to Amstrad.\n\n");
    wr_append("INTERESTS\n");
    wr_append("Miniaturisation, transport, electronics and ");
    wr_append("practical products for mass ownership.\n");
}

void wr_insert_char(int c)
{
    int n;
    if (wr_len >= 1899)
        return;
    n = wr_len - wr_cur;
    if (n > 0)
        memmove(wr_doc + wr_cur + 1,
                wr_doc + wr_cur, (unsigned int)n);
    wr_doc[wr_cur] = (char)c;
    wr_len++;
    wr_cur++;
    wr_doc[wr_len] = 0;
}

void wr_delete_at(int pos)
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

int wr_word_len(int pos)
{
    int n;
    n = 0;
    while (pos + n < wr_len && wr_doc[pos + n] != ' ' &&
           wr_doc[pos + n] != '\n' && n < 60)
        n++;
    return n;
}

void wr_blank(void)
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
    fresh = (wr_view == 0 || wr_doc[wr_view - 1] == '\n');
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
        if (c == '\n') {
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
                (pos == wr_view || pos == 0 ||
                 wr_doc[pos - 1] == ' ' ||
                 wr_doc[pos - 1] == '\n')) {
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

void wr_diff(void)
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

void wr_status(void)
{
    if (wr_stat == wr_insert)
        return;
    app_clear_row(21);
    app_clear_row(22);
    app_clear_row(23);
    if (wr_insert) {
        print_at(21, 1, "INSERT: ESC CMD  BS DEL  ENTER NL");
    } else {
        print_at(21, 1, "CMD: I INS  5/8 MOVE  7/6 PG  X DEL");
        print_at(22, 1, "F FIND  G TOP  Q QUIT");
    }
    print_at(23, 1, "1992 DEMO CV - EDITABLE IN MEMORY");
    wr_stat = wr_insert;
}

void wr_render(void)
{
    wr_build();
    wr_diff();
    wr_status();
}

void wr_start(void)
{
    int i;
    cls();
    paper(0);
    ink(7);
    bright(1);
    print_at(0, 14, "WRITE48 - 1992 RESUME");
    bright(0);
    memset(wr_prev, 0, 1140u);
    wr_pcursor = -1;
    wr_ncursor = -1;
    wr_fast = 0;
    wr_drawn = 0;
    wr_stat = -1;
}

void wr_ensure(void)
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
{
    int i;
    i = 0;
    while (q[i] != 0) {
        if (pos + i >= wr_len)
            return 0;
        if (wr_doc[pos + i] != q[i])
            return 0;
        i++;
    }
    return i > 0;
}

void wr_find(void)
{
    char q[24];
    int p;
    app_clear_row(23);
    print_at(23, 1, "FIND> ");
    if (!app_readline(23, 7, q, 24)) {
        wr_stat = -1;
        return;
    }
    p = wr_cur + 1;
    while (p < wr_len && !wr_match(p, q))
        p++;
    if (p >= wr_len) {
        p = 0;
        while (p < wr_cur && !wr_match(p, q))
            p++;
    }
    if (p < wr_len)
        wr_cur = p;
    wr_stat = -1;
}

void wr_frow(int row)
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

int wr_fmove(int d)
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
            if (row >= 18 || !wr_rowsafe[row] ||
                !wr_rowsafe[row + 1])
                return 0;
            next = (row + 1) * 60;
        } else {
            if (!wr_rowsafe[row] || col >= wr_rowlen[row])
                return 0;
            next = old + 1;
        }
        wr_cur++;
    } else {
        if (wr_cur <= 0)
            return 1;
        if (wr_doc[wr_cur - 1] == '\n') {
            if (row <= 0 || !wr_rowsafe[row] ||
                !wr_rowsafe[row - 1])
                return 0;
            next = (row - 1) * 60 + wr_rowlen[row - 1];
        } else {
            if (!wr_rowsafe[row] || col <= 0)
                return 0;
            next = old - 1;
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

int wr_fins(int c)
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

int wr_fbs(void)
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

void wr_insert_key(void)
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
        wr_insert_char('\n');
        return;
    }
    if (c >= 32 && c <= 126) {
        if (wr_fins(c))
            wr_fast = 1;
        else
            wr_insert_char(c);
    }
}

int main(int argc, char **argv)
{
    int key;
    wr_seed();
    wr_cur = 0;
    wr_view = 0;
    wr_insert = 0;
    wr_start();
    wr_render();
    if (argc > 1 && strcmp(argv[1], "verify") == 0)
        return 0;
    while (1) {
        wr_fast = 0;
        if (wr_insert) {
            wr_insert_key();
        } else {
            key = app_key();
            if (key == 'q')
                return 0;
            if ((key == '8' || key == 'l') && wr_cur < wr_len) {
                if (wr_fmove(1))
                    wr_fast = 1;
                else
                    wr_cur++;
            }
            if ((key == '5' || key == 'h') && wr_cur > 0) {
                if (wr_fmove(-1))
                    wr_fast = 1;
                else
                    wr_cur--;
            }
            if (key == '6') {
                wr_cur = wr_cur + 60;
                if (wr_cur > wr_len)
                    wr_cur = wr_len;
            }
            if (key == '7') {
                wr_cur = wr_cur - 60;
                if (wr_cur < 0)
                    wr_cur = 0;
            }
            if (key == 'i')
                wr_insert = 1;
            if (key == 'x')
                wr_delete_at(wr_cur);
            if (key == 'f')
                wr_find();
            if (key == 'g') {
                wr_cur = 0;
                wr_view = 0;
            }
        }
        {
            int old_view;
            old_view = wr_view;
            wr_ensure();
            if (!wr_fast || wr_view != old_view)
                wr_render();
        }
    }
}
