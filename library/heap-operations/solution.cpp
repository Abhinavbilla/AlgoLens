#include <algolens.h>
#include <string>
#include <utility>
#include <vector>

std::vector<long long> heap_ops(const algolens::Json& ops) {
    std::vector<long long> heap;
    std::vector<long long> popped;
    for (const auto& op : ops) {
        if (op[0].get<std::string>() == "push") {
            heap.push_back(op[1].get<long long>());
            size_t i = heap.size() - 1;
            while (i > 0 && heap[(i - 1) / 2] > heap[i]) {
                size_t parent = (i - 1) / 2;
                std::swap(heap[i], heap[parent]);
                i = parent;
            }
        } else {
            popped.push_back(heap[0]);
            long long last = heap.back();
            heap.pop_back();
            if (!heap.empty()) {
                heap[0] = last;
                size_t i = 0;
                while (true) {
                    size_t smallest = i;
                    for (size_t child : {2 * i + 1, 2 * i + 2}) {
                        if (child < heap.size() && heap[child] < heap[smallest]) {
                            smallest = child;
                        }
                    }
                    if (smallest == i) {
                        break;
                    }
                    std::swap(heap[i], heap[smallest]);
                    i = smallest;
                }
            }
        }
    }
    return popped;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    algolens::emit(algolens::Json(heap_ops(in["args"][0])).dump());
}
