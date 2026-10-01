"""Select a bounded reading set for a concrete Python change target."""

import builtins
from dataclasses import dataclass
from pathlib import Path

from codebase_investigator.references import Reference, collect_references
from codebase_investigator.symbols import CodebaseIndex, Symbol, index_codebase


@dataclass(frozen=True)
class ReadingItem:
    symbol: Symbol
    category: str
    reason: str
    evidence: tuple[Reference, ...]


@dataclass(frozen=True)
class ReadingGuide:
    targets: tuple[Symbol, ...]
    ambiguous: bool
    items: tuple[ReadingItem, ...]
    unresolved: tuple[Reference, ...]
    omitted_items: int
    omitted_unresolved: int
    limitations: tuple[str, ...]


def _select(index: CodebaseIndex, target: str) -> tuple[Symbol, ...]:
    modules = {file.path.as_posix(): file.module for file in index.files}
    target = target.replace("\\", "/")
    if target in modules:
        return (modules[target],)
    if ":" in target:
        path, selector = target.rsplit(":", 1)
        if selector.isdecimal() and path in modules:
            line = int(selector)
            matches = [s for s in index.symbols if s.path.as_posix() == path
                       and s.start_lineno <= line <= s.end_lineno]
            if matches:
                depth = max(s.qualified_name.count(".") for s in matches)
                return tuple(s for s in matches if s.qualified_name.count(".") == depth)
            module = modules[path]
            return (module,) if 1 <= line <= module.end_lineno else ()
        return tuple(s for s in index.symbols if s.path.as_posix() == path and s.qualified_name == selector)
    return tuple(s for s in index.symbols if s.qualified_name == target or
                 s.qualified_name.rsplit(".", 1)[-1] == target)


def _is_test(symbol: Symbol) -> bool:
    return "tests" in symbol.path.parts or symbol.path.name.startswith("test_") or symbol.path.stem.endswith("_test")


def build_reading_guide(
    root: str | Path, target: str, *, import_roots: tuple[str | Path, ...] = (".",),
    limit: int = 20,
) -> ReadingGuide:
    """Return implementation, tests, dependencies and consumers with evidence.

    Select a repository-relative file, file:line, file:qualified_name or symbol
    name. Ambiguous names return choices and no reading items. Related items and
    unresolved evidence are each capped at limit, with omitted counts. Expansion
    is explicit: request another target or raise the limit. No source is executed.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    index = index_codebase(root, import_roots=import_roots)
    targets = _select(index, target)
    if not targets:
        raise ValueError(f"Target not found: {target}")
    limitations = (
        "Static links are evidence of references, not runtime reachability or complete impact.",
        "Dynamic dispatch, re-exports, external callers and runtime imports are not resolved.",
        "Related tests are selected by source references and test paths, not measured coverage.",
        "Reassigned or ambiguous bindings remain unresolved; conditional definitions may not execute.",
    )
    if len(targets) != 1:
        return ReadingGuide(targets, True, (), (), 0, 0, limitations)
    selected = targets[0]
    references = collect_references(index)
    grouped: dict[tuple[Symbol, str], list[Reference]] = {}

    def add(symbol, category, reference=None):
        if symbol == selected:
            return
        evidence = grouped.setdefault((symbol, category), [])
        if reference is not None and reference not in evidence:
            evidence.append(reference)

    def inside(symbol):
        if symbol.path != selected.path:
            return False
        if selected.kind == "module":
            return True
        return symbol == selected or (
            symbol.kind != "module"
            and symbol.qualified_name.startswith(selected.qualified_name + ".")
            and selected.start_lineno <= symbol.lineno <= selected.end_lineno
        )

    # Include the enclosing definition for a method or nested target.
    containers = [s for s in index.symbols if s.path == selected.path and s != selected
                  and s.start_lineno <= selected.start_lineno and s.end_lineno >= selected.end_lineno]
    if containers:
        add(max(containers, key=lambda s: s.qualified_name.count(".")), "context")
    unresolved = []
    for reference in references:
        source_inside = inside(reference.owner)
        target_inside = reference.target is not None and inside(reference.target)
        if reference.status == "resolved":
            if source_inside and not target_inside:
                add(reference.target, "dependency", reference)
            if target_inside and not source_inside:
                add(reference.owner, "test" if _is_test(reference.owner) else "consumer", reference)
            # File-import evidence provides weaker context for a symbol target.
            if (selected.kind != "module" and reference.kind == "import"
                    and reference.target.kind == "module" and reference.target.path == selected.path
                    and not source_inside):
                add(reference.owner, "test" if _is_test(reference.owner) else "consumer", reference)
        elif source_inside or selected in reference.candidates or (
            selected.kind == "module" and any(c.path == selected.path for c in reference.candidates)
        ):
            if (reference.candidates or reference.kind == "import" or
                "." in reference.expression or
                (reference.kind == "call" and reference.expression not in vars(builtins))):
                unresolved.append(reference)
    priority = {"context": 0, "test": 1, "dependency": 2, "consumer": 3}
    reasons = {
        "context": "Enclosing definition supplies context for the target.",
        "test": "Related test source references the target or its module; inspect its assertions.",
        "dependency": "The target references this local definition or module.",
        "consumer": "This source references the target or imports its module; inspect how it is used.",
    }
    # Deduplicate locations: retain the highest-priority category and all evidence.
    ordered = sorted(grouped, key=lambda k: (priority[k[1]], k[0].path.as_posix(), k[0].lineno, k[0].qualified_name))
    items = []
    seen = set()
    for symbol, category in ordered:
        if symbol in seen:
            continue
        if symbol.kind == "module" and category in ("test", "consumer") and any(
            s.path == symbol.path and s.kind != "module" and c == category
            for s, c in grouped
        ):
            continue
        seen.add(symbol)
        evidence = tuple(dict.fromkeys(r for (s, _), refs in grouped.items() if s == symbol for r in refs))
        items.append(ReadingItem(symbol, category, reasons[category], evidence))
    # Reserve space across categories so numerous tests cannot hide dependencies.
    categories = [[item for item in items if item.category == name]
                  for name in priority]
    chosen = []
    for position in range(len(items)):
        for category in categories:
            if position < len(category) and len(chosen) < limit:
                chosen.append(category[position])
    chosen.sort(key=lambda item: (priority[item.category], item.symbol.path.as_posix(), item.symbol.lineno))
    return ReadingGuide(targets, False, tuple(chosen), tuple(unresolved[:limit]),
                        max(0, len(items) - limit), max(0, len(unresolved) - limit), limitations)
