"""Combine Python file discovery with single-file static analysis."""

from pathlib import Path

from codebase_investigator.analysis import FileAnalysis, analyse_python_file
from codebase_investigator.discovery import discover_python_files


def analyse_directory(root: str | Path) -> dict[Path, FileAnalysis]:
    """Return analyses keyed by root-relative paths in discovery order.

    Reuse discovery's file selection and exclusions. Analyse each discovered
    file in sorted order, returning an empty dictionary if none are found.
    Discovery, file, decoding, and syntax errors propagate immediately rather
    than returning partial results. Source code is never executed.
    """
    root = Path(root)
    return {
        path: analyse_python_file(root / path)
        for path in discover_python_files(root)
    }
