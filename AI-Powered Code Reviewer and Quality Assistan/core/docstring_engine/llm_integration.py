"""LLM integration for AI-powered docstring generation via Groq API."""

import os
from typing import Optional

try:
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore


class LLMIntegration:
    """Wraps Groq API calls for LLM-based docstring generation.

    Requires a valid ``GROQ_API_KEY`` in the environment or ``.env`` file.

    Args:
        api_key: Groq API key. Falls back to ``GROQ_API_KEY`` env var.
        model: Groq model name to use for completions.
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        """Initialise LLM integration.

        Args:
            api_key: Groq API key. Falls back to GROQ_API_KEY env var if None.
            model: Model string for the Groq completions endpoint.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model

    def generate_docstring(self, function_source: str, style: str = "google") -> str:
        """Generate a docstring for the given function source via LLM.

        Args:
            function_source: Raw Python source of the function.
            style: Desired docstring style ('google', 'numpy', 'rest').

        Returns:
            Generated docstring text (without surrounding triple quotes).

        Raises:
            RuntimeError: If no API key is configured.
            ConnectionError: If the Groq API is unreachable.
        """
        if not self.api_key:
            raise RuntimeError(
                "No Groq API key configured. "
                "Set GROQ_API_KEY in your environment or .env file."
            )

        try:
            if requests is None:
                return self._fallback_docstring(function_source)

            prompt = (
                f"Write a {style}-style Python docstring for the following function. "
                f"Return ONLY the docstring content (no triple quotes, no code).\n\n"
                f"{function_source}"
            )

            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 512,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

        except Exception as exc:
            raise ConnectionError(f"Groq API error: {exc}") from exc

    def _fallback_docstring(self, source: str) -> str:
        """Return a simple placeholder when requests is unavailable.

        Args:
            source: Original function source (unused, kept for signature parity).

        Returns:
            A generic placeholder docstring string.
        """
        return "TODO: Add docstring."
