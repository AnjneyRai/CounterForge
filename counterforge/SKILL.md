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

Run the deterministic stress engine from the command line:

```bash
python counterforge/scripts/stress.py --solution path/to/solution.cpp --brute path/to/brute.cpp --gen path/to/gen.cpp
```

## Architecture & Roadmap

- **Phase 1 (Current)**:
  - Deterministic C++ stress engine (`engine.py`)
  - Pretty terminal reporting with Rich (`report.py`)
  - Command-line runner (`stress.py`)
  - Example problem with deliberate bug (`examples/max-subarray-bug/`)
  - Test suite with pytest (`tests/test_engine.py`)

- **Phase 2 (TODO)**:
  - Local LLM integration (`llm.py`) to synthesize brute-force solutions and generators when not provided.
  - Local LLM trust and soundness verification (`trust_check.py`).

- **Phase 3 (TODO)**:
  - Delta-debugging / binary counterexample shrinker.

- **Phase 4 (TODO)**:
  - Automated code repair loop proposing diffs to fix identified bugs.
