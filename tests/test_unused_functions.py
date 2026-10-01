from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from codebase_investigator.analysis import FunctionInfo
from codebase_investigator.unused_functions import UnusedFunction, find_unused_functions


def write_files(root, files):
    for name, source in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


@pytest.mark.parametrize("as_string", [False, True])
def test_candidates_preserve_paths_order_duplicates_and_async(tmp_path, as_string):
    write_files(tmp_path, {
        "z.py": "raise RuntimeError('must not execute')\ndef last(): pass\n",
        "a.py": "def unused(): pass\nasync def other(): pass\ndef unused(): pass\n",
    })
    result = find_unused_functions(str(tmp_path) if as_string else tmp_path)
    assert result == (
        UnusedFunction(Path("a.py"), FunctionInfo("unused", 1, False)),
        UnusedFunction(Path("a.py"), FunctionInfo("other", 2, True)),
        UnusedFunction(Path("a.py"), FunctionInfo("unused", 3, False)),
        UnusedFunction(Path("z.py"), FunctionInfo("last", 2, False)),
    )
    with pytest.raises(FrozenInstanceError):
        result[0].path = Path("elsewhere.py")


def test_calls_imports_callbacks_and_attributes_count_as_usage(tmp_path):
    write_files(tmp_path, {
        "functions.py": "def called(): pass\ndef imported(): pass\n"
                        "def callback(): pass\ndef attribute(): pass\ndef unused(): pass\n",
        "tests/test_usage.py": "from functions import imported as alias\n"
                               "called()\nregister(callback)\nmodule.attribute()\n",
    })
    assert find_unused_functions(tmp_path) == (
        UnusedFunction(Path("functions.py"), FunctionInfo("unused", 5, False)),
    )


def test_imports_in_nested_scopes_count_even_without_calls(tmp_path):
    write_files(tmp_path, {
        "a.py": "def used(): pass\n",
        "b.py": "def caller():\n    from a import used as renamed\n",
    })
    assert [item.function.name for item in find_unused_functions(tmp_path)] == ["caller"]


def test_only_direct_functions_are_candidates(tmp_path):
    write_files(tmp_path, {"a.py": "class Example:\n    def method(self): pass\n"
                          "if True:\n    def conditional(): pass\n"
                          "def outer():\n    def nested(): pass\n"})
    assert [item.function.name for item in find_unused_functions(tmp_path)] == ["outer"]


def test_conservative_names_self_references_exports_and_decorators(tmp_path):
    write_files(tmp_path, {
        "a.py": "def same(): pass\ndef recursive(): recursive()\n"
                "@register\ndef decorated(): pass\ndef exported(): pass\n"
                "__all__ = ['exported']\n",
        "b.py": "def caller(same): return same\n",
    })
    assert [item.function.name for item in find_unused_functions(tmp_path)] == ["caller"]


def test_wildcard_import_suppresses_candidates(tmp_path):
    write_files(tmp_path, {"a.py": "def candidate(): pass\nfrom external import *\n"})
    assert find_unused_functions(tmp_path) == ()


def test_module_import_and_strings_do_not_count_as_function_usage(tmp_path):
    write_files(tmp_path, {"a.py": "def candidate(): pass\nimport a\ntext = 'candidate'\n"})
    assert [item.function.name for item in find_unused_functions(tmp_path)] == ["candidate"]


def test_empty_directory_and_discovery_exclusions(tmp_path):
    assert find_unused_functions(tmp_path) == ()
    write_files(tmp_path, {".venv/ignored.py": "invalid syntax!", "a.py": ""})
    assert find_unused_functions(tmp_path) == ()


def test_errors_propagate(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_unused_functions(tmp_path / "missing")
    write_files(tmp_path, {"a.py": "def candidate(): pass\n", "z.py": "invalid syntax!"})
    with pytest.raises(SyntaxError):
        find_unused_functions(tmp_path)
    with pytest.raises(NotADirectoryError):
        find_unused_functions(tmp_path / "a.py")


def test_source_encodings_and_decoding_errors(tmp_path):
    (tmp_path / "a.py").write_bytes(b"# coding: latin-1\ndef caf\xe9(): pass\n")
    assert find_unused_functions(tmp_path)[0].function.name == "caf\u00e9"
    (tmp_path / "z.py").write_bytes(b"# coding: utf-8\n\xff")
    with pytest.raises(UnicodeDecodeError):
        find_unused_functions(tmp_path)
