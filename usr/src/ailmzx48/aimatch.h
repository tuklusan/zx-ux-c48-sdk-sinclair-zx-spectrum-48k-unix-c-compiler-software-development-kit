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

unsigned int ai_mtsalt;

int ai_vhas(unsigned int id)
{
    unsigned int i;
    unsigned int h;
    i = 0;
    while (ai_in[i] != 0) {
        while (ai_in[i] != 0 &&
               !ai_wordchar(ai_in[i])) i = i + 1;
        if (ai_in[i] == 0) break;
        h = 216 + ai_mtsalt;
        while (ai_in[i] != 0 && ai_wordchar(ai_in[i])) {
            h = (h * 33) ^ ai_lower(ai_in[i]);
            i = i + 1;
        }
        if (224 + (h % 3872) == id) return 1;
    }
    return 0;
}
