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

void orbit(int r, int tilt, int f, int col,
           int speed, int phase)
{
    int j;
    int a1;
    int a2;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    int px;
    int py;
    ink(col);
    bright(col & 1);
    for (j = 0; j < 24; j++) {
        a1 = j * 256 / 24;
        if (j == 23) a2 = 0;
        else a2 = (j + 1) * 256 / 24;
        x1 = r * d_cos(a1) / 128;
        z1 = r * d_sin(a1) / 128;
        y1 = 0;
        x2 = r * d_cos(a2) / 128;
        z2 = r * d_sin(a2) / 128;
        y2 = 0;
        d_rot3(x1, y1, z1, tilt, 0, 0,
               &x1, &y1, &z1);
        d_rot3(x2, y2, z2, tilt, 0, 0,
               &x2, &y2, &z2);
        d_line3(x1, y1, z1, x2, y2, z2);
    }
    a1 = f * speed + phase;
    x1 = r * d_cos(a1) / 128;
    z1 = r * d_sin(a1) / 128;
    y1 = 0;
    d_rot3(x1, y1, z1, tilt, 0, 0,
           &x1, &y1, &z1);
    px = d_px(x1, z1);
    py = d_py(y1, z1);
    if (d_ok(px, py)) circle(px, py, 2 + (r > 40));
}

void scene(int f)
{
    cls();
    paper(0);
    ink(6);
    bright(1);
    circle(128, 96, 9);
    circle(128, 96, 5);
    orbit(22, 12, f, 2, 7, 0);
    orbit(36, -18, f, 3, 5, 37);
    orbit(50, 25, f, 5, 3, 91);
    orbit(64, -12, f, 6, 2, 143);
    ink(7);
    bright(1);
    print_at(0, 6, "CLOCKWORK ORRERY / 3D ORBITS");
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
