"""Unit Tests for LLM Integration and Parsing.

These tests verify that:
1. extract_cpp correctly handles ```cpp, ```c++, plain ```, no fence, and text around fences.
2. check_ollama correctly parses available model lists and raises friendly errors when offline.
3. generate sends correct options and handles 404 / connection errors with helpful instructions.
"""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from counterforge.scripts.llm import check_ollama, extract_cpp, generate


def test_extract_cpp_fenced_cpp() -> None:
    """Verifies that extract_cpp extracts code inside ```cpp code blocks."""
    raw = (
        "```cpp\n"
        "#include <iostream>\n"
        "int main() { return 0; }\n"
        "```"
    )
    expected = "#include <iostream>\nint main() { return 0; }"
    assert extract_cpp(raw) == expected


def test_extract_cpp_fenced_cplusplus() -> None:
    """Verifies that extract_cpp extracts code inside ```c++ code blocks."""
    raw = (
        "```c++\n"
        "#include <vector>\n"
        "int main() { return 0; }\n"
        "```"
    )
    expected = "#include <vector>\nint main() { return 0; }"
    assert extract_cpp(raw) == expected


def test_extract_cpp_plain_fence() -> None:
    """Verifies that extract_cpp extracts code inside plain ``` code blocks without language tag."""
    raw = (
        "```\n"
        "int a = 10;\n"
        "```"
    )
    expected = "int a = 10;"
    assert extract_cpp(raw) == expected


def test_extract_cpp_no_fence() -> None:
    """Verifies that extract_cpp returns the entire stripped text when no markdown fence is present."""
    raw = "  #include <iostream>\nint main() { return 0; }  \n"
    expected = "#include <iostream>\nint main() { return 0; }"
    assert extract_cpp(raw) == expected


def test_extract_cpp_text_around_fence() -> None:
    """Verifies that extract_cpp ignores introductory and concluding chatter around code fences."""
    raw = (
        "Sure, here is your C++ solution:\n\n"
        "```cpp\n"
        "#include <iostream>\n"
        "int main() { return 0; }\n"
        "```\n\n"
        "Good luck with your competitive programming contest!"
    )
    expected = "#include <iostream>\nint main() { return 0; }"
    assert extract_cpp(raw) == expected


def test_check_ollama_success() -> None:
    """Verifies that check_ollama parses the list of installed local models from Ollama's tags API."""
    mock_response = io.BytesIO(
        json.dumps(
            {
                "models": [
                    {"name": "qwen2.5-coder:7b"},
                    {"name": "deepseek-r1:8b"},
                ]
            }
        ).encode("utf-8")
    )

    mock_resp = MagicMock()
    mock_resp.read.side_effect = mock_response.read
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        models = check_ollama()
        assert models == ["qwen2.5-coder:7b", "deepseek-r1:8b"]


def test_check_ollama_offline() -> None:
    """Verifies that check_ollama raises a friendly error when Ollama is not running."""
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("Connection refused"),
    ):
        with pytest.raises(RuntimeError, match="Ollama is not running"):
            check_ollama()


def test_generate_success() -> None:
    """Verifies that generate sends the prompt and reads the response field."""
    mock_response = io.BytesIO(
        json.dumps({"response": "```cpp\nint main(){}\n```"}).encode("utf-8")
    )
    mock_resp = MagicMock()
    mock_resp.read.side_effect = mock_response.read
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        result = generate("Write C++ code", model="qwen2.5-coder:7b")
        assert result == "```cpp\nint main(){}\n```"

        req = mock_urlopen.call_args[0][0]
        data = json.loads(req.data.decode("utf-8"))
        assert data["model"] == "qwen2.5-coder:7b"
        assert data["stream"] is False
        assert data["options"]["temperature"] == 0.2


def test_generate_model_not_pulled() -> None:
    """Verifies that generate suggests 'ollama pull' when the model is not found (404)."""
    error = urllib.error.HTTPError(
        url="http://localhost:11434/api/generate",
        code=404,
        msg="Not Found",
        hdrs=None,  # type: ignore
        fp=io.BytesIO(b'{"error": "model \'missing-model\' not found"}'),
    )

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(RuntimeError, match="ollama pull missing-model"):
            generate("test prompt", model="missing-model")
