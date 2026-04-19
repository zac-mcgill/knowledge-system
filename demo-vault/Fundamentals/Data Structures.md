---
type: core-concept
domain: fundamentals
status: complete
has_key_principles: true
has_how_it_works: true
has_tradeoffs: true
difficulty: intermediate
---

## Definition

A data structure is a specialised format for organising, storing, and accessing data efficiently within a computer program.

## Why It Matters

Choosing the right data structure directly impacts algorithm performance, memory usage, and code maintainability.

## Key Principles

- Abstraction — separates interface from implementation
- Efficiency — optimises access patterns for intended use
- Composability — complex structures built from simpler ones

## How It Works

1. Identify the access patterns required by the problem (random access, sequential, key-based).
2. Select a data structure that matches those patterns (array, linked list, hash map, tree).
3. Implement or use a standard library implementation.
4. Profile performance under realistic workloads.

## Examples

- Arrays: contiguous memory, O(1) random access.
- Hash maps: O(1) average-case lookup by key.
- Binary search trees: O(log n) ordered operations.

## Common Pitfalls

- Using a list where a set or map would be more efficient.
- Ignoring cache locality when choosing between arrays and linked lists.
- Not accounting for worst-case performance (e.g. hash collisions).

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Arrays | Fast random access | Fixed size or expensive resizing |
| Linked lists | Efficient insertion/deletion | Poor cache locality |
| Hash maps | Fast lookup | High memory overhead |

## Related Concepts

- [[Algorithms]]
- [[Memory Management]]
- [[Complexity Theory]]

## Further Exploration

- Data Structures and Algorithms in Python (Goodrich et al.)
