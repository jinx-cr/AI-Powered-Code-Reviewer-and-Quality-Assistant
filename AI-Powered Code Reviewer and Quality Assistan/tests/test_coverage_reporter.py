"""Tests for core/reporter/coverage_reporter.py."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.reporter.coverage_reporter import CoverageReporter, FileCoverage, ProjectCoverage
from core.parser.python_parser import FileAnalysis, FunctionInfo


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_analysis(fname: str, funcs: list[tuple[str, bool]]) -> FileAnalysis:
    """Build a fake FileAnalysis for testing."""
    fa = FileAnalysis(file_path=f"/tmp/{fname}", file_name=fname)
    for name, has_doc in funcs:
        fa.functions.append(FunctionInfo(name=name, lineno=1, has_docstring=has_doc))
    return fa


# ── tests ─────────────────────────────────────────────────────────────────────

class TestCoverageReporter:
    """Tests for CoverageReporter."""

    def test_build_all_documented(self):
        """Coverage should be 100 when every function has a docstring."""
        analyses = [_make_analysis("a.py", [("foo", True), ("bar", True)])]
        reporter = CoverageReporter(output_dir=tempfile.mkdtemp())
        cov = reporter.build(analyses)
        assert cov.coverage_pct == 100.0
        assert cov.documented == 2
        assert cov.undocumented == 0

    def test_build_none_documented(self):
        """Coverage should be 0 when no functions have docstrings."""
        analyses = [_make_analysis("b.py", [("foo", False), ("bar", False)])]
        reporter = CoverageReporter(output_dir=tempfile.mkdtemp())
        cov = reporter.build(analyses)
        assert cov.coverage_pct == 0.0
        assert cov.undocumented == 2

    def test_build_mixed(self):
        """Coverage should reflect partial documentation correctly."""
        analyses = [_make_analysis("c.py", [("f1", True), ("f2", False), ("f3", True)])]
        reporter = CoverageReporter(output_dir=tempfile.mkdtemp())
        cov = reporter.build(analyses)
        assert cov.documented == 2
        assert cov.undocumented == 1
        assert abs(cov.coverage_pct - 66.7) < 0.1

    def test_build_multiple_files(self):
        """Total counts should aggregate across files."""
        analyses = [
            _make_analysis("x.py", [("a", True), ("b", False)]),
            _make_analysis("y.py", [("c", True), ("d", True)]),
        ]
        reporter = CoverageReporter(output_dir=tempfile.mkdtemp())
        cov = reporter.build(analyses)
        assert cov.total_files == 2
        assert cov.total_functions == 4
        assert cov.documented == 3

    def test_build_empty(self):
        """Empty analysis list should yield zero stats."""
        reporter = CoverageReporter(output_dir=tempfile.mkdtemp())
        cov = reporter.build([])
        assert cov.total_files == 0
        assert cov.coverage_pct == 0.0

    def test_save_and_load_json(self, tmp_path):
        """Saved JSON should round-trip back to equivalent data."""
        analyses = [_make_analysis("d.py", [("go", True)])]
        reporter = CoverageReporter(output_dir=str(tmp_path))
        cov = reporter.build(analyses)
        reporter.save_json(cov, "test_report.json")
        loaded = reporter.load_json("test_report.json")
        assert loaded is not None
        assert loaded["documented"] == 1
        assert loaded["coverage_pct"] == 100.0

    def test_load_json_missing(self, tmp_path):
        """Loading a nonexistent file should return None."""
        reporter = CoverageReporter(output_dir=str(tmp_path))
        assert reporter.load_json("nonexistent.json") is None

    def test_file_coverage_fields(self):
        """FileCoverage should have correct per-file stats."""
        analyses = [_make_analysis("e.py", [("f", True), ("g", False)])]
        reporter = CoverageReporter(output_dir=tempfile.mkdtemp())
        cov = reporter.build(analyses)
        fc = cov.files[0]
        assert fc.file_name == "e.py"
        assert fc.total_functions == 2
        assert fc.documented == 1
        assert fc.coverage_pct == 50.0

    def test_output_dir_created(self, tmp_path):
        """CoverageReporter should create output_dir if it doesn't exist."""
        new_dir = str(tmp_path / "new" / "nested")
        CoverageReporter(output_dir=new_dir)
        assert os.path.isdir(new_dir)

    def test_project_coverage_type(self):
        """build() should return a ProjectCoverage instance."""
        reporter = CoverageReporter(output_dir=tempfile.mkdtemp())
        result = reporter.build([])
        assert isinstance(result, ProjectCoverage)
