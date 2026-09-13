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
int ai_isalnum(int c)
{
    if (c >= '0' && c <= '9') return 1;
    if (c >= 'a' && c <= 'z') return 1;
    if (c >= 'A' && c <= 'Z') return 1;
    return 0;
}

unsigned int ai_tokid(char *s, unsigned int start,
                      unsigned int len)
{
    unsigned int id;
    unsigned int j;
    unsigned int off;
    int ok;
    id = 1;
    while (id < ai_vcnt) {
        if (ai_vlen[id] == len) {
            off = ai_voff[id];
            j = 0;
            ok = 1;
            while (j < len) {
                if (ai_lower(s[start + j]) !=
                    ai_vblob[off + j]) {
                    ok = 0;
                    break;
                }
                j = j + 1;
            }
            if (ok) return id;
        }
        id = id + 1;
    }
    return 65535;
}

int ai_numspan(char *s, unsigned int start,
               unsigned int len)
{
    unsigned int i;
    i = 0;
    while (i < len) {
        if (s[start + i] < '0' || s[start + i] > '9') {
            return 0;
        }
        i = i + 1;
    }
    return 1;
}

unsigned int ai_encsize(char *s)
{
    unsigned int i;
    unsigned int start;
    unsigned int len;
    unsigned int id;
    unsigned int n;
    n = 2;
    i = 0;
    while (s[i] != 0) {
        if (s[i] == ' ') {
            i = i + 1;
        } else if (ai_isalnum(s[i])) {
            start = i;
            while (s[i] != 0 && ai_isalnum(s[i])) {
                i = i + 1;
            }
            len = i - start;
            id = ai_tokid(s, start, len);
            if (id != 65535) {
                if (id < 224) n = n + 1;
                else n = n + 3;
            } else {
                if (ai_numspan(s, start, len)) {
                    if (len > 15) return 65535;
                } else {
                    if (len > 31) return 65535;
                }
                n = n + 2 + len;
            }
        } else {
            n = n + 3;
            i = i + 1;
        }
        if (n > 255) return 65535;
    }
    return n;
}

void ai_ringput(unsigned int v)
{
    ai_l0ring[ai_l0head] = v;
    ai_l0head = (ai_l0head + 1) % 896;
}

void ai_lmput(unsigned int ref)
{
    ai_lmring[ai_lmhead] = ref;
    ai_lmhead = (ai_lmhead + 1) % 96;
    if (ai_lmcount < 96) ai_lmcount = ai_lmcount + 1;
}

int ai_wirewrite(char *s, unsigned int speaker)
{
    unsigned int i;
    unsigned int start;
    unsigned int len;
    unsigned int id;
    unsigned int j;
    unsigned int code;
    ai_error = 0;
    if (speaker == 0) {
        ai_ringput(3);
        ai_lmput(4101);
    } else {
        ai_ringput(4);
        ai_lmput(4102);
    }
    i = 0;
    while (s[i] != 0) {
        if (s[i] == ' ') {
            i = i + 1;
        } else if (ai_isalnum(s[i])) {
            start = i;
            while (s[i] != 0 && ai_isalnum(s[i])) {
                i = i + 1;
            }
            len = i - start;
            id = ai_tokid(s, start, len);
            if (id != 65535) {
                if (id < 224) {
                    ai_ringput(16 + id);
                } else {
                    ai_ringput(240);
                    ai_ringput(id & 255);
                    ai_ringput(id / 256);
                }
                ai_lmput(id);
            } else {
                code = 241;
                if (ai_numspan(s, start, len)) code = 242;
                else if (s[start] >= 'A' && s[start] <= 'Z') {
                    code = 243;
                }
                ai_ringput(code);
                ai_ringput(len);
                j = 0;
                while (j < len) {
                    ai_ringput(s[start + j]);
                    j = j + 1;
                }
                if (code == 242) ai_lmput(4097);
                else if (code == 243) ai_lmput(4098);
                else ai_lmput(4096);
            }
        } else {
            ai_ringput(241);
            ai_ringput(1);
            ai_ringput(s[i]);
            ai_lmput(4096);
            i = i + 1;
        }
    }
    ai_ringput(5);
    ai_lmput(4103);
    return 0;
}

int ai_ctxcheck(unsigned int un, unsigned int an)
{
    unsigned int bytes;
    unsigned int count;
    unsigned int drop;
    unsigned int need;
    unsigned int n;
    if (un == 65535 || an == 65535) return -1;
    need = un + an;
    if (need > 896) return -1;
    if (ai_l0bytes > 896 || ai_l0count > 32) return -2;
    if ((ai_l0count & 1) != 0) return -2;
    bytes = ai_l0bytes;
    count = ai_l0count;
    drop = 0;
    while (bytes + need > 896 || count + 2 > 32) {
        if (count < 2 || drop + 1 >= ai_l0count) return -2;
        n = ai_l0len[drop] + ai_l0len[drop + 1];
        if (n == 0 || n > bytes) return -2;
        bytes = bytes - n;
        count = count - 2;
        drop = drop + 2;
    }
    return 0;
}
