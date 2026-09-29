# Codebase Investigator

Discover Python source files within a repository or any directory tree.
Also statically analyse individual Python files to identify top-level functions,
classes, and imports.

Requires Python 3.10 or later. The package lives in `src/codebase_investigator`,
and tests live in `tests`.

## Discover Python files

```python
from codebase_investigator.discovery import discover_python_files

for path in discover_python_files("."):
    print(path)
```

The function accepts a string or `pathlib.Path` pointing to a directory and
returns a sorted list of `Path` objects relative to that directory. It includes
regular files with the exact `.py` suffix, including tests and `__init__.py` files.

Discovery skips `.git`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`, `build`,
and `dist` directories at every depth. Symbolic links within the tree are skipped;
the supplied root may itself be a symbolic link to a directory. Missing roots,
non-directory roots, and filesystem access errors raise exceptions rather than
returning incomplete results.

Git is not required, and `.gitignore` rules are not interpreted. Exclusions are
fixed for now; there is no CLI. Discovery does not parse source files; use the
separate analysis API below to inspect their contents.

## Analyse a Python file

```python
from codebase_investigator.analysis import analyse_python_file

analysis = analyse_python_file("src/codebase_investigator/discovery.py")
for function in analysis.functions:
    print(function.name, function.lineno, function.is_async)
for cls in analysis.classes:
    print(cls.name, cls.lineno)
for imported in analysis.imports:
    print(imported.name, imported.alias, imported.module, imported.level)
```

The function accepts a string or `pathlib.Path` and returns a frozen
`FileAnalysis` dataclass with tuples of function, class, and import records.
Each category preserves source order and duplicate entries. Only direct module
statements are included: methods, nested definitions, and statements inside
blocks such as `if` and `try` are excluded. Both regular and async functions
are recognised, including decorated definitions.

Line numbers (`lineno`) are one-based and identify the definition header
(rather than its decorators) or the import statement. Each imported name gets
its own record, preserving its optional alias. For `from` imports, `module`
is the source module and `level` counts leading dots; `from . import name`
has `module=None` and `level=1`. Plain imports have `module=None` and `level=0`.
Wildcard imports retain the name `*` without expanding it.

Analysis uses the standard-library AST parser and respects Python source
encoding declarations. It never executes source code or resolves imports.
File, decoding, and syntax errors propagate rather than returning partial
results. Supported syntax depends on the running Python interpreter.

## Analyse a directory

```python
from codebase_investigator.directory_analysis import analyse_directory

for path, analysis in analyse_directory(".").items():
    print(path, analysis.functions, analysis.classes, analysis.imports)
```

The function accepts a string or `pathlib.Path` pointing to a directory and
returns a dictionary mapping root-relative `Path` objects to `FileAnalysis`
results. Entries follow the sorted order returned by `discover_python_files`.
An empty directory, or one containing no eligible Python files, returns `{}`.

Directory analysis combines the existing discovery and single-file analysis
APIs. It inherits discovery's exclusions and symbolic-link behaviour, and each
file is analysed using `analyse_python_file`. Discovery, file access, decoding,
and syntax errors propagate immediately; no partial result is returned.

## Analyse local import dependencies

```python
from codebase_investigator.dependencies import analyse_dependencies

for dependency in analyse_dependencies("src"):
    print(dependency.source, dependency.imported.lineno, dependency.target)
```

Supply the directory that acts as the import root: use `"."` for a flat
repository or `"src"` for this project's source layout. The function accepts
a string or `Path` and returns a tuple of frozen `Dependency` records with
`source` and `target` paths relative to that root and the original `ImportInfo`
in `imported`. Sources follow sorted discovery order; imports preserve source
order and duplicates. Empty directories or no local matches return `()`.

For example, if `app.py` contains `from database import connect` and
`database.py` exists beside it under the import root, the result links
`app.py` to `database.py`. Aliases do not affect the target. Dotted imports
and explicit relative imports within regular packages are supported. Every
package directory below the root must contain `__init__.py`; the root itself
is a search directory, not a named package.

Resolution uses these structural rules:

- `import package.module` targets the exact module file, without adding
  separate relationships for parent package initialisers.
- `from package import child` prefers an existing child module or package;
  otherwise it targets `package/__init__.py`. `from module import name`
  targets the module file, without checking whether `name` is defined.
- Wildcard imports target the named module or package without expanding names.
- Missing or external targets, namespace packages, and ambiguous module names
  produce no relationship. A collision such as both `item.py` and
  `item/__init__.py` also prevents resolution through that package. An
  ambiguous child does not fall back to its parent package.

These relationships are static file matches, not proof of runtime import
behaviour. Package attributes can shadow child modules; re-exports, dynamic
imports, installed packages and changes to `sys.path` are not resolved. Only
direct module-level imports are considered, matching the existing analysis
scope. Cycles and self-imports are recorded without recursively following them.

The API reuses directory analysis's exclusions and error handling. Source code
is never executed, and file, decoding and syntax errors propagate rather than
returning partial results. Existing analysis APIs remain unchanged.

## Development

Create and activate a virtual environment, then install the package and test tools:

```sh
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the tests:

```sh
python -m pytest
```
