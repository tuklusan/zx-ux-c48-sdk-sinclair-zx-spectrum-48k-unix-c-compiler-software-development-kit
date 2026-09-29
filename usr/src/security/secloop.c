// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
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
