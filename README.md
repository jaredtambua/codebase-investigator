# Codebase Investigator

Discover Python source files within a repository or any directory tree.

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
fixed for now; there is no CLI or source parsing.

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
