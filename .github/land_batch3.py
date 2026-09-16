#!/usr/bin/env python3
from pathlib import Path
import hashlib, shutil, subprocess, sys, tempfile
ROOT=Path.cwd()
BASE='3da2e907b10e22dab057fe1ce2fd268ef5102533'
SCRIPT=Path('.github/land_batch3.py')
WORKFLOW=Path('.github/workflows/land-ailm-batch3.yml')
SRC=Path('usr/src/ailmzx48/ailmzx48.c')
MATCH=Path('usr/src/ailmzx48/aimatch.h')
BIN=Path('usr/bin/ailmzx48/ailmzx48.c48b')
MODEL=Path('usr/bin/ailmzx48/ailm.dat')

def run(a,cwd=None,input=None,timeout=1800,capture=False):
    print('+',' '.join(map(str,a)),flush=True)
    return subprocess.run(a,cwd=cwd or ROOT,input=input,text=True,
        capture_output=capture,check=True,timeout=timeout)
def text(p): return (ROOT/p).read_text()
def write(p,s): (ROOT/p).write_text(s,newline='\n')
def rep(p,old,new,label):
    s=text(p); n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: anchor count {n}')
    write(p,s.replace(old,new,1))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def gout(*a): return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()

def patch():
    rep(SRC,'unsigned char ai_mstage[64];\n',
'''unsigned char ai_mstage[64];
char ai_scanwhy;
unsigned int ai_scanat;
unsigned int ai_scanrec;
''','scan diagnostic globals')
    old='''int ai_modelscan(unsigned int topic)
{
    unsigned int actual;
    unsigned int logical;
'''
    new='''void ai_scanhex(unsigned int v)
{
    char *h;
    h = "0123456789ABCDEF";
    putchar(h[(v >> 12) & 15]);
    putchar(h[(v >> 8) & 15]);
    putchar(h[(v >> 4) & 15]);
    putchar(h[v & 15]);
}

int ai_modelscan(unsigned int topic)
{
    unsigned int logical;
'''
    rep(SRC,old,new,'scanner helpers')
    rep(SRC,'    int score;\n    int slot;\n',
        '    int score;\n    int slot;\n    int rc;\n','scanner rc')
    rep(SRC,'    ai_mtopic = ai_t_id;\n    if (ai_mfd < 3) return -1;\n    actual = 8566;\n    if (actual < 40) return -1;\n',
'''    ai_mtopic = ai_t_id;
    ai_scanwhy = 'I';
    ai_scanat = 0;
    ai_scanrec = 0;
    if (ai_mfd < 3) return -1;
''','remove hard length')
    rep(SRC,'    if (ai_readfull(ai_mhead, 40) != 0) return -1;\n',
'''    if (ai_readfull(ai_mhead, 40) != 0) return -1;
    ai_scanwhy = 'H';
    ai_scanat = 0;
''','header phase')
    rep(SRC,'    i=0;\n    while(i<8){\n',
'''    ai_scanwhy = 'D';
    ai_scanat = 8;
    i=0;
    while(i<8){
''','identity phase')
    rep(SRC,'    ai_mtsalt=ai_getu16(ai_mhead,34);\n',
'''    ai_scanwhy = 'H';
    ai_scanat = 24;
    ai_mtsalt=ai_getu16(ai_mhead,34);
''','header structural phase')
    rep(SRC,'    logical = ai_getu16(ai_mhead, 30);\n    if (logical != actual) return -1;\n    if (logical < 40) return -1;\n',
'''    logical = ai_getu16(ai_mhead, 30);
    ai_scanwhy = 'L';
    ai_scanat = 30;
    if (logical < 40) return -1;
''','logical length phase')
    rep(SRC,'    while (rn < rcount) {\n        if (used > rbytes) return -1;\n',
'''    while (rn < rcount) {
        ai_scanwhy = 'R';
        ai_scanrec = rn;
        ai_scanat = 40 + used;
        if (used > rbytes) return -1;
''','record phase')
    rep(SRC,'        while (pos < plen) {\n            take = plen - pos;\n',
'''        ai_scanwhy = 'P';
        while (pos < plen) {
            ai_scanat = 40 + used + hlen + pos;
            take = plen - pos;
''','payload phase')
    rep(SRC,'            while (i < take) {\n                at = pos + i;\n',
'''            while (i < take) {
                at = pos + i;
                ai_scanat = 40 + used + hlen + at;
''','payload offset')
    rep(SRC,'    if (used != rbytes) return -1;\n    calc = ai_fs1 + (ai_fs2 * 256);\n    if (calc != ai_getu16(ai_mhead, 32)) return -1;\n    if (ai_mbytes != logical) return -1;\n',
'''    ai_scanwhy = 'L';
    ai_scanat = 40 + used;
    if (used != rbytes) return -1;
    if (ai_mbytes != logical) return -1;
    rc = read(ai_mfd, ai_mstage, 1);
    ai_mreads = ai_mreads + 1;
    if (rc < 0) {
        ai_scanwhy = 'I';
        return -1;
    }
    if (rc > 0) return -1;
    ai_scanwhy = 'C';
    ai_scanat = 32;
    calc = ai_fs1 + (ai_fs2 * 256);
    if (calc != ai_getu16(ai_mhead, 32)) return -1;
''','tail and checksum')
    rep(SRC,'        if (rc < 0) {\n            ai_error = 4;\n',
'''        if (rc < 0) {
            puts("Model scan: code byte record");
            putchar(ai_scanwhy);
            putchar(' ');
            ai_scanhex(ai_scanat);
            putchar(' ');
            ai_scanhex(ai_scanrec);
            putchar(10);
            ai_error = 4;
''','print diagnostic')

    old='''        got = read(ai_mfd, &p[done], ask);
        ai_mreads = ai_mreads + 1;
        if (got <= 0) return -1;
        if ((unsigned int)got > ask) return -1;
        done = done + (unsigned int)got;
'''
    new='''        got = read(ai_mfd, &p[done], ask);
        ai_mreads = ai_mreads + 1;
        if (got < 0) {
            ai_scanwhy = 'I';
            return -1;
        }
        if (got == 0) {
            ai_scanwhy = 'E';
            return -2;
        }
        /* SDK read() returns at most the requested count. */
        done = done + (unsigned int)got;
'''
    rep(MATCH,old,new,'readfull eof/error split')

def c48_scan():
    for p in (ROOT/'usr/src/ailmzx48').glob('*'):
        if p.suffix.lower() not in {'.c','.h'}: continue
        for n,line in enumerate(p.read_bytes().splitlines(),1):
            if b'\r' in line: raise SystemExit(f'CR {p}:{n}')
            line.decode('ascii')
            if len(line)>64: raise SystemExit(f'>64 cols {p}:{n} {len(line)}')
    print('C48 AILM SOURCE SCAN PASS',flush=True)

def rebuild():
    run([sys.executable,'-B','compiler/c48.py',str(SRC),'-o',str(BIN)])

def probe(corrupt):
    with tempfile.TemporaryDirectory(prefix='ailm-b3-probe-') as td:
        td=Path(td); shutil.copy2(ROOT/BIN,td/'ailmzx48.c48b')
        data=(ROOT/MODEL).read_bytes()
        if corrupt=='tail': data += b'X'
        if corrupt=='trunc': data=data[:-1]
        (td/'ailm.dat').write_bytes(data)
        r=run([sys.executable,str(ROOT/'compiler/c48run.py'),'ailmzx48.c48b'],
              cwd=td,input='spectrum\nq\n',capture=True,timeout=120)
        out=r.stdout+r.stderr
        if corrupt is None:
            if 'Model scan:' in out: raise SystemExit('valid model scan failed')
        else:
            if 'Model scan:' not in out: raise SystemExit(f'{corrupt}: no diagnostic')
            if corrupt=='tail' and 'L ' not in out:
                raise SystemExit('tail: not length diagnostic')
            if corrupt=='trunc' and 'E ' not in out:
                raise SystemExit('trunc: not eof diagnostic')
        print(f'AILM PROBE {corrupt or "valid"} PASS',flush=True)

def target_tests():
    s=text(SRC); m=text(MATCH)
    for bad in ('actual = 8566','logical != actual'):
        if bad in s: raise SystemExit(f'stale hard length: {bad}')
    if 'rc = read(ai_mfd, ai_mstage, 1);' not in s: raise SystemExit('missing eof probe')
    if 'if (got < 0)' not in m or 'if (got == 0)' not in m:
        raise SystemExit('readfull split missing')
    if 'got > ask' in m: raise SystemExit('unreachable post-write check remains')
    probe(None); probe('tail'); probe('trunc')

def remove_harness():
    for p in (SCRIPT,WORKFLOW):
        q=ROOT/p
        if q.exists(): q.unlink()

def delta_guard():
    allowed={str(SRC),str(MATCH),str(BIN)}
    actual=set(filter(None,gout('diff','--name-only',BASE).splitlines()))
    if actual != allowed:
        raise SystemExit(f'unexpected delta {sorted(actual)}')
    run(['git','diff','--check'])

def tree_files(root):
    return sorted(p for p in root.rglob('*') if p.is_file()
                  and '.git' not in p.relative_to(root).parts)
def manifest(root):
    h=hashlib.sha256()
    for p in tree_files(root):
        h.update(p.relative_to(root).as_posix().encode()+b'\0')
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()
def sop():
    expected=manifest(ROOT)
    for k in range(1,4):
        with tempfile.TemporaryDirectory(prefix=f'sop-b3-{k}-') as td:
            fresh=Path(td)/'repo'
            shutil.copytree(ROOT,fresh,ignore=shutil.ignore_patterns(
                '.git','__pycache__','*.pyc','*.pyo','.coverage'))
            if manifest(fresh)!=expected: raise SystemExit('manifest mismatch')
            for p in tree_files(fresh):
                data=p.read_bytes()
                if b''.join(data.splitlines(keepends=True))!=data:
                    raise SystemExit(f'line reconstruction {p}')
                for n,line in enumerate(data.splitlines(keepends=True),1):
                    if b'<<<<<<<' in line or b'>>>>>>>' in line:
                        raise SystemExit(f'conflict {p}:{n}')
                    if p.suffix.lower() in {'.c','.h'}:
                        body=line.rstrip(b'\n')
                        body.decode('ascii')
                        if b'\r' in line or len(body)>64:
                            raise SystemExit(f'C48 bytes {p}:{n}')
            ss=(fresh/SRC).read_bytes(); mm=(fresh/MATCH).read_bytes()
            for needle in (b'ai_scanhex',b'Model scan: ',b'ai_scanat'):
                if needle not in ss: raise SystemExit(f'missing {needle!r}')
            if b'got == 0' not in mm: raise SystemExit('missing EOF split')
            print(f'SOP PASS {k}: ZERO NEW DEFECTS manifest={expected}',flush=True)

def main():
    run(['git','merge-base','--is-ancestor',BASE,'HEAD'])
    patch(); c48_scan(); rebuild(); target_tests(); remove_harness(); delta_guard()
    run([sys.executable,'-B','compiler/verify_release.py'],timeout=1800)
    sop()
    run(['git','config','user.name','github-actions[bot]'])
    run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'])
    run(['git','add','-A'])
    run(['git','commit','-m','fix: harden ailmzx48 model scanning'])
    run(['git','push','origin','HEAD:main'])
if __name__=='__main__': main()
