from pathlib import Path

import pytest

from codebase_investigator.analysis import ClassInfo, FileAnalysis, FunctionInfo, ImportInfo
from codebase_investigator.directory_analysis import analyse_directory


@pytest.mark.parametrize("as_string", [False, True])
def test_analyses_nested_files_in_discovery_order(tmp_path, as_string):
    (tmp_path / "package").mkdir()
    (tmp_path / "z.py").write_text("class Zebra: pass\n", encoding="utf-8")
    (tmp_path / "package" / "module.py").write_text(
        "import os\nasync def work(): pass\n", encoding="utf-8"
    )
    (tmp_path / "package" / "__init__.py").touch()
    (tmp_path / "a.py").write_text("def first(): pass\n", encoding="utf-8")

    result = analyse_directory(str(tmp_path) if as_string else tmp_path)

    assert list(result) == [
        Path("a.py"), Path("package/__init__.py"),
        Path("package/module.py"), Path("z.py"),
    ]
    assert result == {
        Path("a.py"): FileAnalysis((FunctionInfo("first", 1, False),), (), ()),
        Path("package/__init__.py"): FileAnalysis((), (), ()),
        Path("package/module.py"): FileAnalysis(
            (FunctionInfo("work", 2, True),), (), (ImportInfo("os", None, None, 0, 1),)
        ),
        Path("z.py"): FileAnalysis((), (ClassInfo("Zebra", 1),), ()),
    }


def test_relative_root_resolves_files_against_root(tmp_path, monkeypatch):
    root = tmp_path / "repository"
    root.mkdir()
    (root / "module.py").write_text("def inside(): pass\n", encoding="utf-8")
    (tmp_path / "module.py").write_text("invalid syntax!", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert analyse_directory("repository") == {
        Path("module.py"): FileAnalysis((FunctionInfo("inside", 1, False),), (), ())
    }


def test_inherits_discovery_exclusions(tmp_path):
    for name in (".git", ".venv", "venv", "__pycache__", ".pytest_cache", "build", "dist"):
        directory = tmp_path / "nested" / name
        directory.mkdir(parents=True)
        (directory / "ignored.py").write_text("invalid syntax!", encoding="utf-8")
    (tmp_path / "README.md").write_text("invalid syntax!", encoding="utf-8")
    (tmp_path / "ignored.PY").write_text("invalid syntax!", encoding="utf-8")
    (tmp_path / "keep.py").touch()

    assert analyse_directory(tmp_path) == {Path("keep.py"): FileAnalysis((), (), ())}


def test_empty_directory(tmp_path):
    assert analyse_directory(tmp_path) == {}


def test_missing_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyse_directory(tmp_path / "missing")


def test_file_root(tmp_path):
    path = tmp_path / "module.py"
    path.touch()
    with pytest.raises(NotADirectoryError):
        analyse_directory(path)


def test_discovery_permission_error_propagates(tmp_path, monkeypatch):
    import os

    def blocked_scandir(path):
        raise PermissionError("Directory is unreadable")

    monkeypatch.setattr(os, "scandir", blocked_scandir)
    with pytest.raises(PermissionError, match="Directory is unreadable"):
        analyse_directory(tmp_path)


def test_syntax_error_propagates_without_partial_result(tmp_path):
    (tmp_path / "a.py").touch()
    broken = tmp_path / "b.py"
    broken.write_text("def broken(\n", encoding="utf-8")
    with pytest.raises(SyntaxError) as error:
        analyse_directory(tmp_path)
    assert error.value.filename == str(broken)


def test_decoding_error_propagates(tmp_path):
    (tmp_path / "module.py").write_bytes(b"# coding: utf-8\n# comment\nvalue = '\xff'\n")
    with pytest.raises(UnicodeDecodeError):
        analyse_directory(tmp_path)


def test_file_permission_error_propagates(tmp_path, monkeypatch):
    import tokenize

    (tmp_path / "module.py").touch()

    def blocked_open(path):
        raise PermissionError("File is unreadable")

    monkeypatch.setattr(tokenize, "open", blocked_open)
    with pytest.raises(PermissionError, match="File is unreadable"):
        analyse_directory(tmp_path)
