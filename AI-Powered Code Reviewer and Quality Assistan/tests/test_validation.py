"""Tests for core/validator/validator.py."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.validator.validator import DocstringValidator, PEPIssue, PEP257_RULES


class TestDocstringValidator:
    """Tests for DocstringValidator."""

    def test_d103_missing_function_docstring(self):
        """D103 should be raised for a public function missing a docstring."""
        src = "def my_func():\n    pass\n"
        issues = DocstringValidator().validate_source(src)
        codes = [i.code for i in issues]
        assert "D103" in codes

    def test_d101_missing_class_docstring(self):
        """D101 should be raised for a class missing a docstring."""
        src = "class MyClass:\n    pass\n"
        issues = DocstringValidator().validate_source(src)
        codes = [i.code for i in issues]
        assert "D101" in codes

    def test_d102_missing_method_docstring(self):
        """D102 should be raised for a method missing a docstring."""
        src = (
            "class MyClass:\n"
            '    """Documented class."""\n'
            "    def method(self):\n"
            "        pass\n"
        )
        issues = DocstringValidator().validate_source(src)
        codes = [i.code for i in issues]
        assert "D102" in codes

    def test_d400_missing_period(self):
        """D400 should fire when the first docstring line lacks punctuation."""
        src = 'def foo():\n    """does something without period"""\n    pass\n'
        issues = DocstringValidator().validate_source(src)
        codes = [i.code for i in issues]
        assert "D400" in codes

    def test_no_issues_for_well_documented(self):
        """A fully documented function should produce no issues."""
        src = 'def foo():\n    """Does something."""\n    pass\n'
        issues = DocstringValidator().validate_source(src)
        assert all(i.code != "D103" for i in issues)
        assert all(i.code != "D400" for i in issues)

    def test_syntax_error_returns_empty(self):
        """Syntax errors in source should return an empty issue list."""
        src = "def bad(:\n    pass\n"
        issues = DocstringValidator().validate_source(src)
        assert issues == []

    def test_issue_has_line_number(self):
        """Issues should carry the correct line number."""
        src = "def foo():\n    pass\n"
        issues = DocstringValidator().validate_source(src)
        d103 = next(i for i in issues if i.code == "D103")
        assert d103.line == 1

    def test_issue_has_function_name(self):
        """Issues should carry the function/class name."""
        src = "def my_func():\n    pass\n"
        issues = DocstringValidator().validate_source(src)
        names = [i.function for i in issues]
        assert "my_func" in names

    def test_validate_file(self, tmp_path):
        """validate_file should read from disk and return issues."""
        src = "def undocumented():\n    pass\n"
        f = tmp_path / "sample.py"
        f.write_text(src)
        issues = DocstringValidator().validate_file(str(f))
        assert any(i.code == "D103" for i in issues)

    def test_validate_file_missing(self):
        """validate_file should return empty list for nonexistent file."""
        issues = DocstringValidator().validate_file("/tmp/does_not_exist_abc.py")
        assert issues == []

    def test_all_rule_codes_defined(self):
        """PEP257_RULES should contain all expected rule codes."""
        expected = {"D100", "D101", "D102", "D103", "D200", "D400"}
        assert expected.issubset(set(PEP257_RULES.keys()))

    def test_issue_dataclass_fields(self):
        """PEPIssue should expose code, function, line, and message."""
        issue = PEPIssue(code="D103", function="foo", line=1, message="Missing docstring.")
        assert issue.code == "D103"
        assert issue.function == "foo"
        assert issue.line == 1
        assert "Missing" in issue.message

    def test_multiple_functions_all_flagged(self):
        """All undocumented functions should each get their own issue."""
        src = "def a():\n    pass\ndef b():\n    pass\ndef c():\n    pass\n"
        issues = DocstringValidator().validate_source(src)
        flagged_names = {i.function for i in issues if i.code in ("D102", "D103")}
        assert {"a", "b", "c"}.issubset(flagged_names)

    def test_period_ending_clears_d400(self):
        """A docstring ending with '.' should NOT trigger D400."""
        src = 'def foo():\n    """This ends with a period."""\n    pass\n'
        issues = DocstringValidator().validate_source(src)
        assert all(i.code != "D400" for i in issues)

    def test_question_mark_clears_d400(self):
        """A docstring ending with '?' should NOT trigger D400."""
        src = 'def foo():\n    """Does this work?"""\n    pass\n'
        issues = DocstringValidator().validate_source(src)
        assert all(i.code != "D400" for i in issues)
