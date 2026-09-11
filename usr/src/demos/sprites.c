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

unsigned char s0[8] = {
    24, 60, 126, 255, 255, 90, 24, 24
};
unsigned char s1[8] = {
    24, 60, 126, 255, 219, 126, 36, 66
};
unsigned char s2[8] = {
    24, 24, 90, 255, 255, 126, 60, 24
};
unsigned char s3[8] = {
    66, 36, 126, 219, 255, 126, 60, 24
};
unsigned char a0[8] = {
    24, 126, 255, 189, 255, 126, 60, 24
};
unsigned char a1[8] = {
    60, 255, 219, 255, 189, 255, 126, 24
};
unsigned char a2[8] = {
    24, 60, 126, 255, 189, 255, 126, 24
};
unsigned char a3[8] = {
    24, 126, 255, 189, 255, 219, 255, 60
};

void setup(void)
{
    udg_define(0, s0);
    udg_define(1, s1);
    udg_define(2, s2);
    udg_define(3, s3);
    udg_define(4, a0);
    udg_define(5, a1);
    udg_define(6, a2);
    udg_define(7, a3);
}

void scene(int f)
{
    int i;
    int x;
    int y;
    cls();
    paper(0);
    ink(7);
    for (i = 0; i < 44; i++) {
        x = (i * 47 + f * 3) & 255;
        y = (i * 29 + f * 2) % 176;
        plot(x, y);
    }
    ink(6);
    bright(1);
    udg_draw_2x2(0, 9 + d_sin(f * 5) / 32,
                 14 + d_cos(f * 4) / 32);
    ink(2);
    bright(0);
    udg_draw_2x2(4, 4 + (f % 5), 3 + (f % 9));
    ink(5);
    udg_draw_2x2(4, 15 - (f % 7), 24 - (f % 8));
    ink(3);
    udg_draw_2x2(4, 5 + (f % 9), 20);
    ink(7);
    bright(1);
    print_at(0, 6, "SPRITE STORM / UDG 2X2 FLEET");
}

int main(int argc, char **argv)
{
    int f;
    int n;
    setup();
    n = d_frames(argc, argv, 100);
    for (f = 0; f < n; f++) {
        scene(f);
        yield();
        sleep(3u);
    }
    return 0;
}
