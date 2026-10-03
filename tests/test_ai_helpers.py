"""Unit and Integration Tests for CounterForge AI Helpers.

These tests verify that:
1. gen_sanity_check catches an empty-output generator.
2. gen_sanity_check catches a non-deterministic generator.
3. gen_sanity_check passes on a conforming deterministic generator.
4. End-to-end AI mode with a fake llm_fn synthesizes helpers and finds the planted bug.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add project root to sys.path so 'counterforge' imports resolve cleanly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from counterforge.scripts.ai_helpers import gen_sanity_check, write_helpers
from counterforge.scripts.engine import compile_cpp, run_stress_test


def test_gen_sanity_check_catches_empty_output(tmp_path: Path) -> None:
    """Verifies that gen_sanity_check raises a RuntimeError if the generator outputs nothing.

    Why this matters: A generator that prints nothing cannot test solutions.
    """
    empty_cpp = tmp_path / "empty_gen.cpp"
    empty_exe = tmp_path / "empty_gen"

    empty_cpp.write_text(
        "#include <iostream>\n"
        "int main(int argc, char* argv[]) {\n"
        "    // Prints nothing\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )

    ok, error = compile_cpp(empty_cpp, empty_exe)
    assert ok is True, f"Failed to compile empty_gen: {error}"

    with pytest.raises(RuntimeError, match="empty"):
        gen_sanity_check(empty_exe)


def test_gen_sanity_check_catches_nondeterministic_generator(tmp_path: Path) -> None:
    """Verifies that gen_sanity_check raises a RuntimeError if the generator outputs different results.

    Why this matters: If a generator produces different inputs for the same seed, stress runs aren't reproducible.
    """
    nondet_cpp = tmp_path / "nondet_gen.cpp"
    nondet_exe = tmp_path / "nondet_gen"

    nondet_cpp.write_text(
        "#include <iostream>\n"
        "#include <random>\n"
        "int main(int argc, char* argv[]) {\n"
        "    // Ignores seed argument and uses random_device\n"
        "    std::random_device rd;\n"
        "    std::cout << rd() << \"\\n\";\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )

    ok, error = compile_cpp(nondet_cpp, nondet_exe)
    assert ok is True, f"Failed to compile nondet_gen: {error}"

    with pytest.raises(RuntimeError, match="not deterministic"):
        gen_sanity_check(nondet_exe)


def test_gen_sanity_check_passes_deterministic_generator(tmp_path: Path) -> None:
    """Verifies that gen_sanity_check succeeds on a conforming, deterministic generator.

    Why this matters: Valid generators must pass verification without false alarms.
    """
    gen_src = project_root / "examples" / "max-subarray-bug" / "gen.cpp"
    gen_exe = tmp_path / "valid_gen"

    ok, error = compile_cpp(gen_src, gen_exe)
    assert ok is True, f"Failed to compile valid generator: {error}"

    assert gen_sanity_check(gen_exe) is True


def test_end_to_end_ai_mode_with_fake_llm(tmp_path: Path) -> None:
    """Verifies end-to-end AI mode using an injectable fake llm_fn.

    Why this matters: Validates prompt rendering, code extraction, and bug discovery
    in complete isolation without requiring a live Ollama server.
    """
    example_dir = project_root / "examples" / "max-subarray-bug"
    problem_text = (example_dir / "problem.txt").read_text(encoding="utf-8")
    expected_brute_code = (example_dir / "brute.cpp").read_text(encoding="utf-8")
    expected_gen_code = (example_dir / "gen.cpp").read_text(encoding="utf-8")
    solution_src = example_dir / "solution.cpp"

    prompts_received = []

    def fake_llm(prompt: str, model: str) -> str:
        prompts_received.append((prompt, model))
        if "BRUTE FORCE" in prompt:
            return f"Here is the brute force:\n```cpp\n{expected_brute_code}\n```"
        else:
            return f"Here is the generator:\n```cpp\n{expected_gen_code}\n```"

    ai_out_dir = tmp_path / "ai"
    brute_path, gen_path = write_helpers(
        problem_text=problem_text,
        model="fake-qwen",
        out_dir=ai_out_dir,
        llm_fn=fake_llm,
    )

    # Verify both helper files were generated and written
    assert brute_path.exists()
    assert gen_path.exists()
    assert len(prompts_received) == 2
    assert "fake-qwen" == prompts_received[0][1]

    # Verify sanity check passes on the AI-written generator
    gen_exe = tmp_path / "ai_gen"
    ok, err = compile_cpp(gen_path, gen_exe)
    assert ok is True, f"Compilation failed: {err}"
    assert gen_sanity_check(gen_exe) is True

    # Run stress test end-to-end with the AI-written helpers
    outcome = run_stress_test(
        solution_src=solution_src,
        brute_src=brute_path,
        gen_src=gen_path,
        max_tests=50,
        max_size=10,
        build_dir=tmp_path / "build",
        mode="all",
    )

    # Must find the planted bug
    assert outcome.success is False
    assert outcome.outcome == "wrong_answer"
    assert outcome.failing_case is not None
    assert outcome.failing_case.actual_output.strip() == "0"
    assert int(outcome.failing_case.expected_output.strip()) < 0
