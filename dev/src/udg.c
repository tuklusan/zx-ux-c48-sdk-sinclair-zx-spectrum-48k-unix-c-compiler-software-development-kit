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
    unsigned char a[8] = {24, 60, 126, 219, 255, 36, 90, 165};
    unsigned char b[8] = {129, 66, 36, 24, 24, 36, 66, 129};
    cls();
    udg_define(0, a);
    udg_define(1, b);
    udg_draw(0, 10, 12);
    udg_draw(1, 10, 14);
    print_at(14, 16, "udg sprites");
    return 0;
}
