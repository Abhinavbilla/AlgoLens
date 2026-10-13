#include <iostream>
#include <vector>
#include <algorithm>
int main() {
    std::vector<int> v{3, 1, 2};
    std::sort(v.begin(), v.end());
    std::cout << "hello from c++ " << v[0] << v[1] << v[2] << "\n";
}
