#include <algolens.h>

long long int_sqrt(long long x) {
    long long lo = 0, hi = x;
    while (lo < hi) {
        long long mid = (lo + hi + 1) / 2;
        if (mid * mid <= x) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    return lo;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(int_sqrt(in["args"][0].get<long long>())).dump());
}
