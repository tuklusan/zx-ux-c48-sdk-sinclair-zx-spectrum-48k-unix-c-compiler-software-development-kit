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

void ring(int z, int tw, int col, int f)
{
    int j;
    int a1;
    int a2;
    int s;
    int cx;
    int cy;
    int x1;
    int y1;
    int x2;
    int y2;
    s = 4000 / (z + 24);
    cx = 128 + d_sin(f * 4 + z) / 8;
    cy = 96 + d_cos(f * 3 + z * 2) / 12;
    ink(col);
    bright((z & 32) != 0);
    for (j = 0; j < 8; j++) {
        a1 = tw + j * 32;
        a2 = tw + ((j + 1) & 7) * 32;
        x1 = cx + d_cos(a1) * s / 128;
        y1 = cy + d_sin(a1) * s / 128;
        x2 = cx + d_cos(a2) * s / 128;
        y2 = cy + d_sin(a2) * s / 128;
        if (d_ok(x1, y1) && d_ok(x2, y2)) {
            draw(x1, y1, x2, y2);
        }
    }
}

void scene(int f)
{
    int i;
    int z;
    int sh;
    cls();
    paper(0);
    sh = (f * 7) % 22;
    for (i = 0; i < 12; i++) {
        z = 18 + i * 22 - sh;
        if (z < 18) z = z + 264;
        ring(z, f * 5 + i * 7, 1 + (i % 7), f);
    }
    ink(7);
    bright(1);
    print_at(0, 3, "INFINITY TUNNEL / DEPTH + TWIST");
    print_at(23, 0,
    "MATH: scale=4000/(z+24); x=cx+cos(a)*scale/128");
}

int main(int argc, char **argv)
{
    int f;
    int n;
    n = d_frames(argc, argv, 16);
    for (f = 0; f < n; f++) {
        scene(f);
        yield();
    }
    return 0;
}
