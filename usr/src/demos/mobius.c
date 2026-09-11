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

void mpt(int u, int side, int f,
         int *x, int *y, int *z)
{
    int rr;
    int a;
    int b;
    int c;
    rr = 48 + side * 12 * d_cos(u / 2) / 128;
    a = rr * d_cos(u) / 128;
    c = rr * d_sin(u) / 128;
    b = side * 10 * d_sin(u / 2) / 128;
    d_rot3(a, b, c, 20 + f * 2, f * 4, f,
           x, y, z);
}

void edge(int u1, int u2, int side, int f)
{
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    mpt(u1, side, f, &x1, &y1, &z1);
    mpt(u2, side, f, &x2, &y2, &z2);
    d_line3(x1, y1, z1, x2, y2, z2);
}

void scene(int f)
{
    int i;
    int u1;
    int u2;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    cls();
    paper(0);
    for (i = 0; i < 20; i++) {
        u1 = i * 256 / 20;
        u2 = (i + 1) * 256 / 20;
        if (i == 19) u2 = 0;
        ink(2 + (i % 6));
        bright(i & 1);
        edge(u1, u2, -1, f);
        edge(u1, u2, 1, f);
        mpt(u1, -1, f, &x1, &y1, &z1);
        mpt(u1, 1, f, &x2, &y2, &z2);
        d_line3(x1, y1, z1, x2, y2, z2);
    }
    ink(7);
    bright(1);
    print_at(0, 5, "MOBIUS FLIGHT / ONE SIDED RIBBON");
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
