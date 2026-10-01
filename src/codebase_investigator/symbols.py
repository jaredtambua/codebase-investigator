"""Index Python definitions, source ranges and lexical bindings statically."""

import ast
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
import tokenize

from codebase_investigator.analysis import ImportInfo
from codebase_investigator.discovery import discover_python_files


@dataclass(frozen=True)
class Symbol:
    """A definition identity and the source a developer can read."""

    path: Path
    qualified_name: str
    kind: str
    lineno: int
    start_lineno: int
    end_lineno: int
    signature: str
    docstring: str | None
    source: str


@dataclass(frozen=True)
class _Imported:
    info: ImportInfo


@dataclass
class _Scope:
    parent: "_Scope | None"
    owner: Symbol
    kind: str
    bindings: dict[str, list[Symbol | _Imported | None]] = field(default_factory=dict)
    declarations: set[str] = field(default_factory=set)
    wildcard: bool = False

    def bind(self, name: str, value: Symbol | _Imported | None = None) -> None:
        self.bindings.setdefault(name, []).append(value)


@dataclass
class _File:
    path: Path
    tree: ast.Module
    module: Symbol
    scope: _Scope
    scopes: dict[ast.AST, _Scope]


@dataclass(frozen=True)
class CodebaseIndex:
    """One parsed snapshot; paths are relative to the repository root."""

    root: Path
    import_roots: tuple[Path, ...]
    symbols: tuple[Symbol, ...]
    files: tuple[_File, ...]


class _Builder(ast.NodeVisitor):
    def __init__(self, path: Path, tree: ast.Module, source: str):
        self.path = path
        # Source is read with universal newlines; other separators are literals.
        self.lines = source.split("\n")
        if self.lines[-1] == "":
            self.lines.pop()
        self.decorator_lines = []
        previous_type = tokenize.NEWLINE
        for token in tokenize.generate_tokens(StringIO(source).readline):
            if token.type in (tokenize.NL, tokenize.COMMENT):
                continue
            if (token.type == tokenize.OP and token.string == "@"
                    and previous_type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)):
                self.decorator_lines.append(token.start[0])
            previous_type = token.type
        self.module = Symbol(path, "", "module", 1, 1, max(1, len(self.lines)),
                             path.as_posix(), ast.get_docstring(tree), source)
        self.scope = _Scope(None, self.module, "module")
        self.module_scope = self.scope
        self.scopes: dict[ast.AST, _Scope] = {}
        self.symbols: list[Symbol] = []

    def visit(self, node):
        self.scopes[node] = self.scope
        return super().visit(node)

    def _definition(self, node, kind):
        enclosing = self.scope.owner.qualified_name
        name = f"{enclosing}.{node.name}" if enclosing else node.name
        start = node.lineno
        if node.decorator_list:
            start = max(line for line in self.decorator_lines
                        if line <= node.decorator_list[0].lineno)
        if isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(base) for base in [*node.bases, *node.keywords])
            signature = f"class {node.name}" + (f"({bases})" if bases else "")
        else:
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            signature = f"{prefix} {node.name}({ast.unparse(node.args)})"
            if node.returns:
                signature += f" -> {ast.unparse(node.returns)}"
        symbol = Symbol(self.path, name, kind, node.lineno, start, node.end_lineno,
                        signature, ast.get_docstring(node),
                        "\n".join(self.lines[start - 1:node.end_lineno]))
        self.symbols.append(symbol)
        self.scope.bind(node.name, symbol)
        # Decorators, annotations and defaults are evaluated in the outer scope.
        for decorator in node.decorator_list:
            self.visit(decorator)
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                self.visit(base)
            for keyword in node.keywords:
                self.visit(keyword)
        else:
            self.visit(node.args)
            if node.returns:
                self.visit(node.returns)
        previous = self.scope
        parent = previous
        while parent.kind == "class" and parent.parent is not None:
            parent = parent.parent
        self.scope = _Scope(parent, symbol, "class" if kind == "class" else "function")
        if not isinstance(node, ast.ClassDef):
            self._parameters(node.args)
        for statement in node.body:
            self.visit(statement)
        self.scope = previous

    def visit_FunctionDef(self, node):
        self._definition(node, "method" if self.scope.kind == "class" else "function")

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._definition(node, "class")

    def _parameters(self, args):
        for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs,
                    *([args.vararg] if args.vararg else []),
                    *([args.kwarg] if args.kwarg else [])]:
            self.scope.bind(arg.arg)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.scope.bind(node.id)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.scope.bind(node.name)
        self.generic_visit(node)

    def visit_Global(self, node):
        self.scope.declarations.update(node.names)

    visit_Nonlocal = visit_Global

    def visit_Import(self, node):
        for alias in node.names:
            self.scope.bind(alias.asname or alias.name.split(".")[0], _Imported(
                ImportInfo(alias.name, alias.asname, None, 0, node.lineno)))

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == "*":
                self.scope.wildcard = True
            else:
                self.scope.bind(alias.asname or alias.name, _Imported(
                    ImportInfo(alias.name, alias.asname, node.module, node.level, node.lineno)))

    def visit_Lambda(self, node):
        self.visit(node.args)
        previous = self.scope
        parent = previous
        while parent.kind == "class" and parent.parent is not None:
            parent = parent.parent
        self.scope = _Scope(parent, previous.owner, "lambda")
        self._parameters(node.args)
        self.visit(node.body)
        self.scope = previous

    def _comprehension(self, node):
        previous = self.scope
        self.visit(node.generators[0].iter)
        parent = previous
        while parent.kind == "class" and parent.parent is not None:
            parent = parent.parent
        self.scope = _Scope(parent, previous.owner, "comprehension")
        for position, generator in enumerate(node.generators):
            if position:
                self.visit(generator.iter)
            self.visit(generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        for name in ("elt", "key", "value"):
            if hasattr(node, name):
                self.visit(getattr(node, name))
        self.scope = previous

    visit_ListComp = _comprehension
    visit_SetComp = _comprehension
    visit_DictComp = _comprehension
    visit_GeneratorExp = _comprehension

    def visit_NamedExpr(self, node):
        self.generic_visit(node)
        scope = self.scope
        if scope.kind == "comprehension":
            while scope.kind == "comprehension" and scope.parent is not None:
                scope = scope.parent
            if isinstance(node.target, ast.Name):
                scope.bind(node.target.id)

    def visit_MatchAs(self, node):
        if node.name:
            self.scope.bind(node.name)
        self.generic_visit(node)

    visit_MatchStar = visit_MatchAs

    def visit_MatchMapping(self, node):
        if node.rest:
            self.scope.bind(node.rest)
        self.generic_visit(node)


def index_codebase(
    root: str | Path, *, import_roots: tuple[str | Path, ...] = (".",),
) -> CodebaseIndex:
    """Parse discovered files once, including tests outside explicit import roots.

    Import roots must be directories inside the repository. Definitions include
    methods, nested and conditional definitions, preserving duplicate identities.
    File, decoding and syntax errors propagate; source is never executed.
    """
    root = Path(root).resolve()
    paths = discover_python_files(root)
    roots = []
    for value in import_roots:
        directory = (root / value).resolve()
        if not directory.is_relative_to(root) or not directory.is_dir():
            raise ValueError(f"Import root must be a directory inside the repository: {value}")
        relative = directory.relative_to(root)
        if relative not in roots:
            roots.append(relative)
    if not roots:
        raise ValueError("At least one import root is required")
    files = []
    symbols = []
    for path in paths:
        with tokenize.open(root / path) as source_file:
            source = source_file.read()
        tree = ast.parse(source, filename=str(root / path))
        builder = _Builder(path, tree, source)
        builder.visit(tree)
        # A global/nonlocal write can invalidate bindings used elsewhere too.
        scopes = {id(scope): scope for scope in builder.scopes.values()}
        for scope in scopes.values():
            for name in scope.declarations & scope.bindings.keys():
                parent = scope.parent
                while parent is not None:
                    if name in parent.bindings:
                        parent.bind(name)
                    parent = parent.parent
        files.append(_File(path, tree, builder.module, builder.module_scope, builder.scopes))
        symbols.extend(builder.symbols)
    return CodebaseIndex(root, tuple(roots), tuple(symbols), tuple(files))
