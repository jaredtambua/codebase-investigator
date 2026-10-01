"""Render the reading guide through a small command-line interface."""

import argparse
from collections.abc import Sequence

from codebase_investigator.reading_guide import ReadingGuide, build_reading_guide
from codebase_investigator.symbols import Symbol


def _location(symbol: Symbol) -> str:
    return f"{symbol.path.as_posix()}:{symbol.lineno}"


def format_reading_guide(guide: ReadingGuide) -> str:
    """Render bounded source excerpts and explicit relationship evidence."""
    lines = []
    if guide.ambiguous:
        lines.append("Ambiguous target. Choose a file:line or file:qualified_name:")
        lines.extend(f"  {_location(s)}  {s.qualified_name}" for s in guide.targets)
        return "\n".join(lines)
    target = guide.targets[0]
    lines.extend([f"Understand first: {_location(target)}", target.signature])
    if target.docstring:
        lines.append(target.docstring.splitlines()[0])
    excerpt = target.source.splitlines()
    lines.extend(f"  {target.start_lineno + i}: {line}" for i, line in enumerate(excerpt[:12]))
    if len(excerpt) > 12:
        lines.append(f"  ... {len(excerpt) - 12} further source lines; open the definition.")
    for item in guide.items:
        lines.append(f"\n{item.category}: {_location(item.symbol)}  {item.symbol.signature}")
        lines.append(f"  {item.reason}")
        for reference in item.evidence[:3]:
            lines.append(f"  {reference.kind} at {reference.path.as_posix()}:{reference.lineno}: {reference.expression}")
        if len(item.evidence) > 3:
            lines.append(f"  ... {len(item.evidence) - 3} further evidence records.")
    if guide.omitted_items:
        lines.append(f"\n{guide.omitted_items} reading items omitted; increase --limit or investigate another target.")
    if guide.unresolved:
        lines.append("\nUnresolved or possible references (not definite relationships):")
        for reference in guide.unresolved:
            lines.append(f"  {reference.path.as_posix()}:{reference.lineno} {reference.expression}: {reference.reason}")
    if guide.omitted_unresolved:
        lines.append(f"  {guide.omitted_unresolved} further unresolved records omitted.")
    lines.append("\nLimitations:")
    lines.extend(f"  {limitation}" for limitation in guide.limitations)
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find the Python code to understand before modifying a target.")
    parser.add_argument("target", help="File, file:line, file:qualified_name or symbol name")
    parser.add_argument("--root", default=".", help="Repository directory (default: current directory)")
    parser.add_argument("--import-root", action="append", dest="import_roots",
                        help="Import directory relative to the repository; repeat for multiple roots")
    parser.add_argument("--limit", type=int, default=20, help="Maximum related items and unresolved records (default: 20)")
    args = parser.parse_args(argv)
    try:
        guide = build_reading_guide(args.root, args.target,
                                    import_roots=tuple(args.import_roots or ["."]), limit=args.limit)
    except (OSError, UnicodeError, SyntaxError, ValueError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
    print(format_reading_guide(guide))
    return 2 if guide.ambiguous else 0
