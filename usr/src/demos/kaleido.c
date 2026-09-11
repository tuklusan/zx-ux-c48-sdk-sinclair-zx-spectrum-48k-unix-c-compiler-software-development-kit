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

void ray8(int x, int y, int u, int v)
{
    draw(128 + x, 96 + y, 128 + u, 96 + v);
    draw(128 - x, 96 + y, 128 - u, 96 + v);
    draw(128 + x, 96 - y, 128 + u, 96 - v);
    draw(128 - x, 96 - y, 128 - u, 96 - v);
    draw(128 + y, 96 + x, 128 + v, 96 + u);
    draw(128 - y, 96 + x, 128 - v, 96 + u);
    draw(128 + y, 96 - x, 128 + v, 96 - u);
    draw(128 - y, 96 - x, 128 - v, 96 - u);
}

void scene(int f)
{
    int i;
    int a;
    int b;
    int r1;
    int r2;
    int x1;
    int y1;
    int x2;
    int y2;
    cls();
    paper(0);
    over(1);
    for (i = 0; i < 22; i++) {
        r1 = 12 + i * 3;
        r2 = r1 + 8;
        a = i * 17 + f * 7;
        b = a + 11 + (f & 7);
        x1 = d_cos(a) * r1 / 128;
        y1 = d_sin(a) * r1 / 128;
        x2 = d_cos(b) * r2 / 128;
        y2 = d_sin(b) * r2 / 128;
        ink(1 + (i % 7));
        bright(i & 1);
        ray8(x1, y1, x2, y2);
    }
    over(0);
    ink(7);
    bright(1);
    circle(128, 96, 14 + (f & 7));
    print_at(0, 7, "KALEIDOSCOPE / EIGHTFOLD LINES");
}

int main(int argc, char **argv)
{
    int f;
    int n;
    n = d_frames(argc, argv, 12);
    for (f = 0; f < n; f++) {
        scene(f);
        yield();
    }
    return 0;
}
