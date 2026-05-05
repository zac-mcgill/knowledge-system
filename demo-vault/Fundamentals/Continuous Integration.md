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

Continuous integration is the practice of automatically building and testing code changes as they are committed, providing rapid feedback to developers.

## Why It Matters

CI catches integration errors early, reduces the risk of large merges, and ensures that the main branch is always in a working state.

## Key Principles

- **Fast feedback** means build and test cycles should complete quickly enough that developers can act on results before context-switching.
- **Single shared branch** ensures all contributors integrate to the same mainline frequently, avoiding long-lived divergent branches.
- **Automated verification** replaces manual checks with repeatable build, lint, and test steps that run on every commit.
- **Reproducible builds** ensure the same source code produces the same artefact regardless of environment or timing.
- **Small integration batches** limit the blast radius of any single change, making failures easier to diagnose and revert.

## How It Works

1. A developer pushes a commit to the shared repository.
2. The CI server detects the change and triggers a build.
3. Automated tests run against the built artefact.

## Examples

- GitHub Actions running tests on every pull request.
- Jenkins pipelines for complex multi-stage builds.
- GitLab CI with Docker-based runners.

## Common Pitfalls

- Slow test suites that delay feedback beyond useful limits.
- Ignoring broken builds and continuing to commit.
- Insufficient test coverage making CI checks meaningless.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Frequent integration | Catches errors early | Requires robust test suite |
| Automated builds | Consistent, repeatable | Infrastructure maintenance |
| Fast feedback | Developers fix issues quickly | Investment in pipeline speed |

## Related Concepts

- [[Testing]]
- [[Version Control]]
- [[Software Engineering]]

## Further Exploration

- Continuous Delivery (Humble & Farley)
