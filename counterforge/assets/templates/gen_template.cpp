// CounterForge Generator Starter Template
// Contract: ./gen <seed> <size> <mode>
// argv[1]: seed (unsigned int) - seeds std::mt19937 deterministically
// argv[2]: size (int)          - maximum count of elements / scale
// argv[3]: mode (string)        - "small" (tiny numbers) or "large" (extreme values)

#include <iostream>
#include <random>
#include <string>
#include <algorithm>

int main(int argc, char* argv[]) {
    if (argc < 4) return 1;

    unsigned int seed = std::stoul(argv[1]);
    int size = std::stoi(argv[2]);
    std::string mode = argv[3];

    // Seed std::mt19937 deterministically with the given seed
    std::mt19937 rng(seed);

    // Pick n up to size (at least 1)
    int n = std::uniform_int_distribution<int>(1, std::max(1, size))(rng);
    std::cout << n << "\n";

    long long min_val = -10;
    long long max_val = 10;
    if (mode == "large") {
        min_val = -1000000000LL;
        max_val = 1000000000LL;
    }

    std::uniform_int_distribution<long long> dist(min_val, max_val);
    for (int i = 0; i < n; ++i) {
        std::cout << dist(rng) << (i + 1 == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}
