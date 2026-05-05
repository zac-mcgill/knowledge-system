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

Complexity theory classifies computational problems by the resources required to solve them, primarily time and space.

## Why It Matters

Understanding complexity helps engineers predict scalability, choose appropriate algorithms, and identify problems that are inherently hard.

## Key Principles

- **Big-O notation** describes the upper bound on an algorithm's growth rate, used to characterise worst-case behaviour.
- **Omega notation** describes the lower bound, representing the best-case or minimum resource usage.
- **Theta notation** describes a tight bound where upper and lower bounds are the same asymptotic function.
- **P vs NP** distinguishes problems solvable in polynomial time from those only verifiable in polynomial time; whether P equals NP remains unsolved.
- **Amortised analysis** averages the cost of expensive operations over a sequence, giving a more accurate picture of practical performance.

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
