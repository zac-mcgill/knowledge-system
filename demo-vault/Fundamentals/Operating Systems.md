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

An operating system is system software that manages hardware resources and provides services to application programs.

## Why It Matters

Operating systems abstract hardware complexity, enable multitasking, enforce security boundaries, and provide the foundation for all user-facing software.

## Key Principles

- Abstraction — hides hardware complexity from applications
- Resource management — allocates CPU, memory, and I/O fairly
- Isolation — protects processes from each other

## How It Works

1. The kernel initialises hardware and loads device drivers.
2. The scheduler allocates CPU time to processes using a scheduling algorithm.
3. The memory manager maps virtual addresses to physical memory.
4. The file system provides persistent storage abstraction.
5. System calls provide a controlled interface between user space and kernel space.

## Examples

- Linux kernel with preemptive multitasking.
- Windows NT kernel with hardware abstraction layer.
- Real-time operating systems for embedded devices.

## Common Pitfalls

- Deadlocks from improper resource ordering.
- Priority inversion in real-time systems.
- Race conditions in concurrent access to shared state.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Monolithic kernel | High performance | Harder to maintain and extend |
| Microkernel | Modularity and fault isolation | IPC overhead |
| Hybrid kernel | Balance of performance and modularity | Design complexity |

## Related Concepts

- [[Memory Management]]
- [[Concurrency]]
- [[File Systems]]

## Further Exploration

- Operating Systems: Three Easy Pieces (Arpaci-Dusseau)
