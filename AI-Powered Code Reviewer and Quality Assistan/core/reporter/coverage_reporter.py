"""Coverage reporter — summarises docstring coverage across a project.

Produces per-file and project-level statistics and can export results
to JSON for persistence or CI/CD pipelines.
"""

import json
import os
from dataclasses import asdict, dataclass
from typing import Optional

from core.parser.python_parser import FileAnalysis


@dataclass
class FileCoverage:
    """Docstring coverage stats for a single file.

    Attributes:
        file_name: Basename of the Python file.
        total_functions: Total number of functions/methods found.
        documented: Number with a docstring.
        undocumented: Number missing a docstring.
        coverage_pct: Coverage percentage (0-100).
        maintainability_index: radon MI score, or None.
    """

    file_name: str
    total_functions: int
    documented: int
    undocumented: int
    coverage_pct: float
    maintainability_index: Optional[float]


@dataclass
class ProjectCoverage:
    """Aggregate docstring coverage for the entire project.

    Attributes:
        total_files: Number of Python files analysed.
        total_functions: Total functions across all files.
        documented: Total documented functions.
        undocumented: Total undocumented functions.
        coverage_pct: Overall coverage percentage.
        files: Per-file breakdown.
    """

    total_files: int
    total_functions: int
    documented: int
    undocumented: int
    coverage_pct: float
    files: list[FileCoverage]


class CoverageReporter:
    """Builds coverage reports from parser output.

    Args:
        output_dir: Directory where JSON reports are saved.
    """

    def __init__(self, output_dir: str = "storage/reports") -> None:
        """Initialise the CoverageReporter.

        Args:
            output_dir: Path to write JSON report files.
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def build(self, analyses: list[FileAnalysis]) -> ProjectCoverage:
        """Build a :class:`ProjectCoverage` from a list of file analyses.

        Args:
            analyses: Output from :meth:`PythonParser.parse_directory`.

        Returns:
            A fully populated :class:`ProjectCoverage` object.
        """
        file_coverages: list[FileCoverage] = []
        for fa in analyses:
            total = len(fa.functions)
            documented = sum(1 for f in fa.functions if f.has_docstring)
            undocumented = total - documented
            pct = round(documented / total * 100, 1) if total else 0.0
            file_coverages.append(
                FileCoverage(
                    file_name=fa.file_name,
                    total_functions=total,
                    documented=documented,
                    undocumented=undocumented,
                    coverage_pct=pct,
                    maintainability_index=fa.maintainability_index,
                )
            )

        total_fn = sum(fc.total_functions for fc in file_coverages)
        total_doc = sum(fc.documented for fc in file_coverages)
        total_undoc = total_fn - total_doc
        overall_pct = round(total_doc / total_fn * 100, 1) if total_fn else 0.0

        return ProjectCoverage(
            total_files=len(analyses),
            total_functions=total_fn,
            documented=total_doc,
            undocumented=total_undoc,
            coverage_pct=overall_pct,
            files=file_coverages,
        )

    def save_json(self, coverage: ProjectCoverage, filename: str = "coverage_report.json") -> str:
        """Save a coverage report to JSON.

        Args:
            coverage: The :class:`ProjectCoverage` to serialise.
            filename: Output filename (relative to ``output_dir``).

        Returns:
            Absolute path of the saved file.
        """
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(coverage), fh, indent=2)
        return path

    def load_json(self, filename: str = "coverage_report.json") -> Optional[dict]:
        """Load a previously saved JSON report.

        Args:
            filename: Filename to load from ``output_dir``.

        Returns:
            Parsed dict, or None if the file does not exist.
        """
        path = os.path.join(self.output_dir, filename)
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
