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
#include "appapi.h"

int w_tab[65] = {
    0, 3, 6, 9, 13, 16, 19, 22, 25, 28, 31, 34, 37,
    40, 43, 46, 49, 52, 55, 58, 60, 63, 66, 68, 71,
    74, 76, 79, 81, 84, 86, 88, 91, 93, 95, 97, 99,
    101, 103, 105, 106, 108, 110, 111, 113, 114, 116,
    117, 118, 119, 121, 122, 122, 123, 124, 125, 126,
    126, 127, 127, 127, 128, 128, 128, 128
};

int w_z[7];
int w_w[7];
int w_h[7];
int w_sel;
int w_yaw;
int w_pitch;
int w_zoom;

int w_sin(int a)
{
    int q;
    int n;
    a = a & 255;
    q = a >> 6;
    n = a & 63;
    if (q == 0) return w_tab[n];
    if (q == 1) return w_tab[64 - n];
    if (q == 2) return -w_tab[n];
    return -w_tab[64 - n];
}

int w_cos(int a)
{
    return w_sin(a + 64);
}

void w_reset(void)
{
    w_z[0] = -78;
    w_z[1] = -58;
    w_z[2] = -34;
    w_z[3] = -8;
    w_z[4] = 22;
    w_z[5] = 52;
    w_z[6] = 78;
    w_w[0] = 3;
    w_w[1] = 22;
    w_w[2] = 36;
    w_w[3] = 46;
    w_w[4] = 40;
    w_w[5] = 23;
    w_w[6] = 4;
    w_h[0] = 3;
    w_h[1] = 7;
    w_h[2] = 11;
    w_h[3] = 14;
    w_h[4] = 13;
    w_h[5] = 9;
    w_h[6] = 4;
    w_sel = 3;
    w_yaw = 22;
    w_pitch = 12;
    w_zoom = 128;
}

void w_rot(int x, int y, int z,
           int *ox, int *oy, int *oz)
{
    int sy;
    int cy;
    int sx;
    int cx;
    int u;
    int v;
    int w;
    sy = w_sin(w_yaw);
    cy = w_cos(w_yaw);
    sx = w_sin(w_pitch);
    cx = w_cos(w_pitch);
    u = (x * cy + z * sy) / 128;
    w = (z * cy - x * sy) / 128;
    v = (y * cx - w * sx) / 128;
    w = (y * sx + w * cx) / 128;
    *ox = u;
    *oy = v;
    *oz = w;
}

int w_project(int x, int y, int z, int *sx, int *sy)
{
    int q;
    w_rot(x, y, z, &x, &y, &z);
    q = z + 190;
    if (q < 30)
        return 0;
    *sx = 128 + x * w_zoom / q;
    *sy = 100 - y * w_zoom / q;
    if (*sx < 0 || *sx > 255)
        return 0;
    if (*sy < 8 || *sy > 168)
        return 0;
    return 1;
}

void w_line(int x1, int y1, int z1,
            int x2, int y2, int z2)
{
    int a;
    int b;
    int c;
    int d;
    if (!w_project(x1, y1, z1, &a, &b))
        return;
    if (!w_project(x2, y2, z2, &c, &d))
        return;
    draw(a, b, c, d);
}

void w_plane_point(int p, int n,
                   int *x, int *y, int *z)
{
    *z = w_z[p];
    if (n == 0) {
        *x = 0;
        *y = w_h[p];
    }
    if (n == 1) {
        *x = w_w[p];
        *y = 0;
    }
    if (n == 2) {
        *x = 0;
        *y = -w_h[p];
    }
    if (n == 3) {
        *x = -w_w[p];
        *y = 0;
    }
}

void w_draw_plane(int p)
{
    int n;
    int m;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    for (n = 0; n < 4; n++) {
        m = (n + 1) & 3;
        w_plane_point(p, n, &x1, &y1, &z1);
        w_plane_point(p, m, &x2, &y2, &z2);
        w_line(x1, y1, z1, x2, y2, z2);
    }
}

void w_draw_hull(void)
{
    int p;
    int n;
    int x1;
    int y1;
    int z1;
    int x2;
    int y2;
    int z2;
    ink(5);
    bright(0);
    for (p = 0; p < 7; p++)
        w_draw_plane(p);
    for (p = 0; p < 6; p++) {
        for (n = 0; n < 4; n++) {
            w_plane_point(p, n, &x1, &y1, &z1);
            w_plane_point(p + 1, n, &x2, &y2, &z2);
            w_line(x1, y1, z1, x2, y2, z2);
        }
    }
}

void w_draw_tower(void)
{
    int z1;
    int z2;
    z1 = 2;
    z2 = 28;
    ink(7);
    bright(1);
    w_line(-10, 14, z1, 10, 14, z1);
    w_line(10, 14, z1, 10, 14, z2);
    w_line(10, 14, z2, -10, 14, z2);
    w_line(-10, 14, z2, -10, 14, z1);
    w_line(-7, 27, 8, 7, 27, 8);
    w_line(7, 27, 8, 7, 27, 22);
    w_line(7, 27, 22, -7, 27, 22);
    w_line(-7, 27, 22, -7, 27, 8);
    w_line(-10, 14, z1, -7, 27, 8);
    w_line(10, 14, z1, 7, 27, 8);
    w_line(10, 14, z2, 7, 27, 22);
    w_line(-10, 14, z2, -7, 27, 22);
}

void w_status(void)
{
    char num[8];
    app_clear_row(20);
    app_clear_row(21);
    app_clear_row(22);
    app_clear_row(23);
    print_at(20, 1, "PLANE ");
    app_uint_text(num, (unsigned int)(w_sel + 1));
    print_at(20, 7, num);
    print_at(20, 12, "Z=");
    app_int_text(num, w_z[w_sel]);
    print_at(20, 14, num);
    print_at(20, 24, "W=");
    app_uint_text(num, (unsigned int)w_w[w_sel]);
    print_at(20, 26, num);
    print_at(20, 34, "H=");
    app_uint_text(num, (unsigned int)w_h[w_sel]);
    print_at(20, 36, num);
    print_at(21, 1, "N/P PLANE  A/D WIDTH  W/S HT  Z/X DEPTH");
    print_at(22, 1, "5/8 YAW  7/6 PITCH  +/- ZOOM  R RESET  Q");
    print_at(23, 1, "MODEL: IMPERIAL BATTLESHIP AURELIAN");
}

void w_render(void)
{
    cls();
    paper(0);
    ink(7);
    bright(1);
    print_at(0, 12, "WIRE3D - CROSS-SECTION EDITOR");
    w_draw_hull();
    w_draw_tower();
    ink(6);
    bright(1);
    w_draw_plane(w_sel);
    w_status();
    yield();
}

void w_edit(int key)
{
    if (key == 'n' && w_sel < 6)
        w_sel++;
    if (key == 'p' && w_sel > 0)
        w_sel--;
    if (key == 'a' && w_w[w_sel] > 3)
        w_w[w_sel] = w_w[w_sel] - 2;
    if (key == 'd' && w_w[w_sel] < 60)
        w_w[w_sel] = w_w[w_sel] + 2;
    if (key == 's' && w_h[w_sel] > 3)
        w_h[w_sel] = w_h[w_sel] - 2;
    if (key == 'w' && w_h[w_sel] < 30)
        w_h[w_sel] = w_h[w_sel] + 2;
    if (key == 'z' && w_z[w_sel] > -100)
        w_z[w_sel] = w_z[w_sel] - 3;
    if (key == 'x' && w_z[w_sel] < 100)
        w_z[w_sel] = w_z[w_sel] + 3;
    if (key == '5')
        w_yaw = w_yaw - 6;
    if (key == '8')
        w_yaw = w_yaw + 6;
    if (key == '7')
        w_pitch = w_pitch - 5;
    if (key == '6')
        w_pitch = w_pitch + 5;
    if (key == '+' && w_zoom < 180)
        w_zoom = w_zoom + 8;
    if (key == '-' && w_zoom > 72)
        w_zoom = w_zoom - 8;
    if (key == 'r')
        w_reset();
}

int main(int argc, char **argv)
{
    int key;
    w_reset();
    w_render();
    if (argc > 1 && strcmp(argv[1], "verify") == 0)
        return 0;
    while (1) {
        key = app_key();
        if (key == 'q')
            return 0;
        w_edit(key);
        w_render();
    }
}
