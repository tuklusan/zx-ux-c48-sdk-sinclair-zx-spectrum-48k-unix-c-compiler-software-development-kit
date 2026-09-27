// ============================================================
// Copyright (c) 2026 SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and restricted
// model training prohibited unless separately authorized.
//
// Attribution required: SANYALnet Labs.
// See root LICENSE for full terms.
// ============================================================
#include "appapi.h"

/* 1982 constructor figures used by the startup dashboard. */
/* Wins: official 16-race season results. */
/* Podiums/poles: season constructor statistics. */

int gp_wins[4];
int gp_podiums[4];
int gp_poles[4];

int gp_vx[16];
int gp_vy[16];
int gp_owner[16];

void gp_seed(void)
{
    gp_wins[0] = 3;
    gp_wins[1] = 4;
    gp_wins[2] = 4;
    gp_wins[3] = 1;

    gp_podiums[0] = 11;
    gp_podiums[1] = 8;
    gp_podiums[2] = 8;
    gp_podiums[3] = 7;

    gp_poles[0] = 3;
    gp_poles[1] = 0;
    gp_poles[2] = 10;
    gp_poles[3] = 1;

    gp_vx[0] = 0;
    gp_vy[0] = 1000;
    gp_vx[1] = 383;
    gp_vy[1] = 924;
    gp_vx[2] = 707;
    gp_vy[2] = 707;
    gp_vx[3] = 924;
    gp_vy[3] = 383;
    gp_vx[4] = 1000;
    gp_vy[4] = 0;
    gp_vx[5] = 924;
    gp_vy[5] = -383;
    gp_vx[6] = 707;
    gp_vy[6] = -707;
    gp_vx[7] = 383;
    gp_vy[7] = -924;
    gp_vx[8] = 0;
    gp_vy[8] = -1000;
    gp_vx[9] = -383;
    gp_vy[9] = -924;
    gp_vx[10] = -707;
    gp_vy[10] = -707;
    gp_vx[11] = -924;
    gp_vy[11] = -383;
    gp_vx[12] = -1000;
    gp_vy[12] = 0;
    gp_vx[13] = -924;
    gp_vy[13] = 383;
    gp_vx[14] = -707;
    gp_vy[14] = 707;
    gp_vx[15] = -383;
    gp_vy[15] = 924;

    gp_owner[0] = 0;
    gp_owner[1] = 0;
    gp_owner[2] = 0;
    gp_owner[3] = 0;
    gp_owner[4] = 1;
    gp_owner[5] = 1;
    gp_owner[6] = 1;
    gp_owner[7] = 1;
    gp_owner[8] = 2;
    gp_owner[9] = 2;
    gp_owner[10] = 2;
    gp_owner[11] = 3;
    gp_owner[12] = 3;
    gp_owner[13] = 4;
    gp_owner[14] = 5;
    gp_owner[15] = 6;
}

void gp_box(int x, int y, int w, int h, int style)
{
    int px;
    int py;
    for (py = 0; py < h; py++) {
        for (px = 0; px < w; px++) {
            if (px == 0 || px == w - 1 ||
                py == 0 || py == h - 1) {
                plot(x + px, y + py);
            } else if (style == 0) {
                plot(x + px, y + py);
            } else if (style == 1) {
                if (((px + py) & 1) == 0)
                    plot(x + px, y + py);
            } else {
                if ((px & 1) == 0)
                    plot(x + px, y + py);
            }
        }
    }
}

void gp_bars(void)
{
    int g;
    int x;
    draw(6, 34, 126, 34);
    draw(6, 34, 6, 132);
    draw(4, 74, 8, 74);
    draw(4, 114, 8, 114);
    for (g = 0; g < 4; g++) {
        x = 15 + g * 28;
        gp_box(x, 35, 5, gp_wins[g] * 8, 0);
        gp_box(x + 7, 35, 5, gp_podiums[g] * 8, 1);
        if (gp_poles[g] > 0)
            gp_box(x + 14, 35, 5, gp_poles[g] * 8, 2);
    }
}

int gp_sector(int dx, int dy)
{
    int best;
    int bestdot;
    int dot;
    int k;
    best = 0;
    bestdot = -32767;
    for (k = 0; k < 16; k++) {
        dot = dx * gp_vx[k] + dy * gp_vy[k];
        if (dot > bestdot) {
            bestdot = dot;
            best = k;
        }
    }
    return best;
}

int gp_pattern(int owner, int x, int y)
{
    if (owner == 0)
        return 1;
    if (owner == 1)
        return ((x + y) & 1) == 0;
    if (owner == 2)
        return (x & 1) == 0;
    if (owner == 3)
        return (y & 1) == 0;
    if (owner == 4)
        return ((x + y) & 3) == 0;
    if (owner == 5)
        return ((x - y) & 3) == 0;
    return ((x + y) & 2) == 0;
}

void gp_pie(void)
{
    int cx;
    int cy;
    int r;
    int x;
    int y;
    int dx;
    int dy;
    int k;
    int owner;
    cx = 190;
    cy = 94;
    r = 42;
    for (y = cy - r; y <= cy + r; y++) {
        for (x = cx - r; x <= cx + r; x++) {
            dx = x - cx;
            dy = y - cy;
            if (dx * dx + dy * dy <= r * r) {
                k = gp_sector(dx, dy);
                owner = gp_owner[k];
                if (gp_pattern(owner, x, y))
                    plot(x, y);
            }
        }
    }
    draw(cx, cy, cx, cy + r);
    draw(cx, cy, cx + r, cy);
    draw(cx, cy, cx, cy - r);
    draw(cx, cy, cx - 39, cy - 16);
    draw(cx, cy, cx - 39, cy + 16);
    draw(cx, cy, cx - 30, cy + 30);
    draw(cx, cy, cx - 16, cy + 39);
}

void gp_render(void)
{
    cls();
    paper(0);
    ink(7);
    bright(1);
    print_at(0, 10, "GP82 - GRAND PRIX 1982");
    bright(0);
    print_at(2, 1, "TOP FOUR: WINS / PODIUMS / POLES");
    print_at(2, 35, "RACE WINS - 16 TOTAL");
    gp_bars();
    gp_pie();
    print_at(17, 1, "FER   MCL   REN   WIL");
    print_at(19, 1, "SOLID W  CHECK P  STRIPE POLE");
    print_at(17, 35, "MCL4 REN4 FER3 BRB2");
    print_at(18, 35, "LOT1 WIL1 TYR1");
    print_at(20, 35, "FERRARI CHAMPION: 74 PTS");
    print_at(22, 1, "REAL 1982 SEASON DATA");
    print_at(23, 1, "Q QUIT   R REDRAW");
    yield();
}

int main(int argc, char **argv)
{
    int key;
    gp_seed();
    gp_render();
    if (argc > 1 && strcmp(argv[1], "verify") == 0)
        return 0;
    while (1) {
        key = app_key();
        if (key == 'q')
            return 0;
        if (key == 'r')
            gp_render();
    }
}
