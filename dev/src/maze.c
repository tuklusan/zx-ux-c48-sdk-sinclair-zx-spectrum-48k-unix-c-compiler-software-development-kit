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
    unsigned int s;
    int x;
    int y;
    s = 44257u;
    cls();
    for (y = 8; y < 184; y = y + 8) {
        for (x = 8; x < 248; x = x + 8) {
            s = (s >> 1) ^ ((0 - (s & 1)) & 46080u);
            if (s & 1) draw(x - 3, y - 3, x + 3, y + 3);
            else draw(x - 3, y + 3, x + 3, y - 3);
        }
    }
    print_at(0, 2, "1982 called. it wants its maze back.");
    return 0;
}
