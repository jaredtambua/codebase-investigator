# Codebase Investigator

A minimal Python project scaffold. No application functionality is implemented yet.

Requires Python 3.10 or later. The package lives in `src/codebase_investigator`,
and tests live in `tests`.

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
