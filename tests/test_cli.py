import pytest

from codebase_investigator.cli import main


def test_cli_guide_includes_source_locations_and_evidence(tmp_path, capsys):
    (tmp_path / "a.py").write_text("def helper(): pass\ndef target(): helper()\n", encoding="utf-8")
    assert main(["a.py:target", "--root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "Understand first: a.py:2" in output
    assert "dependency: a.py:1" in output
    assert "call at a.py:2: helper" in output
    assert "Limitations:" in output


def test_cli_ambiguity_and_errors(tmp_path, capsys):
    (tmp_path / "a.py").write_text("def same(): pass\ndef same(): pass\n", encoding="utf-8")
    assert main(["same", "--root", str(tmp_path)]) == 2
    output = capsys.readouterr().out
    assert "Ambiguous target" in output and "a.py:1" in output and "a.py:2" in output
    with pytest.raises(SystemExit) as error:
        main(["absent", "--root", str(tmp_path)])
    assert error.value.code == 2
    assert "Target not found" in capsys.readouterr().err
