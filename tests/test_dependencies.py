from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from codebase_investigator.analysis import ImportInfo
from codebase_investigator.dependencies import Dependency, analyse_dependencies


def write_files(root, files):
    for name, source in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize("as_string", [False, True])
def test_direct_imports_preserve_evidence_order_and_duplicates(tmp_path, as_string):
    write_files(tmp_path, {
        "z.py": "import database\n",
        "database.py": "raise RuntimeError('must not execute')\n",
        "app.py": "import database as db, database\nfrom database import connect\n",
    })
    result = analyse_dependencies(str(tmp_path) if as_string else tmp_path)
    assert result == (
        Dependency(Path("app.py"), Path("database.py"),
                   ImportInfo("database", "db", None, 0, 1)),
        Dependency(Path("app.py"), Path("database.py"),
                   ImportInfo("database", None, None, 0, 1)),
        Dependency(Path("app.py"), Path("database.py"),
                   ImportInfo("connect", None, "database", 0, 2)),
        Dependency(Path("z.py"), Path("database.py"),
                   ImportInfo("database", None, None, 0, 1)),
    )
    with pytest.raises(FrozenInstanceError):
        result[0].source = Path("other.py")


def test_packages_dotted_names_and_relative_imports(tmp_path):
    write_files(tmp_path, {
        "app.py": "import pkg.database as db\nfrom pkg import database\nfrom pkg import *\n",
        "pkg/__init__.py": "from . import database\n",
        "pkg/database.py": "",
        "pkg/sub/__init__.py": "",
        "pkg/sub/service.py": "from ..database import connect\nfrom .. import database\nfrom . import helper\n",
        "pkg/sub/helper.py": "",
    })
    assert [(d.source.as_posix(), d.target.as_posix()) for d in analyse_dependencies(tmp_path)] == [
        ("app.py", "pkg/database.py"),
        ("app.py", "pkg/database.py"),
        ("app.py", "pkg/__init__.py"),
        ("pkg/__init__.py", "pkg/database.py"),
        ("pkg/sub/service.py", "pkg/database.py"),
        ("pkg/sub/service.py", "pkg/database.py"),
        ("pkg/sub/service.py", "pkg/sub/helper.py"),
    ]


def test_unresolved_imports_and_nested_imports_are_excluded(tmp_path):
    write_files(tmp_path, {
        "app.py": "import external\nimport missing\nimport ns.module\nfrom . import local\n"
                  "if True:\n    import local\ndef work():\n    import local\n",
        "local.py": "",
        "ns/module.py": "from . import neighbour\n",
        "ns/neighbour.py": "",
        "pkg/__init__.py": "from .. import local\nfrom ... import local\n",
        ".venv/ignored.py": "invalid syntax!",
    })
    assert analyse_dependencies(tmp_path) == ()


def test_ambiguous_module_and_package_and_descendants_are_excluded(tmp_path):
    write_files(tmp_path, {
        "app.py": "import clash\nimport clash.child\nfrom clash import child\n",
        "clash.py": "",
        "clash/__init__.py": "",
        "clash/child.py": "",
    })
    assert analyse_dependencies(tmp_path) == ()


def test_missing_child_falls_back_to_named_module(tmp_path):
    write_files(tmp_path, {
        "app.py": "from pkg import exported\nfrom module import value\n",
        "pkg/__init__.py": "",
        "module.py": "",
    })
    assert [d.target for d in analyse_dependencies(tmp_path)] == [
        Path("pkg/__init__.py"), Path("module.py"),
    ]


def test_ambiguous_child_does_not_fall_back_to_package(tmp_path):
    write_files(tmp_path, {
        "app.py": "from pkg import child\nimport pkg.missing\n",
        "pkg/__init__.py": "",
        "pkg/child.py": "",
        "pkg/child/__init__.py": "",
    })
    assert analyse_dependencies(tmp_path) == ()


def test_relative_imports_do_not_treat_modules_as_packages(tmp_path):
    write_files(tmp_path, {
        "pkg.py": "",
        "pkg/__init__.py": "from . import child\n",
        "pkg/child.py": "from . import child\n",
    })
    assert analyse_dependencies(tmp_path) == ()


def test_cycles_and_self_imports_are_recorded_without_traversal(tmp_path):
    write_files(tmp_path, {
        "a.py": "import b\nimport a\n",
        "b.py": "import a\n",
    })
    assert [(d.source, d.target) for d in analyse_dependencies(tmp_path)] == [
        (Path("a.py"), Path("b.py")),
        (Path("a.py"), Path("a.py")),
        (Path("b.py"), Path("a.py")),
    ]


def test_import_root_is_explicit(tmp_path, monkeypatch):
    write_files(tmp_path, {
        "src/app.py": "import database\n",
        "src/database.py": "",
    })
    monkeypatch.chdir(tmp_path)
    assert analyse_dependencies(".") == ()
    assert [(d.source, d.target) for d in analyse_dependencies("src")] == [
        (Path("app.py"), Path("database.py")),
    ]


def test_empty_directory(tmp_path):
    assert analyse_dependencies(tmp_path) == ()


def test_errors_propagate(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyse_dependencies(tmp_path / "missing")
    write_files(tmp_path, {"app.py": "import database\n", "database.py": "invalid syntax!"})
    with pytest.raises(SyntaxError):
        analyse_dependencies(tmp_path)
    with pytest.raises(NotADirectoryError):
        analyse_dependencies(tmp_path / "app.py")


def test_decoding_errors_propagate(tmp_path):
    (tmp_path / "bad.py").write_bytes(b"# coding: utf-8\n\xff")
    with pytest.raises(UnicodeDecodeError):
        analyse_dependencies(tmp_path)


def test_file_permission_errors_propagate(tmp_path, monkeypatch):
    import tokenize

    (tmp_path / "app.py").touch()

    def blocked_open(path):
        raise PermissionError("File is unreadable")

    monkeypatch.setattr(tokenize, "open", blocked_open)
    with pytest.raises(PermissionError, match="File is unreadable"):
        analyse_dependencies(tmp_path)
