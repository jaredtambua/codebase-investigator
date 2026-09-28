"""Discover Python source files in a directory tree."""

import os
from pathlib import Path
import stat


_EXCLUDED_DIRECTORIES = frozenset(
    {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist"}
)


def _raise_walk_error(error: OSError) -> None:
    raise error


def discover_python_files(root: str | Path) -> list[Path]:
    """Return sorted, root-relative paths to regular files ending in ``.py``.

    Skip common environment, cache, and build directories at every depth,
    and skip symbolic links encountered within the tree. The supplied root
    may itself be a symbolic link to a directory. Filesystem errors propagate
    to the caller rather than producing an incomplete result.
    """
    root = Path(root)
    if not stat.S_ISDIR(root.stat().st_mode):
        raise NotADirectoryError(f"Not a directory: {root}")

    files = []
    for directory, subdirectories, filenames in os.walk(
        root, topdown=True, onerror=_raise_walk_error, followlinks=False
    ):
        directory = Path(directory)
        subdirectories[:] = [
            name
            for name in subdirectories
            if name not in _EXCLUDED_DIRECTORIES
            and not stat.S_ISLNK((directory / name).lstat().st_mode)
        ]
        for name in filenames:
            path = directory / name
            if path.suffix == ".py" and stat.S_ISREG(path.lstat().st_mode):
                files.append(path.relative_to(root))

    return sorted(files, key=lambda path: path.as_posix())
