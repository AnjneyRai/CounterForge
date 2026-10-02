// CounterForge Example: Buggy Candidate Solution
// Problem: Maximum Non-Empty Subarray Sum
//
// BUG EXPLANATION:
// This solution implements Kadane's algorithm, but makes a common beginner mistake:
// it initializes `max_sum` to 0. If all numbers in the array are negative,
// the maximum non-empty subarray sum should be the single largest negative number.
// However, because `max_sum` is initialized to 0, this program incorrectly prints 0.

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

    // Common bug: initialized to 0 instead of -infinity or a[0].
    // This allows an empty subarray, violating the "non-empty" problem requirement.
    long long max_sum = 0;
    long long current_sum = 0;

    for (int i = 0; i < n; ++i) {
        current_sum += a[i];
        if (current_sum > max_sum) {
            max_sum = current_sum;
        }
        if (current_sum < 0) {
            current_sum = 0;
        }
    }

    std::cout << max_sum << "\n";
    return 0;
}
