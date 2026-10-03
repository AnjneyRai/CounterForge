// CounterForge Brute-Force Starter Template
// Remember: Simple and correct beats fast!
// This reference solution should use the simplest, most obviously correct
// algorithm (even O(N^2) or O(2^N)) to verify faster solutions.

#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    if (!(std::cin >> n)) return 0;

    std::vector<long long> a(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
    }

    // Simple and obviously-correct brute-force logic
    long long max_sum = a[0];
    for (int i = 0; i < n; ++i) {
        long long current_sum = 0;
        for (int j = i; j < n; ++j) {
            current_sum += a[j];
            if (current_sum > max_sum) {
                max_sum = current_sum;
            }
        }
    }

    std::cout << max_sum << "\n";
    return 0;
}
