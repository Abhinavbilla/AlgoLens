A post-order traversal visits a node *after* everything below it: traverse the left subtree, then the right subtree, and only then record the node.

Children always come before their parent, which is exactly what you need when a node's answer depends on its children's answers: a tree's height, the size of each subtree, or freeing a tree from the leaves up. It takes O(n) time and O(h) space for the call stack, where h is the tree's height.
