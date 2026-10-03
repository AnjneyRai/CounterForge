"""trust_check.py - CounterForge's TRUST CHECK (feature 2).

Problem: the AI writes the brute force, and a wrong brute force causes false alarms.
Fix: before using it, run it on the problem's SAMPLE tests (answers we know are
right). If it fails, show the model what went wrong and ask for a fix. Repeat a few
times, then give up honestly.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

# Lets this file also be run directly: python counterforge/scripts/trust_check.py
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from counterforge.scripts.llm import extract_cpp, generate  # noqa: E402

PROMPT_DIR = Path(__file__).resolve().parents[1] / "assets" / "prompts"

CONTRACT = (
    "The program is run as: ./gen <seed> <size> <mode>\n"
    "It prints exactly ONE valid input for the problem to standard output.\n"
    "The same seed, size and mode must always print the same input.\n"
    "mode is 'small' (small values) or 'large' (values near the limits).\n"
    "size is the maximum number of elements (or the main dimension)."
)


@dataclass
class Sample:
    """One sample test: its name, the input, and the known-correct output."""
    name: str
    input_text: str
    expected: str


@dataclass
class TrustResult:
    """Outcome of the trust loop: trusted or not, how many tries, and a log."""
    trusted: bool
    attempts_used: int
    history: List[dict] = field(default_factory=list)
    code_path: Optional[Path] = None


# ---------- small helpers (compile, run, compare) ----------

def _exe_for(source: Path) -> Path:
    """Where the compiled program for a .cpp file is stored."""
    return source.with_suffix(".exe" if os.name == "nt" else ".bin")


def compile_source(source: Path) -> Tuple[bool, str]:
    """Compile a C++ file with g++. Returns (worked, compiler_error_text)."""
    try:
        done = subprocess.run(
            ["g++", "-O2", "-std=c++17", str(source), "-o", str(_exe_for(source))],
            capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return False, "g++ was not found. Install a C++ compiler first."
    except subprocess.TimeoutExpired:
        return False, "Compiling took too long."
    return done.returncode == 0, done.stderr.strip()[:1500]


def run_exe(exe: Path, input_text: str = "", time_limit: float = 2.0,
            args: Sequence[str] = ()) -> Tuple[str, str, str]:
    """Run a program. Returns (status, stdout, stderr); status is
    'ok', 'runtime_error' or 'timeout'."""
    try:
        done = subprocess.run([str(exe), *args], input=input_text,
                              capture_output=True, text=True, timeout=time_limit)
    except subprocess.TimeoutExpired:
        return "timeout", "", ""
    status = "ok" if done.returncode == 0 else "runtime_error"
    return status, done.stdout, done.stderr


def fill_prompt(file_name: str, **values: str) -> str:
    """Load a prompt file and replace {placeholders} with real text."""
    text = (PROMPT_DIR / file_name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    return text


def ask_model(prompt: str, model: str, llm_fn: Callable) -> str:
    """Send a prompt to the model and return just the C++ code it wrote."""
    return extract_cpp(llm_fn(prompt, model))


# ---------- samples ----------

def load_samples(samples_dir: str) -> List[Sample]:
    """Pair every N.in with N.out in a folder. Errors clearly if unpaired/empty."""
    folder = Path(samples_dir)
    inputs = sorted(folder.glob("*.in"))
    if not inputs:
        raise ValueError(f"No .in sample files found in {folder}")
    samples = []
    for in_file in inputs:
        out_file = in_file.with_suffix(".out")
        if not out_file.exists():
            raise ValueError(f"Sample {in_file.name} has no matching {out_file.name}")
        samples.append(Sample(in_file.stem, in_file.read_text(), out_file.read_text()))
    return samples


def check_brute_on_samples(brute_exe: Path, samples: List[Sample],
                           time_limit: float = 2.0) -> List[dict]:
    """Run the brute force on every sample. Returns a list of failures (empty = all pass)."""
    failures = []
    for s in samples:
        status, out, _ = run_exe(brute_exe, s.input_text, time_limit)
        if status == "ok" and out.split() != s.expected.split():
            status = "wrong_answer"
        if status != "ok":
            failures.append({"sample": s.name, "status": status, "input": s.input_text,
                             "expected": s.expected, "actual": out})
    return failures


def _short(f: dict) -> str:
    """One-line description of a failure for the terminal."""
    if f["status"] == "wrong_answer":
        exp, got = " ".join(f["expected"].split())[:25], " ".join(f["actual"].split())[:25]
        return f"sample {f['sample']}: expected {exp}, got {got}"
    return f"sample {f['sample']}: {f['status']}"


def _long(f: dict) -> str:
    """Detailed failure text that is sent back to the model."""
    head = {"wrong_answer": "wrong answer", "runtime_error": "crashed (runtime error)",
            "timeout": "took too long (time limit exceeded)"}[f["status"]]
    text = f"Sample {f['sample']}: {head}.\nInput:\n{f['input']}\nExpected output:\n{f['expected']}"
    if f["status"] == "wrong_answer":
        text += f"\nYour program printed:\n{f['actual']}"
    return text[:1500]


# ---------- the trust loop for the brute force ----------

def trust_brute(problem_text: str, samples: List[Sample], model: str, work_dir,
                max_retries: int = 3, llm_fn: Callable = generate,
                time_limit: float = 2.0, log: Callable = print) -> TrustResult:
    """Check work_dir/brute.cpp on the samples; on failure ask the model to fix it
    and try again, up to max_retries repairs."""
    brute_src = Path(work_dir) / "brute.cpp"
    result = TrustResult(False, 0, [], brute_src)
    for attempt in range(1, max_retries + 2):
        result.attempts_used = attempt
        ok, err = compile_source(brute_src)
        if not ok:
            short, failure = "compile error", "Compile error:\n" + err
        else:
            fails = check_brute_on_samples(_exe_for(brute_src), samples, time_limit)
            if not fails:
                note = f"{len(samples)}/{len(samples)} samples"
                result.history.append({"attempt": attempt, "result": "pass", "detail": note})
                result.trusted = True
                log(f"  attempt {attempt}  PASS  {note}")
                return result
            short, failure = _short(fails[0]), _long(fails[0])
        result.history.append({"attempt": attempt, "result": "fail", "detail": short})
        log(f"  attempt {attempt}  FAIL  {short}")
        if attempt > max_retries:
            break
        try:
            prompt = fill_prompt("brute_repair_prompt.txt", problem=problem_text,
                                 code=brute_src.read_text(), failure=failure)
            brute_src.write_text(ask_model(prompt, model, llm_fn) + "\n")
        except Exception as exc:  # model down, timeout, etc.
            log(f"  could not ask the model for a repair: {exc}")
            break
    return result


# ---------- the generator smoke test and repair ----------

def smoke_test_generator(gen_exe: Path, brute_exe: Path,
                         time_limit: float = 2.0) -> Optional[str]:
    """Try the generator on a few small inputs. Returns a problem description,
    or None if everything looks fine."""
    for seed in range(1, 9):
        for size in (1, 3, 5):
            args = [str(seed), str(size), "small"]
            where = f"gen {seed} {size} small"
            status, out, _ = run_exe(gen_exe, "", time_limit, args)
            if status != "ok":
                return f"{where}: the generator crashed or timed out."
            if not out.strip():
                return f"{where}: the generator printed nothing."
            _, again, _ = run_exe(gen_exe, "", time_limit, args)
            if again != out:
                return f"{where}: printed different output on a second run (must be deterministic)."
            status, _, _ = run_exe(brute_exe, out, time_limit)
            if status != "ok":
                return (f"{where}: the trusted brute force crashed or timed out on this "
                        f"input, so the input may be invalid.\nInput was:\n{out[:500]}")
    return None


def repair_generator(problem_text: str, model: str, work_dir, brute_exe: Path,
                     max_retries: int = 3, llm_fn: Callable = generate,
                     time_limit: float = 2.0, log: Callable = print) -> Tuple[bool, List[dict]]:
    """Check work_dir/gen.cpp with the smoke test; ask the model to repair it on failure."""
    gen_src = Path(work_dir) / "gen.cpp"
    history: List[dict] = []
    for attempt in range(1, max_retries + 2):
        ok, err = compile_source(gen_src)
        problem = None if ok else "Compile error:\n" + err
        if ok:
            problem = smoke_test_generator(_exe_for(gen_src), brute_exe, time_limit)
        if problem is None:
            history.append({"attempt": attempt, "result": "pass"})
            log(f"  generator attempt {attempt}  PASS")
            return True, history
        history.append({"attempt": attempt, "result": "fail", "detail": problem[:200]})
        log(f"  generator attempt {attempt}  FAIL  {problem.splitlines()[0][:80]}")
        if attempt > max_retries:
            break
        try:
            prompt = fill_prompt("gen_repair_prompt.txt", problem=problem_text,
                                 contract=CONTRACT, code=gen_src.read_text(), failure=problem)
            gen_src.write_text(ask_model(prompt, model, llm_fn) + "\n")
        except Exception as exc:
            log(f"  could not ask the model for a repair: {exc}")
            break
    return False, history


# ---------- run this file directly to test the trust check on its own ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="CounterForge trust check")
    parser.add_argument("--problem", required=True)
    parser.add_argument("--samples", required=True)
    parser.add_argument("--model", default=os.environ.get("COUNTERFORGE_MODEL"))
    parser.add_argument("--work-dir", default="build/ai",
                        help="folder that already holds brute.cpp and gen.cpp")
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()
    if not args.model:
        print("Pass --model or set COUNTERFORGE_MODEL.")
        return 2
    problem_text = Path(args.problem).read_text(encoding="utf-8")
    print("Trust check on the brute force:")
    result = trust_brute(problem_text, load_samples(args.samples), args.model,
                         args.work_dir, args.max_retries)
    if not result.trusted:
        print("CounterForge could not get a trustworthy brute force for this problem.")
        print(f"Last attempt is saved at: {result.code_path}")
        return 1
    print("Trust check on the generator:")
    ok, _ = repair_generator(problem_text, args.model, args.work_dir,
                             _exe_for(result.code_path), args.max_retries)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())