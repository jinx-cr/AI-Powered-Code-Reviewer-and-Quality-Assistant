"""AI-powered code review engine using Groq API.

Analyses Python source code for quality issues, style violations,
complexity hotspots, and suggests improvements via LLM.
"""

import os
from typing import Optional


class AIReviewer:
    """Reviews Python source files using an LLM via Groq API.

    Args:
        api_key: Groq API key. Defaults to ``GROQ_API_KEY`` env var.
        model: Groq model to use for reviews.
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

    SYSTEM_PROMPT = (
        "You are an expert Python code reviewer. "
        "Analyse the given code and return a structured review covering: "
        "1) Code quality issues, 2) Missing or poor docstrings, "
        "3) Complexity hotspots, 4) Specific improvement suggestions. "
        "Be concise and actionable."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        """Initialise the AIReviewer.

        Args:
            api_key: Groq API key. Falls back to GROQ_API_KEY env var.
            model: Groq model string for completions.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model

    def review(self, source_code: str, file_name: str = "unknown.py") -> dict:
        """Perform an AI review on the provided source code.

        Args:
            source_code: Raw Python source code to review.
            file_name: Filename label for context (used in the prompt).

        Returns:
            Dict with keys ``ok`` (bool), ``review`` (str), and optionally ``error`` (str).
        """
        if not self.api_key:
            return {"ok": False, "error": "No GROQ_API_KEY configured."}

        try:
            import requests  # type: ignore

            prompt = f"Review the following Python file: `{file_name}`\n\n```python\n{source_code}\n```"
            resp = requests.post(
                self.GROQ_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                },
                timeout=60,
            )
            resp.raise_for_status()
            review_text = resp.json()["choices"][0]["message"]["content"].strip()
            return {"ok": True, "review": review_text}

        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def log_review(self, file_name: str, review: str, log_path: str = "storage/reports/review_logs.json") -> None:
        """Append a review result to the persistent review log.

        Args:
            file_name: Name of the reviewed file.
            review: Review text to log.
            log_path: Path to the JSON log file.
        """
        import json, time  # noqa: E401

        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        entry = {"file": file_name, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "review": review}

        existing: list = []
        if os.path.exists(log_path):
            try:
                with open(log_path, encoding="utf-8") as fh:
                    existing = json.load(fh)
            except json.JSONDecodeError:
                existing = []

        existing.append(entry)
        with open(log_path, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, indent=2)
