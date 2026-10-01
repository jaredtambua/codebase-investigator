from pathlib import Path

import pytest

from codebase_investigator.reading_guide import build_reading_guide
from codebase_investigator.references import collect_references
from codebase_investigator.symbols import index_codebase


def write_files(root, files):
    for name, source in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def test_symbol_ranges_methods_nested_functions_and_duplicate_choices(tmp_path):
    write_files(tmp_path, {"a.py": "@decorate\nclass Service:\n"
                          "    def work(self, value=1):\n        'Work description.'\n"
                          "        def inner(): pass\n        return inner()\n"
                          "def work(): pass\ndef work(): pass\n"})
    index = index_codebase(tmp_path)
    method = next(s for s in index.symbols if s.qualified_name == "Service.work")
    assert (method.lineno, method.start_lineno, method.end_lineno) == (3, 3, 6)
    assert method.signature == "def work(self, value=1)"
    assert method.docstring == "Work description."
    assert any(s.qualified_name == "Service.work.inner" for s in index.symbols)
    guide = build_reading_guide(tmp_path, "work")
    assert guide.ambiguous and len(guide.targets) == 3 and not guide.items
    assert build_reading_guide(tmp_path, "a.py:4").targets == (method,)


@pytest.mark.parametrize("definition", [
    "def target(): pass", "async def target(): pass", "class target: pass",
])
def test_parenthesised_multiline_decorator_includes_opening_line(tmp_path, definition):
    source = "@(\n    decorate @ other\n)\n@second\n" + definition + "\n"
    write_files(tmp_path, {"a.py": source})
    symbol = index_codebase(tmp_path).symbols[0]
    assert (symbol.start_lineno, symbol.lineno, symbol.end_lineno) == (1, 5, 5)
    assert symbol.source == source.removesuffix("\n")
    assert build_reading_guide(tmp_path, "a.py:1").targets == (symbol,)


@pytest.mark.parametrize("separator", ["\u2028", "\u2029", "\x85"])
@pytest.mark.parametrize("ending", ["", "\n"])
def test_unicode_separator_in_literal_preserves_physical_source_lines(tmp_path, separator, ending):
    source = f"text = 'before{separator}after'\ndef target(): pass" + ending
    write_files(tmp_path, {"a.py": source})
    index = index_codebase(tmp_path)
    symbol = index.symbols[0]
    assert (symbol.start_lineno, symbol.lineno, symbol.end_lineno) == (2, 2, 2)
    assert symbol.source == "def target(): pass"
    assert index.files[0].module.end_lineno == 2
    assert index.files[0].module.source == source.replace("\r\n", "\n")
    assert build_reading_guide(tmp_path, "a.py:2").targets == (symbol,)
    with pytest.raises(ValueError, match="not found"):
        build_reading_guide(tmp_path, "a.py:3")


def test_dependencies_consumers_callbacks_and_test_evidence(tmp_path):
    write_files(tmp_path, {
        "a.py": "def helper(): pass\ndef target():\n    return helper()\n"
                "def caller():\n    register(target)\n",
        "test_a.py": "from a import target as renamed\ndef test_target():\n    renamed()\n",
    })
    guide = build_reading_guide(tmp_path, "a.py:target")
    assert not guide.ambiguous
    related = {(item.symbol.qualified_name, item.category) for item in guide.items}
    assert ("helper", "dependency") in related
    assert ("caller", "consumer") in related
    assert ("test_target", "test") in related
    callback = next(item for item in guide.items if item.symbol.qualified_name == "caller")
    assert any(e.kind == "reference" and e.lineno == 5 for e in callback.evidence)
    assert guide == build_reading_guide(str(tmp_path), "a.py:target")


def test_src_layout_tests_outside_import_root_and_nested_imports(tmp_path):
    write_files(tmp_path, {
        "src/pkg/__init__.py": "",
        "src/pkg/service.py": "def target():\n    from .helper import assist as local\n    local()\n",
        "src/pkg/helper.py": "def assist(): pass\n",
        "tests/test_service.py": "import pkg.service as service\n"
                                 "def test_target(): service.target()\n",
    })
    guide = build_reading_guide(tmp_path, "target", import_roots=("src",))
    assert {(i.symbol.path.as_posix(), i.category) for i in guide.items} >= {
        ("src/pkg/helper.py", "dependency"), ("tests/test_service.py", "test"),
    }


@pytest.mark.parametrize("source", [
    "def consumer(target): target()\n",
    "def consumer():\n    target = other\n    target()\n",
    "def consumer():\n    target()\n    target = other\n",
    "def consumer():\n    global target\n    target = other\n    target()\n",
    "def consumer():\n    return [target() for target in values]\n",
    "consumer = lambda target: target()\n",
])
def test_shadowing_never_becomes_confident_consumer(tmp_path, source):
    write_files(tmp_path, {"a.py": "def target(): pass\n" + source})
    guide = build_reading_guide(tmp_path, "a.py:target")
    assert not any(i.category == "consumer" for i in guide.items)


def test_unknown_dispatch_has_possible_evidence_not_resolved_call(tmp_path):
    write_files(tmp_path, {"a.py": "class Service:\n    def target(self): pass\n"
                          "def caller(obj): obj.target()\n"})
    guide = build_reading_guide(tmp_path, "a.py:Service.target")
    assert not any(i.category == "consumer" for i in guide.items)
    assert any(r.expression == "obj.target" and r.status == "possible"
               for r in guide.unresolved)
    assert any(i.category == "context" for i in guide.items)


def test_file_guide_imports_are_module_relationships(tmp_path):
    write_files(tmp_path, {"a.py": "import b\ndef consumer(): pass\n",
                          "b.py": "def target(): pass\n"})
    guide = build_reading_guide(tmp_path, "b.py")
    consumer = next(i for i in guide.items if i.category == "consumer")
    assert consumer.symbol.path == Path("a.py")
    assert all(e.kind == "import" for e in consumer.evidence)


def test_limits_omissions_no_recursive_expansion_and_no_execution(tmp_path):
    write_files(tmp_path, {"a.py": "raise RuntimeError('do not execute')\n"
                          "def third(): pass\ndef helper(): third()\n"
                          "def target(): helper()\ndef caller(): target()\n"})
    guide = build_reading_guide(tmp_path, "a.py:target", limit=1)
    assert len(guide.items) == 1 and guide.omitted_items == 1
    assert guide.items[0].symbol.qualified_name != "third"
    with pytest.raises(ValueError):
        build_reading_guide(tmp_path, "target", limit=0)


def test_wildcards_reassignment_and_duplicate_definitions_are_unresolved(tmp_path):
    write_files(tmp_path, {"a.py": "def target(): pass\ndef target(): pass\n"
                          "def caller(): target()\n",
                          "b.py": "from a import *\ndef consumer(): target()\n"})
    guide = build_reading_guide(tmp_path, "a.py:1")
    assert not any(e.kind == "call" for i in guide.items for e in i.evidence)
    assert guide.unresolved


def test_target_and_import_root_validation_and_parse_errors(tmp_path):
    write_files(tmp_path, {"a.py": "def target(): pass\n"})
    with pytest.raises(ValueError, match="not found"):
        build_reading_guide(tmp_path, "missing")
    with pytest.raises(ValueError):
        index_codebase(tmp_path, import_roots=("../outside",))
    write_files(tmp_path, {".venv/ignored.py": "invalid syntax!"})
    assert build_reading_guide(tmp_path, "target").targets
    write_files(tmp_path, {"z.py": "invalid syntax!"})
    with pytest.raises(SyntaxError):
        build_reading_guide(tmp_path, "target")


def test_balanced_limit_retains_dependencies_among_many_tests(tmp_path):
    write_files(tmp_path, {
        "a.py": "def helper(): pass\ndef target(): helper()\n",
        "tests/test_a.py": "from a import target\n" +
                           "\n".join(f"def test_{n}(): target()" for n in range(12)),
    })
    guide = build_reading_guide(tmp_path, "a.py:target", limit=2)
    assert [i.category for i in guide.items] == ["test", "dependency"]
    assert guide.items[0].symbol.kind == "function"
    assert guide.omitted_items == 11


def test_plain_dotted_and_child_module_imports(tmp_path):
    write_files(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/child.py": "def target(): pass\n",
        "app.py": "import pkg.child\nfrom pkg import child as alias\n"
                  "def caller():\n    pkg.child.target()\n    alias.target()\n",
    })
    guide = build_reading_guide(tmp_path, "pkg/child.py:target")
    caller = next(i for i in guide.items if i.symbol.qualified_name == "caller")
    assert [r.expression for r in caller.evidence] == ["pkg.child.target", "alias.target"]


def test_imported_function_named_after_its_module(tmp_path):
    write_files(tmp_path, {"a.py": "def a(): pass\n",
                          "app.py": "from a import a\ndef caller(): a()\n"})
    guide = build_reading_guide(tmp_path, "a.py:a")
    assert any(i.symbol.qualified_name == "caller" and i.evidence[0].kind == "call"
               for i in guide.items)


def test_decorator_and_default_dependencies_belong_to_target(tmp_path):
    write_files(tmp_path, {"a.py": "def decorate(f): return f\ndef default(): pass\n"
                          "@decorate\ndef target(value=default()): pass\n"})
    guide = build_reading_guide(tmp_path, "a.py:target")
    assert {i.symbol.qualified_name for i in guide.items if i.category == "dependency"} == {"decorate", "default"}
    assert guide.targets[0].start_lineno == 3


def test_function_at_first_line_does_not_inherit_all_module_imports(tmp_path):
    write_files(tmp_path, {"a.py": "def target(): pass\nimport b\n", "b.py": ""})
    assert not build_reading_guide(tmp_path, "a.py:target").items


def test_class_scopes_are_not_method_lambda_or_comprehension_closures(tmp_path):
    write_files(tmp_path, {"a.py": "class Service:\n    def target(): pass\n"
                          "    def method(self): target()\n"
                          "    callback = lambda: target()\n"
                          "    values = [target() for value in items]\n"})
    guide = build_reading_guide(tmp_path, "a.py:Service.target")
    assert not any(e.kind == "call" for i in guide.items for e in i.evidence)


def test_global_and_comprehension_assignment_invalidates_outer_binding(tmp_path):
    for source in (
        "def mutator():\n    global target\n    target = other\n",
        "def enclosing():\n    def target(): pass\n"
        "    values = [(target := value) for value in items]\n    target()\n",
    ):
        write_files(tmp_path, {"a.py": "def target(): pass\ndef caller(): target()\n" + source})
        references = collect_references(index_codebase(tmp_path))
        if "global" in source:
            assert not any(r.kind == "call" and r.target and r.target.qualified_name == "target"
                           for r in references)
        else:
            assert not any(r.kind == "call" and r.target and r.target.qualified_name == "enclosing.target"
                           for r in references)


def test_file_selection_and_errors_preserve_static_contract(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_bytes(b"# coding: latin-1\ndef caf\xe9(): pass\n")
    assert index_codebase(tmp_path).symbols[0].qualified_name == "caf\u00e9"
    with pytest.raises(ValueError):
        build_reading_guide(tmp_path, "a.py:99")
    with pytest.raises(FileNotFoundError):
        index_codebase(tmp_path / "missing")
    import tokenize

    def blocked(path):
        raise PermissionError("unreadable")

    monkeypatch.setattr(tokenize, "open", blocked)
    with pytest.raises(PermissionError):
        index_codebase(tmp_path)


@pytest.mark.parametrize("import_statement, expression", [
    ("import a", "a.target"),
    ("from a import target", "target"),
])
def test_collisions_in_any_import_root_prevent_definite_resolution(tmp_path, import_statement, expression):
    write_files(tmp_path, {
        "r1/a.py": "def target(): pass\n",
        "r2/a.py": "def target(): pass\n",
        "r2/a/__init__.py": "def target(): pass\n",
        "app.py": f"{import_statement}\ndef caller(): {expression}()\n",
    })
    references = collect_references(index_codebase(tmp_path, import_roots=("r1", "r2")))
    assert not any(r.kind == "call" and r.target for r in references)


def test_package_import_does_not_establish_child_module_attribute(tmp_path):
    write_files(tmp_path, {
        "pkg/__init__.py": "",
        "pkg/child.py": "def target(): pass\n",
        "app.py": "import pkg\ndef caller(): pkg.child.target()\n",
    })
    guide = build_reading_guide(tmp_path, "pkg/child.py:target")
    assert not any(e.kind == "call" for i in guide.items for e in i.evidence)
    assert any(r.expression == "pkg.child.target" for r in guide.unresolved)


def test_nested_class_body_does_not_capture_outer_class_namespace(tmp_path):
    write_files(tmp_path, {"a.py": "class Outer:\n    def target(): pass\n"
                          "    class Inner:\n        result = target()\n"})
    guide = build_reading_guide(tmp_path, "a.py:Outer.target")
    assert not any(e.kind == "call" for i in guide.items for e in i.evidence)
    assert any(r.expression == "target" for r in guide.unresolved)


def test_module_attribute_reexport_remains_unresolved(tmp_path):
    write_files(tmp_path, {"a.py": "def target(): pass\n", "b.py": "from a import target\n",
                          "app.py": "import b\ndef caller(): b.target()\n"})
    references = collect_references(index_codebase(tmp_path))
    call = next(r for r in references if r.kind == "call" and r.expression == "b.target")
    assert call.target is None and call.status == "possible"


def test_package_binding_shadows_sibling_module(tmp_path):
    write_files(tmp_path, {
        "pkg/__init__.py": "def child(): pass\n",
        "pkg/child.py": "def target(): pass\n",
        "app.py": "from pkg import child\ndef caller(): child.target()\n",
    })
    references = collect_references(index_codebase(tmp_path))
    assert not any(r.kind == "call" and r.target for r in references)


def test_dotted_child_import_conflicting_with_package_binding_is_uncertain(tmp_path):
    write_files(tmp_path, {
        "pkg/__init__.py": "def child(): pass\n",
        "pkg/child.py": "def target(): pass\n",
        "app.py": "import pkg.child\ndef caller(): pkg.child()\n",
    })
    references = collect_references(index_codebase(tmp_path))
    call = next(r for r in references if r.kind == "call")
    assert call.expression == "pkg.child"
    assert call.target is None and call.status == "possible"
    guide = build_reading_guide(tmp_path, "pkg/__init__.py:child")
    assert not any(i.category == "consumer" for i in guide.items)


@pytest.mark.parametrize("mutation", ["module.target = replacement", "del module.target", "module.target += replacement"])
def test_explicit_module_attribute_mutation_invalidates_links(tmp_path, mutation):
    write_files(tmp_path, {
        "a.py": "def target(): pass\ndef internal(): target()\n",
        "app.py": f"import a as module\n{mutation}\ndef caller(): module.target()\n",
        "other.py": "from a import target\ndef another(): target()\n",
    })
    references = collect_references(index_codebase(tmp_path))
    assert not any(r.kind == "call" and r.target for r in references)
    assert any(r.expression == "module.target" and r.status == "possible" for r in references)


@pytest.mark.parametrize("later_binding", ["def target(): pass", "from b import target"])
def test_class_body_forward_binding_never_resolves_to_later_definition(tmp_path, later_binding):
    write_files(tmp_path, {
        "a.py": "def target(): pass\nclass C:\n    result = target()\n    " + later_binding + "\n",
        "b.py": "def target(): pass\n",
    })
    references = collect_references(index_codebase(tmp_path))
    reference = next(r for r in references if r.path == Path("a.py") and r.lineno == 3 and r.kind == "call")
    assert reference.target is None and reference.status == "possible"
