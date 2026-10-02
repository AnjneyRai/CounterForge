// CounterForge Example: Trusted Reference (Brute Force)
// Problem: Maximum Non-Empty Subarray Sum
//
// This solution checks all non-empty contiguous subarrays in O(N^2) time.
// Because it considers every single non-empty subarray and initializes the
// best sum to a very large negative value, it is guaranteed to be correct
// even when all input values are negative.

#include <iostream>
#include <vector>
#include <algorithm>

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int n;
    if (!(std::cin >> n) || n <= 0) {
        return 0;
    }

    std::vector<long long> a(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
    }

    // Initialize answer to smallest possible value
    // Minimum element can be -10^9, so -2e18 is safely smaller than any single element
    long long max_sum = -2000000000000000000LL;

    // Check every starting position i and ending position j
    for (int i = 0; i < n; ++i) {
        long long current_sum = 0;
        for (int j = i; j < n; ++j) {
            current_sum += a[j];
            max_sum = std::max(max_sum, current_sum);
        }
    }

    std::cout << max_sum << "\n";
    return 0;
}
