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

int hgt(int x, int z, int f)
{
    int a;
    int b;
    a = d_sin(x * 2 + z + f * 5);
    b = d_sin(z * 2 - x + f * 3);
    return -34 + (a + b) / 8;
}

void scene(int f)
{
    int r;
    int c;
    int z1;
    int z2;
    int x1;
    int x2;
    int sh;
    int y1;
    int y2;
    cls();
    paper(0);
    border(6);
    sh = (f * 5) % 18;
    for (r = 0; r < 10; r++) {
        z1 = 20 + r * 18 - sh;
        if (z1 < 16) z1 = z1 + 180;
        ink(2 + (r & 3));
        bright(r < 5);
        for (c = 0; c < 10; c++) {
            x1 = -110 + c * 22;
            x2 = x1 + 22;
            y1 = hgt(x1, z1, f);
            y2 = hgt(x2, z1, f);
            d_line3(x1, y1, z1, x2, y2, z1);
        }
    }
    ink(6);
    bright(0);
    for (c = 0; c < 11; c++) {
        x1 = -110 + c * 22;
        for (r = 0; r < 9; r++) {
            z1 = 20 + r * 18 - sh;
            z2 = z1 + 18;
            if (z1 < 16) {
                z1 = z1 + 180;
                z2 = z2 + 180;
            }
            y1 = hgt(x1, z1, f);
            y2 = hgt(x1, z2, f);
            d_line3(x1, y1, z1, x1, y2, z2);
        }
    }
    ink(6);
    bright(1);
    circle(210, 150, 13);
    print_at(0, 3, "MOUNTAIN FLIGHT / PROCEDURAL GRID");
    print_at(23, 0,
    "MATH: h=-34+(sin(2x+z+5f)+sin(2z-x+3f))/8");
}

int main(int argc, char **argv)
{
    int f;
    int n;
    n = d_frames(argc, argv, 10);
    for (f = 0; f < n; f++) {
        scene(f);
        yield();
    }
    return 0;
}
