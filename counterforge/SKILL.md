---
name: counterforge
description: >-
  Finds the smallest failing input for a C++ competitive programming solution
  using stress testing. A local open-weight model (via Ollama) can write the
  brute force and test generator from the problem statement, and plain code
  compares the outputs. Use when a user's C++ solution gets Wrong Answer, fails
  a hidden test, or they ask for a counterexample, a stress test, or a failing
  test case. Not for interactive problems or problems that accept many valid answers.
license: MIT
compatibility: Requires Python 3.9+, g++, and the rich package. AI mode also needs Ollama running locally with a pulled coder model.
---

# CounterForge

CounterForge compiles the user's C++ solution, a brute force, and a random test
generator, then runs them against each other until their outputs differ. It reports
the smallest failing input it finds. The comparison is plain code, so a reported
mismatch is real. AI is only used to write the brute force and the generator.

## When to use it
- The user's C++ solution gets Wrong Answer, and they cannot see or understand the failing test.
- The user asks for a counterexample, a stress test, or a smaller failing input.

Do not use it for interactive problems, or for problems where many different outputs
are valid (outputs are compared token by token, so a custom checker would be needed).

## Workflow
1. Collect three things from the user, creating the files yourself from what they paste:
   - the solution: a `.cpp` file
   - the problem statement, saved as `problem.txt`
   - the sample tests from the statement, saved in a folder as `1.in`/`1.out`, `2.in`/`2.out`, and so on
2. Pick a mode. If the user already has a brute force and a generator, use manual mode.
   Otherwise use AI mode.
3. Run the command from the user's project folder. Paths below are relative to this skill folder.

   AI mode (needs Ollama running; set COUNTERFORGE_MODEL or pass --model):
```
   python scripts/stress.py --solution solution.cpp --problem problem.txt --samples samples --model qwen2.5-coder:7b
```
   Manual mode:
```
   python scripts/stress.py --solution solution.cpp --brute brute.cpp --gen gen.cpp
```
4. Read the result. Exit code 0 means no difference was found, 1 means a counterexample
   was found, and 2 means setup failed (compile error, Ollama not running, or the trust check failed).
5. Report the failing input, the solution's output, and the brute force's output.
   Ask the user to trace the small input by hand. Point at the area of the bug, but do
   not write the corrected solution unless the user explicitly asks for it.
6. After the user edits their code, run the same command again to confirm it is fixed.

## Rules for the agent
- In AI mode the brute force and generator are written by a model and are NOT proven
  correct. Passing the sample tests lowers the risk but does not remove it. When the
  two programs disagree, check by hand which one is right on the small failing input.
- AI mode runs a trust check: the brute force is run on the samples, and the model is
  asked to repair it (up to `--max-retries` times) if it fails. If it still fails,
  stop and show the user the last attempt's file. Use `--force` only if the user asks.
- Use mode `large` (or the default, which tries both) to catch overflow and slow code.
- Do not invent test results. Only describe what the tool printed.
- Results are saved under `stress_runs/<timestamp>/`. Tell the user where.

## Generator contract
Every generator must be runnable as `./gen <seed> <size> <mode>` and print exactly ONE
valid input to standard output. The same seed, size, and mode must always print the
same input. `mode` is `small` (tiny values, for logic bugs) or `large` (values near
the limits, for overflow and speed).

## Main flags
- `--solution FILE` the candidate C++ solution (required)
- `--problem FILE` problem text, which turns on AI mode
- `--samples DIR` sample tests used by the trust check
- `--model NAME` local Ollama model (or set COUNTERFORGE_MODEL)
- `--brute FILE` and `--gen FILE` your own helpers, which turn on manual mode
- `--max-retries N` repair attempts for the AI helpers
- `--force` continue even if the trust check fails
- `--max-tests`, `--max-size`, `--time-limit`, `--mode` control the stress run
Run `python scripts/stress.py --help` for the full list and defaults.
