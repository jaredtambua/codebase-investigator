# Codebase Investigator

Find the part of a Python codebase to understand before modifying a specific
file, function, class or method. Reading guides identify the implementation,
related tests, direct local dependencies and consumers with source evidence.
The underlying discovery and static-analysis APIs are also available separately.

Requires Python 3.10 or later. The package lives in `src/codebase_investigator`,
and tests live in `tests`.

## Understand a change target

```sh
python -m codebase_investigator analyse_dependencies --root . --import-root src
python -m codebase_investigator src/codebase_investigator/dependencies.py:90 --import-root src
python -m codebase_investigator src/codebase_investigator/dependencies.py --import-root src --limit 10
```

After installation, `codebase-investigator` runs the same command. Targets are
repository-relative file paths, `file.py:line`, `file.py:qualified_name` (for
example `service.py:Service.work`), or bare/qualified symbol names. Duplicate
matches return choices and exit status 2 rather than selecting silently. A line
selects the innermost enclosing definition, or the module outside definitions.
Missing targets, invalid roots and analysis errors also exit with status 2.

Use `--root` for the repository to inspect and `--import-root` for its Python
import layout. Import roots default to `.` and must be directories within the
repository; repeat the flag when necessary. All eligible Python files are
inspected, including tests outside import roots. No code or tests are executed.

```python
from codebase_investigator.reading_guide import build_reading_guide

guide = build_reading_guide(".", "analyse_dependencies", import_roots=("src",))
for item in guide.items:
    print(item.category, item.symbol.path, item.symbol.lineno, item.reason)
    for evidence in item.evidence:
        print(evidence.kind, evidence.path, evidence.lineno, evidence.expression)
```

`ReadingGuide` and its records are frozen dataclasses. `targets` contains the
selected definition or ambiguity choices. Each symbol has its kind, qualified
name, header line, source range including decorators, signature, docstring and
source. `items` supplies enclosing context, related tests, direct dependencies
and consumers, in that priority order with stable path/line ordering. Shared
locations are deduplicated and their evidence is retained. Selection reserves
space across categories so many tests do not crowd out dependencies; broader
test/consumer module entries are omitted when precise entries exist in that file.
`unresolved` contains
possible or unresolved references separately; name similarity is not a definite
relationship. The API's positive `limit` (default 20) caps reading items and
unresolved records separately, with `omitted_items` and `omitted_unresolved`
counts. Ordinary unbound local values and builtin names are omitted from the
guide's uncertainty list unless they have a possible local symbol match; the
underlying reference API retains them. The CLI bounds source excerpts and
evidence display too. To expand,
select a related target or increase the limit; the guide does not recurse.

The index includes methods, nested and conditional definitions. Resolution
supports lexical definitions and explicit local imports, aliases and module
attributes, including imports inside functions. Reassignment, duplicate bindings,
wildcard imports and global/nonlocal declarations prevent confident name
resolution. Forward bindings in class bodies remain uncertain rather than being
treated as references to definitions that have not yet been bound. Explicit
attribute writes or deletions through resolved module aliases
also invalidate links to those attributes across the analysed tree. Static
references may appear in code that never executes. General
object dispatch, namespace packages, re-export chains, dynamic imports and
external callers are not resolved. Import roots with competing module names
remain ambiguous. Existing file/dependency analysis contracts remain unchanged.

Test paths (`tests/`, `test_*.py`, or `*_test.py`) identify related test source;
their references and module imports are evidence of relevance, not coverage.
Module imports provide broader context and are labelled as imports, never as
function calls. A guide can therefore include a module importer without finding
a call to the selected function. The guide neither proves complete change
impact nor infers behaviour beyond source, docstrings and test evidence.

`index_codebase` in `codebase_investigator.symbols` exposes the richer symbol
inventory, and `collect_references` in `codebase_investigator.references` exposes
the underlying reference records. Discovery exclusions and immediate propagation
of filesystem, decoding and syntax errors apply to all new analysis APIs.

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
fixed for now. Discovery does not parse source files; use the
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

## Find potentially unused functions

```python
from codebase_investigator.unused_functions import find_unused_functions

for candidate in find_unused_functions("."):
    print(candidate.path, candidate.function.name, candidate.function.lineno)
```

The function accepts a directory as a string or `Path` and returns a tuple of
frozen `UnusedFunction` records containing a root-relative `path` and a
`FunctionInfo` in `function`. Candidates include only direct module-level
functions, including async functions. Results follow sorted file order then
definition order, preserving duplicates. Empty results are `()`.

Calls, callback references, loaded attributes and `from` imports (including
aliases and imports inside functions) count as possible usage. References are
searched throughout every discovered file, including tests. Plain module imports
alone do not mark their functions as used. Decorated functions and literal names
in direct module-level `__all__` assignments are retained as possible registrations
or exports. Any wildcard import suppresses all candidates.

Matching is conservative and based on names across the entire analysed tree,
without resolving bindings, types or imports. An unrelated local variable,
attribute or imported object with the same name can therefore hide an unused
function. Self-references and references from otherwise unused functions also
count: this is reference detection, not reachability analysis. Strings outside
`__all__`, external callers and dynamic references are not recognised. Reported
functions are candidates for investigation, not proof that removal is safe.

Discovery exclusions and symbolic-link behaviour apply. Source is never executed;
file, decoding and syntax errors propagate without returning partial results.
Existing analysis APIs are unchanged.

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
