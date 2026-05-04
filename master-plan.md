# Context Vault Engine - Master Roadmap

## Project Identity

The project is now named **Context Vault Engine**.

Context Vault Engine is a local-first system for turning structured Markdown vaults into validated, queryable, packageable, and agent-consumable context.

The project exists to support a Context Development Lifecycle, or CDLC, where context is treated as an engineered artefact rather than loose notes, prompt scraps, or manually copied documentation.

The system should remain grounded in deterministic validation, schema-driven structure, and explicit quality controls. It should not become a vague AI-agent framework, a generic RAG wrapper, or a second Obsidian.

## Strategic Thesis

The core thesis is:

> Context Vault Engine manages the lifecycle of high-quality knowledge context: validate it, analyse it, improve it, package it, serve it, observe its use, and feed that evidence back into the vault.

The current system is best understood as a **schema-driven vault auditing and improvement engine**. The roadmap evolves it into a **CDLC-aligned context engine** without rewriting the foundations.

The project should move from:

```text
Markdown vault validation

towards:

Validated context lifecycle engine

The intended lifecycle is:

Human-authored Markdown knowledge
        ↓
Schema-normalised vault
        ↓
Deterministic validation
        ↓
Quality and gap analysis
        ↓
Task generation
        ↓
Context bundle assembly
        ↓
Agent-consumable API and export formats
        ↓
Feedback capture
        ↓
Priority adjustment and vault improvement
Important Evidence Policy

The forensic analysis reports currently attached to the project are useful but temporary evidence.

They are not permanent truth.

They should be treated as dated diagnostic snapshots of the codebase at the time they were produced. As the project changes, those reports will become less accurate. Future decisions must prefer the live codebase over older reports.

Use this authority order:

Current live repository code
Current tests and actual command output
Current documentation
Recent forensic analysis reports
Older forensic reports
Conversation memory and assumptions

When reports conflict with live code, live code wins.

When a roadmap item relies on a forensic report, verify it against the current code before implementation.

When enough roadmap items have been completed, either archive or delete the old forensic reports so they do not mislead future work.

Current System Classification

The current system is a validation and analysis engine with an emerging API layer.

Known strengths:

Schema-driven note validation
Frontmatter validation
Section presence checks
Boolean field synchronisation
Deterministic task scoring
Quality audit logic
Vault-level analysis
Graph primitives
Query surface
CLI and API foundations
Local-first architecture
Markdown-first knowledge structure

Known weaknesses:

API surface is incomplete
Some implemented adapter functions may not yet be routed
Query/index freshness must be treated cautiously
Context bundle generation is not yet first-class
Feedback loop is not yet first-class
Distribution/export format is not yet mature
Security scanning for context is not yet present
Older reports may describe bugs that have since been fixed, or miss new changes
CDLC Alignment

Context Vault Engine should align to four CDLC stages.

1. Generate

Generate does not initially mean generating prose with an LLM.

In this project, Generate means:

Generate templates
Generate schema-valid note structures
Generate improvement tasks
Generate context bundles
Generate exportable context packages
Generate manifests and validation reports
Eventually generate draft context from trusted source material, but only after validation rules are stable

Immediate goal:

Move from note validation to context assembly.
2. Evaluate

Evaluate is the current core strength.

Evaluation should remain deterministic first.

Evaluation includes:

Frontmatter schema validation
Derived field consistency
Required section checks
Section format checks
Quality scoring
Gap detection
Duplicate or conflicting metadata detection
Context bundle validation
Export manifest validation
Optional LLM-as-judge checks only after deterministic checks pass

Rule:

Never replace deterministic validation with LLM judgement.

LLM judgement may be added later as an advisory layer, not as the foundation.

3. Distribute

Distribute means making context portable and reusable.

Initial distribution targets:

context.md
context.json
manifest.json
validation.json
graph.json

Later distribution targets:

Versioned context bundles
Local bundle registry
Signed or hashed artefacts
Team-shareable context packages
MCP-consumable context surfaces
Agent-specific context formats

Do not build a registry before the bundle format is stable.

4. Observe and Adapt

Observe means capturing how context performs when used.

Initial observation model:

Human feedback linked to note paths
Agent failure notes linked to context bundles
Validation drift reports
Query usage metrics
Bundle usage metadata
Repeated failure patterns
Notes that are frequently retrieved but incomplete
Notes that are frequently involved in failed agent outputs

Adapt means feeding this evidence back into:

Task priority
Quality scoring
Missing concept detection
Context bundle selection rules
Documentation improvements
Schema refinements
Non-Goals

Do not turn this into:

A generic AI agent framework
A generic RAG application
A replacement for Obsidian
A fully autonomous content writer
A bloated knowledge management suite
A cloud-first platform
A database-heavy enterprise system
A project that depends on embeddings before deterministic structure is solved

Embeddings, semantic search, and LLM evaluation may be added later, but only after deterministic context packaging works.

Architectural Principles
1. Deterministic first

Every core operation should be repeatable.

Given the same vault state and same command, the system should return the same result.

2. Markdown remains the source format

Markdown vaults remain the main human-authored knowledge layer.

The system may export JSON or other formats, but Markdown remains the editable source of truth.

3. Schema is the contract

The schema defines valid structure, valid metadata, expected sections, allowed domains, and derivation rules.

Any change to the schema interface must be treated as high risk.

4. Context bundles are build artefacts

Context bundles should be generated from the vault.

They should not become the primary editing surface.

5. Validation before packaging

A context bundle should carry its validation status.

Invalid or partial notes may be included only when explicitly requested.

6. Feedback should influence priority, not silently mutate content

Feedback should adjust task scoring and improvement priority.

It should not automatically rewrite notes without review.

7. Avoid hidden state

Caches, indexes, generated reports, and context bundles must have clear invalidation rules.

Stale context is a serious correctness failure.

8. Prefer small composable primitives

Avoid large rewrites.

Extend by adding narrow functions, routes, commands, and export formats.

Roadmap Overview

The roadmap has eight major phases.

Phase 0 - Stabilise correctness
Phase 1 - Expose existing capabilities
Phase 2 - Build context bundle generation
Phase 3 - Add feedback loop
Phase 4 - Add export and packaging
Phase 5 - Add context security checks
Phase 6 - Add documentation and project positioning
Phase 7 - Add optional semantic retrieval
Phase 8 - Add registry and reuse layer
Phase 0 - Stabilise Correctness

Purpose:

Before expanding the system, fix correctness issues that would undermine trust in the context lifecycle.

Priority items:

Fix any known active runtime bugs.
Verify whether old forensic bug claims still exist.
Fix query/index freshness issues.
Ensure note edits are reflected in API query results.
Fix unsafe query behaviour where malformed filters may return too much.
Ensure invalid filters fail clearly or warn explicitly.
Add regression tests for each fix.
Confirm CLI and API behaviour are intentionally aligned or intentionally different.
Update README and Quickstart after confirmed behaviour changes.

Acceptance criteria:

Validation command works.
Analyse command works.
Improve/task generation works.
Query endpoint returns current note state.
Note edits are visible without requiring unrelated schema edits.
Unknown query fields do not silently return all notes.
Malformed query operators do not silently remove filters.
Tests cover the corrected behaviours.
Old forensic reports are marked as dated or superseded where appropriate.
Phase 1 - Expose Existing Capabilities

Purpose:

Make the already-existing engine capabilities accessible through the API.

Target API surfaces:

GET  /validation
GET  /tasks
GET  /notes
GET  /quality
GET  /missing
POST /compare
GET  /graph/{vault}
GET  /graph/{vault}/related
GET  /graph/{vault}/missing

Implementation rules:

Do not rewrite core logic.
Route existing adapter and graph functions.
Preserve existing middleware behaviour.
Add minimal request/response models where needed.
Keep output structured and predictable.
Ensure route errors are explicit.

Acceptance criteria:

Each routed function has a smoke test.
API output includes enough information for external tools to consume.
Task endpoints preserve necessary writing constraints.
Path output uses full vault-relative POSIX paths, not ambiguous stems.
Graph endpoints return deterministic ordering.
Documentation lists every route with example request and response.
Phase 2 - Context Bundle Generation

Purpose:

Make context bundles the first major CDLC artefact.

A context bundle is a deterministic package of selected notes, metadata, sections, graph relationships, validation state, and budget information.

Initial context bundle command:

python run.py bundle

Potential API route:

POST /context/bundle

Minimum bundle inputs:

{
  "vault": "demo-vault",
  "filters": {
    "domain": "fundamentals",
    "status": "complete"
  },
  "include_sections": [
    "Key Principles",
    "How It Works",
    "Trade-offs"
  ],
  "include_related": true,
  "max_notes": 10,
  "max_chars": 20000
}

Minimum bundle output:

{
  "bundle_id": "fundamentals-complete",
  "vault": "demo-vault",
  "filters": {},
  "created_at": "ISO-8601 timestamp",
  "validation_status": "pass",
  "notes": [
    {
      "path": "Fundamentals/Algorithms.md",
      "fields": {},
      "sections": {},
      "body": "..."
    }
  ],
  "graph": {
    "related": []
  },
  "budget": {
    "max_chars": 20000,
    "used_chars": 12500,
    "note_count": 6
  },
  "warnings": []
}

Bundle rules:

Deterministic ordering.
Full paths only.
Include validation status.
Exclude invalid notes by default.
Allow partial notes only when explicitly requested.
Respect max note count.
Respect max character budget.
Include warning if truncation occurs.
Include source paths.
Include schema version if available.
Include generated timestamp.
Include bundle manifest.

Acceptance criteria:

Bundle generation works from CLI.
Bundle generation works from API if API is in scope for the phase.
Bundle output is deterministic except for timestamp and bundle ID.
Bundle can include full note bodies.
Bundle can include selected sections only.
Bundle can include graph-related notes.
Bundle refuses or warns on invalid vault state.
Bundle tests cover complete, partial, invalid, empty, and over-budget cases.
Phase 3 - Feedback Loop

Purpose:

Add the Observe and Adapt layer.

Feedback should capture signals from humans or agents and feed them back into task priority and quality improvement.

Storage location:

<vault>/Vault Files/feedback.md

Feedback entries should link by full vault-relative POSIX path.

Example feedback structure:

feedback:
  - path: Fundamentals/Algorithms.md
    source: human
    signal: unclear
    severity: medium
    comment: "The How It Works section needs a clearer input to output flow."
    created_at: "2026-05-04T12:00:00Z"

Supported signals:

unclear
incomplete
outdated
incorrect
useful
agent_failed
agent_succeeded
needs_example
needs_constraints

Feedback should influence:

Task priority
Quality score modifiers
Improvement recommendations
Context bundle warnings
Future validation checks where appropriate

Feedback should not:

Automatically rewrite source notes
Silently change metadata
Override deterministic validation
Become hidden state outside the vault

Acceptance criteria:

Feedback file is excluded from normal note validation.
Feedback file is included in cache/index invalidation if relevant.
Feedback can be parsed safely.
Feedback linked to missing notes produces a warning.
Task scoring can optionally include feedback weighting.
Feedback influence is visible and explainable.
Tests cover malformed feedback, unknown paths, and multiple signals per note.
Phase 4 - Export and Packaging

Purpose:

Make context portable.

A context package should contain:

context.md
context.json
manifest.json
validation.json
graph.json
feedback-summary.json

Minimum package directory:

dist/context-bundles/<bundle-id>/

Package manifest should include:

{
  "bundle_id": "fundamentals-complete",
  "vault": "demo-vault",
  "schema_version": "3.0.0",
  "created_at": "ISO-8601 timestamp",
  "source_notes": [],
  "validation_status": "pass",
  "hashes": {
    "context.md": "...",
    "context.json": "..."
  }
}

Package rules:

Exports must be reproducible where possible.
Hash all generated artefacts.
Include source note paths.
Include validation state.
Include warnings.
Do not include secrets.
Do not include files outside selected context scope.
Do not overwrite packages without explicit flag or deterministic versioning.

Acceptance criteria:

CLI can export a package.
Package contains Markdown and JSON forms.
Package has a manifest.
Package has validation output.
Package can be regenerated.
Package hashes change when source context changes.
Package docs explain how to consume the artefact.
Phase 5 - Context Security Checks

Purpose:

Add security controls appropriate for CDLC.

Security checks should scan context before packaging or serving it to agents.

Initial checks:

Secret-like strings
API keys
Tokens
Password patterns
Private keys
Prompt injection strings
Instructions to ignore system messages
Tool misuse instructions
External links
Suspicious HTML or script blocks
Unexpected executable code blocks
Overly broad agent instructions

Security result levels:

pass
warning
fail

Security output example:

{
  "status": "warning",
  "findings": [
    {
      "path": "Fundamentals/Example.md",
      "severity": "medium",
      "rule": "prompt-injection-pattern",
      "detail": "Potential instruction override phrase detected."
    }
  ]
}

Acceptance criteria:

Security scan can run independently.
Bundle generation can require security pass.
Findings include path, rule, severity, and explanation.
False positives can be reviewed.
Security checks are documented.
Tests cover safe text, obvious secrets, and prompt injection patterns.
Phase 6 - Documentation and Positioning

Purpose:

Update project documentation to match the new direction.

Documentation should make clear:

The project is now Context Vault Engine.
The system supports CDLC.
It is local-first.
It is deterministic-first.
Markdown vaults remain the source.
Context bundles are generated artefacts.
The API serves validated context.
The system is not a generic agent framework.
The forensic reports are historical diagnostics, not permanent truth.

Docs to update:

README.md
QUICKSTART.md
ARCHITECTURE.md
ROADMAP.md
CONTEXT_BUNDLE_SPEC.md
API.md
TESTING.md

Acceptance criteria:

README explains the project in one clear paragraph.
Quickstart shows init, validate, analyse, improve, bundle.
Architecture explains CLI, core engine, runtime/index, API, bundles.
Roadmap reflects this master plan.
API docs include examples.
Testing docs include commands to verify system behaviour.
Old forensic reports are referenced only as dated snapshots if retained.
Phase 7 - Optional Semantic Retrieval

Purpose:

Add semantic retrieval only after deterministic context bundles work.

Do not start here.

Potential additions:

Embedding index
Semantic search endpoint
Hybrid search combining filters plus embeddings
Similarity ranking
Context budget optimisation
Relevance explanations
Local embedding model support

Rules:

Semantic retrieval must not bypass schema validation.
Semantic results must include source paths.
Semantic ranking must be explainable enough to debug.
Deterministic filters should run before semantic ranking where possible.
Invalid notes should be excluded unless explicitly allowed.

Acceptance criteria:

Semantic search is optional.
System works without embeddings.
Embedding cache invalidates on note changes.
Results include paths and validation state.
Hybrid search can be tested against deterministic expectations.
Phase 8 - Registry and Reuse Layer

Purpose:

Add reusable context packages only after packages are stable.

Potential registry features:

Local context bundle registry
Bundle versioning
Bundle tags
Bundle dependency metadata
Bundle compatibility checks
Bundle signing or hashing
Conflict detection between context packages
Import/export between machines

Do not build this early.

Acceptance criteria:

Registry stores generated packages, not source notes.
Registry can list packages.
Registry can verify hashes.
Registry can report validation status.
Registry can detect stale packages.
Registry can remove or archive old packages.
Testing Strategy

Every phase must include tests.

Minimum test categories:

CLI smoke tests
API route tests
Validation tests
Query correctness tests
Index freshness tests
Cache invalidation tests
Bundle generation tests
Feedback parsing tests
Export hash tests
Security scan tests
Malformed input tests
Path traversal tests

Important test cases:

Note added after server start
Note edited after server start
Note deleted after server start
Unknown query field
Malformed query operator
Duplicate YAML key if detectable
Missing frontmatter
Malformed frontmatter
Duplicate headings
Partial note bundle inclusion
Invalid note exclusion
Over-budget bundle
Feedback linked to missing note
Secret-like string in context
Prompt injection-like text in context
Implementation Discipline

Before implementing any roadmap item:

Verify the current code.
Check whether older reports are still accurate.
Identify the smallest safe change.
Add or update tests.
Run tests.
Update docs if behaviour changes.
Record any superseded forensic findings.

Do not implement from old reports blindly.

Do not stack multiple architectural changes in one prompt unless they are tightly coupled.

Prefer small commits.

Recommended commit style:

fix: correct query filter handling
feat: add context bundle generation
test: cover index rebuild on note edits
docs: document Context Vault Engine roadmap
Stop Conditions

Pause and reassess if:

Schema interface changes become necessary.
Multi-vault support requires config redesign.
Query/index correctness cannot be guaranteed.
Context bundles require too much duplicated logic.
API and CLI outputs diverge in unexplained ways.
Performance becomes unacceptable at realistic vault sizes.
Tests become brittle because architecture is unclear.
Old forensic reports conflict repeatedly with current code.
Definition of Success

Context Vault Engine is successful when it can:

Validate a Markdown vault.
Analyse quality and gaps.
Generate prioritised improvement tasks.
Serve current note data through an API.
Build deterministic context bundles.
Export context packages.
Scan context for security risks.
Capture feedback.
Feed feedback into future improvement priority.
Explain every generated artefact through source paths, validation state, and manifest metadata.

The project should remain small enough to reason about, but structured enough to demonstrate a serious CDLC workflow.

Short Project Description

Context Vault Engine is a local-first CDLC system for structured Markdown knowledge bases. It validates vault content against explicit schemas, analyses quality and gaps, generates improvement tasks, assembles deterministic context bundles, exports agent-consumable packages, and feeds usage feedback back into the vault improvement cycle.

Current Priority

The next priority is not to add AI features.

The next priority is:

Stabilise correctness, expose the existing API surface, then implement context bundle generation.

This protects the project from bloat and keeps the CDLC pivot grounded in the system’s existing strengths.