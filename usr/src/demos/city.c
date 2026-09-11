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

void bldg(int x, int z, int w, int h)
{
    int y0;
    int y1;
    int z2;
    y0 = -42;
    y1 = y0 + h;
    z2 = z + 16;
    d_line3(x, y0, z, x + w, y0, z);
    d_line3(x, y1, z, x + w, y1, z);
    d_line3(x, y0, z, x, y1, z);
    d_line3(x + w, y0, z, x + w, y1, z);
    d_line3(x, y0, z2, x + w, y0, z2);
    d_line3(x, y1, z2, x + w, y1, z2);
    d_line3(x, y0, z2, x, y1, z2);
    d_line3(x + w, y0, z2, x + w, y1, z2);
    d_line3(x, y0, z, x, y0, z2);
    d_line3(x + w, y0, z, x + w, y0, z2);
    d_line3(x, y1, z, x, y1, z2);
    d_line3(x + w, y1, z, x + w, y1, z2);
}

void scene(int f)
{
    int i;
    int z;
    int sh;
    int h;
    cls();
    paper(0);
    sh = (f * 6) % 24;
    ink(4);
    bright(1);
    d_line3(-18, -42, 8, -18, -42, 210);
    d_line3(18, -42, 8, 18, -42, 210);
    d_line3(-70, -42, 8, 0, -42, 210);
    d_line3(70, -42, 8, 0, -42, 210);
    for (i = 0; i < 8; i++) {
        z = 24 + i * 24 - sh;
        if (z < 20) z = z + 192;
        h = 20 + ((i * 13 + f * 3) % 38);
        ink(1 + (i % 6));
        bright(i < 4);
        bldg(-72, z, 24, h);
        bldg(48, z + 8, 24, 16 + ((h * 3) % 42));
    }
    ink(7);
    bright(1);
    print_at(0, 3, "VECTOR METROPOLIS / NIGHT FLIGHT");
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
