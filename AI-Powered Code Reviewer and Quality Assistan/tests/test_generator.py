"""Tests for core/docstring_engine/generator.py."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.docstring_engine.generator import DocstringGenerator


class TestDocstringGenerator:
    """Tests for DocstringGenerator."""

    def test_invalid_style_raises(self):
        """Unsupported style should raise ValueError."""
        with pytest.raises(ValueError):
            DocstringGenerator(style="invalid")

    def test_google_style_contains_args(self):
        """Google-style template should include an Args section."""
        gen = DocstringGenerator(style="google")
        result = gen.generate_for_function("my_func", ["x", "y"])
        assert "Args:" in result
        assert "x" in result
        assert "y" in result

    def test_numpy_style_contains_params(self):
        """NumPy-style template should include a Parameters section."""
        gen = DocstringGenerator(style="numpy")
        result = gen.generate_for_function("my_func", ["a", "b"])
        assert "Parameters" in result
        assert "a" in result

    def test_rest_style_contains_param_tags(self):
        """reST-style template should use :param: tags."""
        gen = DocstringGenerator(style="rest")
        result = gen.generate_for_function("my_func", ["val"])
        assert ":param val:" in result

    def test_no_args_google(self):
        """Google template with no args should not include an Args section."""
        gen = DocstringGenerator(style="google")
        result = gen.generate_for_function("simple", [])
        assert "Args:" not in result

    def test_returns_included_when_provided(self):
        """Returns annotation should appear in all styles."""
        for style in ("google", "numpy", "rest"):
            gen = DocstringGenerator(style=style)
            result = gen.generate_for_function("f", [], returns="int")
            assert "int" in result or "Return" in result or "returns" in result.lower()

    def test_generate_inserts_into_undocumented(self):
        """generate() should add a docstring to an undocumented function."""
        src = "def foo():\n    pass\n"
        gen = DocstringGenerator(style="google")
        result = gen.generate(src)
        assert '"""' in result

    def test_generate_skips_documented(self):
        """generate() should not duplicate docstrings that already exist."""
        src = 'def foo():\n    """Existing docstring."""\n    pass\n'
        gen = DocstringGenerator(style="google")
        result = gen.generate(src)
        assert result.count('"""') == 2  # exactly one opening and one closing

    def test_generate_handles_syntax_error(self):
        """generate() should return source unchanged on syntax error."""
        src = "def broken(:\n    pass\n"
        gen = DocstringGenerator(style="google")
        result = gen.generate(src)
        assert result == src

    def test_all_styles_instantiate(self):
        """All three style constants should instantiate without error."""
        for style in DocstringGenerator.STYLES:
            gen = DocstringGenerator(style=style)
            assert gen.style == style

    def test_function_name_in_output(self):
        """The function name should appear in the generated template."""
        gen = DocstringGenerator(style="google")
        result = gen.generate_for_function("calculate_total", ["price", "tax"])
        assert "calculate_total" in result
