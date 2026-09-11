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
    int x;
    int y;
    int i;
    int cr;
    int ci;
    int zx;
    int zy;
    int xx;
    cls();
    paper(0);
    cr = -22 + d_sin(f * 9) / 12;
    ci = d_cos(f * 7) / 9;
    for (y = 0; y < 48; y++) {
        for (x = 0; x < 64; x++) {
            zx = (x - 32) * 3;
            zy = (y - 24) * 3;
            for (i = 0; i < 12; i++) {
                if (d_abs(zx) > 64) break;
                if (d_abs(zy) > 64) break;
                if (zx * zx + zy * zy > 4096) break;
                xx = (zx * zx - zy * zy) / 32 + cr;
                zy = 2 * zx * zy / 32 + ci;
                zx = xx;
            }
            ink((i + f) & 7);
            bright(i > 6);
            plot(x * 4, y * 4);
            if (i > 8) plot(x * 4 + 1, y * 4);
        }
        if ((y & 7) == 0) yield();
    }
    ink(7);
    bright(1);
    print_at(0, 7, "JULIA BALLET / MOVING CONSTANT");
}

int main(int argc, char **argv)
{
    int f;
    int n;
    n = d_frames(argc, argv, 4);
    for (f = 0; f < n; f++) {
        scene(f);
        yield();
    }
    return 0;
}
