#include <vector>
#include <cstdio>
int main() {
    std::vector<std::vector<char>> chunks;
    for (;;) chunks.emplace_back(16 * 1024 * 1024, 'x');
}
