// ============================================================
// Copyright (c) 2026 SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK
// Governed by the SANYALnet Labs Non-Commercial License.
// See root LICENSE for full terms.
//
// Attribution required: SANYALnet Labs.
// ============================================================
/* Minimal host profile for the recursive visual demos. */
unsigned int strlen(char *s);
int strcmp(char *a, char *b);
int ink(int c);
int paper(int c);
int bright(int on);
int inverse(int on);
int over(int on);
int print_at(int row, int col, char *text);
int udg_define(int slot, unsigned char *bytes);
int udg_draw(int slot, int row, int col);
int udg_draw_2x2(int base, int row, int col);
int yield(void);
int sleep(unsigned int ticks);
