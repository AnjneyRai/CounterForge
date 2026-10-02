// CounterForge Example: Test Case Generator
// Adheres strictly to the CounterForge Generator Contract:
//   ./gen <seed> <size> <mode>
//
// Arguments:
//   argv[1]: seed (integer) for deterministic random generation
//   argv[2]: size (integer) representing array length n
//   argv[3]: mode ("small" for [-10, 10], "large" for [-10^9, 10^9])

#include <iostream>
#include <string>
#include <random>
#include <vector>
#include <algorithm>

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cerr << "Usage: " << argv[0] << " <seed> <size> <mode>\n";
        std::cerr << "  mode: 'small' or 'large'\n";
        return 1;
    }

    unsigned long long seed = std::stoull(argv[1]);
    int size = std::stoi(argv[2]);
    std::string mode = argv[3];

    // Ensure valid non-empty size
    int n = std::max(1, size);

    std::mt19937_64 rng(seed);

    std::cout << n << "\n";

    if (mode == "small") {
        // Small values: easy to mentally calculate and inspect
        std::uniform_int_distribution<long long> dist(-10, 10);
        for (int i = 0; i < n; ++i) {
            std::cout << dist(rng) << (i + 1 == n ? "" : " ");
        }
    } else {
        // Large values: stress boundary values and large sums
        std::uniform_int_distribution<long long> dist(-1000000000LL, 1000000000LL);
        for (int i = 0; i < n; ++i) {
            std::cout << dist(rng) << (i + 1 == n ? "" : " ");
        }
    }

    std::cout << "\n";
    return 0;
}
