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

void burst(int cx, int cy, int t, int col)
{
    int i;
    int a;
    int sp;
    int x1;
    int y1;
    int x2;
    int y2;
    if (t < 1 || t > 27) return;
    ink(col);
    bright(t < 15);
    for (i = 0; i < 24; i++) {
        a = i * 11;
        sp = 2 + (i & 3);
        x2 = cx + d_cos(a) * sp * t / 128;
        y2 = cy + d_sin(a) * sp * t / 128;
        y2 = y2 - t * t / 18;
        x1 = cx + d_cos(a) * sp * (t - 2) / 128;
        y1 = cy + d_sin(a) * sp * (t - 2) / 128;
        y1 = y1 - (t - 2) * (t - 2) / 18;
        if (d_ok(x1, y1) && d_ok(x2, y2)) {
            draw(x1, y1, x2, y2);
        }
    }
}

void sky(void)
{
    int x;
    ink(1);
    bright(0);
    for (x = 0; x < 256; x = x + 16) {
        draw(x, 0, x, 18 + ((x * 7) % 30));
        draw(x, 18 + ((x * 7) % 30),
             x + 14, 18 + ((x * 7) % 30));
    }
}

void scene(int f)
{
    int t1;
    int t2;
    int t3;
    cls();
    paper(0);
    sky();
    t1 = f % 32;
    t2 = (f + 21) % 32;
    t3 = (f + 11) % 32;
    burst(70, 118, t1, 2);
    burst(132, 142, t2, 6);
    burst(196, 110, t3, 5);
    ink(7);
    bright(1);
    print_at(0, 7, "FIREWORK NIGHT / PARTICLES");
}

int main(int argc, char **argv)
{
    int f;
    int n;
    n = d_frames(argc, argv, 18);
    for (f = 0; f < n; f++) {
        scene(f);
        yield();
    }
    return 0;
}
