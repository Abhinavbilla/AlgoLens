// Helpers for C++ test programs run by the AlgoLens sandbox driver.
// The test input arrives as JSON on stdin; the result must be written as JSON with emit(),
// which uses fd 3 so the program's own std::cout output never corrupts the result.
#pragma once

#include <unistd.h>

#include <iostream>
#include <iterator>
#include <string>

namespace algolens {

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
