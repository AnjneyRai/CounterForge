"""CounterForge Reporting and Evidence Module.

This module formats terminal output using the 'rich' library and saves
reproducible evidence (failing input, expected output, actual output) to disk.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from counterforge.scripts.engine import StressOutcome, StressTestCase

# Global console instance for pretty terminal printing
console = Console()


def print_banner() -> None:
    """Displays a welcoming terminal banner for CounterForge."""
    banner_text = Text()
    banner_text.append("  ___                 _             ___                  \n", style="bold cyan")
    banner_text.append(" / __|___ _  _ _ _  _| |_ ___ _ _  | __|__ _ _ __ _ ___ \n", style="bold cyan")
    banner_text.append("| (__/ _ \\ || | ' \\|  _/ -_) '_| | _/ _ \\ '_/ _` / -_)\n", style="bold blue")
    banner_text.append(" \\___\\___/\\_,_|_||_|\\__\\___|_|   |_| \\___/_| \\__, \\___|\n", style="bold blue")
    banner_text.append("                                             |___/      \n", style="bold blue")
    banner_text.append("Deterministic Stress-Testing & Counterexample Engine for C++", style="bold yellow")

    panel = Panel(
        banner_text,
        title="[bold white]CounterForge v0.1.0[/bold white]",
        subtitle="[dim]Pair-Programming Stress Engine[/dim]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)


def print_compilation_status(target_name: str, ok: bool, error: str = "") -> None:
    """Prints whether a specific C++ target compiled successfully or failed.

    Args:
        target_name: Name of the component (e.g. Solution, Brute Force, Generator).
        ok: True if compilation succeeded, False if it failed.
        error: Compiler error text if compilation failed.
    """
    if ok:
        console.print(f"  [bold green][PASS][/bold green] [bold]{target_name}[/bold] compiled successfully")
    else:
        console.print(f"  [bold red][FAIL][/bold red] [bold]{target_name}[/bold] compilation failed!")
        if error:
            console.print(Panel(error, title=f"[red]{target_name} Errors[/red]", border_style="red"))


def print_test_progress(test_case: StressTestCase) -> None:
    """Prints a concise status line for an individual test case.

    Args:
        test_case: The evaluated test case information.
    """
    meta = f"seed={test_case.seed}, size={test_case.size}, mode={test_case.mode}"

    if test_case.status == "ok":
        console.print(f"  [dim]Test #{test_case.test_number:03d}[/dim] ({meta}) [bold green]PASSED[/bold green] [dim]({test_case.duration * 1000:.1f}ms)[/dim]")
    elif test_case.status == "wrong_answer":
        console.print(f"  [bold]Test #{test_case.test_number:03d}[/bold] ({meta}) [bold red]WRONG ANSWER[/bold red]")
    elif test_case.status == "runtime_error":
        console.print(f"  [bold]Test #{test_case.test_number:03d}[/bold] ({meta}) [bold magenta]RUNTIME ERROR[/bold magenta]")
    elif test_case.status == "timeout":
        console.print(f"  [bold]Test #{test_case.test_number:03d}[/bold] ({meta}) [bold yellow]TIME LIMIT EXCEEDED[/bold yellow]")
    else:
        console.print(f"  [bold]Test #{test_case.test_number:03d}[/bold] ({meta}) [bold red]{test_case.status.upper()}[/bold red]")


def print_bug_report(test_case: StressTestCase) -> None:
    """Renders a detailed, human-readable panel showing the counterexample.

    Args:
        test_case: The failing test case to present to the user.
    """
    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Property", style="bold cyan", width=18)
    table.add_column("Value")

    table.add_row("Test Number", f"#{test_case.test_number}")
    table.add_row("Failure Reason", f"[bold red]{test_case.status.upper()}[/bold red]")
    table.add_row("Generator Seed", str(test_case.seed))
    table.add_row("Problem Size", str(test_case.size))
    table.add_row("Generator Mode", test_case.mode)

    # Format input snippet (cap display length if huge)
    input_preview = test_case.input_text.strip()
    if len(input_preview) > 500:
        input_preview = input_preview[:500] + "\n... (truncated)"
    table.add_row("Failing Input", f"[white]{input_preview}[/white]")

    table.add_row("Expected Output (Brute)", f"[bold green]{test_case.expected_output.strip()}[/bold green]")
    table.add_row("Actual Output (Solution)", f"[bold red]{test_case.actual_output.strip() or '(no output)'}[/bold red]")

    if test_case.error_message:
        table.add_row("Diagnostic Message", f"[yellow]{test_case.error_message}[/yellow]")

    panel = Panel(
        table,
        title=f"[bold red] CounterForge Found a Counterexample (Test #{test_case.test_number}) [/bold red]",
        border_style="red",
        padding=(1, 2),
    )
    console.print()
    console.print(panel)


def save_evidence(test_case: StressTestCase, output_dir: Union[str, Path]) -> Path:
    """Saves the failing test case and comparison outputs to files for debugging.

    Args:
        test_case: The failing test case data.
        output_dir: Folder path where files will be stored.

    Returns:
        The Path to the directory where evidence files were written.
    """
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    input_file = out / "failing_input.in"
    expected_file = out / "expected.out"
    actual_file = out / "actual.out"
    report_file = out / "report.json"

    input_file.write_text(test_case.input_text, encoding="utf-8")
    expected_file.write_text(test_case.expected_output, encoding="utf-8")
    actual_file.write_text(test_case.actual_output, encoding="utf-8")

    report_data = {
        "tool": "CounterForge",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_number": test_case.test_number,
        "seed": test_case.seed,
        "size": test_case.size,
        "mode": test_case.mode,
        "status": test_case.status,
        "error_message": test_case.error_message,
        "duration_seconds": test_case.duration,
        "files": {
            "failing_input": str(input_file),
            "expected_output": str(expected_file),
            "actual_output": str(actual_file),
        },
    }
    report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    return out


def print_summary(outcome: StressOutcome, evidence_dir: Optional[Path] = None) -> None:
    """Prints a closing summary of the stress-testing session.

    Args:
        outcome: The overall stress outcome.
        evidence_dir: Path where failure evidence was saved, if applicable.
    """
    console.print()
    if outcome.build_error:
        panel = Panel(
            f"[bold red]Build Failed[/bold red]\n{outcome.build_error}",
            title="[bold red]CounterForge Error[/bold red]",
            border_style="red",
        )
        console.print(panel)
        return

    if outcome.success:
        summary_text = (
            f"[bold green]All {outcome.total_tested} test cases passed![/bold green]\n"
            f"No discrepancies found between solution and brute-force reference."
        )
        panel = Panel(
            summary_text,
            title="[bold green]CounterForge Run Complete[/bold green]",
            border_style="green",
        )
        console.print(panel)
    else:
        case = outcome.failing_case
        msg = f"[bold red]Found a counterexample on Test #{case.test_number}![/bold red]\n"
        msg += f"Status: [yellow]{case.status}[/yellow]\n"
        if evidence_dir:
            msg += f"Saved failing input & outputs to: [cyan]{evidence_dir}[/cyan]\n"
            msg += f"To re-run with this exact input:\n"
            msg += f"  [dim]./gen {case.seed} {case.size} {case.mode}[/dim]"

        panel = Panel(
            msg,
            title="[bold red]Counterexample Isolated[/bold red]",
            border_style="red",
        )
        console.print(panel)
