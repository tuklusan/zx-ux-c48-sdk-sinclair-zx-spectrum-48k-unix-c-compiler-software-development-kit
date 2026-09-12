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
#include "sndapi.h"

int main(void) {
    int rc;
    int silent;
    cls();
    border(1);
    bright(1);
    ink(7);
    paper(0);
    silent = 0;
    print_at(8, 10, "C48 ROM-COMPATIBLE BEEP");
    print_at(10, 7, "C D E F G A B C + HALF-SEMITONE");
    rc = beep(0.08, 0.0);
    if (rc == 14) {
        print_at(13, 5, "AUDIO BACKEND NOT INSTALLED");
        print_at(15, 5, "WINDOWS: built-in winsound (no pip)");
        print_at(16, 2,
                 "LINUX/MAC: pip install playsound3==3.3.2");
        print_at(18, 8, "DEMO CONTINUES WITHOUT SOUND");
        silent = 1;
    } else if (rc != 0) return rc;
    if (!silent) {
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
    } else {
        print_at(20, 16, "SILENT DEMO COMPLETE");
    }
    return 0;
}
