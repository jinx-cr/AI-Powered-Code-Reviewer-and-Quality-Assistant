"""Tests for core/docstring_engine/llm_integration.py."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.docstring_engine.llm_integration import LLMIntegration


class TestLLMIntegration:
    """Tests for LLMIntegration."""

    def test_no_api_key_raises_runtime_error(self):
        """generate_docstring should raise RuntimeError when no key is set."""
        llm = LLMIntegration(api_key="")
        with pytest.raises(RuntimeError, match="No Groq API key"):
            llm.generate_docstring("def foo():\n    pass\n")

    def test_api_key_from_argument(self):
        """API key passed as argument should be stored on the instance."""
        llm = LLMIntegration(api_key="gsk_test_key")
        assert llm.api_key == "gsk_test_key"

    def test_api_key_from_env(self, monkeypatch):
        """API key should be read from GROQ_API_KEY env var when not passed."""
        monkeypatch.setenv("GROQ_API_KEY", "gsk_from_env")
        llm = LLMIntegration()
        assert llm.api_key == "gsk_from_env"

    def test_default_model(self):
        """Default model should be the versatile llama model."""
        llm = LLMIntegration(api_key="gsk_x")
        assert "llama" in llm.model.lower() or llm.model == LLMIntegration.DEFAULT_MODEL

    def test_custom_model_stored(self):
        """Custom model string should be stored correctly."""
        llm = LLMIntegration(api_key="gsk_x", model="gemma2-9b-it")
        assert llm.model == "gemma2-9b-it"

    def test_fallback_docstring_returns_string(self):
        """_fallback_docstring should return a non-empty string."""
        llm = LLMIntegration(api_key="gsk_x")
        result = llm._fallback_docstring("def foo():\n    pass\n")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_api_key_env_fallback(self, monkeypatch):
        """Empty env var should result in empty api_key."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        llm = LLMIntegration()
        assert llm.api_key == ""

    def test_generate_raises_without_key(self):
        """Calling generate_docstring with no key should always raise."""
        llm = LLMIntegration(api_key=None)
        with pytest.raises(RuntimeError):
            llm.generate_docstring("def x(): pass")
