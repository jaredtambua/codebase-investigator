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
