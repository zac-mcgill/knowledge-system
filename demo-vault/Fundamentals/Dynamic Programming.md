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

Dynamic programming is an algorithmic technique that solves complex problems by breaking them into overlapping subproblems and storing intermediate results.

## Why It Matters

Dynamic programming transforms exponential-time brute-force solutions into polynomial-time algorithms for problems with optimal substructure.

## Key Principles

- **Optimal substructure** means the optimal solution to a problem can be constructed from optimal solutions to its subproblems.
- **Overlapping subproblems** means the same smaller instances are solved repeatedly, making caching worthwhile.
- **Memoisation** stores results of recursive calls in a lookup table so each subproblem is computed at most once (top-down approach).
- **Tabulation** fills a result table iteratively from the smallest subproblems upward, avoiding recursion entirely (bottom-up approach).
- **State transition** defines how to move from one subproblem to the next via a recurrence relation that encodes the problem's structure.

## How It Works

1. Identify the recursive structure of the problem.
2. Define the state and the recurrence relation.
3. Implement with memoisation (top-down) or tabulation (bottom-up).

## Examples

- Fibonacci numbers with O(n) time via memoisation.
- Longest common subsequence between two strings.
- Knapsack problem for resource allocation.

## Common Pitfalls

- Incorrect state definition leading to wrong results.
- Forgetting base cases in the recurrence.
- Excessive memory usage from storing all states.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Memoisation | Easy to implement from recursion | Higher memory usage |
| Tabulation | Space-efficient iteration | Requires careful state ordering |
| Greedy alternative | Simpler implementation | Only works for specific problems |

## Related Concepts

- [[Algorithms]]
- [[Recursion]]
- [[Complexity Theory]]

## Further Exploration

- Introduction to Algorithms (Cormen et al.) — Chapter on Dynamic Programming
