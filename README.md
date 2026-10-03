# CounterForge

CounterForge is an open-source stress-testing tool and agent skill designed to find the smallest input where a C++ competitive programming solution produces a Wrong Answer (WA), Runtime Error (RE), or Time Limit Exceeded (TLE).

CounterForge compares your solution against a trusted brute-force implementation using deterministic test case generation.

## Quick Start

### Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

CounterForge supports two operating modes:

#### 1. Manual Mode (User-provided Brute Force & Generator)
Provide your own trusted brute force and generator source files:
```bash
python counterforge/scripts/stress.py --solution examples/max-subarray-bug/solution.cpp --brute examples/max-subarray-bug/brute.cpp --gen examples/max-subarray-bug/gen.cpp
```

#### 2. AI Mode (Local LLM via Ollama)
When you only have the problem statement, CounterForge asks a local model running in Ollama to write the brute force and generator for you:
```bash
python counterforge/scripts/stress.py --solution examples/max-subarray-bug/solution.cpp --problem examples/max-subarray-bug/problem.txt --model qwen2.5-coder:7b
```
*(You can also set the `COUNTERFORGE_MODEL` environment variable so you don't need to specify `--model` each time).*

---

## CLI Options

| Flag | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--solution` | `-s` | Path to the candidate C++ solution source file (`.cpp`) **[Required]** | |
| `--problem` | `-p` | Path to problem statement text file (`.txt`) to activate AI mode | `None` |
| `--model` | `-m` | Local Ollama model name to use in AI mode | `$COUNTERFORGE_MODEL` |
| `--brute` | `-b` | Path to trusted C++ brute-force reference (`.cpp`) for manual mode | `None` |
| `--gen` | `-g` | Path to C++ test generator (`.cpp`) conforming to contract | `None` |
| `--max-tests` | `-n` | Maximum number of test cases to generate and evaluate | `100` |
| `--max-size` | | Maximum scale/size parameter passed to the generator | `20` |
| `--seed` | | Starting random seed for reproducible runs | `1` |
| `--time-limit` | `-t` | Execution time limit per test case in seconds | `1.5` |
| `--mode` | | Value distribution mode: `small`, `large`, `all`, or `both` | `all` |
| `--build-dir` | | Directory where compiled executables are stored | `build` |
| `--output-dir` | | Folder where counterexample evidence is saved on failure | `stress_runs/<timestamp>/` |

---

## Generator Contract

Every test generator used by CounterForge adheres to the standard contract:
```bash
./gen <seed> <size> <mode>
```
- `<seed>`: Integer seed for `std::mt19937` deterministic pseudo-random generation.
- `<size>`: Problem scale / input size parameter (e.g. array length $N$, vertex count $V$).
- `<mode>`:
  - `"small"`: Small values (e.g. $-10$ to $10$) for quick manual inspection and simple corner cases.
  - `"large"`: Boundary/limit values (e.g. up to $\pm 10^9$) to catch integer overflows.
- **Output**: Exactly ONE valid test case printed to `stdout`. Deterministic for identical arguments.

---

## Failure Outcomes & Evidence

When a bug is found, CounterForge halts on the first failure, classifies the outcome:
- `wrong_answer`: Solution output differs from the brute-force reference.
- `runtime_error`: Solution crashed with a non-zero exit code (e.g. segfault, assertion error).
- `timeout`: Solution exceeded the specified `--time-limit`.
- `brute_failed`: Trusted brute-force crashed or timed out.
- `no_difference_found`: All test cases passed successfully.

Evidence is saved into `stress_runs/<timestamp>/` containing:
- `failing_input.in`
- `expected.out`
- `actual.out`
- `report.json`
- Copies of `solution.cpp`, `brute.cpp`, and `gen.cpp` for instant reproducibility.
