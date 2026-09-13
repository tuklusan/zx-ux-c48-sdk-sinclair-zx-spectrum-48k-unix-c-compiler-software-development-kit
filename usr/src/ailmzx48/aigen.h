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
unsigned int ai_trifind(unsigned int first,
                        unsigned int second)
{
    unsigned int lo;
    unsigned int hi;
    unsigned int mid;
    lo = 0;
    hi = ai_tricnt;
    while (lo < hi) {
        mid = lo + ((hi - lo) / 2);
        if (ai_tri1[mid] < first ||
            (ai_tri1[mid] == first &&
             ai_tri2[mid] < second)) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    if (lo >= ai_tricnt) return 0;
    if (ai_tri1[lo] != first) return 0;
    if (ai_tri2[lo] != second) return 0;
    return lo + 1;
}

unsigned int ai_unext(void)
{
    unsigned int i;
    unsigned int id;
    i = 0;
    while (i < 12) {
        id = ai_uni[i];
        if (id != 0 && id < ai_vcnt) {
            if (ai_seen[id] == 0) return id;
        }
        i = i + 1;
    }
    return 0;
}

unsigned int ai_next(unsigned int prev,
                     unsigned int cur,
                     unsigned int topic,
                     unsigned int alt)
{
    unsigned int at;
    unsigned int next;
    unsigned int base;
    next = 0;
    if (prev != 0 && prev < ai_vcnt &&
        cur != 0 && cur < ai_vcnt) {
        at = ai_trifind(prev, cur);
        if (at != 0) {
            at = at - 1;
            next = ai_trin1[at];
            if (alt && ai_trin2[at] != 0) {
                next = ai_trin2[at];
                ai_altuse = 1;
            }
            if (ai_triuse != 65535) {
                ai_triuse = ai_triuse + 1;
            }
        }
    }
    if (next == 0 && topic < ai_tcnt &&
        cur < ai_vcnt) {
        base = topic * ai_vcnt;
        next = ai_n1[base + cur];
        if (alt && ai_n2[base + cur] != 0) {
            next = ai_n2[base + cur];
            ai_altuse = 1;
        }
    }
    if (next != 0 && next < ai_vcnt) {
        if (ai_seen[next] == 0) return next;
    }
    return ai_unext();
}

void ai_lmclear(void)
{
    unsigned int i;
    i = 0;
    while (i < 96) {
        ai_seen[i] = 0;
        i = i + 1;
    }
}

int ai_lmlead(unsigned int topic)
{
    unsigned int prev;
    unsigned int cur;
    unsigned int next;
    unsigned int steps;
    if (topic >= ai_tcnt) return 0;
    ai_olen = 0;
    ai_otokens = 0;
    ai_lmclear();
    prev = 0;
    cur = ai_tseed[topic];
    steps = 0;
    while (cur != 0 && steps < 3) {
        if (cur >= ai_vcnt) return 0;
        if (ai_seen[cur] != 0) break;
        ai_seen[cur] = 1;
        if (!ai_addtok(cur)) return 0;
        ai_otokens = ai_otokens + 1;
        next = ai_next(prev, cur, topic, 0);
        prev = cur;
        cur = next;
        steps = steps + 1;
    }
    return ai_olen != 0;
}

int ai_generate(unsigned int topic, unsigned int alt)
{
    unsigned int prev;
    unsigned int cur;
    unsigned int next;
    unsigned int steps;
    unsigned int limit;
    ai_olen = 0;
    ai_otokens = 0;
    ai_error = 0;
    if (topic >= ai_tcnt) {
        ai_error = 3;
        return -1;
    }
    ai_lmclear();
    prev = 0;
    cur = ai_tseed[topic];
    limit = 10;
    if (topic == ai_t_mem) limit = 8;
    steps = 0;
    while (cur != 0 && steps < limit) {
        if (cur >= ai_vcnt) break;
        if (ai_seen[cur] != 0) break;
        ai_seen[cur] = 1;
        if (!ai_addtok(cur)) {
            ai_error = 2;
            break;
        }
        ai_otokens = ai_otokens + 1;
        if (steps == 0) {
            next = ai_next(prev, cur, topic, alt);
        } else {
            next = ai_next(prev, cur, topic, 0);
        }
        prev = cur;
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
