#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, shutil, subprocess, sys, tempfile, time

ROOT = Path.cwd()
BASE = "3da2e907b10e22dab057fe1ce2fd268ef5102533"
SCRIPT = Path(".github/land_batch3.py")
WORKFLOW = Path(".github/workflows/land-ailm-batch3.yml")
SRC = Path("usr/src/ailmzx48/ailmzx48.c")
MATCH = Path("usr/src/ailmzx48/aimatch.h")
BIN = Path("usr/bin/ailmzx48/ailmzx48.c48b")
MODEL = Path("usr/bin/ailmzx48/ailm.dat")
COLD = Path("usr/src/ailmzx48/model/cold-seed.bin")
EVAL = Path("usr/src/ailmzx48/evaluation")
CONF = EVAL / "sdk-conformance"
STATUS = EVAL / "DESIGN-COMPLIANCE-STATUS.json"
CERT = EVAL / "DESIGN-REVIEW-CERTIFICATE.md"
SCENARIOS = (
    "learned-bridge", "architecture-routing", "literal-context",
    "final-a", "final-b", "final-c",
)

sys.path.insert(0, str(ROOT / "compiler"))
from c48.compiler import compile_file


def run(a, cwd=None, timeout=1800, capture=False):
    print("+", " ".join(map(str, a)), flush=True)
    return subprocess.run(
        a, cwd=cwd or ROOT, text=True, capture_output=capture,
        check=True, timeout=timeout,
    )


def text(p):
    return (ROOT / p).read_text(encoding="utf-8")


def write(p, s):
    (ROOT / p).write_text(s, encoding="utf-8", newline="\n")


def loadj(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def savej(p, value):
    (ROOT / p).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def rep(p, old, new, label):
    s = text(p)
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: anchor count {n}")
    write(p, s.replace(old, new, 1))


def gout(*a):
    return subprocess.check_output(["git", *a], cwd=ROOT, text=True).strip()


def ast_count(label):
    program = compile_file(ROOT / SRC)
    stack = [program]
    count = 0
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            if isinstance(x.get("kind"), str):
                count += 1
            stack.extend(
                v for v in x.values() if isinstance(v, (dict, list))
            )
        elif isinstance(x, list):
            stack.extend(v for v in x if isinstance(v, (dict, list)))
    print(f"{label} semantic AST nodes={count}", flush=True)
    return count


def patch():
    rep(
        SRC,
        "unsigned int ai_mreads;\n",
        "unsigned int ai_mreads;\nunsigned int ai_scanwhy;\n",
        "scan reason state",
    )
    rep(
        SRC,
        "    unsigned int actual;\n    unsigned int logical;\n",
        "    unsigned int logical;\n",
        "remove actual declaration",
    )
    rep(
        SRC,
        "    ai_mtopic = ai_t_id;\n"
        "    if (ai_mfd < 3) return -1;\n"
        "    actual = 8566;\n"
        "    if (actual < 40) return -1;\n",
        "    ai_mtopic = ai_t_id;\n"
        "    if (ai_mfd < 3) return -1;\n",
        "remove hard length",
    )
    rep(
        SRC,
        "    if (ai_readfull(ai_mhead, 40) != 0) return -1;\n",
        "    if (ai_readfull(ai_mhead, 40) != 0) return -1;\n"
        "    ai_scanwhy = 3;\n",
        "format reason",
    )
    rep(
        SRC,
        "    logical = ai_getu16(ai_mhead, 30);\n"
        "    if (logical != actual) return -1;\n"
        "    if (logical < 40) return -1;\n",
        "    logical = ai_getu16(ai_mhead, 30);\n"
        "    if (logical < 40) return -1;\n",
        "logical length",
    )
    rep(
        SRC,
        "    if (used != rbytes) return -1;\n"
        "    calc = ai_fs1 + (ai_fs2 * 256);\n"
        "    if (calc != ai_getu16(ai_mhead, 32)) return -1;\n"
        "    if (ai_mbytes != logical) return -1;\n",
        "    if (used != rbytes) return -1;\n"
        "    if (ai_mbytes != logical) return -1;\n"
        "    slot = read(ai_mfd, ai_mstage, 1);\n"
        "    ai_mreads = ai_mreads + 1;\n"
        "    if (slot < 0) {\n"
        "        ai_scanwhy = 1;\n"
        "        return -1;\n"
        "    }\n"
        "    if (slot != 0) {\n"
        "        ai_scanwhy = 7;\n"
        "        return -1;\n"
        "    }\n"
        "    calc = ai_fs1 + (ai_fs2 * 256);\n"
        "    if (calc != ai_getu16(ai_mhead, 32)) return -1;\n"
        "    ai_scanwhy = 0;\n",
        "exact eof and checksum",
    )
    rep(
        SRC,
        "        if (rc < 0) {\n"
        "            ai_error = 4;\n",
        "        if (rc < 0) {\n"
        "            puts(\"Model scan error code:\");\n"
        "            putchar('0' + ai_scanwhy);\n"
        "            putchar(10);\n"
        "            ai_error = 4;\n",
        "visible scan reason",
    )
    old = """        got = read(ai_mfd, &p[done], ask);
        ai_mreads = ai_mreads + 1;
        if (got <= 0) return -1;
        if ((unsigned int)got > ask) return -1;
        done = done + (unsigned int)got;
"""
    new = """        got = read(ai_mfd, &p[done], ask);
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
"""
    rep(MATCH, old, new, "readfull eof/error split")


def c48_scan(root=ROOT):
    count = 0
    for p in sorted((root / "usr/src/ailmzx48").glob("*")):
        if p.suffix.lower() not in {".c", ".h"}:
            continue
        for n, line in enumerate(p.read_bytes().splitlines(), 1):
            count += 1
            if b"\r" in line:
                raise SystemExit(f"CR {p}:{n}")
            line.decode("ascii")
            if len(line) > 64:
                raise SystemExit(f">64 cols {p}:{n} {len(line)}")
    print(f"C48 AILM SOURCE SCAN PASS lines={count}", flush=True)


def rebuild():
    run([
        sys.executable, "-B", "compiler/c48.py", str(SRC),
        "-o", str(BIN),
    ])


def gv(vm, name):
    lv = vm.global_lvalues[name]
    return vm.mem.load_integer(lv.pointer.address, lv.ctype)


def gs(vm, name):
    lv = vm.global_lvalues[name]
    return vm._read_cstr(lv.pointer).decode("ascii")


def new_vm(program, screen, argv, provider, max_steps):
    from c48.romvm import RomMathVM

    class MeterVM(RomMathVM):
        def __init__(self, *a, **kw):
            self.host_read_calls = 0
            self.host_read_bytes = 0
            self.host_seek_calls = 0
            self.host_max_read = 0
            super().__init__(*a, **kw)

        def _b_read(self, args):
            self.host_read_calls += 1
            req = self._to_unsigned(args[2])
            if req > self.host_max_read:
                self.host_max_read = req
            rv = super()._b_read(args)
            if isinstance(rv.data, int) and rv.data > 0:
                self.host_read_bytes += rv.data
            return rv

        def _b_seek(self, args):
            self.host_seek_calls += 1
            return super()._b_seek(args)

    return MeterVM(
        program, screen, argv=argv, input_provider=provider,
        sound_player=lambda _path: None, tick_provider=lambda: 1000,
        heap_size=0, max_steps=max_steps,
    )


def probe(kind):
    from c48.format import read as read_program
    from c48.screen import Font4x8, ZXScreen

    with tempfile.TemporaryDirectory(prefix="ailm-b3-probe-") as td:
        td = Path(td)
        shutil.copy2(ROOT / BIN, td / "ailmzx48.c48b")
        data = (ROOT / MODEL).read_bytes()
        if kind == "tail":
            data += b"X"
        if kind == "trunc":
            data = data[:-1]
        (td / "ailm.dat").write_bytes(data)
        program = read_program(td / "ailmzx48.c48b")
        font = Font4x8.load(ROOT / "compiler/assets/font4x8-tasword.bin")
        screen = ZXScreen(font)
        keys = iter(ord(c) for c in "spectrum\nq\n")
        vm = new_vm(
            program, screen, [str(td / "ailmzx48.c48b")],
            lambda: next(keys, -1), 2000000,
        )
        status = vm.run()
        if status != 0:
            raise SystemExit(f"{kind or 'valid'}: status {status}")
        err = gv(vm, "ai_error")
        why = gv(vm, "ai_scanwhy")
        mb = gv(vm, "ai_mbytes")
        mr = gv(vm, "ai_mrecords")
        if kind is None:
            if err != 0 or why != 0 or mb != 8566 or mr != 69:
                raise SystemExit(
                    f"valid: err={err} why={why} bytes={mb} rec={mr}"
                )
        else:
            want = 7 if kind == "tail" else 2
            if why != want:
                raise SystemExit(
                    f"{kind}: err={err} why={why} bytes={mb} rec={mr}"
                )
        print(
            f"AILM PROBE {kind or 'valid'} PASS error={err} "
            f"reason={why} bytes={mb} records={mr}",
            flush=True,
        )


def target_tests():
    s = text(SRC)
    m = text(MATCH)
    if "actual = 8566" in s or "logical != actual" in s:
        raise SystemExit("stale hardcoded model length")
    if "slot = read(ai_mfd, ai_mstage, 1);" not in s:
        raise SystemExit("missing exact EOF probe")
    if "if (got < 0)" not in m or "if (got == 0)" not in m:
        raise SystemExit("readfull split missing")
    if "got > ask" in m:
        raise SystemExit("stale impossible read guard")
    if "ai_scanwhy" not in s or "ai_scanwhy = 0;" not in s:
        raise SystemExit("missing scanner diagnostic state")
    probe(None)
    probe("tail")
    probe("trunc")


class Dialogue:
    def __init__(self, request):
        self.prompts = request["prompts"]
        self.expected = request["expected_keywords"]
        if len(self.prompts) != len(self.expected):
            raise SystemExit("request prompt/keyword count mismatch")
        self.vm = None
        self.queue = []
        self.next_prompt = 0
        self.snapshots = []
        self.last_steps = 0

    def bind(self, vm):
        self.vm = vm

    def snapshot(self, index):
        vm = self.vm
        if vm is None:
            raise SystemExit("dialogue VM not bound")
        response = gs(vm, "ai_out")
        expected = str(self.expected[index]).lower()
        hit = expected in response.lower()
        now = vm.steps
        diag_names = (
            "ai_turns", "ai_beeps", "ai_mrecords", "ai_mhits",
            "ai_mbytes", "ai_mreads", "ai_l0bytes", "ai_l1count",
            "ai_l2count", "ai_compact", "ai_l2evict", "ai_litloss",
            "ai_semuse", "ai_triuse", "ai_bruse", "ai_lmcount",
            "ai_altuse", "ai_histuse", "ai_lituse", "ai_lasttop",
            "ai_yields", "ai_error", "ai_scanwhy",
        )
        diag = {name: gv(vm, name) for name in diag_names}
        self.snapshots.append({
            "turn": index + 1,
            "prompt": self.prompts[index],
            "expected_keyword": self.expected[index],
            "keyword_hit": hit,
            "response": response,
            "vm_steps": now - self.last_steps,
            "diag": diag,
        })
        self.last_steps = now

    def __call__(self):
        if not self.queue:
            if self.next_prompt > 0:
                self.snapshot(self.next_prompt - 1)
            if self.next_prompt < len(self.prompts):
                line = self.prompts[self.next_prompt] + "\n"
                self.next_prompt += 1
            else:
                line = "q\n"
                self.next_prompt += 1
            self.queue = [ord(c) for c in line]
        return self.queue.pop(0)


def scenario_run(name):
    from c48.format import read as read_program
    from c48.screen import Font4x8, ZXScreen

    req = loadj(CONF / name / "request.json")
    old_run = loadj(CONF / name / "run.json")
    old_score = loadj(CONF / name / "score.json")
    limit = int(
        old_run.get("max_steps", old_score.get("vm_step_limit", 20000000))
    )
    with tempfile.TemporaryDirectory(prefix=f"ailm-{name}-") as td:
        td = Path(td)
        shutil.copy2(ROOT / BIN, td / "ailmzx48.c48b")
        shutil.copy2(ROOT / MODEL, td / "ailm.dat")
        program = read_program(td / "ailmzx48.c48b")
        font = Font4x8.load(ROOT / "compiler/assets/font4x8-tasword.bin")
        screen = ZXScreen(font)
        dialogue = Dialogue(req)
        vm = new_vm(
            program, screen, [str(td / "ailmzx48.c48b")],
            dialogue, limit,
        )
        dialogue.bind(vm)
        started = time.monotonic()
        status = vm.run()
        elapsed = time.monotonic() - started

    snaps = dialogue.snapshots
    if len(snaps) != len(req["prompts"]):
        raise SystemExit(
            f"{name}: captured {len(snaps)} of {len(req['prompts'])} turns"
        )
    hits = sum(1 for s in snaps if s["keyword_hit"])
    ratio = hits / len(snaps) if snaps else 1.0
    final_kw = str(req.get("final_expected_keyword", "")).lower()
    final_hit = not final_kw or final_kw in snaps[-1]["response"].lower()
    clean = status == 0
    if not clean or ratio < float(req.get("min_keyword_ratio", 1.0)):
        raise SystemExit(
            f"{name}: acceptance failure status={status} ratio={ratio}"
        )

    def total(key):
        return sum(int(s["diag"][key]) for s in snaps)

    def maximum(key):
        return max(int(s["diag"][key]) for s in snaps)

    sem = total("ai_semuse")
    tri = total("ai_triuse")
    bridge = total("ai_bruse")
    yields = total("ai_yields")
    compact = total("ai_compact")
    l2evict = total("ai_l2evict")
    litloss = total("ai_litloss")
    if sem < int(req.get("min_semantic_uses", 0)):
        raise SystemExit(f"{name}: semantic uses {sem} below request gate")
    if compact < int(req.get("min_compactions", 0)):
        raise SystemExit(f"{name}: compactions {compact} below request gate")
    if maximum("ai_l2count") < int(req.get("min_l2_count", 0)):
        raise SystemExit(f"{name}: L2 count below request gate")
    if litloss < int(req.get("min_literal_losses", 0)):
        raise SystemExit(f"{name}: literal losses below request gate")
    if maximum("ai_lmcount") < int(req.get("min_lmcount", 0)):
        raise SystemExit(f"{name}: LM count below request gate")
    if not final_hit:
        raise SystemExit(f"{name}: final expected keyword missing")

    turn_steps = [int(s["vm_steps"]) for s in snaps]
    fresh_run = dict(old_run)
    fresh_run.update({
        "source_sha256": sha(SRC),
        "c48b_sha256": sha(BIN),
        "cold_model_sha256": sha(COLD),
        "cold_model_budget_bytes": (ROOT / COLD).stat().st_size,
        "cold_model_logical_length": (ROOT / COLD).stat().st_size,
        "cold_model_bytes_read": vm.host_read_bytes,
        "cold_model_read_calls": vm.host_read_calls,
        "cold_model_seek_calls": vm.host_seek_calls,
        "cold_model_max_request": vm.host_max_read,
        "cold_record_count": maximum("ai_mrecords"),
        "context_compactions": compact,
        "context_l2_evictions": l2evict,
        "cooperative_yields": yields,
        "elapsed_seconds": round(elapsed, 3),
        "final_keyword_hit": final_hit,
        "heap_size": 0,
        "iteration": int(req["iteration"]),
        "literal_reference_losses": litloss,
        "max_l0bytes": maximum("ai_l0bytes"),
        "max_l1count": maximum("ai_l1count"),
        "max_l2count": maximum("ai_l2count"),
        "max_lmcount": maximum("ai_lmcount"),
        "max_steps": limit,
        "runner_max_seconds": int(req.get("max_seconds", 1200)),
        "semantic_retrieval_uses": sem,
        "trigram_uses": tri,
        "bridge_uses": bridge,
        "vm_steps": vm.steps,
        "vm_turn_steps": turn_steps,
        "vm_turn_steps_avg": sum(turn_steps) / len(turn_steps),
        "vm_turn_steps_max": max(turn_steps),
        "vm_turn_steps_min": min(turn_steps),
    })
    fresh_score = dict(old_score)
    fresh_score.update({
        "accepted_turns": len(snaps),
        "beep_calls": gv(vm, "ai_beeps"),
        "bridge_uses": bridge,
        "clean_exit": clean,
        "cold_record_count": maximum("ai_mrecords"),
        "context_compactions": compact,
        "context_l2_evictions": l2evict,
        "cooperative_yields": yields,
        "final_keyword_hit": final_hit,
        "iteration": int(req["iteration"]),
        "keyword_hits": hits,
        "keyword_ratio": ratio,
        "keyword_total": len(snaps),
        "literal_reference_losses": litloss,
        "max_l0bytes": maximum("ai_l0bytes"),
        "max_l1count": maximum("ai_l1count"),
        "max_l2count": maximum("ai_l2count"),
        "max_lmcount": maximum("ai_lmcount"),
        "semantic_retrieval_uses": sem,
        "trigram_uses": tri,
        "turns": len(snaps),
        "vm_step_limit": limit,
        "vm_steps": vm.steps,
        "vm_turn_steps_avg": sum(turn_steps) / len(turn_steps),
        "vm_turn_steps_max": max(turn_steps),
        "vm_turn_steps_min": min(turn_steps),
    })
    savej(CONF / name / "run.json", fresh_run)
    savej(CONF / name / "score.json", fresh_score)
    tx = ROOT / CONF / name / "transcript.json"
    if tx.exists():
        savej(
            CONF / name / "transcript.json",
            {"schema": 1, "iteration": int(req["iteration"]), "turns": snaps},
        )
    print(
        f"AILM REQUALIFY {name} PASS turns={len(snaps)} "
        f"keywords={hits}/{len(snaps)} sem={sem} tri={tri} "
        f"bridge={bridge} yields={yields} steps={vm.steps}",
        flush=True,
    )


def evidence_summary(name, fields):
    score = loadj(CONF / name / "score.json")
    run_data = loadj(CONF / name / "run.json")
    value = {"iteration": run_data["iteration"]}
    for field in fields:
        value[field] = score.get(field)
    return value


def update_status_and_certificate():
    status = loadj(STATUS)
    old_source = status["source_sha256"]
    old_binary = status["sdk_c48b_sha256"]
    new_source = sha(SRC)
    new_binary = sha(BIN)
    status["source_sha256"] = new_source
    status["sdk_c48b_sha256"] = new_binary
    status["cold_model_sha256"] = sha(COLD)
    sdk = status["sdk_profile"]
    common = (
        "turns", "keyword_ratio", "clean_exit", "bridge_uses",
        "trigram_uses", "cooperative_yields", "semantic_retrieval_uses",
    )
    sdk["learned_bridge"] = evidence_summary("learned-bridge", common)
    sdk["architecture_routing"] = evidence_summary(
        "architecture-routing", common
    )
    sdk["literal_context"] = evidence_summary(
        "literal-context",
        common + (
            "context_compactions", "literal_reference_losses",
            "max_l2count", "max_lmcount", "final_keyword_hit",
        ),
    )
    finals = {}
    for name in ("final-a", "final-b", "final-c"):
        finals[name] = evidence_summary(
            name, common + ("literal_reference_losses",)
        )
    sdk["post_repair_final_regressions"] = finals
    savej(STATUS, status)

    cert = text(CERT)
    if old_source not in cert or old_binary not in cert:
        raise SystemExit("certificate old identity anchor missing")
    cert = cert.replace(old_source, new_source).replace(
        old_binary, new_binary
    )
    write(CERT, cert)
    print(
        f"AILM STATUS IDENTITIES source={new_source} binary={new_binary}",
        flush=True,
    )


def requalify():
    if sha(MODEL) != sha(COLD):
        raise SystemExit("packaged/source A48M identity mismatch")
    for name in SCENARIOS:
        scenario_run(name)
    update_status_and_certificate()
    run([
        sys.executable, "-B",
        "usr/src/ailmzx48/evaluation/check_design_compliance.py",
    ], timeout=1800)


def remove_harness():
    for p in (SCRIPT, WORKFLOW):
        q = ROOT / p
        if q.exists():
            q.unlink()


def delta_guard():
    allowed = {str(SRC), str(MATCH), str(BIN), str(STATUS), str(CERT)}
    for name in SCENARIOS:
        allowed.add(str(CONF / name / "run.json"))
        allowed.add(str(CONF / name / "score.json"))
    allowed.add(str(CONF / "architecture-routing" / "transcript.json"))
    actual = set(filter(None, gout("diff", "--name-only", BASE).splitlines()))
    if actual != allowed:
        raise SystemExit(
            "unexpected delta\nactual="
            + repr(sorted(actual))
            + "\nallowed="
            + repr(sorted(allowed))
        )
    run(["git", "diff", "--check"])


def tree_files(root):
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(root).parts
    )


def manifest(root):
    h = hashlib.sha256()
    for p in tree_files(root):
        h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def sop():
    expected = manifest(ROOT)
    text_ext = {
        ".c", ".h", ".py", ".md", ".json", ".yml", ".yaml", ".txt",
        ".bat", ".sh",
    }
    for k in range(1, 4):
        with tempfile.TemporaryDirectory(prefix=f"sop-b3-{k}-") as td:
            fresh = Path(td) / "repo"
            shutil.copytree(
                ROOT, fresh,
                ignore=shutil.ignore_patterns(
                    ".git", "__pycache__", "*.pyc", "*.pyo", ".coverage"
                ),
            )
            if manifest(fresh) != expected:
                raise SystemExit(f"SOP {k}: fresh-copy manifest mismatch")
            files = 0
            lines = 0
            for p in tree_files(fresh):
                files += 1
                data = p.read_bytes()
                rebuilt = bytearray()
                for n, line in enumerate(data.splitlines(keepends=True), 1):
                    lines += 1
                    rebuilt.extend(line)
                    if b"<<<<<<<" in line or b">>>>>>>" in line:
                        raise SystemExit(f"SOP {k}: conflict {p}:{n}")
                    if p.suffix.lower() in text_ext:
                        line.decode("utf-8")
                    if p.suffix.lower() in {".c", ".h"}:
                        body = line.rstrip(b"\n")
                        body.decode("ascii")
                        if b"\r" in line or len(body) > 64:
                            raise SystemExit(f"SOP {k}: C48 bytes {p}:{n}")
                if bytes(rebuilt) != data:
                    raise SystemExit(f"SOP {k}: line reconstruction {p}")
                if p.suffix.lower() == ".json":
                    json.loads(data.decode("utf-8"))
            c48_scan(fresh)

            ss = (fresh / SRC).read_bytes()
            mm = (fresh / MATCH).read_bytes()
            for needle in (
                b"ai_scanwhy", b"Model scan error code:",
                b"ai_mbytes", b"ai_mrecords",
            ):
                if needle not in ss:
                    raise SystemExit(f"SOP {k}: missing {needle!r}")
            if b"actual = 8566" in ss or b"logical != actual" in ss:
                raise SystemExit(f"SOP {k}: stale hardcoded model length")
            if b"got == 0" not in mm or b"got > ask" in mm:
                raise SystemExit(f"SOP {k}: read-loop defect")

            source_hash = hashlib.sha256((fresh / SRC).read_bytes()).hexdigest()
            binary_hash = hashlib.sha256((fresh / BIN).read_bytes()).hexdigest()
            cold_hash = hashlib.sha256((fresh / COLD).read_bytes()).hexdigest()
            for name in SCENARIOS:
                r = json.loads(
                    (fresh / CONF / name / "run.json").read_text("utf-8")
                )
                if (
                    r.get("source_sha256") != source_hash
                    or r.get("c48b_sha256") != binary_hash
                    or r.get("cold_model_sha256") != cold_hash
                ):
                    raise SystemExit(f"SOP {k}: evidence identity {name}")
            st = json.loads((fresh / STATUS).read_text("utf-8"))
            if (
                st.get("source_sha256") != source_hash
                or st.get("sdk_c48b_sha256") != binary_hash
                or st.get("cold_model_sha256") != cold_hash
            ):
                raise SystemExit(f"SOP {k}: status identity mismatch")
            cert = (fresh / CERT).read_text("utf-8")
            for identity in (
                st["design_sha256"], source_hash, binary_hash, cold_hash
            ):
                if identity not in cert:
                    raise SystemExit(f"SOP {k}: certificate identity missing")
            print(
                f"SOP PASS {k}: ZERO NEW DEFECTS files={files} "
                f"byte-lines={lines} manifest={expected}",
                flush=True,
            )


def main():
    run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"])
    base = ast_count("BASELINE")
    patch()
    c48_scan()
    patched = ast_count("PATCHED")
    print(
        f"AST delta={patched-base} headroom={32768-patched}",
        flush=True,
    )
    if patched > 32768:
        raise SystemExit("patched AST exceeds ceiling")
    rebuild()
    target_tests()
    requalify()
    remove_harness()
    delta_guard()
    run([sys.executable, "-B", "compiler/verify_release.py"], timeout=1800)
    sop()
    run(["git", "config", "user.name", "github-actions[bot]"])
    run([
        "git", "config", "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
    ])
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", "fix: harden ailmzx48 model scanning"])
    run(["git", "push", "origin", "HEAD:main"])


if __name__ == "__main__":
    main()
