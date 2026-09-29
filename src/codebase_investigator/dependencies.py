"""Match direct Python imports to local files without executing source code."""

from dataclasses import dataclass
from pathlib import Path

from codebase_investigator.analysis import ImportInfo
from codebase_investigator.directory_analysis import analyse_directory


@dataclass(frozen=True)
class Dependency:
    """A local file relationship with its original import evidence."""

    source: Path
    target: Path
    imported: ImportInfo


def _module_index(paths: set[Path]) -> dict[tuple[str, ...], Path | None]:
    """Index module candidates, retaining collisions as unresolved entries."""
    index: dict[tuple[str, ...], Path | None] = {}
    for path in sorted(paths, key=lambda item: item.as_posix()):
        parts = path.parent.parts
        if any(Path(*parts[:depth], "__init__.py") not in paths
               for depth in range(1, len(parts) + 1)):
            continue
        name = parts if path.name == "__init__.py" else (*parts, path.stem)
        if not name or not all(part.isidentifier() for part in name):
            continue
        index[name] = None if name in index else path
    return index


def _module_target(
    name: tuple[str, ...], index: dict[tuple[str, ...], Path | None],
) -> Path | None:
    """Require a unique module and unambiguous regular package ancestors."""
    for depth in range(1, len(name)):
        parent = index.get(name[:depth])
        if parent is None or parent.name != "__init__.py":
            return None
    return index.get(name)


def _import_target(
    source: Path, imported: ImportInfo,
    index: dict[tuple[str, ...], Path | None],
) -> Path | None:
    if imported.module is None and imported.level == 0:
        return _module_target(tuple(imported.name.split(".")), index)

    base: tuple[str, ...] = ()
    if imported.level:
        package = source.parent.parts
        if imported.level > len(package):
            return None
        if _module_target(package, index) != source.parent / "__init__.py":
            return None
        base = package[:len(package) - imported.level + 1]
    if imported.module:
        base += tuple(imported.module.split("."))

    target = _module_target(base, index)
    if target is None:
        return None
    if target.name == "__init__.py" and imported.name != "*":
        child = (*base, imported.name)
        if child in index:
            return _module_target(child, index)
    return target


def analyse_dependencies(root: str | Path) -> tuple[Dependency, ...]:
    """Return local import relationships relative to an explicit import root.

    Reuse directory analysis and its exclusions, error handling and direct
    module-level import scope. Results follow sorted source paths and import
    order, preserving duplicates. Only ordinary modules and regular packages
    below the root are targets; namespace packages and collisions are skipped.

    For from-imports, prefer an existing child module of a package, otherwise
    use the named module or package. This is a structural file match, not
    runtime attribute resolution. No source or imported code is executed.
    """
    analyses = analyse_directory(root)
    index = _module_index(set(analyses))
    dependencies = []
    for source, analysis in analyses.items():
        for imported in analysis.imports:
            target = _import_target(source, imported, index)
            if target is not None:
                dependencies.append(Dependency(source, target, imported))
    return tuple(dependencies)
