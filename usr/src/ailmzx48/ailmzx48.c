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
char ai_in[192];
char ai_out[256];
int ai_drop_lf;
unsigned int ai_olen;
unsigned char ai_seen[96];

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
    ai_turns = 0;
    ai_beeps = 0;
    ai_lasttop = ai_t_id;
    ai_ctxuse = 0;
    ai_havectx = 0;
    ai_altuse = 0;
    ai_altstate = 0;
    ai_drop_lf = 0;
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
            puts("Input rejected.");
            continue;
        }
        if (ai_isq()) break;
        ai_ctxuse = 0;
        ai_altuse = 0;
        topic = ai_pick();
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
        ai_generate(topic, alt);
        puts(ai_out);
        ai_lasttop = topic;
        ai_havectx = 1;
        if (ai_turns != 65535) ai_turns = ai_turns + 1;
        ai_yields = 0;
        yield();
        ai_yields = ai_yields + 1;
    }
    return 0;
}
