#!/usr/bin/env python3
# ============================================================================
# Copyright (c) 2026 Supratim Sanyal of SANYALnet Labs.
# Proprietary rights reserved except as expressly licensed herein.
#
# ZX-UX C48 SDK
# This file is governed by the SANYALnet Labs Non-Commercial License in the
# root LICENSE file. Non-Commercial use is permitted; Commercial Use and use
# for AI/ML model training are prohibited unless separately authorized.
#
# Attribution is required: "Based on original work by Supratim Sanyal of
# SANYALnet Labs." See LICENSE for full terms, warranty disclaimer, termination,
# patent, trademark, and governing-law provisions.
# ============================================================================
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "usr/src/ailmzx48/ailmzx48.c"
RUN = ROOT / "usr/src/ailmzx48/tooling/run_iteration.py"


def one(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError("unexpected source while integrating cold model")
    return text.replace(old, new, 1)


COLD_C = r'''
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
'''


def patch_c(text: str) -> str:
    text = one(
        text,
        "int yield(void);\n\n#include \"aimod.h\"",
        "int yield(void);\n"
        "unsigned int ai_mstat(void);\n"
        "int ai_mseek(unsigned int pos);\n"
        "int ai_mread(unsigned char *p, unsigned int n);\n\n"
        "#include \"aimod.h\"",
    )
    text = one(
        text,
        "unsigned char ai_seen[96];\n",
        "unsigned char ai_seen[96];\n"
        "unsigned int ai_mrecords;\n"
        "unsigned int ai_mhits;\n"
        "unsigned int ai_mbytes;\n"
        "unsigned int ai_mreads;\n"
        "unsigned int ai_fs1;\n"
        "unsigned int ai_fs2;\n"
        "unsigned int ai_w1len;\n"
        "unsigned int ai_w2len;\n"
        "int ai_w1score;\n"
        "int ai_w2score;\n"
        "unsigned char ai_mhead[40];\n"
        "unsigned char ai_win1[192];\n"
        "unsigned char ai_win2[192];\n"
        "unsigned char ai_mstage[64];\n",
    )
    text = one(text, "\nvoid ai_start(void)\n", "\n" + COLD_C + "\nvoid ai_start(void)\n")
    text = one(
        text,
        "    ai_drop_lf = 0;\n    ai_start();",
        "    ai_drop_lf = 0;\n"
        "    ai_mrecords = 0;\n"
        "    ai_mhits = 0;\n"
        "    ai_mbytes = 0;\n"
        "    ai_mreads = 0;\n"
        "    ai_start();",
    )
    text = one(
        text,
        "        ai_generate(topic, alt);\n        puts(ai_out);",
        "        rc = ai_modelscan(topic);\n"
        "        if (rc < 0) {\n"
        "            ai_error = 4;\n"
        "            puts(\"Model data unavailable.\");\n"
        "        } else if (rc > 0 && ai_coldans()) {\n"
        "            puts(ai_out);\n"
        "        } else {\n"
        "            ai_generate(topic, alt);\n"
        "            puts(ai_out);\n"
        "        }",
    )
    return text


PY_IMPORT_OLD = '''from c48.format import read
from c48.romvm import RomMathVM
from c48.screen import Font4x8, ZXScreen
'''
PY_IMPORT_NEW = '''from c48.format import read
from c48.romvm import RomMathVM
from c48.screen import Font4x8, ZXScreen
from c48.typesys import INT, UINT
from c48.vm import Value
'''

MODEL_VM = r'''
class ModelVM(RomMathVM):
    def __init__(self, *args, model_data, **kwargs):
        self.model_data = model_data
        self.model_pos = 0
        self.model_calls = 0
        self.model_bytes = 0
        self.model_seeks = 0
        self.model_max_request = 0
        self.model_pattern = (1, 7, 3, 64, 2, 11)
        super().__init__(*args, **kwargs)
        self.builtins["ai_mstat"] = self._b_ai_mstat
        self.builtins["ai_mseek"] = self._b_ai_mseek
        self.builtins["ai_mread"] = self._b_ai_mread

    def _b_ai_mstat(self, args):
        return Value(UINT, len(self.model_data))

    def _b_ai_mseek(self, args):
        offset = self._to_unsigned(args[0])
        if offset > len(self.model_data):
            return Value(INT, -1)
        self.model_pos = offset
        self.model_seeks += 1
        return Value(INT, 0)

    def _b_ai_mread(self, args):
        ptr = self._as_pointer(args[0])
        count = self._to_unsigned(args[1])
        if count > 64:
            return Value(INT, -1)
        if count > self.model_max_request:
            self.model_max_request = count
        if count == 0 or self.model_pos >= len(self.model_data):
            return Value(INT, 0)
        cap = self.model_pattern[
            self.model_calls % len(self.model_pattern)
        ]
        self.model_calls += 1
        take = min(
            count, cap, len(self.model_data) - self.model_pos
        )
        if take:
            self.mem.require_range(ptr, take, write=True)
            data = self.model_data[
                self.model_pos:self.model_pos + take
            ]
            self.mem.write_bytes(ptr.address, data)
            self.model_pos += take
            self.model_bytes += take
        return Value(INT, take)

'''


def patch_run(text: str) -> str:
    text = one(text, PY_IMPORT_OLD, PY_IMPORT_NEW)
    text = one(
        text,
        "BIN = ROOT / \"usr\" / \"bin\" / \"ailmzx48\" / \"ailmzx48.c48b\"\n",
        "BIN = ROOT / \"usr\" / \"bin\" / \"ailmzx48\" / \"ailmzx48.c48b\"\n"
        "COLD = MODEL_DIR / \"cold-seed.bin\"\n",
    )
    text = one(text, "\nclass TraceScreen(ZXScreen):\n", "\n" + MODEL_VM + "\nclass TraceScreen(ZXScreen):\n")
    text = one(
        text,
        "                     \"ai_hcount\", \"ai_litset\",\n"
        "                     \"ai_lituse\"):",
        "                     \"ai_hcount\", \"ai_litset\",\n"
        "                     \"ai_lituse\", \"ai_mrecords\",\n"
        "                     \"ai_mhits\", \"ai_mbytes\",\n"
        "                     \"ai_mreads\"):",
    )
    text = one(
        text,
        "    model_iter.write_bytes(current_model.read_bytes())\n"
        "    BIN.parent.mkdir(parents=True, exist_ok=True)",
        "    model_iter.write_bytes(current_model.read_bytes())\n"
        "    cold_test = A / \"evaluation\" / \"test_a48m_reference.py\"\n"
        "    remaining = max(30, limit - int(time.monotonic() - started))\n"
        "    run([sys.executable, \"-B\", str(cold_test)], remaining)\n"
        "    BIN.parent.mkdir(parents=True, exist_ok=True)",
    )
    text = one(
        text,
        "    vm = RomMathVM(program, screen,\n"
        "                   argv=[str(BIN)],\n"
        "                   heap_size=0,\n"
        "                   max_steps=max_steps,\n"
        "                   input_provider=feeder)",
        "    vm = ModelVM(program, screen,\n"
        "                 model_data=COLD.read_bytes(),\n"
        "                 argv=[str(BIN)],\n"
        "                 heap_size=0,\n"
        "                 max_steps=max_steps,\n"
        "                 input_provider=feeder)",
    )
    text = one(
        text,
        "        \"runner_max_seconds\": limit,\n",
        "        \"runner_max_seconds\": limit,\n"
        "        \"cold_model_sha256\": sha(COLD),\n"
        "        \"cold_model_logical_length\": len(vm.model_data),\n"
        "        \"cold_model_read_calls\": vm.model_calls,\n"
        "        \"cold_model_bytes_read\": vm.model_bytes,\n"
        "        \"cold_model_seek_calls\": vm.model_seeks,\n"
        "        \"cold_model_max_request\": vm.model_max_request,\n",
    )
    return text


def main() -> int:
    ctext = patch_c(SRC.read_text(encoding="ascii"))
    for number, line in enumerate(ctext.splitlines(), 1):
        if len(line) > 64:
            raise RuntimeError(
                "C48 line exceeds 64 columns: " + str(number)
            )
    SRC.write_text(ctext, encoding="ascii")
    pytext = patch_run(RUN.read_text(encoding="utf-8"))
    compile(pytext, str(RUN), "exec")
    RUN.write_text(pytext, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
