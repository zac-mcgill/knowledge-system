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

Testing is the systematic process of verifying that software behaves as intended and identifying defects before deployment.

## Why It Matters

Testing catches bugs early, provides confidence in refactoring, documents expected behaviour, and prevents regressions from reaching production.

## Key Principles

- **Unit isolation** tests a single unit of behaviour in isolation from its dependencies, making failures fast to locate and fix.
- **Regression prevention** re-runs the full test suite on every change to catch newly introduced breakage before it reaches production.
- **Test as documentation** writes test names and assertions as precise specifications so the test suite communicates intended behaviour to future readers.
- **Red-green-refactor** drives development by writing a failing test first, making it pass with minimal code, then improving structure without changing behaviour.
- **Boundary cases** explicitly test inputs at the edges of valid ranges, empty inputs, and off-by-one conditions where bugs are most likely to hide.

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
