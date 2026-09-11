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

char wr_doc[1900];
int wr_len;
int wr_cur;
int wr_view;
int wr_insert;

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
    int i;
    if (wr_len >= 1899)
        return;
    i = wr_len;
    while (i > wr_cur) {
        wr_doc[i] = wr_doc[i - 1];
        i--;
    }
    wr_doc[wr_cur] = (char)c;
    wr_len++;
    wr_cur++;
    wr_doc[wr_len] = 0;
}

void wr_delete_at(int pos)
{
    int i;
    if (pos < 0 || pos >= wr_len)
        return;
    i = pos;
    while (i < wr_len) {
        wr_doc[i] = wr_doc[i + 1];
        i++;
    }
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

void wr_cursor_char(int row, int col, int c)
{
    inverse(1);
    if (c == ' ' || c == '\n' || c == 0)
        app_putc(row, col, '_');
    else
        app_putc(row, col, c);
    inverse(0);
}

void wr_render(void)
{
    int row;
    int col;
    int pos;
    int n;
    int c;
    cls();
    paper(0);
    ink(7);
    bright(1);
    print_at(0, 14, "WRITE48 - 1992 RESUME");
    bright(0);
    row = 2;
    col = 2;
    pos = wr_view;
    while (row < 21 && pos <= wr_len) {
        if (pos == wr_len) {
            if (pos == wr_cur)
                wr_cursor_char(row, col, 0);
            break;
        }
        c = wr_doc[pos];
        if (c == '\n') {
            if (pos == wr_cur)
                wr_cursor_char(row, col, c);
            row++;
            col = 2;
            pos++;
        } else {
            if (c != ' ' && col > 2) {
                n = wr_word_len(pos);
                if (col + n > 62) {
                    row++;
                    col = 2;
                    if (row >= 21)
                        break;
                }
            }
            if (pos == wr_cur)
                wr_cursor_char(row, col, c);
            else
                app_putc(row, col, c);
            col++;
            pos++;
            if (col >= 62) {
                row++;
                col = 2;
            }
        }
    }
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
    yield();
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
    if (!app_readline(23, 7, q, 24))
        return;
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
}

void wr_insert_key(void)
{
    int c;
    c = getchar();
    if (c == 27) {
        wr_insert = 0;
        return;
    }
    if (c == 8) {
        if (wr_cur > 0) {
            wr_cur--;
            wr_delete_at(wr_cur);
        }
        return;
    }
    if (c == 10 || c == 13) {
        wr_insert_char('\n');
        return;
    }
    if (c >= 32 && c <= 126)
        wr_insert_char(c);
}

int main(int argc, char **argv)
{
    int key;
    wr_seed();
    wr_cur = 0;
    wr_view = 0;
    wr_insert = 0;
    wr_render();
    if (argc > 1 && strcmp(argv[1], "verify") == 0)
        return 0;
    while (1) {
        if (wr_insert) {
            wr_insert_key();
        } else {
            key = app_key();
            if (key == 'q')
                return 0;
            if ((key == '8' || key == 'l') && wr_cur < wr_len)
                wr_cur++;
            if ((key == '5' || key == 'h') && wr_cur > 0)
                wr_cur--;
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
        wr_ensure();
        wr_render();
    }
}
