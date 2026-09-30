# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
"""Semantic fixtures shared by host multitask and native execution proofs."""

SHARED_RECURSION_SOURCE = (
    "int fact(int n){if(n<2)return 1;return n*fact(n-1);}"
    "int main(void){if(fact(5)!=120)return 1;return 0;}"
)
