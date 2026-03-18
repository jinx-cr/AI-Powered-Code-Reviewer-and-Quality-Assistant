"""Experiment: local LLM via llama-cpp-python (offline, no API key needed).

Install with:  pip install llama-cpp-python --prefer-binary
Download a GGUF model and set MODEL_PATH below.
"""

MODEL_PATH = "./models/mistral-7b-instruct.Q4_K_M.gguf"


def ask_local(prompt: str, max_tokens: int = 256) -> str:
    """Query a local GGUF model via llama-cpp-python.

    Args:
        prompt: Text prompt to send to the model.
        max_tokens: Maximum tokens to generate.

    Returns:
        str: Generated response text.
    """
    try:
        from llama_cpp import Llama  # type: ignore
        llm = Llama(model_path=MODEL_PATH, n_ctx=2048, verbose=False)
        output = llm(prompt, max_tokens=max_tokens, stop=["</s>"])
        return output["choices"][0]["text"].strip()
    except ImportError:
        return "llama-cpp-python not installed. Run: pip install llama-cpp-python --prefer-binary"
    except Exception as exc:
        return f"Error: {exc}"


if __name__ == "__main__":
    print(ask_local("What is cyclomatic complexity?"))
