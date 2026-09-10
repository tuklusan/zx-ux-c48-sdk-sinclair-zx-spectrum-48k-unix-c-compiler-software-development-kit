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

int main(int argc, char **argv)
{
    int i;
    cls();
    print_at(0, 0, "argv");
    for (i = 0; i < argc; i++) {
        if (i < 20) print_at(i + 2, 0, argv[i]);
    }
    return 0;
}
