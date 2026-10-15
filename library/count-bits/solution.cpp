#include <algolens.h>

int count_bits(long long n) {
    int count = 0;
    while (n > 0) {
        n = n & (n - 1);
        count += 1;
    }
    return count;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(count_bits(in["args"][0].get<long long>())).dump());
}
