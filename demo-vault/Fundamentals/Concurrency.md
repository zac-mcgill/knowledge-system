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

Concurrency is the ability of a system to execute multiple tasks in overlapping time periods, whether truly simultaneously or via interleaving.

## Why It Matters

Modern hardware is inherently parallel. Concurrency enables efficient use of multicore processors, responsive user interfaces, and high-throughput server applications.

## Key Principles

- Parallelism vs concurrency — parallelism is simultaneous execution; concurrency is managing multiple tasks
- Mutual exclusion — preventing simultaneous access to shared resources
- Synchronisation — coordinating the order of operations across threads

## How It Works

1. Identify independent units of work that can execute concurrently.
2. Choose a concurrency model (threads, async/await, actors, CSP).
3. Protect shared state with locks, atomics, or message passing.
4. Handle synchronisation points where tasks must coordinate.
5. Test for race conditions and deadlocks under concurrent load.

## Examples

- Thread pools in web servers handling concurrent requests.
- Async I/O in Python with asyncio.
- Go goroutines with channel-based communication.

## Common Pitfalls

- Data races from unprotected shared mutable state.
- Deadlocks from inconsistent lock ordering.
- Starvation when one thread monopolises a resource.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Threads | True parallelism | Complex synchronisation |
| Async/await | Efficient I/O concurrency | Cannot parallelise CPU-bound work |
| Message passing | No shared state | Overhead of message serialisation |

## Related Concepts

- [[Operating Systems]]
- [[Memory Management]]

## Further Exploration

- Java Concurrency in Practice (Goetz)
- The Art of Multiprocessor Programming (Herlihy & Shavit)
