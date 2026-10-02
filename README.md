# CounterForge

CounterForge is an open-source stress-testing tool and agent skill designed to find the smallest input where a C++ competitive programming solution produces a Wrong Answer (WA), Runtime Error (RE), or Time Limit Exceeded (TLE).

CounterForge compares your solution against a trusted brute-force implementation using deterministic test case generation.

## Quick Start

### Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

### Example Command

Run stress testing on an example problem:
```bash
python counterforge/scripts/stress.py --solution examples/max-subarray-bug/solution.cpp --brute examples/max-subarray-bug/brute.cpp --gen examples/max-subarray-bug/gen.cpp
```

## How It Works

1. **Deterministic Test Generation**: Generates test cases from small to large sizes using a seedable generator adhering to `./gen <seed> <size> <mode>`.
2. **Differential Testing**: Runs both the target solution and reference brute-force solution on each generated input.
3. **Discrepancy Detection**: Halts upon discovering a mismatch, crash, or timeout, presenting the minimal failing counterexample and saving it for inspection.
