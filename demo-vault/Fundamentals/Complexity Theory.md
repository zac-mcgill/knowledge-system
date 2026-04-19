---
type: core-concept
domain: fundamentals
status: partial
has_key_principles: false
has_how_it_works: true
has_tradeoffs: true
difficulty: intermediate
---

## Definition

Complexity theory classifies computational problems by the resources required to solve them, primarily time and space.

## Why It Matters

Understanding complexity helps engineers predict scalability, choose appropriate algorithms, and identify problems that are inherently hard.

## Key Principles

## How It Works

1. Express the number of operations as a function of input size n.
2. Identify the dominant term and discard constants and lower-order terms.
3. Classify the algorithm into a complexity class (O(1), O(log n), O(n), O(n²), etc.).

## Examples

- Linear search is O(n).
- Binary search is O(log n).
- Bubble sort is O(n²).

## Common Pitfalls

- Confusing Big-O (upper bound) with Theta (tight bound).
- Assuming average case equals worst case.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Exact analysis | Precise performance prediction | Mathematically complex |
| Asymptotic analysis | Simple comparison between algorithms | Hides constant factors |
| Amortised analysis | Accounts for occasional expensive operations | Harder to reason about |

## Related Concepts

- [[Algorithms]]
- [[Data Structures]]

## Further Exploration

- Introduction to the Theory of Computation (Sipser)
