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

int wave(int x, int z, int f)
{
    int a;
    int b;
    int c;
    a = d_sin(x * 3 + f * 7);
    b = d_sin(z * 2 - f * 5);
    c = d_sin(x + z + f * 3);
    return (a + b + c) / 18;
}

void scene(int f)
{
    int r;
    int c;
    int x1;
    int x2;
    int z1;
    int z2;
    int y1;
    int y2;
    cls();
    paper(1);
    border(1 + (f & 1) * 4);
    for (r = 0; r < 10; r++) {
        z1 = 18 + r * 18;
        ink(5 + (r & 1));
        bright(r < 6);
        for (c = 0; c < 10; c++) {
            x1 = -110 + c * 22;
            x2 = x1 + 22;
            y1 = wave(x1, z1, f);
            y2 = wave(x2, z1, f);
            d_line3(x1, y1, z1, x2, y2, z1);
        }
    }
    ink(5);
    for (c = 0; c < 11; c++) {
        x1 = -110 + c * 22;
        for (r = 0; r < 9; r++) {
            z1 = 18 + r * 18;
            z2 = z1 + 18;
            y1 = wave(x1, z1, f);
            y2 = wave(x1, z2, f);
            d_line3(x1, y1, z1, x1, y2, z2);
        }
    }
    ink(7);
    bright(1);
    circle(54, 148, 10);
    print_at(0, 4, "OCEAN GRID / THREE WAVE FIELD");
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
