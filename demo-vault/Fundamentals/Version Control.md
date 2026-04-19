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

Version control is a system that records changes to files over time so that specific versions can be recalled, compared, and merged.

## Why It Matters

Version control enables collaboration, provides an audit trail of changes, allows safe experimentation through branching, and is the foundation of modern software development workflows.

## Key Principles

- History — every change is recorded with metadata (author, timestamp, message)
- Branching — divergent lines of development can coexist
- Merging — branches can be reconciled, with conflict resolution when needed
- Distributed — each developer holds a full copy of the repository (in DVCS)

## How It Works

1. Initialise a repository to begin tracking changes.
2. Stage modified files for the next commit.
3. Commit staged changes with a descriptive message.
4. Push commits to a remote repository for collaboration.
5. Pull changes from the remote and resolve any merge conflicts.

## Examples

- Git: the dominant distributed version control system.
- GitHub/GitLab: hosted platforms adding code review and CI/CD.
- Semantic versioning for release management.

## Common Pitfalls

- Committing large binary files that bloat the repository.
- Vague commit messages that provide no context.
- Force-pushing to shared branches, rewriting public history.

## Trade-offs

| Aspect | Benefit | Cost |
| --- | --- | --- |
| Distributed VCS | Offline work, full history locally | Larger local storage |
| Centralised VCS | Simpler model | Single point of failure |
| Monorepo | Unified versioning | Tooling complexity at scale |

## Related Concepts

- [[Software Engineering]]
- [[Testing]]
- [[Continuous Integration]]

## Further Exploration

- Pro Git (Chacon & Straub) — free online
