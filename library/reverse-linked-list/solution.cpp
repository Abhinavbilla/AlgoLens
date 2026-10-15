#include <algolens.h>

algolens::ListNode* reverse_list(algolens::ListNode* head) {
    algolens::ListNode* prev = nullptr;
    algolens::ListNode* curr = head;
    while (curr != nullptr) {
        algolens::ListNode* nxt = curr->next;
        curr->next = prev;
        prev = curr;
        curr = nxt;
    }
    return prev;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto* head = algolens::build_list(in["args"][0]);
    algolens::emit(algolens::to_json(reverse_list(head)).dump());
}
