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

Design patterns are reusable solutions to commonly recurring problems in software design, providing a shared vocabulary for developers.

## Why It Matters

Design patterns accelerate development, improve code quality, and facilitate communication by providing proven solutions that are well-understood across the industry.

## Key Principles

- Intent over implementation — focus on what the pattern solves, not mechanical application
- Composition over inheritance — favour object composition for flexibility
- Open/closed principle — classes should be open for extension, closed for modification

## How It Works

1. Identify a recurring design problem in the codebase.
2. Match the problem to a known pattern (creational, structural, or behavioural).
3. Adapt the pattern to the specific context without over-engineering.
4. Document the pattern usage for team awareness.

## Examples

- Singleton: ensuring a single instance of a resource manager.
- Observer: event-driven UI updates.
- Strategy: swappable algorithm implementations.

## Common Pitfalls

- Applying patterns where simple code would suffice.
- Using patterns as a substitute for understanding the problem.
- Pattern overload making code harder to follow.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Abstraction | Flexibility and reuse | Indirection and complexity |
| Standardisation | Team communication | Learning curve for newcomers |
| Decoupling | Independent component evolution | More files and interfaces |

## Related Concepts

- [[Software Engineering]]
- [[Algorithms]]

## Further Exploration

- Design Patterns: Elements of Reusable Object-Oriented Software (GoF)
- Head First Design Patterns (Freeman et al.)
