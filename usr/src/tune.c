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
#include "c48host.h"

int main(void) {
    int rc;
    cls();
    border(1);
    bright(1);
    ink(7);
    paper(0);
    print_at(8, 10, "C48 ROM-COMPATIBLE BEEP");
    print_at(10, 7, "C D E F G A B C + HALF-SEMITONE");
    rc = beep(0.08, 0.0);
    if (rc != 0) return rc;
    rc = beep(0.08, 2.0);
    if (rc != 0) return rc;
    rc = beep(0.08, 4.0);
    if (rc != 0) return rc;
    rc = beep(0.08, 5.0);
    if (rc != 0) return rc;
    rc = beep(0.08, 7.0);
    if (rc != 0) return rc;
    rc = beep(0.08, 9.0);
    if (rc != 0) return rc;
    rc = beep(0.08, 11.0);
    if (rc != 0) return rc;
    rc = beep(0.12, 12.0);
    if (rc != 0) return rc;
    rc = beep(0.18, 0.5);
    if (rc != 0) return rc;
    print_at(13, 19, "BEEP COMPLETE");
    return 0;
}
