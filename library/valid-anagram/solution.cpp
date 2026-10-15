#include <algolens.h>
#include <string>
#include <unordered_map>

bool is_anagram(const std::string& s, const std::string& t) {
    if (s.size() != t.size()) {
        return false;
    }
    std::unordered_map<char, int> counts;
    for (char c : s) {
        counts[c] += 1;
    }
    for (char c : t) {
        if (counts[c] == 0) {
            return false;
        }
        counts[c] -= 1;
    }
    return true;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto s = in["args"][0].get<std::string>();
    auto t = in["args"][1].get<std::string>();
    algolens::emit(algolens::Json(is_anagram(s, t)).dump());
}
