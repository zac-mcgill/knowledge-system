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

An algorithm is a finite sequence of well-defined instructions used to solve a class of problems or perform a computation.

## Why It Matters

Algorithms are the backbone of all computation. Efficient algorithms reduce resource consumption and enable solutions to otherwise intractable problems.

## Key Principles

- Correctness — must produce the right output for all valid inputs
- Termination — must halt after a finite number of steps
- Determinism — same input always yields same output
- Efficiency — measured by time and space complexity

## How It Works

1. Define the problem and its constraints clearly.
2. Choose an appropriate algorithmic strategy (divide and conquer, greedy, dynamic programming).
3. Implement the algorithm with attention to edge cases.
4. Analyse time and space complexity using Big-O notation.
5. Test against known inputs and verify correctness.

## Examples

- Binary search: O(log n) lookup in sorted arrays.
- Merge sort: O(n log n) comparison-based sorting.
- Dijkstra's algorithm: shortest path in weighted graphs.

## Common Pitfalls

- Ignoring edge cases (empty input, single element).
- Confusing average-case with worst-case complexity.
- Premature optimisation before correctness is established.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Time complexity | Faster execution | Higher implementation complexity |
| Space complexity | Lower memory use | May require more computation |
| Generality | Reusable across problems | May be suboptimal for specific cases |

## Related Concepts

- [[Data Structures]]
- [[Complexity Theory]]
- [[Recursion]]

## Further Exploration

- Introduction to Algorithms (Cormen et al.)
- Algorithm Design Manual (Skiena)
