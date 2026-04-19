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

Testing is the systematic process of verifying that software behaves as intended and identifying defects before deployment.

## Why It Matters

Testing catches bugs early, provides confidence in refactoring, documents expected behaviour, and prevents regressions from reaching production.

## Key Principles

## How It Works

1. Write a test that describes expected behaviour for a unit of code.
2. Run the test and confirm it fails (red phase in TDD).
3. Implement the minimum code to make the test pass (green phase).

## Examples

- pytest for Python unit and integration testing.
- Jest for JavaScript/TypeScript testing.
- Selenium for browser-based end-to-end testing.

## Common Pitfalls

- Testing implementation details instead of behaviour.
- Flaky tests that pass or fail nondeterministically.
- Insufficient test coverage on critical paths.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Unit tests | Fast feedback, high isolation | Cannot catch integration issues |
| Integration tests | Tests real interactions | Slower, more complex setup |
| End-to-end tests | Validates full user flows | Brittle and slow |

## Related Concepts

- [[Software Engineering]]
- [[Continuous Integration]]

## Further Exploration

- Test-Driven Development by Example (Beck)
