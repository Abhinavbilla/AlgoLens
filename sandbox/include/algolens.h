// Helpers for C++ test programs run by the AlgoLens sandbox driver.
// The test input arrives as JSON on stdin; the result must be written as JSON with emit(),
// which uses fd 3 so the program's own std::cout output never corrupts the result.
//
// This header is precompiled in the sandbox image (algolens.h.gch, built with the same
// flags the sandbox compiles with), so make it the first #include of a solution: parsing
// nlohmann/json takes ~2.5 s otherwise, which a busy machine can stretch past the limit.
#pragma once

#include <unistd.h>

// The standard headers solutions commonly use come with it too, at no compile-time cost
// (they're in the precompiled header), so a forgotten #include isn't a failure.
#include <algorithm>
#include <array>
#include <bitset>
#include <climits>
#include <cmath>
#include <cstdint>
#include <deque>
#include <functional>
#include <iostream>
#include <iterator>
#include <limits>
#include <list>
#include <map>
#include <nlohmann/json.hpp>
#include <numeric>
#include <queue>
#include <set>
#include <sstream>
#include <stack>
#include <string>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace algolens {

using Json = nlohmann::json;

inline std::string read_input() {
    return std::string(std::istreambuf_iterator<char>(std::cin), std::istreambuf_iterator<char>());
}

inline void emit(const std::string& json) {
    const char* p = json.data();
    size_t left = json.size();
    while (left > 0) {
        ssize_t n = ::write(3, p, left);
        if (n <= 0) return;
        p += n;
        left -= static_cast<size_t>(n);
    }
}

}  // namespace algolens
