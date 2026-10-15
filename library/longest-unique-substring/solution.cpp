#include <algolens.h>

int longest_unique(const std::string& s) {
    std::unordered_set<char> seen;
    int left = 0;
    int best = 0;
    for (int right = 0; right < static_cast<int>(s.size()); ++right) {
        while (seen.count(s[right])) {
            seen.erase(s[left]);
            left += 1;
        }
        seen.insert(s[right]);
        best = std::max(best, right - left + 1);
    }
    return best;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(longest_unique(in["args"][0].get<std::string>())).dump());
}
