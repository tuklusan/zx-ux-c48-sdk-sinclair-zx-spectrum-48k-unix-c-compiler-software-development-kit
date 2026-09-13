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

int ai_capref(unsigned char *p, unsigned int o,
              unsigned int ref)
{
    if (ai_capget(p, o + 4) == ref) return 1;
    if (ai_capget(p, o + 6) == ref) return 1;
    if (ai_capget(p, o + 8) == ref) return 1;
    if (ai_capget(p, o + 10) == ref) return 1;
    if (p[o + 1] == 3 &&
        ai_capget(p, o + 12) == ref) return 1;
    return 0;
}

void ai_clrref(unsigned char *p, unsigned int count,
               unsigned int ref)
{
    unsigned int i;
    unsigned int o;
    unsigned int at;
    int lost;
    i = 0;
    while (i < count) {
        o = ai_capoff(i);
        lost = 0;
        if (p[o + 1] != 0) {
            at = 4;
            while (at <= 10) {
                if (ai_capget(p, o + at) == ref) {
                    p[o + at] = 0;
                    p[o + at + 1] = 0;
                    lost = 1;
                }
                at = at + 2;
            }
            if (p[o + 1] == 3 &&
                ai_capget(p, o + 12) == ref) {
                p[o + 12] = 0;
                p[o + 13] = 0;
                lost = 1;
            }
            if (lost && ai_litloss != 65535) {
                ai_litloss = ai_litloss + 1;
            }
        }
        i = i + 1;
    }
}

void ai_invref(unsigned int ref)
{
    if (ref == 0) return;
    ai_clrref(ai_l1, 48, ref);
    ai_clrref(ai_l2, 24, ref);
}

int ai_litmatch(unsigned int slot, char *s,
                unsigned int start, unsigned int n)
{
    unsigned int i;
    unsigned int off;
    if (slot >= 8 || ai_litlen[slot] != n) return 0;
    off = slot * 31;
    i = 0;
    while (i < n) {
        if (ai_lower(ai_litbuf[off + i]) !=
            ai_lower(s[start + i])) return 0;
        i = i + 1;
    }
    return 1;
}

unsigned int ai_litpick(char *s, unsigned int start,
                        unsigned int n)
{
    unsigned int slot;
    unsigned int ref;
    unsigned int i;
    unsigned int o;
    unsigned int prot;
    unsigned int imp;
    unsigned int age;
    unsigned int sp;
    unsigned int si;
    unsigned int sa;
    unsigned int best;
    unsigned int bp;
    unsigned int bi;
    unsigned int ba;
    int found;
    int any;
    slot = 0;
    while (slot < 8) {
        if (ai_slotref(slot) != 0 &&
            ai_litmatch(slot, s, start, n)) return slot + 8;
        slot = slot + 1;
    }
    slot = 0;
    while (slot < 8) {
        ref = ai_slotref(slot);
        any = 0;
        if (ref != 0) {
            i = 0;
            while (i < 48 && !any) {
                o = ai_capoff(i);
                if (ai_l1[o + 1] != 0 &&
                    ai_capref(ai_l1, o, ref)) any = 1;
                i = i + 1;
            }
            i = 0;
            while (i < 24 && !any) {
                o = ai_capoff(i);
                if (ai_l2[o + 1] != 0 &&
                    ai_capref(ai_l2, o, ref)) any = 1;
                i = i + 1;
            }
        }
        if (!any) return slot;
        slot = slot + 1;
    }
    best = 0;
    bp = 0;
    bi = 0;
    ba = 0;
    found = 0;
    slot = 0;
    while (slot < 8) {
        ref = ai_slotref(slot);
        sp = 0;
        si = 0;
        sa = 255;
        any = 0;
        i = 0;
        while (i < 48) {
            o = ai_capoff(i);
            if (ai_l1[o + 1] != 0 &&
                ai_capref(ai_l1, o, ref)) {
                prot = ai_protect(ai_l1, o);
                imp = ai_l1[o + 14];
                age = ai_l1[o + 15];
                if (!any || prot > sp ||
                    (prot == sp && imp > si) ||
                    (prot == sp && imp == si && age < sa)) {
                    sp = prot;
                    si = imp;
                    sa = age;
                    any = 1;
                }
            }
            i = i + 1;
        }
        i = 0;
        while (i < 24) {
            o = ai_capoff(i);
            if (ai_l2[o + 1] != 0 &&
                ai_capref(ai_l2, o, ref)) {
                prot = ai_protect(ai_l2, o);
                imp = ai_l2[o + 14];
                age = ai_l2[o + 15];
                if (!any || prot > sp ||
                    (prot == sp && imp > si) ||
                    (prot == sp && imp == si && age < sa)) {
                    sp = prot;
                    si = imp;
                    sa = age;
                    any = 1;
                }
            }
            i = i + 1;
        }
        if (!found || sp < bp ||
            (sp == bp && si < bi) ||
            (sp == bp && si == bi && sa > ba)) {
            best = slot;
            bp = sp;
            bi = si;
            ba = sa;
            found = 1;
        }
        slot = slot + 1;
    }
    return best;
}

int ai_catraw(char *s)
{
    unsigned int i;
    i = 0;
    while (s[i] != 0) {
        if (ai_olen >= 255) return 0;
        ai_out[ai_olen] = s[i];
        ai_olen = ai_olen + 1;
        i = i + 1;
    }
    ai_out[ai_olen] = 0;
    return 1;
}

int ai_catref(unsigned int ref)
{
    unsigned int slot;
    unsigned int off;
    unsigned int i;
    if (!ai_refvalid(ref)) return 0;
    slot = ref & 7;
    if (ai_litlen[slot] > 255 - ai_olen) return 0;
    off = slot * 31;
    i = 0;
    while (i < ai_litlen[slot]) {
        ai_out[ai_olen] = ai_litbuf[off + i];
        ai_olen = ai_olen + 1;
        i = i + 1;
    }
    ai_out[ai_olen] = 0;
    return 1;
}

void ai_namecommit(void)
{
    int pos;
    unsigned int start;
    unsigned int n;
    unsigned int i;
    unsigned int gen;
    unsigned int slot;
    unsigned int off;
    pos = ai_find("my name is ");
    if (pos < 0) return;
    start = pos + 11;
    n = 0;
    while (ai_in[start + n] != 0 && n < 32) {
        n = n + 1;
    }
    if (n == 0 || n > 31) return;
    slot = ai_litpick(ai_in, start, n);
    if (slot >= 8) {
        slot = slot - 8;
        ai_litold = 0;
        ai_litcur = ai_slotref(slot);
        ai_litset = 1;
        ai_namesem();
        return;
    }
    ai_litold = ai_slotref(slot);
    gen = ai_litgen[slot] + 1;
    if (gen == 0 || gen > 4095) gen = 1;
    ai_litgen[slot] = gen;
    ai_litlen[slot] = n;
    off = slot * 31;
    i = 0;
    while (i < n) {
        ai_litbuf[off + i] = ai_in[start + i];
        i = i + 1;
    }
    ai_litcur = ai_slotref(slot);
    ai_litset = 1;
    ai_namesem();
}

void ai_nameack(void)
{
    int pos;
    unsigned int start;
    unsigned int n;
    unsigned int i;
    ai_settext("I will remember ");
    pos = ai_find("my name is ");
    if (pos < 0) {
        ai_settext("I could not store that name.");
        puts(ai_out);
        return;
    }
    start = pos + 11;
    n = 0;
    while (ai_in[start + n] != 0 && n < 32) {
        n = n + 1;
    }
    if (n == 0 || n > 31 || n > 254 - ai_olen) {
        ai_settext("I could not store that name.");
        puts(ai_out);
        return;
    }
    i = 0;
    while (i < n) {
        ai_out[ai_olen] = ai_in[start + i];
        ai_olen = ai_olen + 1;
        i = i + 1;
    }
    if (ai_olen < 255) {
        ai_out[ai_olen] = '.';
        ai_olen = ai_olen + 1;
    }
    ai_out[ai_olen] = 0;
    puts(ai_out);
}

void ai_nameans(void)
{
    unsigned int ref;
    ref = ai_namefind();
    if (ref == 0) {
        ai_settext("I do not have your name yet.");
        puts(ai_out);
        return;
    }
    ai_lituse = 1;
    ai_semuse = 1;
    ai_settext("I remember your name as ");
    if (!ai_catref(ref) || !ai_catraw(".")) {
        ai_settext("I could not recover your name.");
    }
    puts(ai_out);
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
