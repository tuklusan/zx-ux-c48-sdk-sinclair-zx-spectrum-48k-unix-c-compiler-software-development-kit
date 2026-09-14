// ============================================================
// Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
// Proprietary rights reserved except as licensed in LICENSE.
//
// ZX-UX C48 SDK - SANYALnet Labs Non-Commercial License.
// Attribution required: Based on original work by Supratim
// Sanyal of SANYALnet Labs. See root LICENSE for full terms.
// Learned factual bridge runtime.
// ============================================================
unsigned int ai_bp1;
unsigned int ai_bp2;

unsigned int ai_bhash(unsigned char *p, unsigned int n)
{
    unsigned int h;
    unsigned int i;
    h = 216;
    i = 0;
    while (i < n) {
        h = ((h * 33) ^ p[i]) & 65535;
        i = i + 1;
    }
    return h;
}

void ai_bpush(unsigned char *p, unsigned int n)
{
    ai_bp2 = ai_bp1;
    ai_bp1 = ai_bhash(p, n);
}

void ai_bpushv(unsigned int id)
{
    unsigned int off;
    unsigned int len;
    if (id == 0 || id >= ai_vcnt) return;
    off = ai_voff[id];
    len = ai_vlen[id];
    ai_bpush(&ai_vblob[off], len);
}

unsigned int ai_bkey(unsigned int topic,
                     unsigned int p2,
                     unsigned int p1)
{
    unsigned int h;
    h = (216 + ai_bsalt) & 65535;
    h = ((h * 33) ^ (topic & 255)) & 65535;
    h = ((h * 33) ^ (topic / 256)) & 65535;
    h = ((h * 33) ^ (p2 & 255)) & 65535;
    h = ((h * 33) ^ (p2 / 256)) & 65535;
    h = ((h * 33) ^ (p1 & 255)) & 65535;
    h = ((h * 33) ^ (p1 / 256)) & 65535;
    return h;
}

unsigned int ai_bfind(unsigned int topic,
                      unsigned int p2,
                      unsigned int p1)
{
    unsigned int key;
    unsigned int i;
    key = ai_bkey(topic, p2, p1);
    i = 0;
    while (i < ai_brcnt) {
        if (ai_brkey[i] == key) return ai_brnext[i];
        i = i + 1;
    }
    return 0;
}

int ai_addlit(unsigned char *p, unsigned int n)
{
    unsigned int i;
    if (ai_olen != 0) {
        if (ai_olen >= 254) return 0;
        ai_out[ai_olen] = ' ';
        ai_olen = ai_olen + 1;
    }
    if (n > 254 - ai_olen) return 0;
    i = 0;
    while (i < n) {
        ai_out[ai_olen] = p[i];
        ai_olen = ai_olen + 1;
        i = i + 1;
    }
    return 1;
}

int ai_bcopy(unsigned int pos,
             unsigned int end,
             unsigned int track)
{
    unsigned int code;
    unsigned int id;
    unsigned int n;
    while (pos < end) {
        code = ai_win1[pos];
        pos = pos + 1;
        if (code >= 16 && code <= 239) {
            id = code - 16;
            if (!ai_addtok(id)) return 0;
            if (track) ai_bpushv(id);
        } else if (code == 240) {
            if (pos + 2 > end) return 0;
            id = ai_getu16(ai_win1, pos);
            pos = pos + 2;
            if (!ai_addtok(id)) return 0;
            if (track) ai_bpushv(id);
        } else if (code == 241 || code == 242 ||
                   code == 243) {
            if (pos >= end) return 0;
            n = ai_win1[pos];
            pos = pos + 1;
            if (pos + n > end) return 0;
            if (!ai_addlit(&ai_win1[pos], n)) return 0;
            if (track) ai_bpush(&ai_win1[pos], n);
            pos = pos + n;
        } else {
            return 0;
        }
        ai_otokens = ai_otokens + 1;
    }
    return 1;
}

int ai_bmatch(unsigned int pos,
              unsigned int end,
              unsigned int pred)
{
    unsigned int code;
    unsigned int id;
    unsigned int n;
    unsigned int off;
    unsigned int len;
    unsigned int i;
    unsigned int found;
    if (pred == 0 || pred >= ai_vcnt) return 0;
    off = ai_voff[pred];
    len = ai_vlen[pred];
    found = 0;
    while (pos < end) {
        code = ai_win1[pos];
        pos = pos + 1;
        if (code == 1 || code == 2 || code == 6) {
        } else if (code >= 16 && code <= 239) {
            if (found) return 0;
            id = code - 16;
            if (id != pred) return 0;
            found = 1;
        } else if (code == 240) {
            if (pos + 2 > end || found) return 0;
            id = ai_getu16(ai_win1, pos);
            pos = pos + 2;
            if (id != pred) return 0;
            found = 1;
        } else if (code == 241 || code == 242 ||
                   code == 243) {
            if (pos >= end || found) return 0;
            n = ai_win1[pos];
            pos = pos + 1;
            if (pos + n > end || n != len) return 0;
            i = 0;
            while (i < n) {
                if (ai_win1[pos + i] != ai_vblob[off + i]) {
                    return 0;
                }
                i = i + 1;
            }
            pos = pos + n;
            found = 1;
        } else {
            return 0;
        }
    }
    return found;
}

int ai_bemit(unsigned int pred)
{
    if (!ai_addtok(pred)) return 0;
    ai_otokens = ai_otokens + 1;
    if (ai_bruse != 65535) ai_bruse = ai_bruse + 1;
    return 1;
}

int ai_coldans(void)
{
    unsigned int tcnt;
    unsigned int acnt;
    unsigned int apos;
    unsigned int pbase;
    unsigned int s1;
    unsigned int e1;
    unsigned int s2;
    unsigned int e2;
    unsigned int pred;
    if (ai_w1len < 11) return 0;
    tcnt = ai_win1[9];
    apos = 10 + (tcnt * 2);
    if (apos >= ai_w1len) return 0;
    acnt = ai_win1[apos];
    if (acnt == 0 || acnt > 2) return 0;
    pbase = apos + 1 + (acnt * 2);
    if (pbase >= ai_w1len) return 0;
    if (!ai_lmlead(ai_mtopic)) {
        ai_olen = 0;
        ai_otokens = 0;
    }
    ai_bp1 = 0;
    ai_bp2 = 0;
    s1 = pbase + ai_win1[apos + 1];
    e1 = s1 + ai_win1[apos + 2];
    if (e1 > ai_w1len || e1 <= s1) return 0;
    if (acnt == 1) {
        pred = ai_bfind(ai_mtopic, 0, 0);
        if (pred == 0) return 0;
        if (!ai_bmatch(pbase, s1, pred)) return 0;
        if (!ai_bemit(pred)) return 0;
        if (!ai_bcopy(s1, e1, 0)) return 0;
    } else {
        s2 = pbase + ai_win1[apos + 3];
        e2 = s2 + ai_win1[apos + 4];
        if (e2 > ai_w1len || e2 <= s2) return 0;
        if (s2 <= e1) return 0;
        if (!ai_bcopy(s1, e1, 1)) return 0;
        pred = ai_bfind(ai_mtopic, ai_bp2, ai_bp1);
        if (pred == 0) return 0;
        if (!ai_bmatch(e1, s2, pred)) return 0;
        if (!ai_bemit(pred)) return 0;
        if (!ai_bcopy(s2, e2, 0)) return 0;
    }
    if (ai_olen >= 254) return 0;
    ai_out[ai_olen] = '.';
    ai_olen = ai_olen + 1;
    ai_out[ai_olen] = 0;
    if (ai_out[0] >= 'a' && ai_out[0] <= 'z') {
        ai_out[0] = ai_out[0] - 32;
    }
    return 1;
}
