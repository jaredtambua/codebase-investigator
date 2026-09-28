import os
from pathlib import Path

import pytest

from codebase_investigator.discovery import discover_python_files


def test_discovers_sorted_relative_python_files(tmp_path):
    for name in (
        "z.py", "src/package/module.py", "src/package/__init__.py", "a.py",
        "README.md", "compiled.pyc", "uppercase.PY", "stub.pyi",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    (tmp_path / "directory.py").mkdir()

    assert discover_python_files(str(tmp_path)) == [
        Path("a.py"),
        Path("src/package/__init__.py"),
        Path("src/package/module.py"),
        Path("z.py"),
    ]


@pytest.mark.parametrize(
    "excluded", [".git", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist"]
)
def test_excludes_directories_at_every_depth(tmp_path, excluded):
    for parent in (tmp_path, tmp_path / "nested"):
        directory = parent / excluded
        directory.mkdir(parents=True)
        (directory / "ignored.py").touch()
    (tmp_path / "keep.py").touch()

    assert discover_python_files(tmp_path) == [Path("keep.py")]


def test_empty_directory(tmp_path):
    assert discover_python_files(tmp_path) == []


def test_missing_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_python_files(tmp_path / "missing")


def test_file_root(tmp_path):
    root = tmp_path / "file.py"
    root.touch()
    with pytest.raises(NotADirectoryError):
        discover_python_files(root)


def test_relative_root(tmp_path, monkeypatch):
    root = tmp_path / "repository"
    root.mkdir()
    (root / "module.py").touch()
    monkeypatch.chdir(tmp_path)

    assert discover_python_files("repository") == [Path("module.py")]


def test_unreadable_directory_raises(tmp_path, monkeypatch):
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (tmp_path / "visible.py").touch()
    original_scandir = os.scandir

    def scandir(path):
        if Path(path) == blocked:
            raise PermissionError("Directory is unreadable")
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", scandir)
    with pytest.raises(PermissionError, match="Directory is unreadable"):
        discover_python_files(tmp_path)


def test_skips_symbolic_links(tmp_path):
    root = tmp_path / "repository"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "external.py").touch()
    (root / "local.py").touch()
    try:
        (root / "linked.py").symlink_to(outside / "external.py")
        (root / "linked_directory").symlink_to(outside, target_is_directory=True)
        (root / "loop").symlink_to(root, target_is_directory=True)
        (root / "broken.py").symlink_to(tmp_path / "missing.py")
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"Symbolic links are unavailable: {error}")

    assert discover_python_files(root) == [Path("local.py")]
