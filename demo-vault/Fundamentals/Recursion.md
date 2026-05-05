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

Recursion is a technique where a function calls itself to solve smaller instances of the same problem until reaching a base case.

## Why It Matters

Recursion simplifies solutions to problems with self-similar structure such as tree traversal, divide-and-conquer algorithms, and mathematical sequences.

## Key Principles

- **Base case** is the condition that stops recursion and returns a result directly without making further calls.
- **Recursive step** breaks the problem into a smaller instance of the same problem and delegates to a recursive call.
- **Call stack** tracks each active function invocation; deep recursion grows the stack and risks overflow if depth is unbounded.
- **Progress toward termination** requires that every recursive call moves strictly closer to the base case, guaranteeing eventual termination.
- **Tail recursion** places the recursive call as the final operation, enabling compilers and runtimes to reuse the current stack frame and avoid stack growth.

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
