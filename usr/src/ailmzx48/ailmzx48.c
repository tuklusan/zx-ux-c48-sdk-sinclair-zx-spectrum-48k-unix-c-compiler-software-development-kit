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
int getchar(void);
int putchar(int c);
int puts(char *s);
int beep(float duration, float pitch);
int yield(void);
unsigned int ai_mstat(void);
int ai_mseek(unsigned int pos);
int ai_mread(unsigned char *p, unsigned int n);

#include "aimod.h"

unsigned int ai_turns;
unsigned int ai_otokens;
unsigned int ai_yields;
unsigned int ai_error;
unsigned int ai_beeps;
unsigned int ai_lasttop;
unsigned int ai_ctxuse;
unsigned int ai_havectx;
unsigned int ai_altuse;
unsigned int ai_altstate;
unsigned int ai_histuse;
unsigned int ai_hcount;
unsigned char ai_hist[6];
unsigned int ai_litgen[8];
unsigned char ai_litlen[8];
char ai_litbuf[248];
unsigned int ai_litset;
unsigned int ai_lituse;
char ai_in[192];
char ai_out[256];
int ai_drop_lf;
unsigned int ai_olen;
unsigned char ai_seen[96];
unsigned int ai_mrecords;
unsigned int ai_mhits;
unsigned int ai_mbytes;
unsigned int ai_mreads;
unsigned int ai_fs1;
unsigned int ai_fs2;
unsigned int ai_w1len;
unsigned int ai_w2len;
int ai_w1score;
int ai_w2score;
unsigned char ai_mhead[40];
unsigned char ai_win1[192];
unsigned char ai_win2[192];
unsigned char ai_mstage[64];

unsigned char ai_l0ring[896];
unsigned int ai_l0start[32];
unsigned char ai_l0len[32];
unsigned char ai_l0meta[32];
unsigned int ai_l0head;
unsigned int ai_l0bytes;
unsigned int ai_l0count;
unsigned char ai_l1[768];
unsigned char ai_l2[384];
unsigned int ai_l1count;
unsigned int ai_l2count;
unsigned int ai_compact;
unsigned int ai_l2evict;
unsigned int ai_l1drop;
unsigned int ai_litloss;
unsigned int ai_encfail;
unsigned int ai_semuse;
unsigned int ai_lmring[96];
unsigned int ai_lmhead;
unsigned int ai_lmcount;
unsigned int ai_l0wire;

int ai_lower(int c)
{
    if (c >= 65 && c <= 90) return c + 32;
    return c;
}

int ai_has(char *s)
{
    unsigned int i;
    unsigned int j;
    int ok;
    i = 0;
    while (ai_in[i] != 0) {
        j = 0;
        ok = 1;
        while (s[j] != 0 && ai_in[i + j] != 0) {
            if (ai_lower(ai_in[i + j]) != s[j]) ok = 0;
            if (!ok) break;
            j = j + 1;
        }
        if (s[j] == 0 && ok) return 1;
        i = i + 1;
    }
    return 0;
}

int ai_find(char *s)
{
    unsigned int i;
    unsigned int j;
    int ok;
    i = 0;
    while (ai_in[i] != 0) {
        j = 0;
        ok = 1;
        while (s[j] != 0 && ai_in[i + j] != 0) {
            if (ai_lower(ai_in[i + j]) != s[j]) ok = 0;
            if (!ok) break;
            j = j + 1;
        }
        if (s[j] == 0 && ok) return i;
        i = i + 1;
    }
    return -1;
}

int ai_readline(void)
{
    unsigned int n;
    int c;
    int bad;
    n = 0;
    bad = 0;
    while (1) {
        c = getchar();
        if (c < 0) return -1;
        if (ai_drop_lf) {
            ai_drop_lf = 0;
            if (c == 10) continue;
        }
        if (c == 13) {
            ai_drop_lf = 1;
            break;
        }
        if (c == 10) break;
        if (c < 32 || c > 126) bad = 1;
        if (n < 191 && !bad) {
            ai_in[n] = c;
            n = n + 1;
        } else {
            bad = 1;
        }
    }
    ai_in[n] = 0;
    if (bad) return -2;
    return (int)n;
}

int ai_isq(void)
{
    if (ai_in[0] == 'q' && ai_in[1] == 0) return 1;
    return 0;
}

int ai_namecmd(void)
{
    if (ai_find("my name is ") >= 0) return 1;
    if (ai_has("what is my name")) return 2;
    if (ai_has("remember my name")) return 2;
    return 0;
}

int ai_setname(void)
{
    int pos;
    unsigned int start;
    unsigned int n;
    unsigned int i;
    unsigned int gen;
    pos = ai_find("my name is ");
    if (pos < 0) return 0;
    start = pos + 11;
    n = 0;
    while (ai_in[start + n] != 0 && n < 32) {
        n = n + 1;
    }
    if (n == 0 || n > 31) return 0;
    gen = ai_litgen[0] + 1;
    if (gen == 0 || gen > 4095) gen = 1;
    ai_litgen[0] = gen;
    ai_litlen[0] = n;
    i = 0;
    while (i < n) {
        ai_litbuf[i] = ai_in[start + i];
        i = i + 1;
    }
    ai_litset = 1;
    return 1;
}

void ai_putraw(char *s)
{
    unsigned int i;
    i = 0;
    while (s[i] != 0) {
        putchar(s[i]);
        i = i + 1;
    }
}

void ai_putname(void)
{
    unsigned int i;
    i = 0;
    while (i < ai_litlen[0]) {
        putchar(ai_litbuf[i]);
        i = i + 1;
    }
}

void ai_nameack(void)
{
    ai_putraw("I will remember ");
    ai_putname();
    puts(".");
}

void ai_nameans(void)
{
    if (ai_litlen[0] == 0) {
        puts("I do not have your name yet.");
        return;
    }
    ai_lituse = 1;
    ai_putraw("I remember your name as ");
    ai_putname();
    puts(".");
}

void ai_histpush(unsigned int topic)
{
    unsigned int i;
    if (ai_hcount < 6) {
        ai_hist[ai_hcount] = topic;
        ai_hcount = ai_hcount + 1;
        return;
    }
    i = 1;
    while (i < 6) {
        ai_hist[i - 1] = ai_hist[i];
        i = i + 1;
    }
    ai_hist[5] = topic;
}

unsigned int ai_pick(void)
{
    if (ai_has("memory")) return ai_t_mem;
    if (ai_has("48k")) return ai_t_mem;
    if (ai_has("game")) return ai_t_games;
    if (ai_has("network")) return ai_t_local;
    if (ai_has("local")) return ai_t_local;
    if (ai_has("chat")) return ai_t_local;
    if (ai_has("1982")) return ai_t_hist;
    if (ai_has("history")) return ai_t_hist;
    if (ai_has("spectrum")) return ai_t_spec;
    if (ai_has("computer")) return ai_t_spec;
    if (ai_hcount != 0 && ai_has("go back")) {
        ai_ctxuse = 1;
        ai_histuse = 1;
        return ai_hist[ai_hcount - 1];
    }
    if (ai_havectx) {
        if (ai_has("tell me more")) {
            ai_ctxuse = 1;
            return ai_lasttop;
        }
        if (ai_has("what about that")) {
            ai_ctxuse = 1;
            return ai_lasttop;
        }
        if (ai_has("same topic")) {
            ai_ctxuse = 1;
            return ai_lasttop;
        }
    }
    return ai_t_id;
}

int ai_addtok(unsigned int id)
{
    unsigned int i;
    unsigned int off;
    unsigned int len;
    if (id == 0 || id >= ai_vcnt) return 0;
    off = ai_voff[id];
    len = ai_vlen[id];
    if (ai_olen != 0) {
        if (ai_olen >= 254) return 0;
        ai_out[ai_olen] = ' ';
        ai_olen = ai_olen + 1;
    }
    if (len > 254 - ai_olen) return 0;
    i = 0;
    while (i < len) {
        ai_out[ai_olen] = ai_vblob[off + i];
        ai_olen = ai_olen + 1;
        i = i + 1;
    }
    return 1;
}

int ai_generate(unsigned int topic, unsigned int alt)
{
    unsigned int cur;
    unsigned int next;
    unsigned int steps;
    unsigned int limit;
    unsigned int base;
    unsigned int i;
    ai_olen = 0;
    ai_otokens = 0;
    ai_error = 0;
    if (topic >= ai_tcnt) {
        ai_error = 3;
        return -1;
    }
    i = 0;
    while (i < 96) {
        ai_seen[i] = 0;
        i = i + 1;
    }
    base = topic * ai_vcnt;
    cur = ai_tseed[topic];
    limit = 10;
    if (topic == ai_t_mem) limit = 8;
    steps = 0;
    while (cur != 0 && steps < limit) {
        if (ai_seen[cur] != 0) break;
        ai_seen[cur] = 1;
        if (!ai_addtok(cur)) {
            ai_error = 2;
            break;
        }
        ai_otokens = ai_otokens + 1;
        if (steps == 0 && alt) {
            next = ai_n2[base + cur];
            if (next == 0) next = ai_n1[base + cur];
            if (next != ai_n1[base + cur]) ai_altuse = 1;
        } else {
            next = ai_n1[base + cur];
        }
        if (next != 0 && ai_seen[next] != 0) {
            next = ai_n2[base + cur];
            if (next != 0 && ai_seen[next] != 0) {
                next = 0;
            }
        }
        cur = next;
        steps = steps + 1;
    }
    if (ai_olen < 254) {
        ai_out[ai_olen] = '.';
        ai_olen = ai_olen + 1;
    }
    ai_out[ai_olen] = 0;
    if (ai_olen != 0) {
        if (ai_out[0] >= 'a' && ai_out[0] <= 'z') {
            ai_out[0] = ai_out[0] - 32;
        }
    }
    return 0;
}


void ai_mcopy(unsigned char *dst, unsigned char *src,
              unsigned int n)
{
    unsigned int i;
    i = 0;
    while (i < n) {
        dst[i] = src[i];
        i = i + 1;
    }
}

unsigned int ai_getu16(unsigned char *p, unsigned int n)
{
    return p[n] + ((unsigned int)p[n + 1] * 256);
}

void ai_fdata(unsigned char *p, unsigned int n)
{
    unsigned int i;
    i = 0;
    while (i < n) {
        ai_fs1 = (ai_fs1 + p[i]) % 255;
        ai_fs2 = (ai_fs2 + ai_fs1) % 255;
        i = i + 1;
    }
}

void ai_fhead(void)
{
    unsigned int i;
    unsigned int v;
    ai_fs1 = 0;
    ai_fs2 = 0;
    i = 0;
    while (i < 40) {
        v = ai_mhead[i];
        if (i == 32 || i == 33) v = 0;
        ai_fs1 = (ai_fs1 + v) % 255;
        ai_fs2 = (ai_fs2 + ai_fs1) % 255;
        i = i + 1;
    }
}

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

int ai_modelscan(unsigned int topic)
{
    unsigned int actual;
    unsigned int logical;
    unsigned int rbytes;
    unsigned int rcount;
    unsigned int used;
    unsigned int rn;
    unsigned int rlen;
    unsigned int tcnt;
    unsigned int acnt;
    unsigned int hlen;
    unsigned int plen;
    unsigned int rtopic;
    unsigned int apos;
    unsigned int a1s;
    unsigned int a1e;
    unsigned int a2s;
    unsigned int a2e;
    unsigned int amask;
    unsigned int pstate;
    unsigned int prem;
    unsigned int pkind;
    unsigned int plow;
    unsigned int pos;
    unsigned int take;
    unsigned int i;
    unsigned int at;
    unsigned int code;
    unsigned int tid;
    unsigned int calc;
    int score;
    int slot;
    ai_mrecords = 0;
    ai_mhits = 0;
    ai_mbytes = 0;
    ai_mreads = 0;
    ai_w1len = 0;
    ai_w2len = 0;
    ai_w1score = -1;
    ai_w2score = -1;
    actual = ai_mstat();
    if (actual < 40) return -1;
    if (ai_mseek(0) != 0) return -1;
    if (ai_readfull(ai_mhead, 40) != 0) return -1;
    if (ai_mhead[0] != 'A') return -1;
    if (ai_mhead[1] != '4') return -1;
    if (ai_mhead[2] != '8') return -1;
    if (ai_mhead[3] != 'M') return -1;
    if (ai_mhead[4] != 1) return -1;
    if (ai_mhead[5] != 0) return -1;
    if (ai_mhead[6] != 40) return -1;
    if (ai_mhead[7] != 1) return -1;
    i = 34;
    while (i < 40) {
        if (ai_mhead[i] != 0) return -1;
        i = i + 1;
    }
    rcount = ai_getu16(ai_mhead, 24);
    if (ai_getu16(ai_mhead, 26) != 40) return -1;
    rbytes = ai_getu16(ai_mhead, 28);
    logical = ai_getu16(ai_mhead, 30);
    if (logical != actual) return -1;
    if (logical < 40) return -1;
    if (rbytes != logical - 40) return -1;
    ai_fhead();
    used = 0;
    rn = 0;
    while (rn < rcount) {
        if (used > rbytes) return -1;
        if (rbytes - used < 11) return -1;
        if (ai_readfull(ai_mstage, 10) != 0) return -1;
        rlen = ai_mstage[0];
        tcnt = ai_mstage[9];
        if (rlen < 11 || rlen > 192) return -1;
        if (rlen > rbytes - used) return -1;
        if (tcnt > 4) return -1;
        hlen = 11 + (tcnt * 2);
        if (hlen > rlen || hlen > 64) return -1;
        if (ai_readfull(&ai_mstage[10],
                        hlen - 10) != 0) return -1;
        acnt = ai_mstage[hlen - 1];
        if (acnt > 2) return -1;
        if (hlen + (acnt * 2) > rlen) return -1;
        if (ai_readfull(&ai_mstage[hlen],
                        acnt * 2) != 0) return -1;
        hlen = hlen + (acnt * 2);
        ai_fdata(ai_mstage, hlen);
        plen = rlen - hlen;
        if (plen == 0) return -1;
        code = ai_mstage[1];
        if (code < 1 || code > 7) return -1;
        if (code <= 6 && acnt == 0) return -1;
        rtopic = ai_getu16(ai_mstage, 2);
        if (ai_getu16(ai_mstage, 4) > 32767) return -1;
        if (ai_getu16(ai_mstage, 6) > 32767) return -1;
        i = 0;
        while (i < tcnt) {
            tid = ai_getu16(ai_mstage, 10 + (i * 2));
            if (tid > 4095) return -1;
            i = i + 1;
        }
        a1s = 0;
        a1e = 0;
        a2s = 0;
        a2e = 0;
        apos = 11 + (tcnt * 2);
        if (acnt > 0) {
            a1s = ai_mstage[apos];
            a1e = a1s + ai_mstage[apos + 1];
            if (a1e <= a1s || a1e > plen) return -1;
        }
        if (acnt > 1) {
            a2s = ai_mstage[apos + 2];
            a2e = a2s + ai_mstage[apos + 3];
            if (a2e <= a2s || a2e > plen) return -1;
            if (a1s < a2e && a2s < a1e) return -1;
        }
        score = -1;
        if (rtopic == topic) score = ai_mstage[8];
        slot = 0;
        if (score > ai_w1score) {
            if (ai_w1score >= 0) {
                ai_mcopy(ai_win2, ai_win1, ai_w1len);
                ai_w2len = ai_w1len;
                ai_w2score = ai_w1score;
            }
            slot = 1;
        } else if (score > ai_w2score) {
            slot = 2;
        }
        if (slot == 1) ai_mcopy(ai_win1, ai_mstage, hlen);
        if (slot == 2) ai_mcopy(ai_win2, ai_mstage, hlen);
        amask = 0;
        pstate = 0;
        prem = 0;
        pkind = 0;
        plow = 0;
        pos = 0;
        while (pos < plen) {
            take = plen - pos;
            if (take > 64) take = 64;
            if (ai_readfull(ai_mstage, take) != 0) return -1;
            ai_fdata(ai_mstage, take);
            if (slot == 1) {
                ai_mcopy(&ai_win1[hlen + pos],
                         ai_mstage, take);
            }
            if (slot == 2) {
                ai_mcopy(&ai_win2[hlen + pos],
                         ai_mstage, take);
            }
            i = 0;
            while (i < take) {
                at = pos + i;
                if (pstate == 0) {
                    if (acnt > 0 && at == a1s) {
                        amask = amask | 1;
                    }
                    if (acnt > 0 && at == a1e) {
                        amask = amask | 2;
                    }
                    if (acnt > 1 && at == a2s) {
                        amask = amask | 4;
                    }
                    if (acnt > 1 && at == a2e) {
                        amask = amask | 8;
                    }
                    code = ai_mstage[i];
                    if (code == 1 || code == 2 || code == 6) {
                        if (acnt > 0 && at >= a1s && at < a1e) {
                            return -1;
                        }
                        if (acnt > 1 && at >= a2s && at < a2e) {
                            return -1;
                        }
                    } else if (code >= 16 && code <= 239) {
                    } else if (code == 240) {
                        pstate = 1;
                    } else if (code == 241 || code == 242 ||
                               code == 243) {
                        pkind = code;
                        pstate = 3;
                    } else {
                        return -1;
                    }
                } else if (pstate == 1) {
                    plow = ai_mstage[i];
                    pstate = 2;
                } else if (pstate == 2) {
                    tid = plow + (ai_mstage[i] * 256);
                    if (tid < 224 || tid > 4095) return -1;
                    pstate = 0;
                } else if (pstate == 3) {
                    prem = ai_mstage[i];
                    if (prem == 0) return -1;
                    if (pkind == 242 && prem > 15) return -1;
                    if (pkind != 242 && prem > 31) return -1;
                    pstate = 4;
                } else {
                    code = ai_mstage[i];
                    if (code < 32 || code > 126) return -1;
                    prem = prem - 1;
                    if (prem == 0) pstate = 0;
                }
                i = i + 1;
            }
            pos = pos + take;
        }
        if (pstate != 0) return -1;
        if (acnt > 0 && plen == a1s) amask = amask | 1;
        if (acnt > 0 && plen == a1e) amask = amask | 2;
        if (acnt > 1 && plen == a2s) amask = amask | 4;
        if (acnt > 1 && plen == a2e) amask = amask | 8;
        if (acnt == 1 && (amask & 3) != 3) return -1;
        if (acnt == 2 && (amask & 15) != 15) return -1;
        if (slot == 1) {
            ai_w1len = rlen;
            ai_w1score = score;
        }
        if (slot == 2) {
            ai_w2len = rlen;
            ai_w2score = score;
        }
        used = used + rlen;
        rn = rn + 1;
        ai_mrecords = ai_mrecords + 1;
    }
    if (used != rbytes) return -1;
    calc = ai_fs1 + (ai_fs2 * 256);
    if (calc != ai_getu16(ai_mhead, 32)) return -1;
    if (ai_mbytes != logical) return -1;
    if (ai_w1score >= 0) {
        ai_mhits = 1;
        if (ai_w2score >= 0) ai_mhits = 2;
        return 1;
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

int ai_coldans(void)
{
    unsigned int tcnt;
    unsigned int acnt;
    unsigned int apos;
    unsigned int pbase;
    unsigned int pos;
    unsigned int end;
    unsigned int code;
    unsigned int n;
    unsigned int id;
    if (ai_w1len < 11) return 0;
    tcnt = ai_win1[9];
    apos = 10 + (tcnt * 2);
    if (apos >= ai_w1len) return 0;
    acnt = ai_win1[apos];
    if (acnt == 0 || acnt > 2) return 0;
    pbase = apos + 1 + (acnt * 2);
    if (pbase >= ai_w1len) return 0;
    pos = pbase + ai_win1[apos + 1];
    end = pos + ai_win1[apos + 2];
    if (end > ai_w1len || end <= pos) return 0;
    ai_olen = 0;
    ai_otokens = 0;
    while (pos < end) {
        code = ai_win1[pos];
        pos = pos + 1;
        if (code >= 16 && code <= 239) {
            id = code - 16;
            if (!ai_addtok(id)) return 0;
        } else if (code == 240) {
            if (pos + 2 > end) return 0;
            id = ai_getu16(ai_win1, pos);
            pos = pos + 2;
            if (!ai_addtok(id)) return 0;
        } else if (code == 241 || code == 242 ||
                   code == 243) {
            if (pos >= end) return 0;
            n = ai_win1[pos];
            pos = pos + 1;
            if (pos + n > end) return 0;
            if (!ai_addlit(&ai_win1[pos], n)) return 0;
            pos = pos + n;
        } else {
            return 0;
        }
        ai_otokens = ai_otokens + 1;
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


unsigned int ai_strlen(char *s)
{
    unsigned int n;
    n = 0;
    while (s[n] != 0) n = n + 1;
    return n;
}

unsigned char ai_l0char(unsigned int d, unsigned int n)
{
    unsigned int p;
    p = ai_l0start[d] + n;
    p = p % 896;
    return ai_l0ring[p];
}

int ai_l0has(unsigned int d, char *s)
{
    unsigned int i;
    unsigned int j;
    unsigned int sl;
    int ok;
    sl = ai_strlen(s);
    if (sl == 0 || sl > ai_l0len[d]) return 0;
    i = 0;
    while (i + sl <= ai_l0len[d]) {
        j = 0;
        ok = 1;
        while (j < sl) {
            if (ai_lower(ai_l0char(d, i + j)) != s[j]) {
                ok = 0;
                break;
            }
            j = j + 1;
        }
        if (ok) return 1;
        i = i + 1;
    }
    return 0;
}

unsigned int ai_capoff(unsigned int n)
{
    return n * 16;
}

unsigned int ai_capget(unsigned char *p, unsigned int n)
{
    return p[n] + ((unsigned int)p[n + 1] * 256);
}

void ai_capset(unsigned char *p, unsigned int topic,
               unsigned int rel, unsigned int imp,
               unsigned int age)
{
    unsigned int i;
    i = 0;
    while (i < 16) {
        p[i] = 0;
        i = i + 1;
    }
    p[1] = rel;
    p[2] = topic & 255;
    p[3] = topic / 256;
    p[14] = imp;
    p[15] = age;
}

void ai_capage(void)
{
    unsigned int i;
    unsigned int o;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] != 0 && ai_l1[o + 15] < 255) {
            ai_l1[o + 15] = ai_l1[o + 15] + 1;
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] != 0 && ai_l2[o + 15] < 255) {
            ai_l2[o + 15] = ai_l2[o + 15] + 1;
        }
        i = i + 1;
    }
}

unsigned int ai_victim(unsigned char *p, unsigned int count)
{
    unsigned int i;
    unsigned int o;
    unsigned int best;
    unsigned int bimp;
    unsigned int bage;
    unsigned int imp;
    unsigned int age;
    best = 0;
    bimp = 256;
    bage = 0;
    i = 0;
    while (i < count) {
        o = ai_capoff(i);
        if (p[o + 1] != 0) {
            imp = p[o + 14];
            age = p[o + 15];
            if (imp < bimp) {
                best = i;
                bimp = imp;
                bage = age;
            } else if (imp == bimp && age > bage) {
                best = i;
                bage = age;
            }
        }
        i = i + 1;
    }
    return best;
}

void ai_l2merge(unsigned char *src)
{
    unsigned int i;
    unsigned int o;
    unsigned int rel;
    unsigned int topic;
    unsigned int imp;
    unsigned int age;
    unsigned int victim;
    rel = src[1];
    topic = ai_capget(src, 2);
    imp = src[14];
    age = src[15];
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == rel) {
            if (ai_capget(ai_l2, o + 2) == topic) {
                if (imp > ai_l2[o + 14]) {
                    ai_l2[o + 14] = imp;
                }
                if (age < ai_l2[o + 15]) {
                    ai_l2[o + 15] = age;
                }
                return;
            }
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == 0) {
            ai_mcopy(&ai_l2[o], src, 16);
            ai_l2count = ai_l2count + 1;
            return;
        }
        i = i + 1;
    }
    victim = ai_victim(ai_l2, 24);
    o = ai_capoff(victim);
    ai_mcopy(&ai_l2[o], src, 16);
    ai_l2evict = ai_l2evict + 1;
}

void ai_l1add(unsigned int topic, unsigned int rel,
              unsigned int imp, unsigned int age)
{
    unsigned int i;
    unsigned int o;
    unsigned int victim;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 0) {
            ai_capset(&ai_l1[o], topic, rel, imp, age);
            ai_l1count = ai_l1count + 1;
            return;
        }
        i = i + 1;
    }
    victim = ai_victim(ai_l1, 48);
    o = ai_capoff(victim);
    ai_l2merge(&ai_l1[o]);
    ai_compact = ai_compact + 1;
    ai_capset(&ai_l1[o], topic, rel, imp, age);
}

void ai_descshift(void)
{
    unsigned int i;
    i = 2;
    while (i < ai_l0count) {
        ai_l0start[i - 2] = ai_l0start[i];
        ai_l0len[i - 2] = ai_l0len[i];
        ai_l0meta[i - 2] = ai_l0meta[i];
        i = i + 1;
    }
    ai_l0count = ai_l0count - 2;
}

void ai_promote(void)
{
    unsigned int topic;
    unsigned int rel;
    unsigned int imp;
    topic = (ai_l0meta[0] / 2) & 7;
    rel = 2;
    imp = 32;
    if ((ai_l0meta[0] & 32) != 0) {
        rel = 1;
        imp = 255;
    }
    ai_l1add(topic, rel, imp, 1);
}

int ai_ctxevict(void)
{
    unsigned int n;
    if (ai_l0count < 2) return -1;
    ai_promote();
    n = ai_l0len[0] + ai_l0len[1];
    if (n > ai_l0bytes) return -1;
    ai_l0bytes = ai_l0bytes - n;
    ai_descshift();
    return 0;
}


int ai_pinreq(void);
#include "aictx.h"

int ai_ctxwrite(char *s, unsigned int speaker,
                unsigned int topic)
{
    unsigned int n;
    unsigned int meta;
    n = ai_encsize(s);
    if (n == 65535 || n == 0 || n > 255) return -1;
    if (ai_l0count >= 32) return -1;
    ai_l0start[ai_l0count] = ai_l0head;
    ai_l0len[ai_l0count] = n;
    meta = speaker + (topic * 2);
    if (speaker == 0 && ai_pinreq()) meta = meta | 32;
    ai_l0meta[ai_l0count] = meta;
    if (ai_wirewrite(s, speaker) != 0) return -1;
    ai_l0bytes = ai_l0bytes + n;
    ai_l0count = ai_l0count + 1;
    return 0;
}

int ai_ctxpair(unsigned int topic)
{
    unsigned int un;
    unsigned int an;
    unsigned int need;
    un = ai_encsize(ai_in);
    an = ai_encsize(ai_out);
    if (un == 65535 || an == 65535) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    need = un + an;
    if (need > 896) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    ai_capage();
    while (ai_l0bytes + need > 896 ||
           ai_l0count + 2 > 32) {
        if (ai_ctxevict() != 0) {
            ai_encfail = ai_encfail + 1;
            return -1;
        }
    }
    if (ai_ctxwrite(ai_in, 0, topic) != 0) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    if (ai_ctxwrite(ai_out, 1, topic) != 0) {
        ai_encfail = ai_encfail + 1;
        return -1;
    }
    return 0;
}

int ai_pinreq(void)
{
    if (ai_has("remember this topic")) return 1;
    if (ai_has("remember that topic")) return 1;
    return 0;
}

int ai_recallreq(void)
{
    if (ai_has("topic i asked you to remember")) return 1;
    if (ai_has("return to the remembered topic")) return 1;
    return 0;
}

unsigned int ai_semrecall(void)
{
    unsigned int i;
    unsigned int o;
    unsigned int best;
    unsigned int bimp;
    unsigned int bage;
    unsigned int imp;
    unsigned int age;
    unsigned int topic;
    i = ai_l0count;
    while (i >= 2) {
        i = i - 2;
        if ((ai_l0meta[i] & 32) != 0) {
            return (ai_l0meta[i] / 2) & 7;
        }
    }
    best = 65535;
    bimp = 0;
    bage = 255;
    i = 0;
    while (i < 48) {
        o = ai_capoff(i);
        if (ai_l1[o + 1] == 1) {
            imp = ai_l1[o + 14];
            age = ai_l1[o + 15];
            if (best == 65535 || imp > bimp ||
                (imp == bimp && age < bage)) {
                best = ai_capget(ai_l1, o + 2);
                bimp = imp;
                bage = age;
            }
        }
        i = i + 1;
    }
    i = 0;
    while (i < 24) {
        o = ai_capoff(i);
        if (ai_l2[o + 1] == 1) {
            imp = ai_l2[o + 14];
            age = ai_l2[o + 15];
            if (best == 65535 || imp > bimp ||
                (imp == bimp && age < bage)) {
                topic = ai_capget(ai_l2, o + 2);
                best = topic;
                bimp = imp;
                bage = age;
            }
        }
        i = i + 1;
    }
    return best;
}

void ai_settext(char *s)
{
    unsigned int i;
    i = 0;
    while (s[i] != 0 && i < 255) {
        ai_out[i] = s[i];
        i = i + 1;
    }
    ai_out[i] = 0;
    ai_olen = i;
    ai_otokens = 0;
}

void ai_start(void)
{
    puts("Welcome to SANYALnet Labs ZX-UX AI LM Chat.");
    puts("Copyright (c) 2026 Supratim Sanyal");
    puts("");
    puts("I am ailmzx48.");
    puts("I know a bit about the Sinclair ZX Spectrum -");
    puts("which is fortunate, because I live inside one.");
    puts("48K seemed enormous in 1982. I have opinions now.");
    puts("");
    puts("Ask me about the Spectrum, or just have a chat.");
    puts("Enter q at any time to quit.");
    puts("");
}

int main(void)
{
    int rc;
    unsigned int topic;
    unsigned int alt;
    int namecmd;
    ai_turns = 0;
    ai_beeps = 0;
    ai_lasttop = ai_t_id;
    ai_ctxuse = 0;
    ai_havectx = 0;
    ai_altuse = 0;
    ai_altstate = 0;
    ai_histuse = 0;
    ai_hcount = 0;
    ai_litset = 0;
    ai_lituse = 0;
    ai_drop_lf = 0;
    ai_mrecords = 0;
    ai_mhits = 0;
    ai_mbytes = 0;
    ai_mreads = 0;
    ai_l0head = 0;
    ai_l0bytes = 0;
    ai_l0count = 0;
    ai_l1count = 0;
    ai_l2count = 0;
    ai_compact = 0;
    ai_l2evict = 0;
    ai_l1drop = 0;
    ai_litloss = 0;
    ai_encfail = 0;
    ai_semuse = 0;
    ai_lmhead = 0;
    ai_lmcount = 0;
    ai_l0wire = 1;
    ai_start();
    while (1) {
        ai_beeps = ai_beeps + 1;
        beep(0.5, 0.0);
        putchar('>');
        putchar(' ');
        rc = ai_readline();
        if (rc == -1) break;
        if (rc < 0) {
            ai_ctxuse = 0;
            ai_altuse = 0;
            ai_histuse = 0;
            ai_litset = 0;
            ai_lituse = 0;
            puts("Input rejected.");
            continue;
        }
        if (ai_isq()) break;
        ai_ctxuse = 0;
        ai_altuse = 0;
        ai_histuse = 0;
        ai_litset = 0;
        ai_lituse = 0;
        ai_compact = 0;
        ai_l2evict = 0;
        ai_l1drop = 0;
        ai_litloss = 0;
        ai_encfail = 0;
        ai_semuse = 0;
        namecmd = ai_namecmd();
        if (namecmd != 0) {
            ai_otokens = 0;
            ai_error = 0;
            if (namecmd == 1) {
                if (ai_setname()) {
                    ai_nameack();
                } else {
                    puts("I could not store that name.");
                }
            } else {
                ai_nameans();
            }
            if (ai_turns != 65535) {
                ai_turns = ai_turns + 1;
            }
            ai_yields = 0;
            yield();
            ai_yields = ai_yields + 1;
            continue;
        }
        if (ai_pinreq() && ai_havectx) {
            topic = ai_lasttop;
            ai_ctxuse = 1;
            ai_settext("I will remember this topic.");
            puts(ai_out);
            rc = ai_ctxpair(topic);
            if (rc < 0) ai_error = 5;
            if (ai_turns != 65535) {
                ai_turns = ai_turns + 1;
            }
            ai_yields = 0;
            yield();
            ai_yields = ai_yields + 1;
            continue;
        }
        if (ai_recallreq()) {
            topic = ai_semrecall();
            if (topic != 65535) {
                ai_ctxuse = 1;
                ai_semuse = 1;
            } else {
                topic = ai_pick();
            }
        } else {
            topic = ai_pick();
        }
        alt = 0;
        if (ai_havectx && topic == ai_lasttop) {
            if (ai_altstate == 0) {
                ai_altstate = 1;
                alt = 1;
            } else {
                ai_altstate = 0;
            }
        } else {
            ai_altstate = 0;
        }
        rc = ai_modelscan(topic);
        if (rc < 0) {
            ai_error = 4;
            ai_settext("Model data unavailable.");
            puts(ai_out);
        } else if (rc > 0 && ai_coldans()) {
            puts(ai_out);
        } else {
            ai_generate(topic, alt);
            puts(ai_out);
        }
        rc = ai_ctxpair(topic);
        if (rc < 0 && ai_error == 0) ai_error = 5;
        if (ai_histuse) {
            if (ai_hcount != 0) {
                ai_hcount = ai_hcount - 1;
            }
        } else {
            if (!ai_ctxuse && ai_havectx) {
                if (topic != ai_lasttop) {
                    ai_histpush(ai_lasttop);
                }
            }
        }
        ai_lasttop = topic;
        ai_havectx = 1;
        if (ai_turns != 65535) ai_turns = ai_turns + 1;
        ai_yields = 0;
        yield();
        ai_yields = ai_yields + 1;
    }
    return 0;
}
