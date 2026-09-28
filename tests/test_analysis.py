import tokenize

import pytest

from codebase_investigator.analysis import (
    ClassInfo,
    FileAnalysis,
    FunctionInfo,
    ImportInfo,
    analyse_python_file,
)


def test_definitions_preserve_order_and_duplicates_without_execution(tmp_path):
    path = tmp_path / "module.py"
    path.write_text(
        "raise RuntimeError('must not execute')\n"
        "@unknown_decorator\n"
        "def zebra():\n"
        "    def nested(): pass\n"
        "    import hidden\n"
        "@unknown_decorator\n"
        "async def alpha(): pass\n"
        "class Zebra:\n"
        "    def method(self): pass\n"
        "    class Nested: pass\n"
        "    import hidden\n"
        "@unknown_decorator\n"
        "class Alpha: pass\n"
        "def zebra(): pass\n"
        "class Zebra: pass\n",
        encoding="utf-8",
    )

    expected = FileAnalysis(
        (FunctionInfo("zebra", 3, False), FunctionInfo("alpha", 7, True),
         FunctionInfo("zebra", 14, False)),
        (ClassInfo("Zebra", 8), ClassInfo("Alpha", 13), ClassInfo("Zebra", 15)),
        (),
    )
    assert analyse_python_file(path) == expected
    assert analyse_python_file(str(path)) == expected


def test_import_forms(tmp_path):
    path = tmp_path / "module.py"
    path.write_text(
        "import os, package.child as child\n"
        "from collections import deque as queue, Counter\n"
        "from . import sibling\n"
        "from ..package import item as renamed\n"
        "from package import *\n"
        "import os\n",
        encoding="utf-8",
    )

    assert analyse_python_file(path) == FileAnalysis((), (), (
        ImportInfo("os", None, None, 0, 1),
        ImportInfo("package.child", "child", None, 0, 1),
        ImportInfo("deque", "queue", "collections", 0, 2),
        ImportInfo("Counter", None, "collections", 0, 2),
        ImportInfo("sibling", None, None, 1, 3),
        ImportInfo("item", "renamed", "package", 2, 4),
        ImportInfo("*", None, "package", 0, 5),
        ImportInfo("os", None, None, 0, 6),
    ))


@pytest.mark.parametrize("source", [
    "",
    "# comment\nvalue = 1\n",
    "if True:\n    def hidden(): pass\n    class Hidden: pass\n    import os\n",
    "try:\n    import os\nexcept ImportError:\n    class Hidden: pass\n",
    "for item in []:\n    def hidden(): pass\n    import os\n",
])
def test_no_direct_definitions_or_imports(tmp_path, source):
    path = tmp_path / "module.py"
    path.write_text(source, encoding="utf-8")
    assert analyse_python_file(path) == FileAnalysis((), (), ())


@pytest.mark.parametrize("source", [
    "# coding: latin-1\ndef café(): pass\n".encode("latin-1"),
    "def café(): pass\n".encode("utf-8-sig"),
])
def test_python_source_encodings(tmp_path, source):
    path = tmp_path / "module.py"
    path.write_bytes(source)
    result = analyse_python_file(path)
    assert [function.name for function in result.functions] == ["café"]


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyse_python_file(tmp_path / "missing.py")


def test_unreadable_file(tmp_path, monkeypatch):
    path = tmp_path / "module.py"
    path.touch()
    def blocked_open(filename):
        assert filename == path
        raise PermissionError("File is unreadable")

    monkeypatch.setattr(tokenize, "open", blocked_open)
    with pytest.raises(PermissionError, match="File is unreadable"):
        analyse_python_file(path)


def test_invalid_syntax_includes_filename(tmp_path):
    path = tmp_path / "broken.py"
    path.write_text("import os\ndef broken(\n", encoding="utf-8")
    with pytest.raises(SyntaxError) as error:
        analyse_python_file(path)
    assert error.value.filename == str(path)


def test_invalid_encoding(tmp_path):
    path = tmp_path / "module.py"
    path.write_bytes(b"# coding: utf-8\n# comment\nvalue = '\xff'\n")
    with pytest.raises(UnicodeDecodeError):
        analyse_python_file(path)
