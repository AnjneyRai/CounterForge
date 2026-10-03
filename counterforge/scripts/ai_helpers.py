"""CounterForge AI Helper Synthesis and Sanity Verification.

This module uses a local LLM to generate the trusted brute-force solution
and test generator from a competitive programming problem statement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Tuple, Union

from counterforge.scripts.engine import run_generator
from counterforge.scripts.llm import extract_cpp, generate

# Standard description of the Generator Contract passed into prompts
CONTRACT_TEXT = (
    "Invocation: ./gen <seed> <size> <mode>\n"
    "- argv[1]: seed (unsigned int) - seeds std::mt19937 deterministically\n"
    "- argv[2]: size (int)          - maximum count of elements / scale\n"
    "- argv[3]: mode (string)        - 'small' (tiny values) or 'large' (extreme values)\n"
    "Output: Exactly ONE valid input conforming to all problem constraints printed to stdout.\n"
    "Determinism: Identical (seed, size, mode) arguments must produce identical output."
)


def _load_asset(relative_path: str) -> str:
    """Loads a template or prompt file from the assets directory.

    Args:
        relative_path: Relative path to the asset file (e.g. 'templates/brute_template.cpp').

    Returns:
        The text content of the asset file.

    Raises:
        FileNotFoundError: If the asset file cannot be located.
    """
    # Try looking in counterforge/assets first, then root assets
    base_counterforge = Path(__file__).resolve().parent.parent / "assets" / relative_path
    if base_counterforge.exists():
        return base_counterforge.read_text(encoding="utf-8")

    base_root = Path(__file__).resolve().parent.parent.parent / "assets" / relative_path
    if base_root.exists():
        return base_root.read_text(encoding="utf-8")

    raise FileNotFoundError(f"CounterForge asset not found: {relative_path}")


def write_helpers(
    problem_text: str,
    model: str,
    out_dir: Union[str, Path],
    llm_fn: Callable[..., str] = generate,
) -> Tuple[Path, Path]:
    """Generates brute.cpp and gen.cpp using a local LLM and saves them to out_dir.

    This function loads prompt templates and starter code, queries the model twice
    (once for the brute force and once for the test generator), extracts the clean
    C++ code blocks, and saves them to the specified directory.

    Args:
        problem_text: Text of the competitive programming problem statement.
        model: Name of the local LLM model to query (e.g. 'qwen2.5-coder:7b').
        out_dir: Directory where brute.cpp and gen.cpp will be written.
        llm_fn: Callable used to query the model (injectable for testing).

    Returns:
        A tuple of (brute_path, gen_path) pointing to the generated source files.
    """
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # 1. Generate Brute Force Solution
    brute_prompt_template = _load_asset("prompts/brute_prompt.txt")
    brute_template = _load_asset("templates/brute_template.cpp")
    brute_prompt = brute_prompt_template.replace("{problem}", problem_text).replace(
        "{template}", brute_template
    )

    brute_raw_response = llm_fn(brute_prompt, model)
    brute_code = extract_cpp(brute_raw_response)
    brute_path = out / "brute.cpp"
    brute_path.write_text(brute_code, encoding="utf-8")

    # 2. Generate Test Generator
    gen_prompt_template = _load_asset("prompts/gen_prompt.txt")
    gen_template = _load_asset("templates/gen_template.cpp")
    gen_prompt = (
        gen_prompt_template.replace("{problem}", problem_text)
        .replace("{contract}", CONTRACT_TEXT)
        .replace("{template}", gen_template)
    )

    gen_raw_response = llm_fn(gen_prompt, model)
    gen_code = extract_cpp(gen_raw_response)
    gen_path = out / "gen.cpp"
    gen_path.write_text(gen_code, encoding="utf-8")

    return brute_path, gen_path


def gen_sanity_check(
    gen_exe: Union[str, Path],
    test_seed: int = 12345,
    test_size: int = 5,
    test_mode: str = "small",
) -> bool:
    """Verifies that a compiled generator runs, outputs non-empty text, and is deterministic.

    The generator is executed twice with the exact same seed, size, and mode.
    If the generator crashes, produces empty output, or produces different outputs
    on the two runs, this function stops and raises a clear error.

    Args:
        gen_exe: Path to the compiled generator binary.
        test_seed: Integer seed used for sanity testing.
        test_size: Size parameter passed during verification.
        test_mode: Mode string ('small' or 'large') passed during verification.

    Returns:
        True if all checks pass cleanly.

    Raises:
        RuntimeError: If the generator produces empty output or non-deterministic results.
    """
    # First execution
    res1 = run_generator(gen_exe, seed=test_seed, size=test_size, mode=test_mode)
    if res1.status != "ok":
        raise RuntimeError(
            f"Generator sanity check failed: generator crashed or timed out on first run:\n{res1.stderr}"
        )

    output1 = res1.stdout.strip()
    if not output1:
        raise RuntimeError("Generator sanity check failed: generator output is empty.")

    # Second execution with identical arguments to verify determinism
    res2 = run_generator(gen_exe, seed=test_seed, size=test_size, mode=test_mode)
    if res2.status != "ok":
        raise RuntimeError(
            f"Generator sanity check failed: generator crashed or timed out on second run:\n{res2.stderr}"
        )

    output2 = res2.stdout.strip()
    if output1 != output2:
        raise RuntimeError(
            "Generator sanity check failed: generator is not deterministic. "
            "Running with the same seed produced different outputs."
        )

    return True
