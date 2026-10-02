"""CounterForge Deterministic Stress-Testing Engine.

This module provides the core functionality to compile C++ code, execute
programs safely with resource and time limits, and run differential stress
testing against a brute-force reference.

GENERATOR CONTRACT:
    Every test generator used by CounterForge must follow this invocation pattern:
        ./gen <seed> <size> <mode>
    - <seed>: An integer used to seed random generation deterministically.
    - <size>: Problem scale parameter (e.g., array size, number of nodes).
    - <mode>: Either "small" (tiny numbers/structures) or "large" (extreme/boundary numbers).
    - Output: Exactly ONE valid input printed to standard output (stdout).
    - Determinism: Identical (seed, size, mode) arguments must produce identical output.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple, Union


@dataclass
class RunResult:
    """Represents the outcome of executing an external program.

    Attributes:
        status: The execution status ("ok", "runtime_error", or "timeout").
        stdout: Output text received from the program on standard output.
        stderr: Error text received from the program on standard error.
        returncode: Exit code returned by the process (0 indicates clean exit).
        duration: Elapsed execution time in seconds.
    """

    status: str
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    duration: float = 0.0


@dataclass
class StressTestCase:
    """Represents a single test case generated and evaluated during stress testing.

    Attributes:
        test_number: Sequential index of the test (1-based).
        seed: Random seed used to generate this test case.
        size: Size parameter passed to the generator.
        mode: Generator mode ("small" or "large").
        input_text: The test input fed to the programs.
        expected_output: Output from the trusted brute-force program.
        actual_output: Output from the solution program being tested.
        status: Test result ("ok", "wrong_answer", "runtime_error", or "timeout").
        error_message: Optional error message if a failure occurred.
        duration: Execution duration of the solution program in seconds.
    """

    test_number: int
    seed: int
    size: int
    mode: str
    input_text: str
    expected_output: str = ""
    actual_output: str = ""
    status: str = "ok"
    error_message: str = ""
    duration: float = 0.0


@dataclass
class StressOutcome:
    """Represents the final result of a complete stress-testing session.

    Attributes:
        success: True if all tests passed without discrepancies, False otherwise.
        total_tested: Total number of test cases evaluated.
        failing_case: The first failing test case encountered, or None if all passed.
        build_error: Error message if C++ compilation failed, or None.
    """

    success: bool
    total_tested: int
    failing_case: Optional[StressTestCase] = None
    build_error: Optional[str] = None


def get_executable_path(base_path: Union[str, Path]) -> Path:
    """Returns a platform-appropriate executable path, appending .exe on Windows.

    Args:
        base_path: Desired executable path without or with extension.

    Returns:
        A Path object with '.exe' appended if running on Windows.
    """
    path = Path(base_path)
    if sys.platform == "win32" or os.name == "nt":
        if path.suffix.lower() != ".exe":
            return path.with_suffix(".exe")
    return path


def compile_cpp(
    src_path: Union[str, Path],
    out_path: Union[str, Path],
    extra_flags: Sequence[str] = (),
) -> Tuple[bool, str]:
    """Compiles a C++ source file into an executable binary using g++.

    Args:
        src_path: Path to the .cpp source file.
        out_path: Path where the compiled executable should be written.
        extra_flags: Additional compiler flags to pass to g++.

    Returns:
        A tuple of (ok, error_text). If compilation succeeds, ok is True and
        error_text is empty. If compilation fails, ok is False and error_text
        contains the compiler diagnostics.
    """
    src = Path(src_path).resolve()
    out = get_executable_path(out_path).resolve()

    if not src.exists():
        return False, f"Source file does not exist: {src}"

    # Ensure the parent directory for the output executable exists
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "g++",
        "-O2",
        "-std=c++17",
        str(src),
        "-o",
        str(out),
        *extra_flags,
    ]

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode == 0:
            return True, ""
        return False, process.stderr.strip() or process.stdout.strip()
    except FileNotFoundError:
        return False, "g++ compiler not found in system PATH. Please ensure GCC/g++ is installed."
    except Exception as exc:
        return False, f"Unexpected compilation error: {exc}"


def run_program(
    exe_path: Union[str, Path],
    input_text: str,
    time_limit: float = 2.0,
) -> RunResult:
    """Executes a binary with standard input text and enforces a time limit.

    Args:
        exe_path: Path to the executable to run.
        input_text: Text string to pass into the program's standard input.
        time_limit: Maximum allowed runtime in seconds before timing out.

    Returns:
        A RunResult object describing the outcome, stdout, stderr, and duration.
    """
    exe = get_executable_path(exe_path).resolve()
    if not exe.exists():
        return RunResult(
            status="runtime_error",
            stderr=f"Executable file not found: {exe}",
            returncode=-1,
        )

    start_time = time.perf_counter()
    try:
        process = subprocess.run(
            [str(exe)],
            input=input_text,
            capture_output=True,
            text=True,
            timeout=time_limit,
            check=False,
        )
        elapsed = time.perf_counter() - start_time

        if process.returncode == 0:
            return RunResult(
                status="ok",
                stdout=process.stdout,
                stderr=process.stderr,
                returncode=0,
                duration=elapsed,
            )
        return RunResult(
            status="runtime_error",
            stdout=process.stdout,
            stderr=process.stderr,
            returncode=process.returncode,
            duration=elapsed,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start_time
        return RunResult(
            status="timeout",
            stdout=exc.stdout or "" if isinstance(exc.stdout, str) else "",
            stderr=f"Time Limit Exceeded (timed out after {time_limit:.2f} seconds)",
            returncode=-1,
            duration=elapsed,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        return RunResult(
            status="runtime_error",
            stderr=f"Failed to execute program: {exc}",
            returncode=-1,
            duration=elapsed,
        )


def run_generator(
    gen_exe: Union[str, Path],
    seed: int,
    size: int,
    mode: str,
    time_limit: float = 5.0,
) -> RunResult:
    """Runs a compiled generator following the CounterForge Generator Contract.

    Args:
        gen_exe: Path to the compiled generator executable.
        seed: Random seed integer.
        size: Scale parameter (e.g. array length).
        mode: Value distribution mode ("small" or "large").
        time_limit: Timeout in seconds for generator execution.

    Returns:
        A RunResult object where stdout contains the generated test input.
    """
    exe = get_executable_path(gen_exe).resolve()
    if not exe.exists():
        return RunResult(
            status="runtime_error",
            stderr=f"Generator executable not found: {exe}",
            returncode=-1,
        )

    start_time = time.perf_counter()
    try:
        process = subprocess.run(
            [str(exe), str(seed), str(size), mode],
            capture_output=True,
            text=True,
            timeout=time_limit,
            check=False,
        )
        elapsed = time.perf_counter() - start_time
        if process.returncode == 0:
            return RunResult(
                status="ok",
                stdout=process.stdout,
                stderr=process.stderr,
                returncode=0,
                duration=elapsed,
            )
        return RunResult(
            status="runtime_error",
            stdout=process.stdout,
            stderr=process.stderr,
            returncode=process.returncode,
            duration=elapsed,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start_time
        return RunResult(
            status="timeout",
            stderr=f"Generator timed out after {time_limit:.2f} seconds",
            returncode=-1,
            duration=elapsed,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        return RunResult(
            status="runtime_error",
            stderr=f"Failed to run generator: {exc}",
            returncode=-1,
            duration=elapsed,
        )


def compare_outputs(actual: str, expected: str, token_mode: bool = True) -> bool:
    """Compares actual and expected outputs, ignoring harmless whitespace differences.

    Args:
        actual: Output string produced by the candidate solution.
        expected: Output string produced by the trusted brute-force solution.
        token_mode: If True, splits outputs into whitespace-delimited tokens
            and compares token sequences. If False, strips leading and trailing
            whitespace from the full output strings.

    Returns:
        True if the outputs are equivalent, False if there is a discrepancy.
    """
    if token_mode:
        actual_tokens = actual.split()
        expected_tokens = expected.split()
        return actual_tokens == expected_tokens
    return actual.strip() == expected.strip()


def run_stress_test(
    solution_src: Union[str, Path],
    brute_src: Union[str, Path],
    gen_src: Union[str, Path],
    max_tests: int = 100,
    max_size: int = 20,
    start_seed: int = 1,
    time_limit: float = 1.5,
    build_dir: Union[str, Path] = "build",
    mode: str = "all",
    token_mode: bool = True,
    on_test_done: Optional[Callable[[StressTestCase], None]] = None,
    stop_on_first_bug: bool = True,
) -> StressOutcome:
    """Executes a complete deterministic stress-testing run.

    This function compiles the solution, brute-force, and generator source files,
    then generates test cases starting with small sizes and seeds to find the
    smallest input where the solution fails.

    Args:
        solution_src: Path to the C++ solution file to test.
        brute_src: Path to the trusted C++ brute-force file.
        gen_src: Path to the C++ generator file.
        max_tests: Total number of test cases to generate and run.
        max_size: Maximum size parameter to pass to the generator.
        start_seed: Starting seed integer.
        time_limit: Timeout limit for each test execution in seconds.
        build_dir: Directory where compiled binaries will be stored.
        mode: Generator mode: "small", "large", or "all" (alternating).
        token_mode: Whether to compare outputs token-by-token.
        on_test_done: Optional callback invoked after each test case completes.
        stop_on_first_bug: If True, halts immediately when the first bug is found.

    Returns:
        A StressOutcome detailing whether all tests passed or a bug was found.
    """
    build_path = Path(build_dir).resolve()
    build_path.mkdir(parents=True, exist_ok=True)

    solution_exe = build_path / "solution"
    brute_exe = build_path / "brute"
    gen_exe = build_path / "gen"

    # Step 1: Compile all three C++ files
    targets = [
        ("Solution", solution_src, solution_exe),
        ("Brute Force", brute_src, brute_exe),
        ("Generator", gen_src, gen_exe),
    ]

    for name, src, exe in targets:
        ok, error = compile_cpp(src, exe)
        if not ok:
            return StressOutcome(
                success=False,
                total_tested=0,
                build_error=f"Failed to compile {name} ({src}):\n{error}",
            )

    # Step 2: Determine mode sequence
    # Searching small sizes first guarantees the counterexample found is minimal
    modes_to_test = ["small", "large"] if mode == "all" else [mode]

    total_tested = 0
    current_seed = start_seed

    # We gradually increase size from 1 to max_size so smallest inputs are tested first
    size = 1
    tests_per_size = max(2, max_tests // max_size) if max_size > 0 else 5

    while total_tested < max_tests:
        for m in modes_to_test:
            if total_tested >= max_tests:
                break

            total_tested += 1
            test_number = total_tested

            # Run generator
            gen_res = run_generator(gen_exe, current_seed, size, m)
            if gen_res.status != "ok":
                failing_case = StressTestCase(
                    test_number=test_number,
                    seed=current_seed,
                    size=size,
                    mode=m,
                    input_text="",
                    status="generator_error",
                    error_message=f"Generator failed: {gen_res.stderr}",
                )
                if on_test_done:
                    on_test_done(failing_case)
                return StressOutcome(
                    success=False,
                    total_tested=total_tested,
                    failing_case=failing_case,
                )

            input_text = gen_res.stdout

            # Run trusted brute force
            brute_res = run_program(brute_exe, input_text, time_limit=time_limit * 2.0)
            if brute_res.status != "ok":
                failing_case = StressTestCase(
                    test_number=test_number,
                    seed=current_seed,
                    size=size,
                    mode=m,
                    input_text=input_text,
                    status="brute_error",
                    error_message=f"Trusted brute-force crashed/timed out: {brute_res.stderr}",
                )
                if on_test_done:
                    on_test_done(failing_case)
                return StressOutcome(
                    success=False,
                    total_tested=total_tested,
                    failing_case=failing_case,
                )

            expected_output = brute_res.stdout

            # Run candidate solution
            sol_res = run_program(solution_exe, input_text, time_limit=time_limit)

            test_case = StressTestCase(
                test_number=test_number,
                seed=current_seed,
                size=size,
                mode=m,
                input_text=input_text,
                expected_output=expected_output,
                actual_output=sol_res.stdout,
                duration=sol_res.duration,
            )

            if sol_res.status == "timeout":
                test_case.status = "timeout"
                test_case.error_message = f"Time Limit Exceeded (> {time_limit:.2f}s)"
            elif sol_res.status == "runtime_error":
                test_case.status = "runtime_error"
                test_case.error_message = f"Runtime Error (exit code {sol_res.returncode}): {sol_res.stderr.strip()}"
            else:
                matches = compare_outputs(sol_res.stdout, expected_output, token_mode=token_mode)
                if matches:
                    test_case.status = "ok"
                else:
                    test_case.status = "wrong_answer"
                    test_case.error_message = "Output mismatch against brute force."

            if on_test_done:
                on_test_done(test_case)

            if test_case.status != "ok":
                if stop_on_first_bug:
                    return StressOutcome(
                        success=False,
                        total_tested=total_tested,
                        failing_case=test_case,
                    )

            current_seed += 1

            # Step up size gradually
            if total_tested % tests_per_size == 0 and size < max_size:
                size += 1

    return StressOutcome(
        success=True,
        total_tested=total_tested,
        failing_case=None,
    )
