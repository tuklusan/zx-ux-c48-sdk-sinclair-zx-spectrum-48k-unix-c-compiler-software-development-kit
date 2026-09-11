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
#include "demoapi.h"

void stars(int f)
{
    int i;
    int x;
    int y;
    for (i = 0; i < 54; i++) {
        x = (i * 53 + f * 7) & 255;
        y = (i * 31 + f * 3) % 182;
        ink(1 + (i % 7));
        bright(i & 1);
        plot(x, y);
    }
}

void rings(int f)
{
    int r;
    over(1);
    for (r = 12; r < 90; r = r + 10) {
        ink(1 + ((r + f) % 7));
        bright(r < 44);
        circle(128, 96, r + d_sin(f * 5 + r) / 32);
    }
    over(0);
}

void logo(int s)
{
    int l;
    int r;
    int t;
    int b;
    l = 128 - 42 * s / 3;
    r = 128 + 42 * s / 3;
    t = 96 + 24 * s / 3;
    b = 96 - 24 * s / 3;
    ink(7);
    bright(1);
    draw(l + 20, t, l, t);
    draw(l, t, l, b);
    draw(l, b, l + 20, b);
    draw(l + 30, t, l + 30, 96);
    draw(l + 30, 96, l + 48, 96);
    draw(l + 48, t, l + 48, b);
    draw(l + 30, 96, l + 48, t);
    circle(r - 15, 108, 12 * s / 3);
    circle(r - 15, 84, 12 * s / 3);
}

void scene(int f)
{
    int s;
    cls();
    paper(0);
    stars(f);
    rings(f);
    s = 2 + ((f >> 2) & 1);
    logo(s);
    ink(6);
    bright(1);
    print_at(0, 12, "ZX-UX C48 SDK");
    ink(7);
    print_at(22, 6, "21 DEMOS / ONE 48K-STYLE SCREEN");
}

int main(int argc, char **argv)
{
    int f;
    int n;
    n = d_frames(argc, argv, 14);
    for (f = 0; f < n; f++) {
        scene(f);
        yield();
    }
    return 0;
}
