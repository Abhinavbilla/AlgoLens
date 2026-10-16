"""The computed Python -> C++ line map (animation/linemap.py), used to highlight the C++ of
generated approaches while their animation plays."""

import json

from algolens.animation.linemap import align
from algolens.config import get_settings

TWO_POINTER_PY = """def maxArea(height):
    left, right = 0, len(height) - 1
    best = 0
    while left < right:
        width = right - left
        if height[left] < height[right]:
            best = max(best, height[left] * width)
            left += 1
        else:
            best = max(best, height[right] * width)
            right -= 1
    return best"""

TWO_POINTER_CPP = """#include <algolens.h>
using namespace algolens;
long long maxArea(const std::vector<long long>& h){
    int l=0, r=(int)h.size()-1;
    long long best=0;
    while(l<r){
        long long width=r-l;
        if(h[l]<h[r]){best=std::max(best,h[l]*width); ++l;}
        else{best=std::max(best,h[r]*width); --r;}
    }
    return best;
}
int main(){
    auto in=Json::parse(read_input());
    auto nums=in["args"][0].get<std::vector<long long>>();
    emit(Json(maxArea(nums)).dump());
    return 0;
}"""


def test_short_names_and_packed_lines():
    m = align(TWO_POINTER_PY, TWO_POINTER_CPP)
    assert m[1] == 3 and m[2] == 4 and m[3] == 5 and m[4] == 6 and m[5] == 7
    assert m[6] == m[7] == m[8] == 8  # three Python lines share one C++ line
    assert m[9] == m[10] == m[11] == 9
    assert m[12] == 11
    assert all(v < 13 for v in m.values())  # nothing maps into main()


def test_helpers_defined_in_a_different_order():
    py = """def count_islands(grid):
    def sink(r, c):
        if r < 0 or c < 0:
            return
        grid[r][c] = 0
    count = 0
    for r in range(len(grid)):
        count += 1
        sink(r, 0)
    return count"""
    cpp = """#include <algolens.h>
void sink(std::vector<std::vector<int>>& grid, int r, int c) {
    if (r < 0 || c < 0) return;
    grid[r][c] = 0;
}
int count_islands(std::vector<std::vector<int>> grid) {
    int count = 0;
    for (int r = 0; r < (int)grid.size(); r++) {
        count++;
        sink(grid, r, 0);
    }
    return count;
}
int main() { return 0; }"""
    m = align(py, cpp)
    assert m[2] == 2 and m[3] == 3 and m[5] == 4  # the helper, though C++ has it first
    assert m[6] == 7 and m[7] == 8 and m[8] == 9 and m[9] == 10 and m[10] == 12


def test_matches_the_hand_made_library_maps():
    right = total = 0
    for f in sorted(get_settings().library_dir.glob("*/entry.json")):
        truth = json.loads(f.read_text(encoding="utf-8"))["cpp_lines"]
        got = align((f.parent / "solution.py").read_text(encoding="utf-8"),
                    (f.parent / "solution.cpp").read_text(encoding="utf-8"))  # fmt: skip
        for k, v in truth.items():
            total += 1
            right += got.get(int(k)) == v
    assert total > 400 and right / total >= 0.93, f"{right} of {total}"


def test_nothing_to_align():
    assert align("", "int main() {}") == {}
    assert align("def f():\n    return 1", "") == {}
