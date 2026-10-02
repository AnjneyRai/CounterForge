# CounterForge Usage Notes

This reference guide contains practical notes on writing generators and brute-force solutions for CounterForge stress testing.

## Writing a CounterForge Generator

Your generator program must accept 3 command-line arguments:

```bash
./gen <seed> <size> <mode>
```

### Best Practices:
1. **Deterministic RNG**: Use `std::mt19937` or `std::mt19937_64` seeded with the first argument:
   ```cpp
   int seed = std::stoi(argv[1]);
   std::mt19937 rng(seed);
   ```
2. **Size Handling**: Use `size` (second argument) to bound the input length $N$, ensuring tests start tiny ($N=1, 2, \dots$) and scale upward.
3. **Modes**:
   - `"small"`: Generate small numbers (e.g. within $[-10, 10]$) so failing outputs can be solved in your head.
   - `"large"`: Generate full constraint numbers (e.g. up to $10^9$) to catch integer overflows (`long long` vs `int`).
4. **Valid Format**: Only output valid problem inputs. Do not print debug logs or prompts to stdout.

## Writing a Brute Force Solution

A good brute-force reference:
- Simplicity over speed: Correctness is paramount; $O(N^2)$, $O(N^3)$, or $O(2^N)$ is perfectly fine since size is small.
- Avoid tricky optimizations or clever data structures.
- Use wide numeric types (e.g., `long long` or `__int128_t`) to avoid overflow bugs in the reference.

## Common CP Bugs Caught by Stress Testing

- **All Negatives**: Algorithms initializing answers to `0` instead of `-INF`.
- **Integer Overflow**: Using `int` for sums or products exceeding $2 \times 10^9$.
- **Off-By-One Errors**: Looping `< n` vs `<= n` or indexing `0`-based vs `1`-based.
- **Empty / Single-Element Inputs**: Edge cases where $N = 1$ or constraints at their absolute minimum.
