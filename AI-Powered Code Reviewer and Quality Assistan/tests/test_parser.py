"""Tests for core/parser/python_parser.py."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.parser.python_parser import PythonParser, FileAnalysis, FunctionInfo


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_temp(source: str, suffix: str = ".py") -> str:
    """Write source to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w") as fh:
        fh.write(source)
    return path


# ── tests ─────────────────────────────────────────────────────────────────────

class TestPythonParser:
    """Tests for PythonParser."""

    def test_parse_documented_function(self):
        """Parser should detect a documented function correctly."""
        src = 'def foo():\n    """Foo does something."""\n    pass\n'
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert len(result.functions) == 1
        assert result.functions[0].has_docstring is True
        assert result.functions[0].name == "foo"

    def test_parse_undocumented_function(self):
        """Parser should flag a function without a docstring."""
        src = "def bar():\n    pass\n"
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert result.functions[0].has_docstring is False

    def test_parse_multiple_functions(self):
        """Parser should return one entry per function."""
        src = (
            "def a():\n    pass\n"
            "def b():\n    pass\n"
            "def c():\n    pass\n"
        )
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert len(result.functions) == 3

    def test_parse_method_detection(self):
        """Functions inside a class should be flagged as methods."""
        src = (
            "class MyClass:\n"
            "    def method(self):\n"
            '        """Does stuff."""\n'
            "        pass\n"
        )
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        methods = [f for f in result.functions if f.is_method]
        assert len(methods) == 1
        assert methods[0].name == "method"

    def test_parse_syntax_error(self):
        """Parser should gracefully handle files with syntax errors."""
        src = "def broken(:\n    pass\n"
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert result.syntax_error is not None
        assert result.functions == []

    def test_parse_missing_file(self):
        """Parser should return an error for a nonexistent file."""
        result = PythonParser().parse_file("/tmp/does_not_exist_xyz.py")
        assert result.syntax_error is not None

    def test_complexity_simple(self):
        """A function with no branches should have complexity 1."""
        src = 'def simple():\n    """Doc."""\n    return 42\n'
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert result.functions[0].complexity == 1

    def test_complexity_branching(self):
        """A function with branches should have complexity > 1."""
        src = (
            "def branchy(x):\n"
            "    if x > 0:\n"
            "        return True\n"
            "    elif x < 0:\n"
            "        return False\n"
            "    else:\n"
            "        return None\n"
        )
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert result.functions[0].complexity > 1

    def test_parse_async_function(self):
        """Parser should handle async functions."""
        src = 'async def fetch():\n    """Fetches data."""\n    pass\n'
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert len(result.functions) == 1
        assert result.functions[0].name == "fetch"

    def test_file_name_in_result(self):
        """FileAnalysis.file_name should match the basename."""
        src = "def x():\n    pass\n"
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert result.file_name == os.path.basename(path)

    def test_parse_directory(self, tmp_path):
        """parse_directory should return one FileAnalysis per .py file."""
        for i in range(3):
            (tmp_path / f"mod_{i}.py").write_text(f"def f{i}():\n    pass\n")
        results = PythonParser().parse_directory(str(tmp_path))
        assert len(results) == 3

    def test_args_extraction(self):
        """Parser should extract parameter names correctly."""
        src = "def greet(name, age):\n    pass\n"
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        assert "name" in result.functions[0].args
        assert "age" in result.functions[0].args

    def test_self_excluded_from_args(self):
        """'self' should be excluded from method args."""
        src = (
            "class C:\n"
            "    def method(self, value):\n"
            "        pass\n"
        )
        path = _write_temp(src)
        result = PythonParser().parse_file(path)
        args = result.functions[0].args
        assert "self" not in args
        assert "value" in args
