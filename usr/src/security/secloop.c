// ============================================================
// Copyright (c) 2026 SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Non-commercial use permitted; Commercial Use and model
// training prohibited unless separately authorized.
//
// Attribution required: SANYALnet Labs.
// See root LICENSE for full terms.
// ============================================================
#include "secapi.h"

int main(void)
{
    cls();
    print_at(0, 0, "SECURITY TEST: INFINITE LOOP");
    print_at(2, 0, "ATTEMPT: run forever");
    print_at(3, 0, "MITIGATION: --max-steps must stop VM");
    for (;;) {
        ;
    }
    return 99;
}
