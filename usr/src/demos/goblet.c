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

int gr[10] = {18, 28, 36, 40, 36, 16, 7, 7, 28, 32};
int gy[10] = {58, 48, 34, 16, 0, -20, -42, -58, -66, -70};

void gpt(int p, int a, int f, int *x, int *y, int *z)
{
    int u;
    int v;
    int w;
    u = gr[p] * d_cos(a) / 128;
    v = gy[p];
    w = gr[p] * d_sin(a) / 128;
    d_rot3(u, v, w, 10 + f * 2, f * 5, f, x, y, z);
    *x = *x * 2;
}

void scene(int f)
{
    int p;
    int j;
    int a1;
    int a2;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    cls();
    paper(0);
    border(3 + (f & 1) * 4);
    ink(7);
    bright(1);
    for (p = 0; p < 10; p++) {
        for (j = 0; j < 12; j++) {
            a1 = j * 21;
            if (j == 11) a2 = 0;
            else a2 = (j + 1) * 21;
            gpt(p, a1, f, &x1, &y1, &z1);
            gpt(p, a2, f, &x2, &y2, &z2);
            d_line3(x1, y1, z1, x2, y2, z2);
        }
    }
    for (p = 0; p < 9; p++) {
        for (j = 0; j < 12; j++) {
            a1 = j * 21;
            gpt(p, a1, f, &x1, &y1, &z1);
            gpt(p + 1, a1, f, &x2, &y2, &z2);
            d_line3(x1, y1, z1, x2, y2, z2);
        }
    }
    print_at(0, 2, "CRYSTAL GOBLET / 3D WIREFRAME");
    print_at(23, 0,
    "MATH: p=(r(profile)*cos a,y(profile),r(profile)*sin a)");
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
