"""Statically identify direct module-level Python definitions and imports."""

import ast
from dataclasses import dataclass
from pathlib import Path
import tokenize


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    lineno: int
    is_async: bool


@dataclass(frozen=True)
class ClassInfo:
    name: str
    lineno: int


@dataclass(frozen=True)
class ImportInfo:
    name: str
    alias: str | None
    module: str | None
    level: int
    lineno: int


@dataclass(frozen=True)
class FileAnalysis:
    functions: tuple[FunctionInfo, ...]
    classes: tuple[ClassInfo, ...]
    imports: tuple[ImportInfo, ...]


def analyse_python_file(path: str | Path) -> FileAnalysis:
    """Analyse direct module statements without executing source code.

    Results preserve source order within each category, including duplicates.
    Definitions and imports inside other statements are excluded. Line numbers
    are one-based and refer to definition headers or import statements.
    File, decoding, and syntax errors propagate to the caller. Supported syntax
    depends on the running Python interpreter.
    """
    with tokenize.open(path) as source:
        tree = ast.parse(source.read(), filename=str(path))

    functions = []
    classes = []
    imports = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(
                FunctionInfo(node.name, node.lineno, isinstance(node, ast.AsyncFunctionDef))
            )
        elif isinstance(node, ast.ClassDef):
            classes.append(ClassInfo(node.name, node.lineno))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            level = node.level if isinstance(node, ast.ImportFrom) else 0
            for name in node.names:
                imports.append(
                    ImportInfo(name.name, name.asname, module, level, node.lineno)
                )

    return FileAnalysis(tuple(functions), tuple(classes), tuple(imports))
