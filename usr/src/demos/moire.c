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

void scene(int f)
{
    int r;
    int x1;
    int y1;
    int x2;
    int y2;
    cls();
    paper(0);
    over(1);
    x1 = 96 + d_sin(f * 7) / 5;
    y1 = 96 + d_cos(f * 5) / 8;
    x2 = 160 + d_cos(f * 6) / 5;
    y2 = 96 + d_sin(f * 4) / 8;
    for (r = 8; r <= 80; r = r + 6) {
        ink(1 + ((r >> 2) % 7));
        bright(r & 8);
        circle(x1, y1, r);
        ink(1 + (((r >> 2) + 3) % 7));
        circle(x2, y2, r);
    }
    over(0);
    ink(7);
    bright(1);
    draw(x1, y1, x2, y2);
    print_at(0, 7, "MOIRE ENGINE / XOR INTERFERENCE");
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
