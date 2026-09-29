// ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs
// supratim-sanyal.blogspot.com
//
// SANYALnet Labs Non-Commercial License, attribution to
// SANYALnet Labs required, see LICENSE for more information
unsigned int ai_protect(unsigned char *p,
                        unsigned int o)
{
    unsigned int src;
    if ((p[o] & 4) != 0 || (p[o] & 16) != 0) return 3;
    src = (p[o] / 64) & 3;
    if (src == 0) return 2;
    if (src == 1) return 1;
    return 0;
}

unsigned int ai_victim(unsigned char *p, unsigned int count)
{
    unsigned int i;
    unsigned int o;
    unsigned int best;
    unsigned int bprot;
    unsigned int bimp;
    unsigned int bage;
    unsigned int prot;
    unsigned int imp;
    unsigned int age;
    int found;
    best = 0;
    bprot = 0;
    bimp = 0;
    bage = 0;
    found = 0;
    i = 0;
    while (i < count) {
        o = ai_capoff(i);
        if (p[o + 1] != 0) {
            prot = ai_protect(p, o);
            imp = p[o + 14];
            age = p[o + 15];
            if (!found || prot < bprot ||
                (prot == bprot && imp < bimp) ||
                (prot == bprot && imp == bimp &&
                 age > bage)) {
                best = i;
                bprot = prot;
                bimp = imp;
                bage = age;
                found = 1;
            }
        }
        i = i + 1;
    }
    return best;
}
