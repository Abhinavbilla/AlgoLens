#include <algolens.h>

bool is_palindrome(const std::string& s) {
    int left = 0, right = static_cast<int>(s.size()) - 1;
    while (left < right) {
        if (s[left] != s[right]) {
            return false;
        }
        left += 1;
        right -= 1;
    }
    return true;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(is_palindrome(in["args"][0].get<std::string>())).dump());
}
