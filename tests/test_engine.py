"""Unit and Integration Tests for CounterForge Stress Engine.

These tests use pytest to verify that:
1. C++ compilation handles valid and invalid source files correctly.
2. Program execution accurately captures stdout, runtime crashes, and timeouts.
3. Output comparison properly normalizes whitespace without missing discrepancies.
4. The Generator Contract behaves deterministically.
5. End-to-end stress testing correctly identifies the counterexample in the example problem.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path so 'counterforge' imports resolve cleanly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from counterforge.scripts.engine import (
    compare_outputs,
    compile_cpp,
    get_executable_path,
    run_generator,
    run_program,
    run_stress_test,
)


def test_compile_cpp_success(tmp_path: Path) -> None:
    """Verifies that compile_cpp successfully compiles valid C++ code.

    Why this matters: If valid C++ code cannot compile, stress testing cannot begin.
    """
    cpp_file = tmp_path / "hello.cpp"
    exe_file = tmp_path / "hello"

    cpp_file.write_text(
        '#include <iostream>\nint main() { std::cout << "Hello CounterForge\\n"; return 0; }\n',
        encoding="utf-8",
    )

    ok, error = compile_cpp(cpp_file, exe_file)
    assert ok is True
    assert error == ""
    assert get_executable_path(exe_file).exists()


def test_compile_cpp_syntax_error(tmp_path: Path) -> None:
    """Verifies that compile_cpp returns an error when given invalid C++ code.

    Why this matters: Users need clear compiler diagnostics when their code has typos.
    """
    cpp_file = tmp_path / "bad.cpp"
    exe_file = tmp_path / "bad"

    cpp_file.write_text(
        "int main() { this is not valid c++ code; }\n",
        encoding="utf-8",
    )

    ok, error = compile_cpp(cpp_file, exe_file)
    assert ok is False
    assert len(error) > 0
    assert not get_executable_path(exe_file).exists()


def test_run_program_success(tmp_path: Path) -> None:
    """Verifies that run_program passes stdin, receives stdout, and marks status as ok.

    Why this matters: Stress testing relies on feeding generated input to programs and reading output.
    """
    cpp_file = tmp_path / "echo.cpp"
    exe_file = tmp_path / "echo"

    cpp_file.write_text(
        "#include <iostream>\n"
        "#include <string>\n"
        "int main() {\n"
        "    std::string s;\n"
        "    std::cin >> s;\n"
        '    std::cout << "Echo: " << s << "\\n";\n'
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )

    ok, _ = compile_cpp(cpp_file, exe_file)
    assert ok is True

    result = run_program(exe_file, input_text="CounterForge\n", time_limit=2.0)
    assert result.status == "ok"
    assert result.returncode == 0
    assert result.stdout.strip() == "Echo: CounterForge"


def test_run_program_runtime_error(tmp_path: Path) -> None:
    """Verifies that run_program catches non-zero exit codes as runtime_error.

    Why this matters: Solutions that crash (e.g. segfault, divide by zero) must be flagged.
    """
    cpp_file = tmp_path / "crash.cpp"
    exe_file = tmp_path / "crash"

    cpp_file.write_text(
        "#include <cstdlib>\n"
        "int main() {\n"
        "    return 42;\n"
        "}\n",
        encoding="utf-8",
    )

    ok, _ = compile_cpp(cpp_file, exe_file)
    assert ok is True

    result = run_program(exe_file, input_text="", time_limit=2.0)
    assert result.status == "runtime_error"
    assert result.returncode == 42


def test_run_program_timeout(tmp_path: Path) -> None:
    """Verifies that run_program detects infinite loops and marks status as timeout.

    Why this matters: TLE (Time Limit Exceeded) bugs must be caught without hanging forever.
    """
    cpp_file = tmp_path / "loop.cpp"
    exe_file = tmp_path / "loop"

    cpp_file.write_text(
        "int main() {\n"
        "    while (true) {}\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )

    ok, _ = compile_cpp(cpp_file, exe_file)
    assert ok is True

    result = run_program(exe_file, input_text="", time_limit=0.5)
    assert result.status == "timeout"
    assert "timed out" in result.stderr.lower()


def test_compare_outputs() -> None:
    """Verifies that compare_outputs correctly compares strings and token sequences.

    Why this matters: In competitive programming, extra spaces or trailing newlines should not cause false alarms.
    """
    # Exact match
    assert compare_outputs("42\n", "42") is True

    # Whitespace differences normalized in token mode
    assert compare_outputs("1  2   3 \n", "1 2 3") is True
    assert compare_outputs("1\n2\n3\n", "1 2 3") is True

    # Genuine differences must fail
    assert compare_outputs("42", "43") is False
    assert compare_outputs("1 2", "1 2 3") is False


def test_generator_contract_determinism(tmp_path: Path) -> None:
    """Verifies that the generator contract produces identical outputs for the same seed, size, and mode.

    Why this matters: Stress testing must be reproducible so users can debug the counterexample.
    """
    gen_src = project_root / "examples" / "max-subarray-bug" / "gen.cpp"
    gen_exe = tmp_path / "gen"

    ok, error = compile_cpp(gen_src, gen_exe)
    assert ok is True, f"Failed to compile generator: {error}"

    # Same parameters must yield identical outputs
    run1 = run_generator(gen_exe, seed=123, size=5, mode="small")
    run2 = run_generator(gen_exe, seed=123, size=5, mode="small")
    assert run1.status == "ok"
    assert run2.status == "ok"
    assert run1.stdout == run2.stdout
    assert len(run1.stdout.strip()) > 0

    # Different seeds should produce different outputs
    run3 = run_generator(gen_exe, seed=999, size=5, mode="small")
    assert run3.stdout != run1.stdout


def test_end_to_end_stress_finds_max_subarray_bug(tmp_path: Path) -> None:
    """Verifies that run_stress_test detects the bug in the max-subarray example.

    Why this matters: This tests the entire CounterForge pipeline end-to-end against a known bug.
    """
    example_dir = project_root / "examples" / "max-subarray-bug"
    sol_src = example_dir / "solution.cpp"
    brute_src = example_dir / "brute.cpp"
    gen_src = example_dir / "gen.cpp"

    outcome = run_stress_test(
        solution_src=sol_src,
        brute_src=brute_src,
        gen_src=gen_src,
        max_tests=50,
        max_size=10,
        build_dir=tmp_path / "build",
        mode="all",
    )

    assert outcome.success is False
    assert outcome.failing_case is not None
    assert outcome.failing_case.status == "wrong_answer"
    assert outcome.outcome == "wrong_answer"
    # Kadane initialized to 0 gives 0 on all-negative inputs, whereas brute returns negative
    assert outcome.failing_case.actual_output.strip() == "0"
    assert int(outcome.failing_case.expected_output.strip()) < 0


def test_end_to_end_stress_passes_on_correct_solution(tmp_path: Path) -> None:
    """Verifies that run_stress_test reports success when the solution matches the brute-force reference.

    Why this matters: The tool must not report false positives when a solution is completely correct.
    """
    example_dir = project_root / "examples" / "max-subarray-bug"
    brute_src = example_dir / "brute.cpp"
    gen_src = example_dir / "gen.cpp"

    # Test brute against itself
    outcome = run_stress_test(
        solution_src=brute_src,
        brute_src=brute_src,
        gen_src=gen_src,
        max_tests=10,
        max_size=5,
        build_dir=tmp_path / "build",
        mode="small",
    )

    assert outcome.success is True
    assert outcome.failing_case is None
    assert outcome.total_tested == 10
    assert outcome.outcome == "no_difference_found"


def test_stress_outcome_runtime_error(tmp_path: Path) -> None:
    """Verifies that the stress loop returns the distinct outcome 'runtime_error' when solution crashes.

    Why this matters: Crashing code (e.g. segfault, divide by zero) must be categorized distinctly from WA.
    """
    example_dir = project_root / "examples" / "max-subarray-bug"
    brute_src = example_dir / "brute.cpp"
    gen_src = example_dir / "gen.cpp"

    crash_sol = tmp_path / "crash_sol.cpp"
    crash_sol.write_text(
        "#include <iostream>\n"
        "#include <cstdlib>\n"
        "int main() {\n"
        "    int n;\n"
        "    if (std::cin >> n) {\n"
        "        return 42;\n"
        "    }\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )

    outcome = run_stress_test(
        solution_src=crash_sol,
        brute_src=brute_src,
        gen_src=gen_src,
        max_tests=5,
        max_size=5,
        build_dir=tmp_path / "build",
        mode="small",
    )

    assert outcome.success is False
    assert outcome.outcome == "runtime_error"
    assert outcome.failing_case is not None
    assert outcome.failing_case.status == "runtime_error"


def test_stress_outcome_timeout(tmp_path: Path) -> None:
    """Verifies that the stress loop returns the distinct outcome 'timeout' when solution exceeds time limit.

    Why this matters: TLE bugs must be isolated and flagged as 'timeout'.
    """
    example_dir = project_root / "examples" / "max-subarray-bug"
    brute_src = example_dir / "brute.cpp"
    gen_src = example_dir / "gen.cpp"

    tle_sol = tmp_path / "tle_sol.cpp"
    tle_sol.write_text(
        "#include <iostream>\n"
        "int main() {\n"
        "    int n;\n"
        "    if (std::cin >> n) {\n"
        "        while (true) {}\n"
        "    }\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )

    outcome = run_stress_test(
        solution_src=tle_sol,
        brute_src=brute_src,
        gen_src=gen_src,
        max_tests=5,
        max_size=5,
        time_limit=0.5,
        build_dir=tmp_path / "build",
        mode="small",
    )

    assert outcome.success is False
    assert outcome.outcome == "timeout"
    assert outcome.failing_case is not None
    assert outcome.failing_case.status == "timeout"


def test_stress_outcome_brute_failed(tmp_path: Path) -> None:
    """Verifies that the stress loop returns the distinct outcome 'brute_failed' when brute force fails.

    Why this matters: If the reference brute force is broken, we must not blame the candidate solution.
    """
    example_dir = project_root / "examples" / "max-subarray-bug"
    sol_src = example_dir / "solution.cpp"
    gen_src = example_dir / "gen.cpp"

    broken_brute = tmp_path / "broken_brute.cpp"
    broken_brute.write_text(
        "#include <iostream>\n"
        "#include <cstdlib>\n"
        "int main() {\n"
        "    return 42;\n"
        "}\n",
        encoding="utf-8",
    )

    outcome = run_stress_test(
        solution_src=sol_src,
        brute_src=broken_brute,
        gen_src=gen_src,
        max_tests=5,
        max_size=5,
        build_dir=tmp_path / "build",
        mode="small",
    )

    assert outcome.success is False
    assert outcome.outcome == "brute_failed"
    assert outcome.failing_case is not None
    assert outcome.failing_case.status == "brute_failed"


def test_stress_mode_both(tmp_path: Path) -> None:
    """Verifies that --mode both runs and alternates between small and large modes.

    Why this matters: Users need an easy way to alternate small and large inputs in a single run.
    """
    example_dir = project_root / "examples" / "max-subarray-bug"
    sol_src = example_dir / "solution.cpp"
    brute_src = example_dir / "brute.cpp"
    gen_src = example_dir / "gen.cpp"

    modes_seen = []

    def record_progress(case):
        modes_seen.append(case.mode)

    outcome = run_stress_test(
        solution_src=sol_src,
        brute_src=brute_src,
        gen_src=gen_src,
        max_tests=20,
        max_size=10,
        build_dir=tmp_path / "build",
        mode="both",
        on_test_done=record_progress,
        stop_on_first_bug=False,
    )

    assert "small" in modes_seen
    assert "large" in modes_seen
