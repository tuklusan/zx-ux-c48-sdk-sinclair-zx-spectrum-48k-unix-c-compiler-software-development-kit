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
        got = read(ai_mfd, &p[done], ask);
        ai_mreads = ai_mreads + 1;
        if (got < 0) {
            ai_scanwhy = 1;
            return -1;
        }
        if (got == 0) {
            ai_scanwhy = 2;
            return -1;
        }
        /* read() <= requested count. */
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

unsigned int ai_hfind(unsigned int id)
{
    unsigned int lo;
    unsigned int hi;
    unsigned int mid;
    lo = 0;
    hi = ai_hcnt;
    while (lo < hi) {
        mid = lo + ((hi - lo) / 2);
        if (ai_hid[mid] < id) lo = mid + 1;
        else hi = mid;
    }
    if (lo >= ai_hcnt) return 0;
    if (ai_hid[lo] != id) return 0;
    return lo + 1;
}

int ai_hsame(unsigned int at, char *s,
             unsigned int start, unsigned int len)
{
    unsigned int i;
    unsigned int off;
    if (at >= ai_hcnt) return 0;
    if (ai_hlen[at] != len) return 0;
    off = ai_hoff[at];
    i = 0;
    while (i < len) {
        if (ai_lower(s[start + i]) != ai_hblob[off + i]) {
            return 0;
        }
        i = i + 1;
    }
    return 1;
}

void ai_hprep(void)
{
    unsigned int i;
    unsigned int start;
    unsigned int len;
    unsigned int h;
    unsigned int id;
    unsigned int at;
    unsigned int n;
    i = 0;
    n = 0;
    while (ai_in[i] != 0) {
        while (ai_in[i] != 0 &&
               !ai_wordchar(ai_in[i])) i = i + 1;
        if (ai_in[i] == 0) break;
        start = i;
        h = 216 + ai_mtsalt;
        while (ai_in[i] != 0 && ai_wordchar(ai_in[i])) {
            h = (h * 33) ^ ai_lower(ai_in[i]);
            i = i + 1;
        }
        len = i - start;
        id = 224 + (h % 3872);
        at = ai_hfind(id);
        if (at != 0) {
            at = at - 1;
            if (ai_hsame(at, ai_in, start, len)) {
                if (n >= 48) {
                    ai_mhits = 49;
                    return;
                }
                ai_seen[n * 2] = id & 255;
                ai_seen[(n * 2) + 1] = id / 256;
                n = n + 1;
            }
        }
    }
    ai_mhits = n;
}

int ai_vhas(unsigned int id)
{
    unsigned int i;
    unsigned int value;
    i = 0;
    while (i < ai_mhits && i < 48) {
        value = ai_seen[i * 2];
        value = value +
                ((unsigned int)ai_seen[(i * 2) + 1] * 256);
        if (value == id) return 1;
        i = i + 1;
    }
    return 0;
}
