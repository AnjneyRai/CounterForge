#include <iostream>
using namespace std;

int main() {
    long long n;
    int k;
    if (!(cin >> n >> k)) return 0;

    // INTENTIONAL BUG: i < k - 1 makes the loop stop exactly ONE step too early!
    // It will pass the sample test if the sample data doesn't catch it, 
    // but fail on almost every other test case.
    for (int i = 0; i < k - 1; i++) {
        if (n % 10 == 0) {
            n /= 10;
        } else {
            n--;
        }
    }

    cout << n << endl;
    return 0;
}