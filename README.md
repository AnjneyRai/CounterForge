# CounterForge

CounterForge is an open-source stress-testing tool and agent skill designed to find the smallest input where a C++ competitive programming solution produces a Wrong Answer (WA), Runtime Error (RE), or Time Limit Exceeded (TLE).

CounterForge compares your solution against a trusted brute-force implementation using deterministic test case generation.

## The problem
You get "Wrong Answer on test 82" and the judge hides the test, or shows an input
too big to trace by hand. Stress testing fixes this: compare your fast solution
against a slow brute force on thousands of small random inputs until they disagree.
But writing the brute force and generator for every problem is slow, so many people skip it.

## What CounterForge does
1. A local open-weight model (via Ollama) reads the problem and writes a brute force and a random test generator.
2. [Trust check: the brute force is run on the sample tests and the model repairs it if it fails.]
3. Plain code compiles everything, runs both programs on growing random inputs, and compares outputs.
4. It stops at the first difference and shows the failing input and both answers.

The comparison step uses no AI, so a reported mismatch is real.

## Open-source AI used
- Model: `qwen2.5-coder:7b`, an open-weight model run locally through Ollama (no API keys, no cloud).
- Agent skill: the `counterforge/` folder follows the Agent Skills standard [and passes `skills-ref validate`].

## Requirements
Python 3.9+, g++, Ollama with a pulled coder model (`ollama pull qwen2.5-coder:7b`).

## Install
```
git clone https://github.com/AnjneyRai/CounterForge.git
cd CounterForge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Quick start
Manual mode (your own brute force and generator, no AI):
```
python counterforge/scripts/stress.py --solution examples/max-subarray-bug/solution.cpp --brute examples/max-subarray-bug/brute.cpp --gen examples/max-subarray-bug/gen.cpp
```
AI mode (the model writes them; Ollama must be running):
```
python counterforge/scripts/stress.py --solution examples/max-subarray-bug/solution.cpp --problem examples/max-subarray-bug/problem.txt --model qwen2.5-coder:7b --samples examples/max-subarray-bug/samples
```
The example solution has a planted bug (it fails on all-negative arrays). CounterForge finds a one-element counterexample.

![CounterForge setup](docs/demo-1.png)
![CounterForge finds the counterexample](docs/demo-2.png)

## Use it as an agent skill
Copy the `counterforge/` folder into your agent's skills directory. See `counterforge/SKILL.md`.

## Limitations
- The AI-written brute force can still be wrong even if it passes the samples. Always check the failing input by hand.
- Only problems with one correct output are supported (no "print any valid answer", no interactive problems).
- Small models sometimes fail to write a working helper, and the first AI run is slow.
- Intended for practice and upsolving. Check each contest's rules on AI help.

## Future work
Hint levels, an input shrinker, a benchmark of trust-check success rates, and a browser extension that sends a problem straight to the tool.

## License
MIT