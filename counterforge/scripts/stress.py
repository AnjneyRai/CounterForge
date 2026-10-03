"""CounterForge Command-Line Stress-Testing Runner.

This script is the main command-line entry point for CounterForge. It supports:
1. Manual Mode: provide --solution, --brute, and --gen.
2. AI Mode: provide --solution and --problem (plus --model).
   A local Ollama model automatically synthesizes brute.cpp and gen.cpp.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path so 'counterforge' imports succeed when run as a script
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from rich.panel import Panel

from counterforge.scripts.ai_helpers import gen_sanity_check, write_helpers
from counterforge.scripts.engine import compile_cpp, run_stress_test
from counterforge.scripts.llm import check_ollama
from counterforge.scripts.trust_check import (
    _exe_for,
    compile_source,
    load_samples,
    repair_generator,
    trust_brute,
)
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
        "--problem",
        "-p",
        type=str,
        default=None,
        help="Path to the competitive programming problem statement file (.txt) to enable AI mode.",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=os.environ.get("COUNTERFORGE_MODEL"),
        help="Ollama model name (defaults to COUNTERFORGE_MODEL environment variable).",
    )
    parser.add_argument(
        "--brute",
        "-b",
        type=str,
        default=None,
        help="Path to the trusted C++ brute-force reference file (.cpp) (manual mode).",
    )
    parser.add_argument(
        "--gen",
        "-g",
        type=str,
        default=None,
        help="Path to the C++ test generator source file (.cpp) adhering to ./gen <seed> <size> <mode> (manual mode).",
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
        choices=["small", "large", "all", "both"],
        default="all",
        help="Generator mode: 'small' (tiny values), 'large' (extreme values), or 'all'/'both' (alternating).",
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
        default=None,
        help="Directory where failing counterexample evidence will be saved (defaults to stress_runs/<timestamp>/).",
    )
    parser.add_argument(
        "--samples",
        help="Folder with sample tests (1.in / 1.out, ...). Used by the trust check in AI mode.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="How many times the AI may retry a failing brute force or generator (default 3).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Continue even if the AI brute force never passes the samples (not recommended).",
    )
    return parser


def main() -> int:
    """Main entry point for the CounterForge stress testing CLI.

    Returns:
        Exit code: 0 if all tests passed, 1 if a counterexample was found,
        or 2 if compilation / setup / trust check failed.
    """
    print_banner()

    parser = create_argument_parser()
    args = parser.parse_args()

    is_ai_mode = False
    trust_log = None
    quiet = lambda message: console.print(message, markup=False)  # prints text as-is

    # Determine whether AI Mode or Manual Mode is active
    if args.problem and not (args.brute or args.gen):
        is_ai_mode = True
        model_name = args.model

        if not model_name:
            console.print(
                "[bold red]Error:[/bold red] No model specified for AI mode.\n"
                "Please pass [cyan]--model <name>[/cyan] or set the [cyan]COUNTERFORGE_MODEL[/cyan] environment variable.\n"
                "Run [dim]ollama list[/dim] to see installed local models."
            )
            return 2

        problem_path = Path(args.problem).resolve()
        if not problem_path.exists():
            console.print(f"[bold red]Error:[/bold red] Problem file not found: {args.problem}")
            return 2

        problem_text = problem_path.read_text(encoding="utf-8")

        # Verify that Ollama is reachable and the model exists
        try:
            available_models = check_ollama()
        except RuntimeError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            return 2

        model_found = (
            model_name in available_models
            or f"{model_name}:latest" in available_models
            or any(m.startswith(f"{model_name}:") for m in available_models)
        )
        if not model_found:
            console.print(f"[bold red]Error:[/bold red] Model '{model_name}' not found in Ollama.")
            console.print(f"Available models: {', '.join(available_models) if available_models else 'none'}")
            console.print(f"Please run: [cyan]ollama pull {model_name}[/cyan]")
            return 2

        console.print(
            Panel(
                f"[bold yellow]AI Assistance Active[/bold yellow]\n\n"
                f"Model:   [cyan]{model_name}[/cyan]\n"
                f"Problem: [cyan]{args.problem}[/cyan]\n\n"
                f"[bold red]WARNING: These helpers were written by the AI and are NOT proven correct.[/bold red]",
                border_style="yellow",
                title="[bold yellow]CounterForge AI Mode[/bold yellow]",
            )
        )

        ai_dir = Path(args.build_dir) / "ai"
        console.print(f"Synthesizing brute force and generator into [cyan]{ai_dir}[/cyan]...")

        try:
            brute_src, gen_src = write_helpers(problem_text, model_name, ai_dir)
        except Exception as exc:
            console.print(f"[bold red]Error during AI helper synthesis:[/bold red] {exc}")
            return 2

        console.print("  [bold green][OK][/bold green] Brute-force and generator synthesized.")
        brute_src = Path(brute_src)
        gen_src = Path(gen_src)

        # ---- TRUST CHECK (feature 2): verify the AI's brute force on the samples ----
        brute_history = []
        if args.samples:
            try:
                samples = load_samples(args.samples)
            except ValueError as exc:
                console.print(f"[bold red]Error:[/bold red] {exc}")
                return 2

            console.print("\n[bold]Trust check:[/bold] running the AI brute force on the sample tests")
            trust = trust_brute(
                problem_text,
                samples,
                model_name,
                ai_dir,
                max_retries=args.max_retries,
                log=quiet,
            )
            brute_history = trust.history

            if not trust.trusted:
                console.print(
                    "\n[bold red]CounterForge could not get a trustworthy brute force for this problem.[/bold red]"
                )
                console.print(f"Last attempt saved at: [cyan]{trust.code_path}[/cyan]")
                if not args.force:
                    console.print("Check that file by hand, or run again with [cyan]--force[/cyan] to continue anyway.")
                    return 2
                console.print("[bold yellow]--force given: continuing with an UNTRUSTED brute force.[/bold yellow]")
        else:
            console.print(
                "\n[bold yellow]No --samples given: the AI-written brute force is unverified.[/bold yellow]"
            )

        # The generator check needs a compiled brute force
        ok, err = compile_source(brute_src)
        if not ok:
            console.print(f"[bold red]Failed to compile the AI-written brute force:[/bold red]\n{err}")
            return 2

        console.print("\n[bold]Generator check:[/bold] smoke test, with AI repairs if needed")
        gen_ok, gen_history = repair_generator(
            problem_text,
            model_name,
            ai_dir,
            _exe_for(brute_src),
            max_retries=args.max_retries,
            log=quiet,
        )
        if not gen_ok:
            console.print("[bold red]CounterForge could not get a working generator for this problem.[/bold red]")
            console.print(f"Last attempt saved at: [cyan]{gen_src}[/cyan]")
            return 2

        trust_log = {"brute_force": brute_history, "generator": gen_history}

    elif args.brute and args.gen and not args.problem:
        # Manual Mode
        brute_src = Path(args.brute).resolve()
        gen_src = Path(args.gen).resolve()

        if not brute_src.exists():
            console.print(f"[bold red]Error:[/bold red] Brute-force file not found: {args.brute}")
            return 2
        if not gen_src.exists():
            console.print(f"[bold red]Error:[/bold red] Generator file not found: {args.gen}")
            return 2
    else:
        console.print(
            "[bold red]Error:[/bold red] Invalid combination of arguments.\n"
            "  * AI Mode:     Provide [cyan]--problem[/cyan] (and optionally [cyan]--model[/cyan], [cyan]--samples[/cyan]), without --brute/--gen.\n"
            "  * Manual Mode: Provide both [cyan]--brute[/cyan] and [cyan]--gen[/cyan], without --problem."
        )
        return 2

    console.print(f"\n[bold]Starting stress run:[/bold]")
    console.print(f"  - Solution:    [cyan]{args.solution}[/cyan]")
    console.print(f"  - Brute-force: [cyan]{brute_src}[/cyan]")
    console.print(f"  - Generator:   [cyan]{gen_src}[/cyan]")
    console.print(f"  - Max Tests:   {args.max_tests} | Max Size: {args.max_size} | Mode: {args.mode}")
    if is_ai_mode:
        console.print(
            "  [yellow](Note: the brute force and generator are AI-written. "
            "Passing the samples does not prove the brute force is correct.)[/yellow]"
        )
    console.print()

    outcome = run_stress_test(
        solution_src=args.solution,
        brute_src=brute_src,
        gen_src=gen_src,
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
        evidence_dir = save_evidence(
            test_case=outcome.failing_case,
            output_dir=args.output_dir,
            solution_src=args.solution,
            brute_src=brute_src,
            gen_src=gen_src,
        )
        if is_ai_mode:
            console.print(
                "[yellow]Reminder: the brute force was written by an AI. Look at the failing input "
                "and both outputs above, and check by hand which program is right.[/yellow]"
            )
            if trust_log is not None and evidence_dir:
                try:
                    (Path(evidence_dir) / "trust_log.json").write_text(
                        json.dumps(trust_log, indent=2), encoding="utf-8"
                    )
                except OSError:
                    pass
        print_summary(outcome, evidence_dir)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())