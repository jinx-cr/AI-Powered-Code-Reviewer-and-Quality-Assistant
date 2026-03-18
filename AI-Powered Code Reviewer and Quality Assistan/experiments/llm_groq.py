"""Experiment: direct Groq API call without LangChain."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL   = "llama-3.3-70b-versatile"
URL     = "https://api.groq.com/openai/v1/chat/completions"


def ask(prompt: str) -> str:
    """Send a prompt to Groq and return the response text.

    Args:
        prompt: The user message to send.

    Returns:
        str: Model response content.
    """
    if not API_KEY:
        return "No GROQ_API_KEY set in .env"
    resp = requests.post(
        URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 512},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    print(ask("Say hello in one sentence."))
