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

Pointers are variables that store memory addresses, enabling direct manipulation of data locations and dynamic memory management.

## Why It Matters

Pointers are fundamental to systems programming, enabling efficient data structures, hardware interaction, and manual memory control in languages like C and C++.

## Key Principles

- Indirection — accessing data through its address rather than directly
- Pointer arithmetic — navigating memory by offsetting addresses
- Null safety — guarding against dereferencing invalid addresses

## How It Works

1. Declare a pointer variable with the appropriate type.
2. Assign it the address of an existing variable or a dynamically allocated block.
3. Dereference the pointer to read or write the value at that address.

## Examples

- Linked list nodes connected via next pointers.
- Function pointers enabling callbacks and polymorphism in C.
- Smart pointers in C++ (unique_ptr, shared_ptr) for automatic cleanup.

## Common Pitfalls

- Dangling pointers referencing freed memory.
- Buffer overflows from unchecked pointer arithmetic.
- Memory leaks from lost pointer references.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Raw pointers | Maximum control and performance | Error-prone, unsafe |
| Smart pointers | Automatic memory management | Runtime overhead |
| References | Safe aliasing | Cannot be null or reseated |

## Related Concepts

- [[Memory Management]]
- [[Data Structures]]

## Further Exploration

- The C Programming Language (Kernighan & Ritchie)
