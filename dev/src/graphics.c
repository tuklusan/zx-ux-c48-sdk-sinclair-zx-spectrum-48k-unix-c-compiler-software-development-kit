// ============================================================================
// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
// Proprietary rights reserved except as expressly licensed herein.
//
// ZX-UX C48 SDK
// This file is governed by the SANYALnet Labs Non-Commercial License in the
// root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
// for AI/ML model training are prohibited unless separately authorized.
//
// Attribution is required: "Based on original work by Supratim Sanyal of
// SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
// patent, trademark, and governing-law provisions.
// ============================================================================
#include "c48host.h"

int main(void)
{
    int x;
    cls();
    ink(7);
    draw(0, 0, 255, 191);
    draw(0, 191, 255, 0);
    circle(128, 96, 70);
    circle(128, 96, 35);
    for (x = 0; x < 256; x++) {
        if ((x & 7) == 0) plot(x, 96);
    }
    print_at(1, 22, "c48 graphics");
    return 0;
}
