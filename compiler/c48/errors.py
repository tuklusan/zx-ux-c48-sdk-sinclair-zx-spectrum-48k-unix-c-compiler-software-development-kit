# ZX-UX Unix ZX Spectrum 48K SDK © 2026 SANYALnet Labs supratim-sanyal.blogspot.com
#
# SANYALnet Labs Non-Commercial License, attribution to SANYALnet Labs required, see LICENSE for more information
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourcePos:
    source: str
    line: int
    column: int

    def format(self) -> str:
        return f"{self.source}:{self.line}:{self.column}"


class C48Error(Exception):
    category = "error"
    exit_status = 1

    def __init__(self, message: str, pos: SourcePos | None = None):
        super().__init__(message)
        self.message = message
        self.pos = pos

    def __str__(self) -> str:
        prefix = f"{self.pos.format()}: " if self.pos else ""
        return f"{prefix}{self.category}: {self.message}"


class UsageC48Error(C48Error):
    category = "usage"


class LexicalError(C48Error):
    category = "lexical"


class UnsupportedFeatureError(C48Error):
    category = "unsupported"


class PreprocessorError(C48Error):
    category = "preprocessing"


class SyntaxC48Error(C48Error):
    category = "syntax"


class TypeC48Error(C48Error):
    category = "type"


class DeclarationError(C48Error):
    category = "declaration"


class ConstantExpressionError(C48Error):
    category = "constant-expression"


class LiteralRangeError(C48Error):
    category = "literal-range"


class ResourceLimitError(C48Error):
    category = "resource-limit"


class IOC48Error(C48Error):
    category = "io"


class RuntimeC48Error(C48Error):
    category = "runtime error"


class RuntimeExit(Exception):
    def __init__(self, status: int):
        super().__init__(status)
        self.status = status & 0xFF
