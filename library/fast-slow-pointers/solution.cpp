#include <algolens.h>

algolens::ListNode* middle_node(algolens::ListNode* head) {
    algolens::ListNode* slow = head;
    algolens::ListNode* fast = head;
    while (fast != nullptr && fast->next != nullptr) {
        slow = slow->next;
        fast = fast->next->next;
    }
    return slow;
}

int main() {
    auto in = algolens::Json::parse(algolens::read_input());
    auto* head = algolens::build_list(in["args"][0]);
    algolens::emit(algolens::to_json(middle_node(head)).dump());
}
