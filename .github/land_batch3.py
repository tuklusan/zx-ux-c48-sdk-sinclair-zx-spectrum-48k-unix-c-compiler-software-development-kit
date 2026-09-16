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
sys.path.insert(0,str(ROOT/'compiler'))
from c48.compiler import compile_file

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
def gout(*a): return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()

def ast_count(label):
    program=compile_file(ROOT/SRC)
    stack=[program]; count=0
    while stack:
        x=stack.pop()
        if isinstance(x,dict):
            if isinstance(x.get('kind'),str): count+=1
            stack.extend(v for v in x.values() if isinstance(v,(dict,list)))
        elif isinstance(x,list):
            stack.extend(v for v in x if isinstance(v,(dict,list)))
    print(f'{label} semantic AST nodes={count}',flush=True)
    return count

def patch():
    rep(SRC,'unsigned int ai_mreads;\n',
        'unsigned int ai_mreads;\nunsigned int ai_scanwhy;\n',
        'scan reason state')
    rep(SRC,'    unsigned int actual;\n    unsigned int logical;\n',
        '    unsigned int logical;\n','remove actual declaration')
    rep(SRC,'    ai_mtopic = ai_t_id;\n    if (ai_mfd < 3) return -1;\n    actual = 8566;\n    if (actual < 40) return -1;\n',
'''    ai_mtopic = ai_t_id;
    ai_scanwhy = 1;
    if (ai_mfd < 3) return -1;
''','remove hard length')
    rep(SRC,'    if (ai_readfull(ai_mhead, 40) != 0) return -1;\n',
'''    if (ai_readfull(ai_mhead, 40) != 0) return -1;
    ai_scanwhy = 3;
''','header reason')
    rep(SRC,'    logical = ai_getu16(ai_mhead, 30);\n    if (logical != actual) return -1;\n    if (logical < 40) return -1;\n',
'''    logical = ai_getu16(ai_mhead, 30);
    if (logical < 40) return -1;
''','logical length')
    rep(SRC,'    while (rn < rcount) {\n        if (used > rbytes) return -1;\n',
'''    ai_scanwhy = 4;
    while (rn < rcount) {
        if (used > rbytes) return -1;
''','record reason')
    rep(SRC,'        while (pos < plen) {\n            take = plen - pos;\n',
'''        ai_scanwhy = 5;
        while (pos < plen) {
            take = plen - pos;
''','payload reason')
    rep(SRC,'    if (used != rbytes) return -1;\n    calc = ai_fs1 + (ai_fs2 * 256);\n    if (calc != ai_getu16(ai_mhead, 32)) return -1;\n    if (ai_mbytes != logical) return -1;\n',
'''    ai_scanwhy = 6;
    if (used != rbytes) return -1;
    if (ai_mbytes != logical) return -1;
    slot = read(ai_mfd, ai_mstage, 1);
    ai_mreads = ai_mreads + 1;
    if (slot < 0) {
        ai_scanwhy = 1;
        return -1;
    }
    if (slot != 0) {
        ai_scanwhy = 7;
        return -1;
    }
    calc = ai_fs1 + (ai_fs2 * 256);
    if (calc != ai_getu16(ai_mhead, 32)) return -1;
''','exact eof and checksum')
    rep(SRC,'        if (rc < 0) {\n            ai_error = 4;\n',
'''        if (rc < 0) {
            puts("Model scan error code:");
            putchar('0' + ai_scanwhy);
            putchar(10);
            ai_error = 4;
''','visible scan reason')
    old='''        got = read(ai_mfd, &p[done], ask);
        ai_mreads = ai_mreads + 1;
        if (got <= 0) return -1;
        if ((unsigned int)got > ask) return -1;
        done = done + (unsigned int)got;
'''
    new='''        got = read(ai_mfd, &p[done], ask);
        ai_mreads = ai_mreads + 1;
        if (got < 0) {
            ai_scanwhy = 1;
            return -1;
        }
        if (got == 0) {
            ai_scanwhy = 2;
            return -1;
        }
        /* read() cannot return more than the requested count. */
        done = done + (unsigned int)got;
'''
    rep(MATCH,old,new,'readfull eof/error split')

def c48_scan(root=ROOT):
    for p in (root/'usr/src/ailmzx48').glob('*'):
        if p.suffix.lower() not in {'.c','.h'}: continue
        for n,line in enumerate(p.read_bytes().splitlines(),1):
            if b'\r' in line: raise SystemExit(f'CR {p}:{n}')
            line.decode('ascii')
            if len(line)>64: raise SystemExit(f'>64 cols {p}:{n} {len(line)}')
    print('C48 AILM SOURCE SCAN PASS',flush=True)

def rebuild():
    run([sys.executable,'-B','compiler/c48.py',str(SRC),'-o',str(BIN)])

def probe(kind):
    with tempfile.TemporaryDirectory(prefix='ailm-b3-probe-') as td:
        td=Path(td); shutil.copy2(ROOT/BIN,td/'ailmzx48.c48b')
        data=(ROOT/MODEL).read_bytes()
        if kind=='tail': data+=b'X'
        if kind=='trunc': data=data[:-1]
        (td/'ailm.dat').write_bytes(data)
        r=run([sys.executable,str(ROOT/'compiler/c48run.py'),'ailmzx48.c48b'],
              cwd=td,input='spectrum\nq\n',capture=True,timeout=120)
        out=r.stdout+r.stderr
        if kind is None:
            if 'Model scan error code:' in out:
                raise SystemExit('valid model scan failed')
        else:
            if 'Model scan error code:' not in out:
                raise SystemExit(f'{kind}: no scan diagnostic')
            code='7' if kind=='tail' else '2'
            if f'Model scan error code:\n{code}\n' not in out:
                raise SystemExit(f'{kind}: wrong diagnostic: {out[-300:]}')
        print(f'AILM PROBE {kind or "valid"} PASS',flush=True)

def target_tests():
    s=text(SRC); m=text(MATCH)
    if 'actual = 8566' in s or 'logical != actual' in s:
        raise SystemExit('stale hardcoded model length')
    if 'slot = read(ai_mfd, ai_mstage, 1);' not in s:
        raise SystemExit('missing exact EOF probe')
    if 'if (got < 0)' not in m or 'if (got == 0)' not in m:
        raise SystemExit('readfull split missing')
    if 'got > ask' in m: raise SystemExit('stale impossible read guard')
    if 'ai_scanwhy' not in s:
        raise SystemExit('missing reason instrumentation')
    probe(None); probe('tail'); probe('trunc')

def remove_harness():
    for p in (SCRIPT,WORKFLOW):
        q=ROOT/p
        if q.exists(): q.unlink()

def delta_guard():
    allowed={str(SRC),str(MATCH),str(BIN)}
    actual=set(filter(None,gout('diff','--name-only',BASE).splitlines()))
    if actual!=allowed: raise SystemExit(f'unexpected delta {sorted(actual)}')
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
                        body=line.rstrip(b'\n'); body.decode('ascii')
                        if b'\r' in line or len(body)>64:
                            raise SystemExit(f'C48 bytes {p}:{n}')
            c48_scan(fresh)
            ss=(fresh/SRC).read_bytes(); mm=(fresh/MATCH).read_bytes()
            for needle in (b'ai_scanwhy',b'Model scan error code:',b'ai_mbytes',b'ai_mrecords'):
                if needle not in ss: raise SystemExit(f'missing {needle!r}')
            if b'got == 0' not in mm: raise SystemExit('missing EOF split')
            print(f'SOP PASS {k}: ZERO NEW DEFECTS manifest={expected}',flush=True)

def main():
    run(['git','merge-base','--is-ancestor',BASE,'HEAD'])
    base=ast_count('BASELINE')
    patch(); c48_scan(); patched=ast_count('PATCHED')
    print(f'AST delta={patched-base} headroom={32768-patched}',flush=True)
    rebuild(); target_tests(); remove_harness(); delta_guard()
    run([sys.executable,'-B','compiler/verify_release.py'],timeout=1800)
    sop()
    run(['git','config','user.name','github-actions[bot]'])
    run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'])
    run(['git','add','-A'])
    run(['git','commit','-m','fix: harden ailmzx48 model scanning'])
    run(['git','push','origin','HEAD:main'])
if __name__=='__main__': main()
