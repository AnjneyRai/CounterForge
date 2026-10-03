"""CounterForge Ollama LLM Client.

This module provides simple, zero-dependency functions to communicate with a
local Ollama instance. It uses only Python's standard library (urllib and json).
No external packages or cloud API keys are used.
"""

from __future__ import annotations

import http.client
import json
import re
import urllib.error
import urllib.request
from typing import List


def check_ollama(host: str = "http://localhost:11434") -> List[str]:
    """Checks if Ollama is running and returns the list of available local models.

    Args:
        host: URL where Ollama is listening (default: http://localhost:11434).

    Returns:
        A list of model name strings (e.g. ['qwen2.5-coder:7b']).

    Raises:
        RuntimeError: If Ollama is not running or unreachable.
    """
    url = f"{host.rstrip('/')}/api/tags"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [
                m["name"]
                for m in data.get("models", [])
                if isinstance(m, dict) and "name" in m
            ]
            return models
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        raise RuntimeError(
            f"Ollama is not running at {host}. Start Ollama, then try again."
        ) from exc


def generate(
    prompt: str,
    model: str,
    host: str = "http://localhost:11434",
    timeout: float = 300.0,
) -> str:
    """Sends a generation prompt to a local Ollama model and returns its response.

    Args:
        prompt: The prompt text to send to the model.
        model: Name of the local Ollama model (e.g. 'qwen2.5-coder:7b').
        host: URL where Ollama is listening.
        timeout: Maximum time in seconds to wait for model completion.

    Returns:
        The generated text string from the model.

    Raises:
        RuntimeError: If the model is not pulled, Ollama is down, or generation fails.
    """
    url = f"{host.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404 or "not found" in err_body.lower():
            raise RuntimeError(
                f"Model '{model}' is not pulled in Ollama. Run: ollama pull {model}"
            ) from exc
        raise RuntimeError(
            f"Ollama request failed with HTTP error {exc.code}: {err_body}"
        ) from exc
    except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:
        raise RuntimeError(
            f"Ollama is not running at {host}. Start Ollama, then try again."
        ) from exc


def extract_cpp(text: str) -> str:
    """Extracts C++ source code from text, stripping markdown code fences.

    This function searches for the first ```cpp, ```c++, or plain ``` code block.
    If no code block fence is present, it returns the whole text. Surrounding
    whitespace is always stripped.

    Args:
        text: The raw output text received from the model.

    Returns:
        The clean C++ code string.
    """
    # Find the first fenced block matching ```cpp, ```c++, or ```
    pattern = r"```(?:cpp|c\+\+)?\s*\n?(.*?)```"
    match = re.search(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()
