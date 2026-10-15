#include <algolens.h>

bool is_valid(const std::string& s) {
    std::map<char, char> pairs{{')', '('}, {']', '['}};
    std::vector<char> stack;
    for (char c : s) {
        if (pairs.count(c)) {
            if (stack.empty() || stack.back() != pairs[c]) {
                return false;
            }
            stack.pop_back();
        } else {
            stack.push_back(c);
        }
    }
    return stack.empty();
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(is_valid(in["args"][0].get<std::string>())).dump());
}
