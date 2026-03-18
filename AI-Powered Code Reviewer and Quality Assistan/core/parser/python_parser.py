"""Python source-code parser using the built-in ``ast`` module.

Extracts function/class metadata, docstring status, complexity scores,
and maintainability index from raw Python source files.
"""

import ast
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FunctionInfo:
    """Metadata for a single Python function or method.

    Attributes:
        name: Function name.
        lineno: Line number where the function is defined.
        is_method: True if inside a class.
        has_docstring: True if a docstring is present.
        complexity: Cyclomatic complexity score.
        args: List of parameter names.
    """

    name: str
    lineno: int
    is_method: bool = False
    has_docstring: bool = False
    complexity: int = 1
    args: list[str] = field(default_factory=list)


@dataclass
class FileAnalysis:
    """Full analysis result for a single Python file.

    Attributes:
        file_path: Absolute path to the analysed file.
        file_name: Basename of the file.
        functions: List of FunctionInfo for each function/method found.
        maintainability_index: radon MI score (0-100), or None if unavailable.
        syntax_error: Error message if the file could not be parsed.
    """

    file_path: str
    file_name: str
    functions: list[FunctionInfo] = field(default_factory=list)
    maintainability_index: Optional[float] = None
    syntax_error: Optional[str] = None


class PythonParser:
    """Parses Python source files and extracts code-quality metadata.

    Uses ``ast`` for structural analysis and ``radon`` (if installed)
    for cyclomatic complexity and maintainability index scoring.
    """

    def parse_file(self, file_path: str) -> FileAnalysis:
        """Parse a single Python file and return its analysis.

        Args:
            file_path: Absolute or relative path to a ``.py`` file.

        Returns:
            A :class:`FileAnalysis` populated with all extracted metadata.
        """
        result = FileAnalysis(
            file_path=file_path,
            file_name=os.path.basename(file_path),
        )

        try:
            with open(file_path, encoding="utf-8") as fh:
                source = fh.read()
        except OSError as exc:
            result.syntax_error = str(exc)
            return result

        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            result.syntax_error = str(exc)
            return result

        # Collect method names to distinguish methods from functions
        method_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for child in ast.walk(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_names.add(child.name)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info = FunctionInfo(
                    name=node.name,
                    lineno=node.lineno,
                    is_method=node.name in method_names,
                    has_docstring=ast.get_docstring(node) is not None,
                    complexity=self._cyclomatic_complexity(node),
                    args=[a.arg for a in node.args.args if a.arg not in ("self", "cls")],
                )
                result.functions.append(info)

        result.maintainability_index = self._maintainability_index(source)
        return result

    def parse_directory(self, directory: str) -> list[FileAnalysis]:
        """Recursively parse all ``.py`` files in a directory.

        Args:
            directory: Path to the root directory to scan.

        Returns:
            List of :class:`FileAnalysis` objects, one per file.
        """
        results: list[FileAnalysis] = []
        for root, _, files in os.walk(directory):
            for fname in files:
                if fname.endswith(".py") and not fname.startswith("__"):
                    results.append(self.parse_file(os.path.join(root, fname)))
        return results

    # ── private helpers ───────────────────────────────────────────────────────

    def _cyclomatic_complexity(self, node: ast.AST) -> int:
        """Compute a simple cyclomatic complexity score for a function node.

        Args:
            node: An AST FunctionDef or AsyncFunctionDef node.

        Returns:
            Integer complexity score (minimum 1).
        """
        score = 1
        branch_types = (
            ast.If, ast.For, ast.While, ast.ExceptHandler,
            ast.With, ast.Assert, ast.comprehension,
        )
        for child in ast.walk(node):
            if isinstance(child, branch_types):
                score += 1
            elif isinstance(child, ast.BoolOp):
                score += len(child.values) - 1
        return score

    def _maintainability_index(self, source: str) -> Optional[float]:
        """Compute the radon Maintainability Index for a source string.

        Args:
            source: Raw Python source code.

        Returns:
            Float MI score (0-100), or None if radon is not installed.
        """
        try:
            from radon.metrics import mi_visit  # type: ignore
            return round(mi_visit(source, multi=True), 2)
        except ImportError:
            return None
