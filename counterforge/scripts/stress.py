"""CounterForge Command-Line Stress-Testing Runner.

This script is the main command-line entry point for CounterForge. It parses
user arguments, initiates C++ compilation and differential testing, and reports
any discovered counterexamples to the terminal.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path so 'counterforge' imports succeed when run as a script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from counterforge.scripts.engine import run_stress_test
from counterforge.scripts.report import (
    console,
    print_banner,
    print_bug_report,
    print_summary,
    print_test_progress,
    save_evidence,
)


def create_argument_parser() -> argparse.ArgumentParser:
    """Builds and returns the command-line argument parser for CounterForge.

    Returns:
        An argparse.ArgumentParser configured with stress testing flags.
    """
    parser = argparse.ArgumentParser(
        prog="counterforge",
        description="CounterForge: Find the smallest failing input for your C++ solution via stress testing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--solution",
        "-s",
        type=str,
        required=True,
        help="Path to the C++ candidate solution source file (.cpp).",
    )
    parser.add_argument(
        "--brute",
        "-b",
        type=str,
        required=True,
        help="Path to the trusted C++ brute-force reference file (.cpp).",
    )
    parser.add_argument(
        "--gen",
        "-g",
        type=str,
        required=True,
        help="Path to the C++ test generator source file (.cpp) adhering to ./gen <seed> <size> <mode>.",
    )
    parser.add_argument(
        "--max-tests",
        "-n",
        type=int,
        default=100,
        help="Maximum number of test cases to generate and evaluate.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=20,
        help="Maximum scale/size parameter to pass to the generator.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1,
        help="Starting random seed for reproducible runs.",
    )
    parser.add_argument(
        "--time-limit",
        "-t",
        type=float,
        default=1.5,
        help="Execution time limit per test case in seconds.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["small", "large", "all"],
        default="all",
        help="Generator mode: 'small' (tiny values), 'large' (extreme values), or 'all' (alternates).",
    )
    parser.add_argument(
        "--build-dir",
        type=str,
        default="build",
        help="Directory to store compiled binaries.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="stress_runs/latest",
        help="Directory where failing counterexample evidence will be saved.",
    )

    return parser


def main() -> int:
    """Main entry point for the CounterForge stress testing CLI.

    Returns:
        Exit code: 0 if all tests passed, 1 if a counterexample was found,
        or 2 if compilation / setup failed.
    """
    print_banner()

    parser = create_argument_parser()
    args = parser.parse_args()

    console.print(f"[bold]Starting stress run:[/bold]")
    console.print(f"  - Solution:    [cyan]{args.solution}[/cyan]")
    console.print(f"  - Brute-force: [cyan]{args.brute}[/cyan]")
    console.print(f"  - Generator:   [cyan]{args.gen}[/cyan]")
    console.print(f"  - Max Tests:   {args.max_tests} | Max Size: {args.max_size} | Mode: {args.mode}")
    console.print()

    outcome = run_stress_test(
        solution_src=args.solution,
        brute_src=args.brute,
        gen_src=args.gen,
        max_tests=args.max_tests,
        max_size=args.max_size,
        start_seed=args.seed,
        time_limit=args.time_limit,
        build_dir=args.build_dir,
        mode=args.mode,
        on_test_done=print_test_progress,
        stop_on_first_bug=True,
    )

    if outcome.build_error:
        print_summary(outcome)
        return 2

    if outcome.success:
        print_summary(outcome)
        return 0

    # Counterexample found!
    if outcome.failing_case:
        print_bug_report(outcome.failing_case)
        evidence_dir = save_evidence(outcome.failing_case, args.output_dir)
        print_summary(outcome, evidence_dir)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
