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
    char *p;
    cls();
    print_at(0, 0, "SECURITY TEST: INTERIOR FREE");
    print_at(2, 0, "ATTEMPT: free malloc pointer + 1");
    print_at(3, 0, "MITIGATION: exact-base guard must trap");
    p = malloc(8);
    if (p == 0) return 2;
    free(p + 1);
    print_at(5, 0, "FAILED: interior free escaped guard");
    return 99;
}
