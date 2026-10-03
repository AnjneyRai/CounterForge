---
name: counterforge
description: >-
  CounterForge finds counterexamples for failing C++ competitive programming
  solutions via stress testing. Use this skill when you encounter Wrong Answer (WA),
  need to find a failing test case, run stress testing against a brute-force
  solution, or isolate a minimal counterexample.
---

# CounterForge

CounterForge is an automated stress-testing tool and pair-programming skill that discovers the smallest input where a C++ competitive programming solution produces an incorrect answer, runtime crash, or timeout.

## Generator Contract

Every test generator used with CounterForge must adhere to the following contract:

```bash
./gen <seed> <size> <mode>
```

- **Arguments**:
  - `<seed>`: Integer seed for deterministic pseudo-random number generation.
  - `<size>`: Problem scale / input size parameter (e.g., number of elements $N$, vertices $V$).
  - `<mode>`: Value distribution mode:
    - `"small"`: Tiny values (e.g., numbers between $-10$ and $10$, dense graphs) ideal for quick manual inspection and spotting corner cases.
    - `"large"`: Extreme values (e.g., numbers up to $10^9$ or $-10^9$, sparse/chain graphs) designed to trigger 32-bit overflows and boundary limits.
- **Behavior**:
  - Prints exactly **ONE** valid test case to standard output (`stdout`).
  - Given the same `seed`, `size`, and `mode`, it **must always** output the exact same test case.

## Usage

### 1. Manual Mode
Run stress testing with user-provided brute-force and generator C++ files:

```bash
python counterforge/scripts/stress.py --solution path/to/solution.cpp --brute path/to/brute.cpp --gen path/to/gen.cpp
```

### 2. AI Mode (Local LLM via Ollama)
When only the problem description is available, let a local Ollama model synthesize the brute-force solution and generator automatically:

```bash
python counterforge/scripts/stress.py --solution path/to/solution.cpp --problem path/to/problem.txt --model qwen2.5-coder:7b
```
*(Or set `COUNTERFORGE_MODEL=qwen2.5-coder:7b` in your environment).*

## CLI Flags

| Flag | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--solution` | `-s` | Path to candidate C++ solution (`.cpp`) **[Required]** | |
| `--problem` | `-p` | Path to problem statement text file (`.txt`) for AI mode | `None` |
| `--model` | `-m` | Local Ollama model name for AI mode | `$COUNTERFORGE_MODEL` |
| `--brute` | `-b` | Path to trusted brute-force reference (`.cpp`) | `None` |
| `--gen` | `-g` | Path to C++ test generator (`.cpp`) | `None` |
| `--max-tests` | `-n` | Maximum test cases to evaluate | `100` |
| `--max-size` | | Maximum scale/size parameter for generator | `20` |
| `--seed` | | Starting random seed | `1` |
| `--time-limit` | `-t` | Time limit per test case in seconds | `1.5` |
| `--mode` | | Generator mode (`small`, `large`, `all`, `both`) | `all` |
| `--build-dir` | | Directory for compiled binaries | `build` |
| `--output-dir` | | Directory to save counterexample evidence | `stress_runs/<timestamp>/` |

## Architecture & Roadmap

- **Phase 1 (Completed)**:
  - Deterministic C++ stress engine (`engine.py`)
  - Pretty terminal reporting with Rich (`report.py`)
  - Command-line runner (`stress.py`)
  - Example problem with deliberate bug (`examples/max-subarray-bug/`)
  - Test suite with pytest (`tests/test_engine.py`)

- **Phase 2 (Completed)**:
  - Zero-dependency local Ollama LLM client (`llm.py`) using Python standard library `urllib`.
  - AI helper synthesis and generator sanity check (`ai_helpers.py`).
  - Starter templates (`assets/templates/`) and prompts (`assets/prompts/`).
  - Timestamped reproducible evidence runs (`stress_runs/<timestamp>/`).
  - Distinct stress loop outcomes (`wrong_answer`, `runtime_error`, `timeout`, `brute_failed`, `no_difference_found`).

- **Phase 3 (Next)**:
  - Trust check with sample verification and LLM retries.
  - Delta-debugging / binary counterexample shrinker.
