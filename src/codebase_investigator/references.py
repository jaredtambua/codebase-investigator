"""Collect source-backed relationships with deliberately bounded resolution."""

import ast
from dataclasses import dataclass
from pathlib import Path

from codebase_investigator.analysis import ImportInfo
from codebase_investigator.dependencies import _import_target, _module_index, _module_target
from codebase_investigator.symbols import CodebaseIndex, Symbol, _File, _Imported


@dataclass(frozen=True)
class Reference:
    """A static relationship; unresolved candidates are never definite callers."""

    path: Path
    lineno: int
    owner: Symbol
    expression: str
    kind: str
    status: str
    target: Symbol | None
    candidates: tuple[Symbol, ...]
    reason: str


class _Resolver:
    def __init__(self, index: CodebaseIndex):
        self.index = index
        self.files = {file.path: file for file in index.files}
        self.modules = {}
        self.ambiguous_modules = set()
        self.invalidated_attributes = set()
        self.root_indexes = []
        for root in index.import_roots:
            paths = {path.relative_to(root) for path in self.files if path.is_relative_to(root)}
            local = _module_index(paths)
            self.root_indexes.append((root, local))
            for name in local:
                path = _module_target(name, local)
                if path is not None:
                    self.modules.setdefault(name, set()).add(root / path)
                else:
                    self.ambiguous_modules.add(name)
        mutations = set()
        for file in index.files:
            for node in ast.walk(file.tree):
                if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    scope = file.scopes.get(node)
                    if scope is not None:
                        module = self.expression(file, scope, node.value)
                        if module is not None and module.kind == "module":
                            mutations.add((module.path, node.attr))
        self.invalidated_attributes = mutations

    def _ambiguous_module(self, name):
        return any(name[:depth] in self.ambiguous_modules for depth in range(1, len(name) + 1))

    def module(self, name: tuple[str, ...]) -> Symbol | None:
        if self._ambiguous_module(name):
            return None
        paths = self.modules.get(name, set())
        if len(paths) == 1:
            return self.files[next(iter(paths))].module
        return None

    def imported(self, file: _File, info: ImportInfo, *, binding: bool) -> Symbol | None:
        if info.module is None and info.level == 0:
            parts = tuple(info.name.split("."))
            return self.module(parts if info.alias or not binding else parts[:1])
        if not info.level:
            base_name = tuple(info.module.split(".")) if info.module else ()
            if self._ambiguous_module(base_name) or self._ambiguous_module((*base_name, info.name)):
                return None
        targets = set()
        bases = set()
        for root, local in self.root_indexes:
            if info.level and not file.path.is_relative_to(root):
                continue
            source = file.path.relative_to(root) if file.path.is_relative_to(root) else file.path
            target = _import_target(source, info, local)
            if target is not None:
                targets.add(root / target)
            base_info = ImportInfo("*", None, info.module, info.level, info.lineno)
            base = _import_target(source, base_info, local)
            if base is not None:
                bases.add(root / base)
        if len(targets) != 1:
            return None
        target_file = self.files[next(iter(targets))]
        # A from-import naming a child module is a module reference, not a symbol.
        if target_file.path not in bases:
            for base in bases:
                package = self.files[base]
                if (base, info.name) in self.invalidated_attributes:
                    return None
                if info.name in package.scope.bindings or package.scope.wildcard:
                    return self._binding(package, package.scope, info.name, follow_imports=False)
            return target_file.module
        if info.name == "*":
            return target_file.module if not binding else None
        return self._binding(target_file, target_file.scope, info.name, follow_imports=False)

    def _binding(self, file, scope, name, *, follow_imports=True, lineno=None):
        while scope is not None:
            if scope.kind == "module" and (file.path, name) in self.invalidated_attributes:
                return None
            if scope.wildcard or name in scope.declarations:
                return None
            if name in scope.bindings:
                values = scope.bindings[name]
                if len(values) != 1:
                    return None
                value = values[0]
                if scope.kind == "class" and lineno is not None:
                    binding_line = value.lineno if isinstance(value, Symbol) else (
                        value.info.lineno if isinstance(value, _Imported) else None
                    )
                    if binding_line is not None and binding_line >= lineno:
                        return None
                if isinstance(value, Symbol):
                    return value
                if isinstance(value, _Imported) and follow_imports:
                    return self.imported(file, value.info, binding=True)
                return None
            scope = scope.parent
        return None

    def expression(self, file, scope, node):
        if isinstance(node, ast.Name):
            return self._binding(file, scope, node.id, lineno=node.lineno)
        if isinstance(node, ast.Attribute):
            base = self.expression(file, scope, node.value)
            if base is not None and base.kind == "module":
                if (base.path, node.attr) in self.invalidated_attributes:
                    return None
                target_file = self.files[base.path]
                # Dotted module imports bind their top-level package.
                parts = ast.unparse(node).split(".")
                current = scope
                while current is not None:
                    if current.wildcard or parts[0] in current.declarations:
                        return None
                    values = current.bindings.get(parts[0])
                    if values is not None:
                        if len(values) == 1 and isinstance(values[0], _Imported):
                            info = values[0].info
                            imported_parts = tuple(info.name.split("."))
                            if (info.module is None and info.level == 0 and not info.alias
                                    and tuple(parts) == imported_parts[:len(parts)]):
                                # Importing a child can replace a package binding.
                                if node.attr in target_file.scope.bindings:
                                    return None
                                return self.module(tuple(parts))
                        break
                    current = current.parent
                if node.attr in target_file.scope.bindings:
                    return self._binding(target_file, target_file.scope, node.attr, follow_imports=False)
        return None


def collect_references(index: CodebaseIndex) -> tuple[Reference, ...]:
    """Resolve lexical names and explicit module imports, retaining uncertainty.

    Bindings with reassignment, duplicates, wildcard imports or global/nonlocal
    declarations remain unresolved. No object type inference, general attribute
    dispatch, re-export traversal or runtime reachability is attempted. Possible
    references share a spelling only; they are not evidence of actual usage.
    """
    resolver = _Resolver(index)
    result = []
    by_name = {}
    for symbol in index.symbols:
        by_name.setdefault(symbol.qualified_name.rsplit(".", 1)[-1], []).append(symbol)
    for file in index.files:
        parents = {child: parent for parent in ast.walk(file.tree) for child in ast.iter_child_nodes(parent)}
        definitions = {s.lineno: s for s in index.symbols if s.path == file.path}
        nodes = sorted(ast.walk(file.tree), key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0)))
        for node in nodes:
            scope = file.scopes.get(node)
            if scope is None:
                continue
            owner = scope.owner
            ancestor = node
            while ancestor in parents:
                if isinstance(ancestor, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    owner = definitions[ancestor.lineno]
                    break
                ancestor = parents[ancestor]
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    info = ImportInfo(alias.name, alias.asname,
                                      node.module if isinstance(node, ast.ImportFrom) else None,
                                      node.level if isinstance(node, ast.ImportFrom) else 0, node.lineno)
                    target = resolver.imported(file, info, binding=False)
                    # Keep module-level import evidence even when symbol resolution fails.
                    if target is None and isinstance(node, ast.ImportFrom):
                        wildcard = ImportInfo("*", None, info.module, info.level, info.lineno)
                        target = resolver.imported(file, wildcard, binding=False)
                    candidates = tuple(by_name.get(alias.name, ())) if target is None else ()
                    result.append(Reference(file.path, node.lineno, owner, ast.unparse(node),
                                            "import", "resolved" if target else "unresolved",
                                            target, candidates, "explicit import" if target else "import not resolved"))
                continue
            if not isinstance(node, (ast.Name, ast.Attribute)) or not isinstance(node.ctx, ast.Load):
                continue
            parent = parents.get(node)
            if isinstance(parent, ast.Attribute) and parent.value is node:
                continue
            target = resolver.expression(file, scope, node)
            name = node.id if isinstance(node, ast.Name) else node.attr
            candidates = tuple(by_name.get(name, ())) if target is None else ()
            kind = "call" if isinstance(parent, ast.Call) and parent.func is node else "reference"
            result.append(Reference(
                file.path, node.lineno, owner, ast.unparse(node), kind,
                "resolved" if target else "possible" if candidates else "unresolved",
                target, candidates, "lexical or explicit import binding" if target else
                "binding or attribute unresolved; matching names are only possible links",
            ))
    return tuple(result)
