#include <algolens.h>

algolens::ListNode* merge_lists(algolens::ListNode* a, algolens::ListNode* b) {
    algolens::ListNode dummy(0);
    algolens::ListNode* tail = &dummy;
    while (a != nullptr && b != nullptr) {
        if (a->val <= b->val) {
            tail->next = a;
            a = a->next;
        } else {
            tail->next = b;
            b = b->next;
        }
        tail = tail->next;
    }
    tail->next = a != nullptr ? a : b;
    return dummy.next;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto* a = algolens::build_list(in["args"][0]);
    auto* b = algolens::build_list(in["args"][1]);
    algolens::emit(algolens::to_json(merge_lists(a, b)).dump());
}
