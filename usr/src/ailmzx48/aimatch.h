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
int ai_readfull(unsigned char *p, unsigned int n)
{
    unsigned int done;
    unsigned int ask;
    int got;
    done = 0;
    while (done < n) {
        ask = n - done;
        if (ask > 64) ask = 64;
        got = ai_mread(&p[done], ask);
        ai_mreads = ai_mreads + 1;
        if (got <= 0) return -1;
        if ((unsigned int)got > ask) return -1;
        done = done + (unsigned int)got;
        ai_mbytes = ai_mbytes + (unsigned int)got;
    }
    return 0;
}

int ai_wordchar(int c)
{
    c = ai_lower(c);
    if (c >= 'a' && c <= 'z') return 1;
    if (c >= '0' && c <= '9') return 1;
    return 0;
}

int ai_vhas(unsigned int id)
{
    unsigned int i;
    unsigned int j;
    unsigned int off;
    unsigned int len;
    int ok;
    if (id == 0 || id >= ai_vcnt) return 0;
    off = ai_voff[id];
    len = ai_vlen[id];
    if (len == 0) return 0;
    i = 0;
    while (ai_in[i] != 0) {
        if (i != 0 && ai_wordchar(ai_in[i - 1])) {
            i = i + 1;
            continue;
        }
        j = 0;
        ok = 1;
        while (j < len) {
            if (ai_in[i + j] == 0) {
                ok = 0;
                break;
            }
            if (ai_lower(ai_in[i + j]) != ai_vblob[off + j]) {
                ok = 0;
                break;
            }
            j = j + 1;
        }
        if (ok && !ai_wordchar(ai_in[i + len])) return 1;
        i = i + 1;
    }
    return 0;
}
