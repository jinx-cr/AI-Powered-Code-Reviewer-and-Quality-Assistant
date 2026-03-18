"""PEP 257 docstring compliance validator.

Checks Python source files against PEP 257 rules and returns
structured issue reports per function/class.
"""

import ast
from dataclasses import dataclass


# ── PEP 257 rule definitions ──────────────────────────────────────────────────

PEP257_RULES: dict[str, str] = {
    "D100": "Missing docstring in public module",
    "D101": "Missing docstring in public class",
    "D102": "Missing docstring in public method",
    "D103": "Missing docstring in public function",
    "D200": "No blank lines allowed surrounding docstring text",
    "D400": "First line should end with a period, question mark, or exclamation point",
}


@dataclass
class PEPIssue:
    """A single PEP 257 violation.

    Attributes:
        code: PEP 257 rule code (e.g. 'D103').
        function: Name of the function/class with the issue.
        line: Line number of the definition.
        message: Human-readable description of the violation.
    """

    code: str
    function: str
    line: int
    message: str


class DocstringValidator:
    """Validates Python source code against PEP 257 docstring conventions.

    Checks for missing docstrings (D100-D103) and basic style rules
    (D200, D400) without requiring an external linter.
    """

    def validate_source(self, source_code: str) -> list[PEPIssue]:
        """Validate a source code string and return all PEP 257 issues.

        Args:
            source_code: Raw Python source code to analyse.

        Returns:
            List of :class:`PEPIssue` objects for each violation found.
        """
        issues: list[PEPIssue] = []

        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return issues

        # Collect method names for D102 vs D103 distinction
        method_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_names.add(child.name)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                label = getattr(node, "name", "module")
                lineno = getattr(node, "lineno", 0)
                docstr = ast.get_docstring(node)

                if docstr is None:
                    code_map = {
                        ast.Module: "D100",
                        ast.ClassDef: "D101",
                        ast.FunctionDef: "D102" if label in method_names else "D103",
                        ast.AsyncFunctionDef: "D102" if label in method_names else "D103",
                    }
                    code = code_map.get(type(node))
                    if code:
                        issues.append(PEPIssue(
                            code=code,
                            function=label,
                            line=lineno,
                            message=PEP257_RULES[code],
                        ))
                else:
                    # D400: first line should end with punctuation
                    first_line = docstr.strip().splitlines()[0].strip()
                    if first_line and first_line[-1] not in ".!?":
                        issues.append(PEPIssue(
                            code="D400",
                            function=label,
                            line=lineno,
                            message=PEP257_RULES["D400"],
                        ))
                    # D200: no blank lines surrounding single-line docstring
                    if "\n" not in docstr.strip() and docstr != docstr.strip():
                        issues.append(PEPIssue(
                            code="D200",
                            function=label,
                            line=lineno,
                            message=PEP257_RULES["D200"],
                        ))

        return issues

    def validate_file(self, file_path: str) -> list[PEPIssue]:
        """Validate a Python file on disk.

        Args:
            file_path: Absolute or relative path to the ``.py`` file.

        Returns:
            List of :class:`PEPIssue` objects.
        """
        try:
            with open(file_path, encoding="utf-8") as fh:
                return self.validate_source(fh.read())
        except OSError:
            return []
