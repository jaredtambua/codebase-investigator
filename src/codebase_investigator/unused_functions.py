"""Find potentially unused direct module-level functions without execution."""

import ast
from dataclasses import dataclass
from pathlib import Path
import tokenize

from codebase_investigator.analysis import FunctionInfo
from codebase_investigator.discovery import discover_python_files


@dataclass(frozen=True)
class UnusedFunction:
    """A candidate definition with its root-relative source path."""

    path: Path
    function: FunctionInfo


def _referenced_names(tree: ast.Module) -> set[str]:
    """Collect possible references conservatively across all lexical scopes."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            names.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
    return names


def find_unused_functions(root: str | Path) -> tuple[UnusedFunction, ...]:
    """Return direct module-level definitions with no possible static reference.

    Match names conservatively across every discovered Python file, including
    tests. Loaded names and attributes count as usage, as do from-imported names
    even when unused or aliased. A wildcard import suppresses all candidates.
    Plain module imports alone do not reference their functions.

    No binding, type or reachability resolution is attempted: unrelated objects
    sharing a name can hide unused functions. Self-references count as usage.
    Decorated functions and literal names in a module's __all__ are retained as
    possible registrations or exports. External callers and dynamic references
    cannot be detected, so results are candidates, not proof of dead code.

    Results follow discovery order then definition order, preserving duplicates.
    Reuse discovery exclusions and propagate file, decoding and syntax errors.
    Source code is never executed. Methods, nested functions and definitions
    inside module control-flow blocks are not candidates.
    """
    root = Path(root)
    candidates = []
    referenced = set()
    for path in discover_python_files(root):
        with tokenize.open(root / path) as source:
            tree = ast.parse(source.read(), filename=str(root / path))
        referenced.update(_referenced_names(tree))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.decorator_list:
                    referenced.add(node.name)
                candidates.append(UnusedFunction(
                    path,
                    FunctionInfo(node.name, node.lineno, isinstance(node, ast.AsyncFunctionDef)),
                ))
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if node.value is not None and any(
                    isinstance(target, ast.Name) and target.id == "__all__"
                    for target in targets
                ):
                    referenced.update(
                        item.value for item in ast.walk(node.value)
                        if isinstance(item, ast.Constant) and isinstance(item.value, str)
                    )
    if "*" in referenced:
        return ()
    return tuple(item for item in candidates if item.function.name not in referenced)
