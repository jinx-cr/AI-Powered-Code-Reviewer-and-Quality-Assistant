"""Docstring generator module.

Generates Google-style, NumPy-style, or reST-style docstrings
for Python functions and classes using templates or LLM integration.
"""

import ast
from typing import Optional


class DocstringGenerator:
    """Generates docstrings for Python functions and classes.

    Supports Google, NumPy, and reStructuredText docstring styles.
    Can operate in template mode (no API key required) or LLM mode.

    Args:
        style: Docstring style — 'google', 'numpy', or 'rest'.
        use_llm: Whether to use LLM for smarter generation.
    """

    STYLES = ("google", "numpy", "rest")

    def __init__(self, style: str = "google", use_llm: bool = False) -> None:
        """Initialise the DocstringGenerator.

        Args:
            style: Docstring style — 'google', 'numpy', or 'rest'.
            use_llm: If True, LLMIntegration will be used when available.

        Raises:
            ValueError: If ``style`` is not one of the supported styles.
        """
        if style not in self.STYLES:
            raise ValueError(f"style must be one of {self.STYLES}, got {style!r}")
        self.style = style
        self.use_llm = use_llm

    # ── public API ────────────────────────────────────────────────────────────

    def generate(self, source: str) -> str:
        """Generate docstrings for all undocumented functions in *source*.

        Args:
            source: Raw Python source code string.

        Returns:
            Modified source code with docstrings inserted.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return source

        lines = source.splitlines(keepends=True)
        insertions: list[tuple[int, str]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    docstr = self._build_docstring(node)
                    insertions.append((node.body[0].lineno - 1, docstr))

        # Apply insertions in reverse so line numbers stay valid
        for lineno, docstr in sorted(insertions, reverse=True):
            indent = " " * (node.col_offset + 4)  # type: ignore[assignment]
            lines.insert(lineno, indent + docstr + "\n")

        return "".join(lines)

    def generate_for_function(
        self, name: str, args: list[str], returns: Optional[str] = None
    ) -> str:
        """Build a docstring template for a single function.

        Args:
            name: Function name.
            args: List of parameter names (excluding 'self'/'cls').
            returns: Optional return type annotation string.

        Returns:
            A formatted docstring string (without surrounding quotes).
        """
        dispatch = {
            "google": self._google_template,
            "numpy": self._numpy_template,
            "rest": self._rest_template,
        }
        return dispatch[self.style](name, args, returns)

    # ── private helpers ───────────────────────────────────────────────────────

    def _build_docstring(self, node: ast.AST) -> str:
        """Build a docstring for an AST node.

        Args:
            node: An AST FunctionDef, AsyncFunctionDef, or ClassDef node.

        Returns:
            Triple-quoted docstring string.
        """
        if isinstance(node, ast.ClassDef):
            return f'"""Class {node.name}."""'
        args = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]  # type: ignore[union-attr]
        template = self.generate_for_function(node.name, args)  # type: ignore[union-attr]
        return f'"""{template}"""'

    def _google_template(
        self, name: str, args: list[str], returns: Optional[str]
    ) -> str:
        parts = [f"{name}.\n\n"]
        if args:
            parts.append("Args:\n")
            for a in args:
                parts.append(f"    {a}: Description of {a}.\n")
        if returns:
            parts.append(f"\nReturns:\n    {returns}: Description.\n")
        return "".join(parts)

    def _numpy_template(
        self, name: str, args: list[str], returns: Optional[str]
    ) -> str:
        parts = [f"{name}.\n\n"]
        if args:
            parts.append("Parameters\n----------\n")
            for a in args:
                parts.append(f"{a} : type\n    Description of {a}.\n")
        if returns:
            parts.append(f"\nReturns\n-------\n{returns}\n    Description.\n")
        return "".join(parts)

    def _rest_template(
        self, name: str, args: list[str], returns: Optional[str]
    ) -> str:
        parts = [f"{name}.\n\n"]
        for a in args:
            parts.append(f":param {a}: Description of {a}.\n")
        if returns:
            parts.append(f":returns: Description.\n:rtype: {returns}\n")
        return "".join(parts)
