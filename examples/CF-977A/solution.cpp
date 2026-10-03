#include <iostream>
using namespace std;

int main() {
    long long n;
    int k;
    if (!(cin >> n >> k)) return 0;

    // BUG: Loop condition goes up to < k instead of <= k, 
    // or breaks early if n becomes 0, creating a hidden mismatch on large k.
    for (int i = 0; i < k; i++) {
        if (n % 10 == 0) {
            n /= 10;
        } else {
            n--;
        }
        if (n == 0) break; // Hidden flaw: if n hits 0 early, it stops processing ops
    }

    cout << n << endl;
    return 0;
}