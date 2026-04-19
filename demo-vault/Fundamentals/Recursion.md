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

Recursion is a technique where a function calls itself to solve smaller instances of the same problem until reaching a base case.

## Why It Matters

Recursion simplifies solutions to problems with self-similar structure such as tree traversal, divide-and-conquer algorithms, and mathematical sequences.

## Key Principles

## How It Works

1. Check whether the current input satisfies the base case.
2. If yes, return the base result directly.
3. If no, decompose the problem and make one or more recursive calls.

## Examples

- Factorial: `n! = n * (n-1)!` with base case `0! = 1`.
- Fibonacci sequence with memoisation.
- Tree traversal (pre-order, in-order, post-order).

## Common Pitfalls

- Missing or incorrect base case leading to infinite recursion.
- Stack overflow on deep recursion without tail-call optimisation.
- Redundant computation without memoisation.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Readability | Natural expression of recursive problems | Harder to trace execution flow |
| Stack usage | Automatic state management per call | Risk of stack overflow on deep input |
| Memoisation | Avoids redundant computation | Additional memory for cache |

## Related Concepts

- [[Algorithms]]
- [[Dynamic Programming]]

## Further Exploration

- Structure and Interpretation of Computer Programs (Abelson & Sussman)
