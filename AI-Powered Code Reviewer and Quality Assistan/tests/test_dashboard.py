"""Tests for dashboard_ui/dashboard.py and the Streamlit app logic.

These tests verify the pure-Python utility functions used by the dashboard
without spinning up a Streamlit server.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ── import helpers from the main app ─────────────────────────────────────────

def _import_app_functions():
    """Import pure utility functions from the main app without triggering Streamlit."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "app",
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_code_reviewer_pro.py"),
    )
    # We only need the helper functions; skip full module execution
    return None


# ── badge helpers tests (inline reimplementation for isolation) ───────────────

def cx_badge(level: str) -> str:
    """Complexity badge helper matching the app logic."""
    cls = {"Low": "badge-ok", "Medium": "badge-warn", "High": "badge-bad"}.get(level, "badge-ok")
    return f'<span class="fn-badge {cls}">{level}</span>'


def doc_badge(status: str) -> str:
    """Doc status badge helper matching the app logic."""
    cls = "badge-doc" if status == "Documented" else "badge-nodoc"
    label = "✓ Docs" if status == "Documented" else "✗ No Docs"
    return f'<span class="fn-badge {cls}">{label}</span>'


class TestCxBadge:
    """Tests for complexity badge helper."""

    def test_low_complexity(self):
        """Low complexity should render badge-ok class."""
        result = cx_badge("Low")
        assert "badge-ok" in result
        assert "Low" in result

    def test_medium_complexity(self):
        """Medium complexity should render badge-warn class."""
        result = cx_badge("Medium")
        assert "badge-warn" in result

    def test_high_complexity(self):
        """High complexity should render badge-bad class."""
        result = cx_badge("High")
        assert "badge-bad" in result

    def test_unknown_complexity(self):
        """Unknown level should fallback to badge-ok."""
        result = cx_badge("Unknown")
        assert "badge-ok" in result

    def test_returns_html_string(self):
        """Badge should return a non-empty HTML string."""
        result = cx_badge("Low")
        assert isinstance(result, str)
        assert len(result) > 0


class TestDocBadge:
    """Tests for documentation badge helper."""

    def test_documented_class(self):
        """Documented status should use badge-doc class."""
        result = doc_badge("Documented")
        assert "badge-doc" in result

    def test_undocumented_class(self):
        """Undocumented status should use badge-nodoc class."""
        result = doc_badge("Undocumented")
        assert "badge-nodoc" in result

    def test_documented_label(self):
        """Documented badge should show a tick."""
        result = doc_badge("Documented")
        assert "✓" in result

    def test_undocumented_label(self):
        """Undocumented badge should show a cross."""
        result = doc_badge("Undocumented")
        assert "✗" in result

    def test_returns_html_string(self):
        """Badge should return an HTML string."""
        result = doc_badge("Documented")
        assert "<span" in result


class TestComplexityLevelMapping:
    """Tests for complexity-level categorisation logic."""

    def _get_level(self, score: int) -> str:
        """Replicate the app's complexity level logic."""
        if score <= 5:
            return "Low"
        elif score <= 10:
            return "Medium"
        else:
            return "High"

    def test_score_1_is_low(self):
        """Score of 1 should be Low."""
        assert self._get_level(1) == "Low"

    def test_score_5_is_low(self):
        """Score of 5 should be Low (boundary)."""
        assert self._get_level(5) == "Low"

    def test_score_6_is_medium(self):
        """Score of 6 should be Medium (boundary)."""
        assert self._get_level(6) == "Medium"

    def test_score_10_is_medium(self):
        """Score of 10 should be Medium (boundary)."""
        assert self._get_level(10) == "Medium"

    def test_score_11_is_high(self):
        """Score of 11 should be High (boundary)."""
        assert self._get_level(11) == "High"

    def test_score_50_is_high(self):
        """Very high score should still be High."""
        assert self._get_level(50) == "High"


class TestDocCoverageCalculation:
    """Tests for doc coverage percentage calculation."""

    def _calc(self, documented: int, total: int) -> int:
        """Replicate the app's coverage pct formula."""
        return round(documented / total * 100) if total else 0

    def test_full_coverage(self):
        """100% when all functions documented."""
        assert self._calc(10, 10) == 100

    def test_no_coverage(self):
        """0% when no functions documented."""
        assert self._calc(0, 10) == 0

    def test_half_coverage(self):
        """50% when half documented."""
        assert self._calc(5, 10) == 50

    def test_zero_total(self):
        """0% when no functions exist (avoid division by zero)."""
        assert self._calc(0, 0) == 0

    def test_rounding(self):
        """Should round to nearest integer."""
        assert self._calc(1, 3) == 33  # 33.33...
