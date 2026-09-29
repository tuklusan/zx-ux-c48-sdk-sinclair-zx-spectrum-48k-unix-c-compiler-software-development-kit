# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
"""Deterministic cooperative host session for multiple C48 programs."""
from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable

from .errors import RuntimeC48Error, RuntimeExit
from .float5 import Float5, Float5Error
from .limits import VM_CALL_DEPTH
from .memory import PointerRecord
from .romvm import RomMathVM
from .typesys import (
    CHAR,
    FLOAT,
    INT,
    UINT,
    VOID,
    CType,
    arithmetic_common,
    ptr,
)
from .vm import LValue, Value


UPSTREAM_REFERENCE_COMMIT = "69348ee366c48b436aa0d07237ae2e7473e55327"

FREE = "FREE"
READY = "READY"
RUNNING = "RUNNING"
SLEEPING = "SLEEPING"
WAIT_CHILD = "WAIT_CHILD"
WAIT_INPUT = "WAIT_INPUT"
ZOMBIE = "ZOMBIE"

_NO_RESULT = object()
_NORMAL = object()
_BREAK = object()
_CONTINUE = object()


@dataclass(frozen=True)
class ReturnControl:
    value: Value | None


@dataclass(frozen=True)
class VMEvent:
    kind: str
    value: int = 0


@dataclass
class Frame:
    kind: str
    node: Any = None
    pc: int = 0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessDescriptor:
    pid: int
    state: str = FREE
    parent: int | None = None
    exit_status: int | None = None
    wake_tick: int | None = None
    cancelled: bool = False
    vm: "ResumableRomMathVM | None" = None
    resume_value: int | object = _NO_RESULT
    error: str | None = None


class SessionLimitError(RuntimeC48Error):
    """Session-wide deterministic or wall-clock safety ceiling."""


class SessionAbort(RuntimeC48Error):
    """Global session cancellation requested by the display."""


class SessionBudget:
    def __init__(
        self,
        *,
        max_steps: int | None,
        time_quota: float,
        abort_requested: Callable[[], bool] | None = None,
    ):
        self.max_steps = max_steps
        self.time_quota = float(time_quota)
        self.abort_requested = abort_requested or (lambda: False)
        self.steps = 0
        self.started: float | None = None

    def start(self) -> None:
        self.started = time.monotonic()

    def check(self) -> None:
        if self.abort_requested():
            raise SessionAbort("C48 multitask session aborted")
        if self.started is not None and self.time_quota > 0.0:
            if time.monotonic() - self.started > self.time_quota:
                raise SessionLimitError(
                    f"C48 multitask session time quota exceeded ({self.time_quota:g}s)"
                )

    def charge(self) -> None:
        self.check()
        if self.max_steps is None:
            return
        self.steps += 1
        if self.steps > self.max_steps:
            raise SessionLimitError(
                f"C48 multitask session step limit exceeded ({self.max_steps})"
            )


class ResumableRomMathVM(RomMathVM):
    """ROM-profile VM using explicit execution frames for resumable C48 state."""

    def __init__(
        self,
        *args,
        pid: int,
        charge_step: Callable[[], None],
        **kwargs,
    ):
        self.pid = int(pid)
        self._charge_step = charge_step
        self.frames: list[Frame] = []
        self._last: Any = _NO_RESULT
        self._started = False
        self._terminal = False
        super().__init__(*args, max_steps=None, **kwargs)

    def _push(self, kind: str, node: Any = None, **data: Any) -> None:
        self._last = _NO_RESULT
        self.frames.append(Frame(kind, node, 0, dict(data)))

    def _complete(self, value: Any) -> None:
        self.frames.pop()
        self._last = value

    def _take(self) -> Any:
        if self._last is _NO_RESULT:
            raise RuntimeC48Error("multitask continuation result missing")
        value = self._last
        self._last = _NO_RESULT
        return value

    def _start_main(self) -> None:
        f = self.functions.get("main")
        if f is None:
            raise RuntimeC48Error("program has no main definition")
        ft = CType.from_dict(f["ctype"])
        if len(ft.params or ()) == 0:
            args: list[Value] = []
        else:
            argc, argvp = self._build_argv()
            args = [Value(INT, argc), Value(ptr(ptr(CHAR)), argvp)]
        self._push("call", name="main", args=args)
        self._started = True

    def snapshot(self) -> dict[str, int]:
        live_heap = 0
        for aid in self.heap_allocs:
            allocation = self.mem.allocation(aid)
            if allocation is not None:
                live_heap += allocation.size
        return {
            "frames": len(self.frames),
            "scopes": len(self.scope_stack),
            "scope_alloc_lists": len(self.scope_allocs),
            "call_depth": self.call_depth,
            "heap_live_bytes": self.heap_live_bytes,
            "heap_live_sum": live_heap,
        }

    def assert_invariants(self) -> None:
        snap = self.snapshot()
        if snap["scopes"] != snap["scope_alloc_lists"]:
            raise RuntimeC48Error("multitask scope bookkeeping mismatch")
        entered_calls = sum(
            1
            for frame in self.frames
            if frame.kind == "call" and frame.data.get("entered")
        )
        if entered_calls != self.call_depth:
            raise RuntimeC48Error("multitask call-frame bookkeeping mismatch")
        if snap["heap_live_bytes"] != snap["heap_live_sum"]:
            raise RuntimeC48Error("multitask heap accounting mismatch")

    def cancel_cleanup(self) -> None:
        while self.scope_stack:
            self._pop_scope()
        self.frames.clear()
        self.call_depth = 0
        self._last = _NO_RESULT
        self._terminal = True

    def resume(self, resume_value: int | object = _NO_RESULT) -> VMEvent:
        if self._terminal:
            raise RuntimeC48Error("terminated multitask process resumed")
        if not self._started:
            self._start_main()
        if resume_value is not _NO_RESULT:
            if not self.frames:
                raise RuntimeC48Error("multitask resume value without continuation")
            frame = self.frames[-1]
            if frame.kind != "expr" or frame.pc != 90:
                raise RuntimeC48Error("multitask resume value at invalid boundary")
            frame.data["resume_value"] = int(resume_value)
        try:
            while self.frames:
                frame = self.frames[-1]
                if frame.kind == "expr":
                    event = self._step_expr(frame)
                elif frame.kind == "lvalue":
                    event = self._step_lvalue(frame)
                elif frame.kind == "stmt":
                    event = self._step_stmt(frame)
                elif frame.kind == "compound":
                    event = self._step_compound(frame)
                elif frame.kind == "init":
                    event = self._step_init(frame)
                elif frame.kind == "call":
                    event = self._step_call(frame)
                else:
                    raise RuntimeC48Error(
                        f"unknown multitask continuation frame {frame.kind}"
                    )
                if event is not None:
                    self.assert_invariants()
                    return event
            rv = self._take()
            if rv is None:
                raise RuntimeC48Error("main returned no value")
            status = self._to_unsigned(self._convert(rv, INT)) & 0xFF
            self._terminal = True
            return VMEvent("exit", status)
        except RuntimeExit as exc:
            self.cancel_cleanup()
            return VMEvent("exit", exc.status & 0xFF)
        except (RuntimeC48Error, MemoryError, RecursionError):
            self.cancel_cleanup()
            raise

    def _step_call(self, frame: Frame) -> VMEvent | None:
        name = str(frame.data["name"])
        args = list(frame.data["args"])
        if frame.pc == 0:
            f = self.functions.get(name)
            if f is None:
                raise RuntimeC48Error(
                    f"multitask user-function continuation missing {name!r}"
                )
            if self.call_depth >= VM_CALL_DEPTH:
                raise RuntimeC48Error(
                    f"C48 function-call depth limit exceeded ({VM_CALL_DEPTH})"
                )
            ft = CType.from_dict(f["ctype"])
            params = ft.params or ()
            if len(args) != len(params):
                raise RuntimeC48Error("internal argument-count mismatch")
            self.call_depth += 1
            self._push_scope()
            frame.data["entered"] = True
            frame.data["return_type"] = ft.ret
            pnodes = f["declarator"]["suffix"]["params"]
            for pn, pt, arg in zip(pnodes, params, args):
                lv = self._allocate_local(pn["name"], pt)
                self._store(lv, self._convert(arg, pt))
            frame.pc = 1
            self._push("compound", f["body"], reuse_scope=True)
            return None
        if frame.pc == 1:
            control = self._take()
            ret_type = frame.data["return_type"]
            self._pop_scope()
            self.call_depth -= 1
            frame.data["entered"] = False
            if isinstance(control, ReturnControl):
                if ret_type == VOID:
                    self._complete(None)
                    return None
                if control.value is None:
                    raise RuntimeC48Error(
                        "non-void function returned without value"
                    )
                self._complete(self._convert(control.value, ret_type))
                return None
            if control is not _NORMAL:
                raise RuntimeC48Error("loop control escaped C48 function")
            if ret_type == VOID:
                self._complete(None)
                return None
            raise RuntimeExit(1)
        raise RuntimeC48Error("invalid multitask call continuation state")

    def _step_compound(self, frame: Frame) -> VMEvent | None:
        node = frame.node
        if frame.pc == 0:
            reuse = bool(frame.data.get("reuse_scope"))
            frame.data["reuse_scope"] = reuse
            if not reuse:
                self._push_scope()
            frame.data["decl_index"] = 0
            frame.data["idecl_index"] = 0
            frame.data["stmt_index"] = 0
            frame.pc = 1

        if frame.pc == 2:
            self._take()
            frame.pc = 1

        if frame.pc == 3:
            control = self._take()
            if control is not _NORMAL:
                if not frame.data["reuse_scope"]:
                    self._pop_scope()
                self._complete(control)
                return None
            frame.pc = 1

        if frame.pc == 1:
            declarations = node["declarations"]
            while frame.data["decl_index"] < len(declarations):
                decl = declarations[frame.data["decl_index"]]
                idecls = decl["declarators"]
                if frame.data["idecl_index"] >= len(idecls):
                    frame.data["decl_index"] += 1
                    frame.data["idecl_index"] = 0
                    continue
                idecl = idecls[frame.data["idecl_index"]]
                frame.data["idecl_index"] += 1
                ctype = CType.from_dict(idecl["ctype"])
                lv = self._allocate_local(
                    idecl["declarator"]["name"],
                    ctype,
                )
                init = idecl.get("initializer")
                if init is None:
                    continue
                frame.pc = 2
                self._push("init", init, lvalue=lv)
                return None

            statements = node["statements"]
            if frame.data["stmt_index"] < len(statements):
                stmt = statements[frame.data["stmt_index"]]
                frame.data["stmt_index"] += 1
                frame.pc = 3
                self._push("stmt", stmt)
                return None

            if not frame.data["reuse_scope"]:
                self._pop_scope()
            self._complete(_NORMAL)
            return None
        raise RuntimeC48Error("invalid multitask compound continuation state")

    def _step_init(self, frame: Frame) -> VMEvent | None:
        lv: LValue = frame.data["lvalue"]
        init = frame.node
        ctype = lv.ctype
        if frame.pc == 0:
            if not ctype.is_array:
                frame.pc = 1
                self._push("expr", init["value"])
                return None
            assert ctype.base is not None and ctype.length is not None
            allocation = self.mem.allocation(lv.pointer.aid)
            if allocation is None:
                raise RuntimeC48Error("initializer storage is not live")
            self.mem.ram[allocation.start:allocation.end] = b"\0" * allocation.size
            self.mem.init[allocation.start:allocation.end] = b"\x01" * allocation.size
            if init["kind"] == "string_initializer":
                data = bytes(init["value"]["bytes"]) + b"\0"
                for i, byte in enumerate(data):
                    self.mem.store_integer(
                        allocation.start + i * ctype.base.size,
                        ctype.base,
                        byte,
                    )
                self._complete(None)
                return None
            if init["kind"] != "init_list":
                raise RuntimeC48Error("invalid array initializer")
            frame.data["index"] = 0
            frame.pc = 2

        if frame.pc == 1:
            value = self._take()
            self._store(lv, self._convert(value, ctype))
            self._complete(None)
            return None

        if frame.pc == 3:
            value = self._take()
            allocation = self.mem.allocation(lv.pointer.aid)
            if allocation is None or ctype.base is None:
                raise RuntimeC48Error("initializer storage is not live")
            index = frame.data["index"]
            elv = LValue(
                ctype.base,
                PointerRecord(
                    allocation.start + index * ctype.base.size,
                    allocation.aid,
                    index * ctype.base.size,
                ),
            )
            self._store(elv, self._convert(value, ctype.base))
            frame.data["index"] += 1
            frame.pc = 2

        if frame.pc == 2:
            values = init["values"]
            index = frame.data["index"]
            if index >= len(values):
                self._complete(None)
                return None
            frame.pc = 3
            self._push("expr", values[index])
            return None
        raise RuntimeC48Error("invalid multitask initializer continuation state")

    def _step_stmt(self, frame: Frame) -> VMEvent | None:
        node = frame.node
        kind = node["kind"]
        if frame.pc == 0:
            self._charge_step()
            if kind == "compound":
                frame.pc = 1
                self._push("compound", node, reuse_scope=False)
                return None
            if kind == "expr_stmt":
                if node["value"] is None:
                    self._complete(_NORMAL)
                    return None
                frame.pc = 1
                self._push("expr", node["value"])
                return None
            if kind == "if":
                frame.pc = 10
                self._push("expr", node["condition"])
                return None
            if kind == "while":
                frame.pc = 20
                self._push("expr", node["condition"])
                return None
            if kind == "do_while":
                frame.pc = 30
                self._push("stmt", node["body"])
                return None
            if kind == "for":
                if node["init"] is None:
                    frame.pc = 41
                    return None
                frame.pc = 40
                self._push("expr", node["init"])
                return None
            if kind == "break":
                self._complete(_BREAK)
                return None
            if kind == "continue":
                self._complete(_CONTINUE)
                return None
            if kind == "return":
                if node["value"] is None:
                    self._complete(ReturnControl(None))
                    return None
                frame.pc = 50
                self._push("expr", node["value"])
                return None
            raise RuntimeC48Error(f"unknown statement {kind}")

        if kind in {"compound", "expr_stmt"} and frame.pc == 1:
            result = self._take()
            if kind == "expr_stmt":
                self._complete(_NORMAL)
            else:
                self._complete(result)
            return None

        if kind == "if":
            if frame.pc == 10:
                condition = self._take()
                branch = node["then"] if self._truth(condition) else node["otherwise"]
                if branch is None:
                    self._complete(_NORMAL)
                    return None
                frame.pc = 11
                self._push("stmt", branch)
                return None
            if frame.pc == 11:
                self._complete(self._take())
                return None

        if kind == "while":
            if frame.pc == 20:
                condition = self._take()
                if not self._truth(condition):
                    self._complete(_NORMAL)
                    return None
                frame.pc = 21
                self._push("stmt", node["body"])
                return None
            if frame.pc == 21:
                control = self._take()
                if isinstance(control, ReturnControl):
                    self._complete(control)
                    return None
                if control is _BREAK:
                    self._complete(_NORMAL)
                    return None
                if control not in {_NORMAL, _CONTINUE}:
                    raise RuntimeC48Error("invalid while-loop control")
                frame.pc = 20
                self._push("expr", node["condition"])
                return None

        if kind == "do_while":
            if frame.pc == 30:
                control = self._take()
                if isinstance(control, ReturnControl):
                    self._complete(control)
                    return None
                if control is _BREAK:
                    self._complete(_NORMAL)
                    return None
                if control not in {_NORMAL, _CONTINUE}:
                    raise RuntimeC48Error("invalid do-loop control")
                frame.pc = 31
                self._push("expr", node["condition"])
                return None
            if frame.pc == 31:
                condition = self._take()
                if self._truth(condition):
                    frame.pc = 30
                    self._push("stmt", node["body"])
                    return None
                self._complete(_NORMAL)
                return None

        if kind == "for":
            if frame.pc == 40:
                self._take()
                frame.pc = 41
            if frame.pc == 41:
                if node["condition"] is None:
                    frame.pc = 43
                    self._push("stmt", node["body"])
                    return None
                frame.pc = 42
                self._push("expr", node["condition"])
                return None
            if frame.pc == 42:
                condition = self._take()
                if not self._truth(condition):
                    self._complete(_NORMAL)
                    return None
                frame.pc = 43
                self._push("stmt", node["body"])
                return None
            if frame.pc == 43:
                control = self._take()
                if isinstance(control, ReturnControl):
                    self._complete(control)
                    return None
                if control is _BREAK:
                    self._complete(_NORMAL)
                    return None
                if control not in {_NORMAL, _CONTINUE}:
                    raise RuntimeC48Error("invalid for-loop control")
                if node["step"] is None:
                    frame.pc = 41
                    return None
                frame.pc = 44
                self._push("expr", node["step"])
                return None
            if frame.pc == 44:
                self._take()
                frame.pc = 41
                return None

        if kind == "return" and frame.pc == 50:
            self._complete(ReturnControl(self._take()))
            return None
        raise RuntimeC48Error("invalid multitask statement continuation state")

    def _step_lvalue(self, frame: Frame) -> VMEvent | None:
        node = frame.node
        kind = node["kind"]
        if frame.pc == 0:
            if kind == "identifier":
                self._complete(self._lookup_lv(node["name"]))
                return None
            if kind == "unary" and node["op"] == "*":
                frame.pc = 1
                self._push("expr", node["operand"])
                return None
            if kind == "index":
                frame.pc = 2
                self._push("expr", node["base"])
                return None
            raise RuntimeC48Error("expression is not an lvalue")
        if kind == "unary" and frame.pc == 1:
            value = self._take()
            pointer = self._as_pointer(value)
            ctype = CType.from_dict(node["ctype"])
            self.mem.check_access(pointer, ctype)
            allocation = self.mem.allocation(pointer.aid)
            self._complete(
                LValue(
                    ctype,
                    pointer,
                    bool(allocation.readonly if allocation else False),
                )
            )
            return None
        if kind == "index":
            if frame.pc == 2:
                frame.data["base"] = self._take()
                frame.pc = 3
                self._push("expr", node["index"])
                return None
            if frame.pc == 3:
                base: Value = frame.data["base"]
                index: Value = self._take()
                pointer = self._as_pointer(base)
                base_type = base.ctype.base
                if base_type is None:
                    raise RuntimeC48Error("index on incomplete pointer")
                shifted = self._pointer_shift(
                    pointer,
                    self._int_math(index) * base_type.size,
                )
                self.mem.check_access(shifted, base_type)
                allocation = self.mem.allocation(shifted.aid)
                self._complete(
                    LValue(
                        base_type,
                        shifted,
                        bool(allocation.readonly if allocation else False),
                    )
                )
                return None
        raise RuntimeC48Error("invalid multitask lvalue continuation state")

    def _step_expr(self, frame: Frame) -> VMEvent | None:
        node = frame.node
        kind = node["kind"]

        if frame.pc == 90:
            if "resume_value" not in frame.data:
                raise RuntimeC48Error("multitask scheduling boundary resumed without value")
            value = int(frame.data.pop("resume_value"))
            boundary = frame.data["boundary"]
            if boundary == "input":
                self._complete(Value(INT, value))
            else:
                self._complete(Value(INT, 0))
            return None

        if frame.pc == 0:
            self._charge_step()
            if kind == "identifier":
                if node.get("entity") == "function":
                    raise RuntimeC48Error("function designator used as value")
                lv = self._lookup_lv(node["name"])
                if lv.ctype.is_array:
                    assert lv.ctype.base is not None
                    self._complete(Value(ptr(lv.ctype.base), lv.pointer))
                else:
                    self._complete(self._load(lv))
                return None
            if kind == "integer_literal":
                ctype = CType.from_dict(node["ctype"])
                self._complete(
                    Value(ctype, self._norm_int(int(node["value"]), ctype))
                )
                return None
            if kind == "character_literal":
                self._complete(Value(INT, int(node["value"])))
                return None
            if kind == "floating_literal":
                self._complete(
                    Value(FLOAT, Float5(bytes.fromhex(node["float5"])))
                )
                return None
            if kind == "string_literal":
                sid = int(node["sid"])
                allocation = self.string_allocs.get(sid)
                if allocation is None:
                    data = bytes(node["bytes"]) + b"\0"
                    ctype = CType("array", base=CHAR, length=len(data))
                    allocation = self.mem.allocate(
                        len(data),
                        1,
                        ctype,
                        "string",
                        zero=True,
                        readonly=False,
                    )
                    self.mem.write_bytes(allocation.start, data)
                    allocation.readonly = True
                    self.string_allocs[sid] = allocation
                self._complete(
                    Value(ptr(CHAR), self.mem.pointer_for(allocation))
                )
                return None
            if kind in {"sizeof_type", "sizeof_expr"}:
                self._complete(Value(UINT, int(node["sizeof_value"])))
                return None
            if kind == "cast":
                frame.pc = 1
                self._push("expr", node["operand"])
                return None
            if kind == "assign":
                frame.pc = 10
                self._push("lvalue", node["left"])
                return None
            if kind in {"unary", "postfix"}:
                op = node["op"]
                if op == "&":
                    frame.pc = 20
                    self._push("lvalue", node["operand"])
                    return None
                if op == "*":
                    frame.pc = 21
                    self._push("lvalue", node)
                    return None
                if op in {"++", "--"} or kind == "postfix":
                    frame.pc = 22
                    self._push("lvalue", node["operand"])
                    return None
                frame.pc = 23
                self._push("expr", node["operand"])
                return None
            if kind == "index":
                frame.pc = 30
                self._push("lvalue", node)
                return None
            if kind == "call":
                frame.data["args"] = []
                frame.data["arg_index"] = 0
                frame.pc = 40
                return None
            if kind == "binary":
                frame.pc = 50
                self._push("expr", node["left"])
                return None
            raise RuntimeC48Error(f"unknown expression {kind}")

        if kind == "cast" and frame.pc == 1:
            self._complete(
                self._convert(self._take(), CType.from_dict(node["ctype"]))
            )
            return None

        if kind == "assign":
            if frame.pc == 10:
                frame.data["lvalue"] = self._take()
                frame.pc = 11
                self._push("expr", node["right"])
                return None
            if frame.pc == 11:
                lv: LValue = frame.data["lvalue"]
                value = self._convert(self._take(), lv.ctype)
                self._store(lv, value)
                self._complete(value)
                return None

        if kind in {"unary", "postfix"}:
            op = node["op"]
            if frame.pc == 20:
                lv: LValue = self._take()
                self._complete(
                    Value(CType.from_dict(node["ctype"]), lv.pointer)
                )
                return None
            if frame.pc == 21:
                self._complete(self._load(self._take()))
                return None
            if frame.pc == 22:
                lv = self._take()
                old = self._load(lv)
                new = self._inc(old, 1 if op == "++" else -1)
                self._store(lv, new)
                self._complete(old if kind == "postfix" else new)
                return None
            if frame.pc == 23:
                value = self._take()
                result_type = CType.from_dict(node["ctype"])
                if op == "!":
                    self._complete(Value(INT, 0 if self._truth(value) else 1))
                    return None
                if op == "+":
                    self._complete(self._convert(value, result_type))
                    return None
                if op == "-":
                    value = self._convert(value, result_type)
                    if result_type.is_float:
                        try:
                            assert isinstance(value.data, Float5)
                            self._complete(Value(FLOAT, value.data.neg()))
                            return None
                        except Float5Error:
                            raise RuntimeExit(1)
                    self._complete(
                        Value(
                            result_type,
                            self._norm_int(
                                -self._int_math(value),
                                result_type,
                            ),
                        )
                    )
                    return None
                if op == "~":
                    value = self._convert(value, result_type)
                    self._complete(
                        Value(
                            result_type,
                            self._norm_int(
                                ~self._int_math(value),
                                result_type,
                            ),
                        )
                    )
                    return None
                raise RuntimeC48Error(f"unknown unary {op}")

        if kind == "index" and frame.pc == 30:
            self._complete(self._load(self._take()))
            return None

        if kind == "call":
            return self._step_call_expr(frame)

        if kind == "binary":
            if frame.pc == 50:
                left = self._take()
                frame.data["left"] = left
                op = node["op"]
                if op == "&&" and not self._truth(left):
                    self._complete(Value(INT, 0))
                    return None
                if op == "||" and self._truth(left):
                    self._complete(Value(INT, 1))
                    return None
                frame.pc = 51
                self._push("expr", node["right"])
                return None
            if frame.pc == 51:
                left = frame.data["left"]
                right = self._take()
                op = node["op"]
                if op == "&&":
                    self._complete(Value(INT, 1 if self._truth(right) else 0))
                    return None
                if op == "||":
                    self._complete(Value(INT, 1 if self._truth(right) else 0))
                    return None
                self._complete(
                    self._binary_values(
                        op,
                        left,
                        right,
                        CType.from_dict(node["ctype"]),
                    )
                )
                return None
        raise RuntimeC48Error("invalid multitask expression continuation state")

    def _step_call_expr(self, frame: Frame) -> VMEvent | None:
        node = frame.node
        ft = CType.from_dict(node["function"]["ctype"])
        params = ft.params or ()
        args_nodes = node["args"]
        if len(args_nodes) != len(params):
            raise RuntimeC48Error("internal argument-count mismatch")

        if frame.pc == 90:
            if "resume_value" not in frame.data:
                raise RuntimeC48Error(
                    "multitask scheduler boundary resumed without a value"
                )
            value = int(frame.data.pop("resume_value"))
            frame.data.pop("boundary", None)
            self._complete(Value(INT, value))
            return None

        if frame.pc == 41:
            index = frame.data["arg_index"]
            value = self._take()
            frame.data["args"].append(self._convert(value, params[index]))
            frame.data["arg_index"] += 1
            frame.pc = 40

        if frame.pc == 42:
            rv = self._take()
            if rv is None:
                if CType.from_dict(node["ctype"]) == VOID:
                    self._complete(Value(VOID, None))
                    return None
                raise RuntimeC48Error("function returned no value")
            self._complete(rv)
            return None

        if frame.pc == 40:
            index = frame.data["arg_index"]
            if index < len(args_nodes):
                frame.pc = 41
                self._push("expr", args_nodes[index])
                return None

            name = node["function"]["name"]
            args = list(frame.data["args"])
            if name in self.functions:
                frame.pc = 42
                self._push("call", name=name, args=args)
                return None
            if name in {"spawn", "wait", "kill"}:
                raise RuntimeC48Error(
                    f"{name} is unsupported in c48run multitask sessions"
                )
            if name == "getpid":
                self._complete(Value(INT, self.pid))
                return None
            if name == "yield":
                self.display_update()
                frame.pc = 90
                frame.data["boundary"] = "yield"
                return VMEvent("yield")
            if name == "sleep":
                ticks = self._to_unsigned(args[0])
                if ticks == 0:
                    self._complete(Value(INT, 0))
                    return None
                self.display_update()
                frame.pc = 90
                frame.data["boundary"] = "sleep"
                return VMEvent("sleep", ticks)
            if name == "getchar":
                self.display_update()
                frame.pc = 90
                frame.data["boundary"] = "input"
                return VMEvent("input")
            rv = self._call_builtin(name, args)
            if rv is None:
                if CType.from_dict(node["ctype"]) == VOID:
                    self._complete(Value(VOID, None))
                    return None
                raise RuntimeC48Error("function returned no value")
            self._complete(rv)
            return None
        raise RuntimeC48Error("invalid multitask call-expression state")

    def _binary_values(
        self,
        op: str,
        left: Value,
        right: Value,
        result_type: CType,
    ) -> Value:
        if op in {"<<", ">>"}:
            count = self._int_math(right) & (7 if left.ctype.bits == 8 else 15)
            av = self._int_math(left)
            if op == "<<":
                value = av << count
            elif left.ctype.is_signed:
                value = av >> count
            else:
                value = (av & ((1 << left.ctype.bits) - 1)) >> count
            return Value(result_type, self._norm_int(value, result_type))

        if left.ctype.is_pointer or right.ctype.is_pointer:
            return self._pointer_binary(op, left, right, result_type)

        common = arithmetic_common(left.ctype, right.ctype)
        a = self._convert(left, common)
        b = self._convert(right, common)
        if common.is_float:
            fa, fb = a.data, b.data
            assert isinstance(fa, Float5) and isinstance(fb, Float5)
            try:
                if op == "+":
                    return Value(FLOAT, fa.add(fb))
                if op == "-":
                    return Value(FLOAT, fa.sub(fb))
                if op == "*":
                    return Value(FLOAT, fa.mul(fb))
                if op == "/":
                    return Value(FLOAT, fa.div(fb))
                comparison = fa.compare(fb)
                ok = {
                    "==": comparison == 0,
                    "!=": comparison != 0,
                    "<": comparison < 0,
                    "<=": comparison <= 0,
                    ">": comparison > 0,
                    ">=": comparison >= 0,
                }[op]
                return Value(INT, int(ok))
            except Float5Error:
                raise RuntimeExit(1)

        av = self._int_math(a)
        bv = self._int_math(b)
        if op == "+":
            value = av + bv
        elif op == "-":
            value = av - bv
        elif op == "*":
            value = av * bv
        elif op in {"/", "%"}:
            if bv == 0:
                raise RuntimeExit(1)
            if common.is_signed:
                quotient = abs(av) // abs(bv)
                if (av < 0) ^ (bv < 0):
                    quotient = -quotient
            else:
                quotient = (av & 0xFFFF) // (bv & 0xFFFF)
            value = quotient if op == "/" else av - quotient * bv
        elif op == "&":
            value = (av & 0xFFFF) & (bv & 0xFFFF)
        elif op == "|":
            value = (av & 0xFFFF) | (bv & 0xFFFF)
        elif op == "^":
            value = (av & 0xFFFF) ^ (bv & 0xFFFF)
        elif op in {"==", "!=", "<", "<=", ">", ">="}:
            ok = {
                "==": av == bv,
                "!=": av != bv,
                "<": av < bv,
                "<=": av <= bv,
                ">": av > bv,
                ">=": av >= bv,
            }[op]
            return Value(INT, int(ok))
        else:
            raise RuntimeC48Error(f"unknown binary op {op}")
        return Value(result_type, self._norm_int(value, result_type))


class CooperativeSession:
    """Eight-slot cooperative process session with PID0/PID1 reserved."""

    def __init__(
        self,
        programs: list[dict[str, Any]],
        program_tokens: list[str],
        screen,
        *,
        approximate_rom_math: bool = False,
        heap_size: int = 1024,
        max_steps: int | None = None,
        time_quota: float = 0.0,
        tick_provider: Callable[[], int] | None = None,
        input_poll: Callable[[int], int | None] | None = None,
        idle_wait: Callable[[int | None], None] | None = None,
        display_update: Callable[[], None] | None = None,
        display_present: Callable[[str], None] | None = None,
        abort_requested: Callable[[], bool] | None = None,
        sound_player=None,
    ):
        if not programs:
            raise RuntimeC48Error("multitask mode requires at least one program")
        if len(programs) > 6:
            raise RuntimeC48Error("multitask mode supports at most six programs")
        if len(programs) != len(program_tokens):
            raise RuntimeC48Error("multitask program metadata mismatch")
        self.screen = screen
        self._tick_provider = tick_provider or (
            lambda: int(time.monotonic_ns() // 20000000)
        )
        self._input_poll = input_poll
        self._idle_wait = idle_wait or self._default_idle_wait
        self._display_update = display_update or (lambda: None)
        self._display_present = display_present or (lambda _reason: None)
        self.budget = SessionBudget(
            max_steps=max_steps,
            time_quota=time_quota,
            abort_requested=abort_requested,
        )
        self.descriptors = [
            ProcessDescriptor(pid=i) for i in range(8)
        ]
        self.descriptors[0].state = READY
        self.descriptors[0].parent = None
        self.descriptors[1].state = WAIT_CHILD
        self.descriptors[1].parent = 0
        self.trace: list[tuple[Any, ...]] = []
        self.last_pid = 1
        self._last_tick: int | None = None
        self.input_owner: int | None = None

        for offset, (program, token) in enumerate(
            zip(programs, program_tokens),
            2,
        ):
            descriptor = self.descriptors[offset]
            descriptor.state = READY
            descriptor.parent = 1
            descriptor.vm = ResumableRomMathVM(
                program,
                screen,
                pid=offset,
                charge_step=self.budget.charge,
                argv=[token],
                approximate_rom_math=approximate_rom_math,
                heap_size=heap_size,
                tick_provider=lambda: self._now() & 0xFFFF,
                display_update=self._display_update,
                display_present=self._display_present,
                sound_player=sound_player,
            )
        self._user_pids = list(range(2, 2 + len(programs)))

    def _now(self) -> int:
        value = int(self._tick_provider())
        if value < 0:
            raise RuntimeC48Error("session tick provider returned a negative value")
        if self._last_tick is not None and value < self._last_tick:
            raise RuntimeC48Error("session tick provider moved backwards")
        self._last_tick = value
        return value

    def _default_idle_wait(self, next_wake: int | None) -> None:
        if next_wake is None:
            time.sleep(0.01)
            return
        remaining = max(0, next_wake - self._now())
        time.sleep(min(0.02, max(0.001, remaining / 50.0)))

    def _next_ready(self) -> int | None:
        for delta in range(1, 7):
            pid = 2 + ((self.last_pid - 2 + delta) % 6)
            if pid in self._user_pids and self.descriptors[pid].state == READY:
                return pid
        return None

    def _wake_sleepers(self) -> None:
        now = self._now()
        for pid in self._user_pids:
            descriptor = self.descriptors[pid]
            if (
                descriptor.state == SLEEPING
                and descriptor.wake_tick is not None
                and now >= descriptor.wake_tick
            ):
                descriptor.wake_tick = None
                descriptor.resume_value = 0
                descriptor.state = READY
                self.trace.append(("wake", pid, now))

    def _choose_input_owner(self) -> None:
        if self.input_owner is not None:
            descriptor = self.descriptors[self.input_owner]
            if descriptor.state == WAIT_INPUT:
                return
            self.input_owner = None
        waiters = [
            pid for pid in self._user_pids
            if self.descriptors[pid].state == WAIT_INPUT
        ]
        if waiters:
            self.input_owner = min(waiters)

    def _service_input(self) -> None:
        self._choose_input_owner()
        if self.input_owner is None or self._input_poll is None:
            return
        value = self._input_poll(self.input_owner)
        if value is None:
            return
        descriptor = self.descriptors[self.input_owner]
        byte = int(value)
        if byte < -1 or byte > 255:
            raise RuntimeC48Error("session input provider returned invalid byte")
        descriptor.resume_value = byte
        descriptor.state = READY
        self.trace.append(("input", self.input_owner, byte))
        self.input_owner = None

    def _mark_failure(self, descriptor: ProcessDescriptor, exc: BaseException) -> None:
        descriptor.exit_status = 1
        descriptor.error = str(exc)
        descriptor.state = ZOMBIE
        descriptor.wake_tick = None
        descriptor.resume_value = _NO_RESULT
        if descriptor.vm is not None:
            descriptor.vm.cancel_cleanup()
        self.trace.append(("error", descriptor.pid, type(exc).__name__))

    def _abort_all(self, status: int, reason: str) -> int:
        for pid in self._user_pids:
            descriptor = self.descriptors[pid]
            if descriptor.state != ZOMBIE:
                descriptor.cancelled = True
                descriptor.exit_status = status & 0xFF
                descriptor.error = reason
                descriptor.state = ZOMBIE
                descriptor.wake_tick = None
                descriptor.resume_value = _NO_RESULT
                if descriptor.vm is not None:
                    descriptor.vm.cancel_cleanup()
        self.descriptors[0].state = READY
        self.descriptors[1].state = RUNNING
        self.trace.append(("session_stop", status & 0xFF))
        return status & 0xFF

    def _all_terminal(self) -> bool:
        return all(
            self.descriptors[pid].state == ZOMBIE
            for pid in self._user_pids
        )

    def _session_status(self) -> int:
        for pid in self._user_pids:
            status = self.descriptors[pid].exit_status
            if status not in {None, 0}:
                return int(status) & 0xFF
        return 0

    def run(self) -> int:
        self.budget.start()
        while not self._all_terminal():
            descriptor: ProcessDescriptor | None = None
            try:
                self.budget.check()
                self._wake_sleepers()
                self._service_input()
                pid = self._next_ready()
                if pid is None:
                    next_wake = min(
                        (
                            d.wake_tick
                            for d in (
                                self.descriptors[p] for p in self._user_pids
                            )
                            if d.state == SLEEPING and d.wake_tick is not None
                        ),
                        default=None,
                    )
                    self.descriptors[0].state = RUNNING
                    self.trace.append(("idle", self._now()))
                    self._idle_wait(next_wake)
                    self.descriptors[0].state = READY
                    continue

                descriptor = self.descriptors[pid]
                vm = descriptor.vm
                if vm is None:
                    raise RuntimeC48Error("runnable process has no VM")
                descriptor.state = RUNNING
                self.last_pid = pid
                self.trace.append(("dispatch", pid))
                resume_value = descriptor.resume_value
                descriptor.resume_value = _NO_RESULT
                event = vm.resume(resume_value)
                vm.assert_invariants()

                if event.kind == "yield":
                    self._display_present("yield")
                    descriptor.resume_value = 0
                    descriptor.state = READY
                    self.trace.append(("yield", pid))
                elif event.kind == "sleep":
                    self._display_present("sleep")
                    now = self._now()
                    descriptor.wake_tick = now + event.value
                    descriptor.state = SLEEPING
                    self.trace.append(
                        ("sleep", pid, event.value, descriptor.wake_tick)
                    )
                elif event.kind == "input":
                    self._display_present("input")
                    if self._input_poll is None:
                        self._mark_failure(
                            descriptor,
                            RuntimeC48Error(
                                "multitask headless input requires an injected event source"
                            ),
                        )
                    else:
                        descriptor.state = WAIT_INPUT
                        self.trace.append(("input_wait", pid))
                        if self.input_owner is None:
                            self.input_owner = pid
                elif event.kind == "exit":
                    descriptor.exit_status = event.value & 0xFF
                    descriptor.state = ZOMBIE
                    descriptor.wake_tick = None
                    self.trace.append(("exit", pid, descriptor.exit_status))
                else:
                    raise RuntimeC48Error(
                        f"unknown multitask scheduling event {event.kind!r}"
                    )
            except SessionAbort as exc:
                return self._abort_all(130, str(exc))
            except SessionLimitError as exc:
                return self._abort_all(1, str(exc))
            except RuntimeC48Error as exc:
                if descriptor is not None and descriptor.state == RUNNING:
                    self._mark_failure(descriptor, exc)
                else:
                    return self._abort_all(1, str(exc))
            except (MemoryError, RecursionError) as exc:
                if descriptor is not None and descriptor.state == RUNNING:
                    self._mark_failure(descriptor, exc)
                else:
                    return self._abort_all(1, str(exc))

        self.descriptors[1].state = RUNNING
        self._display_update()
        status = self._session_status()
        self.trace.append(("session_exit", status))
        return status
