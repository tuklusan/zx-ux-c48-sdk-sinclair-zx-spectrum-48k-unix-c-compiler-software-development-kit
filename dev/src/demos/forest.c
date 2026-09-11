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

void branch(int x, int y, int len, int ang, int dep)
{
    int nx;
    int ny;
    if (dep <= 0 || len < 3) return;
    nx = x + d_cos(ang) * len / 128;
    ny = y + d_sin(ang) * len / 128;
    if (!d_ok(nx, ny)) return;
    ink(2 + (dep & 3));
    bright(dep < 3);
    draw(x, y, nx, ny);
    if (dep == 1) {
        ink(4 + ((x + y) & 1));
        circle(nx, ny, 2);
        return;
    }
    branch(nx, ny, len * 3 / 4, ang + 18, dep - 1);
    branch(nx, ny, len * 3 / 4, ang - 22, dep - 1);
}

void scene(int f)
{
    int i;
    int x;
    int sway;
    cls();
    paper(0);
    ink(2);
    bright(0);
    draw(0, 18, 255, 18);
    for (i = 0; i < 4; i++) {
        x = 38 + i * 60;
        sway = d_sin(f * 6 + i * 31) / 18;
        branch(x, 18, 32 + (i & 1) * 6,
               64 + sway, 6);
    }
    ink(6);
    bright(1);
    circle(214, 156, 11);
    print_at(0, 7, "FRACTAL FOREST / RECURSIVE WIND");
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
