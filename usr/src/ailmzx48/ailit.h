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

unsigned int ai_slotref(unsigned int slot)
{
    unsigned int gen;
    if (slot >= 8) return 0;
    gen = ai_litgen[slot];
    if (gen == 0 || gen > 4095) return 0;
    return 32768 + (gen * 8) + slot;
}

int ai_refvalid(unsigned int ref)
{
    unsigned int slot;
    unsigned int gen;
    if (ref < 32768) return 0;
    slot = ref & 7;
    gen = (ref - 32768) / 8;
    if (gen == 0 || gen > 4095) return 0;
    if (ai_litgen[slot] != gen) return 0;
    if (ai_litlen[slot] == 0 || ai_litlen[slot] > 31) {
        return 0;
    }
    return 1;
}

void ai_putref(unsigned int ref)
{
    unsigned int slot;
    unsigned int off;
    unsigned int i;
    if (!ai_refvalid(ref)) return;
    slot = ref & 7;
    off = slot * 31;
    i = 0;
    while (i < ai_litlen[slot]) {
        putchar(ai_litbuf[off + i]);
        i = i + 1;
    }
}

void ai_invref(unsigned int ref)
{
    unsigned int i;
    unsigned int o;
    unsigned int got;
    if (ref == 0) return;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] != 0) {
            got = ai_capget(ai_l1, o + 12);
            if (got == ref) {
                ai_l1[o + 12] = 0;
                ai_l1[o + 13] = 0;
                if (ai_litloss != 65535) {
                    ai_litloss = ai_litloss + 1;
                }
            }
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] != 0) {
            got = ai_capget(ai_l2, o + 12);
            if (got == ref) {
                ai_l2[o + 12] = 0;
                ai_l2[o + 13] = 0;
                if (ai_litloss != 65535) {
                    ai_litloss = ai_litloss + 1;
                }
            }
        }
        i = i + 1;
    }
}

void ai_namesuper(void)
{
    unsigned int i;
    unsigned int o;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 3 &&
            (ai_l1[o] & 32) == 0) {
            ai_l1[o] = ai_l1[o] | 32;
            ai_l1[o + 14] = 0;
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == 3 &&
            (ai_l2[o] & 32) == 0) {
            ai_l2[o] = ai_l2[o] | 32;
            ai_l2[o + 14] = 0;
        }
        i = i + 1;
    }
}

void ai_nameadd(unsigned int ref)
{
    unsigned int i;
    unsigned int o;
    unsigned int victim;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 0) {
            ai_capset(&ai_l1[o], 0, 3, 255, 0);
            ai_l1[o + 12] = ref & 255;
            ai_l1[o + 13] = ref / 256;
            ai_l1count = ai_l1count + 1;
            return;
        }
        i = i + 1;
    }
    victim = ai_victim(ai_l1, 48);
    o = ai_capoff(victim);
    ai_l2merge(&ai_l1[o]);
    if (ai_compact != 65535) {
        ai_compact = ai_compact + 1;
    }
    ai_capset(&ai_l1[o], 0, 3, 255, 0);
    ai_l1[o + 12] = ref & 255;
    ai_l1[o + 13] = ref / 256;
}

void ai_namesem(void)
{
    ai_capage();
    ai_namesuper();
    if (ai_litold != 0) ai_invref(ai_litold);
    ai_nameadd(ai_litcur);
}

unsigned int ai_namefind(void)
{
    unsigned int i;
    unsigned int o;
    unsigned int ref;
    unsigned int best;
    unsigned int imp;
    unsigned int age;
    unsigned int bimp;
    unsigned int bage;
    best = 0;
    bimp = 0;
    bage = 255;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 3 &&
            (ai_l1[o] & 32) == 0) {
            ref = ai_capget(ai_l1, o + 12);
            if (ref != 0 && !ai_refvalid(ref)) {
                ai_l1[o + 12] = 0;
                ai_l1[o + 13] = 0;
                if (ai_litloss != 65535) {
                    ai_litloss = ai_litloss + 1;
                }
                ref = 0;
            }
            if (ref != 0) {
                imp = ai_l1[o + 14];
                age = ai_l1[o + 15];
                if (best == 0 || imp > bimp ||
                    (imp == bimp && age < bage)) {
                    best = ref;
                    bimp = imp;
                    bage = age;
                }
            }
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == 3 &&
            (ai_l2[o] & 32) == 0) {
            ref = ai_capget(ai_l2, o + 12);
            if (ref != 0 && !ai_refvalid(ref)) {
                ai_l2[o + 12] = 0;
                ai_l2[o + 13] = 0;
                if (ai_litloss != 65535) {
                    ai_litloss = ai_litloss + 1;
                }
                ref = 0;
            }
            if (ref != 0) {
                imp = ai_l2[o + 14];
                age = ai_l2[o + 15];
                if (best == 0 || imp > bimp ||
                    (imp == bimp && age < bage)) {
                    best = ref;
                    bimp = imp;
                    bage = age;
                }
            }
        }
        i = i + 1;
    }
    return best;
}
