Context Vault Engine - Updated Master Roadmap
Executive Direction

Context Vault Engine should now move from “technically strong pipeline” to “usable local application”.

The system is already solid as a deterministic backend: schema validation, analysis, improvement tasks, context bundles, export packages, security scanning, feedback, lexical search, API routes, and a complete demo vault are all implemented. The README now correctly presents it as a local-first Python content security and packaging pipeline with credential leak scanning, prompt-injection detection, schema enforcement, path-traversal blocking, SHA-256 artefact integrity, and 180 tests.

The next strategic problem is friction.

A terminal-only workflow is acceptable for developers, but not ideal for the project’s actual use case: helping a user bootstrap, validate, improve, package, and inspect a structured knowledge vault. For that, the ideal direction is:

A local-first web UI backed by the existing FastAPI/API engine, with the CLI retained as an automation and power-user layer.

Do not replace the CLI. Do not turn this into a cloud app. Do not rush semantic retrieval. The next major value is a usable interface with buttons, forms, status panels, guided vault creation, and clear outputs.

1. Current Project State
1.1 Project Identity

Name: Context Vault Engine

Current public positioning:
A local-first Python content security and packaging pipeline for structured Markdown vaults.

Public value statement:
Context Vault Engine validates, scans, packages, and serves structured Markdown content as deterministic context artefacts. It enforces schema contracts, detects credential leaks and prompt-injection patterns, rejects unsafe paths, exports SHA-256 verified packages, and exposes the workflow through a CLI and FastAPI API.

1.2 Current Release State

Current release: v1.0.0

Current achieved baseline:

Area	Status
Demo vault	19/19 notes complete
Validation	Complete
Analysis	Complete
Improvement tasks	Complete
Context bundles	Complete
Export packages	Complete
Security scanner	Complete
Feedback loop	Complete
Deterministic lexical search	Complete
API documentation	Complete
README positioning	Security-focused
Tests	180 passing
Semantic retrieval	Deferred
UI	Not yet implemented
1.3 Implemented System Capabilities

The current system includes:

Schema validation on every note
Derived-field consistency checks
Required section checks
Analysis reports
Improvement task generation
Deterministic lexical search on POST /query
Context bundle generation
Export package generation to dist/context-bundles/<bundle-id>/
SHA-256 package manifests
Feedback parsing and task weighting
Missing concept detection using EXPECTED_CONCEPTS
Security scanning for:
private keys
AWS/GitHub/Slack token-like values
bearer tokens
password-like assignments
prompt-injection phrases
suspicious scripts and executable blocks
Optional export security gate
Rate-limited FastAPI API
Path-traversal protection
Structured JSON errors
Full route documentation

The API currently exposes routes for vaults, health, contract checks, summary, query, note retrieval, stats, validation, tasks, notes, quality, missing concepts, gaps, feedback, compare, graph, context bundle, context export, and context security.

2. Strategic Assessment
2.1 What Is Strong

The backend is no longer the weak point.

The strongest parts are:

Deterministic architecture
Local-first operation
Schema-driven validation
Security scanner with explainable findings
Export package integrity
Structured API
Strong testing story
Complete demo vault
Recruiter-friendly security positioning
2.2 What Is Weak

The major weakness is now usability:

Weakness	Impact
Terminal-first workflow	High friction for non-developer users
Bootstrap is interactive terminal-only	Hard to understand, hard to preview, hard to recover from mistakes
API exists but has no human UI	Powerful backend, poor discoverability
Reports are mostly command outputs	Hard to inspect visually
Bundle/export/security outputs are JSON-first	Useful for tools, less friendly for humans
No dashboard	User cannot quickly see vault health
No guided setup	User must know command order
No visual feedback loop	Feedback exists, but editing feedback.md manually is clunky
No package browser	Exports work, but are not browsable in-app
2.3 Terminal Application vs UI
Terminal-only is not ideal

The CLI should remain, but it should not be the main user experience.

A terminal app is good for:

automation
testing
CI
reproducible workflows
advanced users
scripting

A terminal app is poor for:

guided vault bootstrapping
editing fields
browsing notes
reviewing validation errors
inspecting package artefacts
visualising security findings
understanding graph relationships
presenting the project to non-technical reviewers
Ideal direction

The ideal product shape is:

Local browser UI
    ↓
Existing FastAPI API
    ↓
Existing deterministic engine
    ↓
Markdown vault on disk

In practical terms:

User runs one command, such as py run.py app
Browser opens to http://127.0.0.1:8000/app
User can:
create/bootstrap a vault
choose a schema/domain
run validation
inspect issues
generate tasks
create bundles
run security scans
export packages
review feedback
browse notes
inspect missing concepts

This gives the project a real “application” feel without abandoning the local-first backend.

3. Updated Product Vision
3.1 New North Star

Context Vault Engine should become a local-first desktop-style web application for validating, securing, packaging, and improving structured Markdown vaults.

The backend stays deterministic. The UI makes it usable.

3.2 Product Principles Going Forward
1. Local-first

No cloud requirement. No hosted account. No external API dependency.

2. UI-first for humans, CLI-first for automation

The CLI remains stable, but common workflows should be available through buttons and forms.

3. Markdown remains the source of truth

The UI may edit or generate Markdown files, but the vault remains the canonical data layer.

4. Deterministic before intelligent

Do not add embeddings or LLM features until the UI and local workflow are good.

5. Security controls stay visible

Security scanning should not be hidden in logs. Findings need a UI panel.

6. Guided workflows beat raw endpoints

Users should not need to know the correct command order.

7. Progressive disclosure

Beginner users see simple statuses. Advanced users can open raw JSON, manifests, and API output.

4. Roadmap Overview
Completed
Phase	Name	Status
Phase 0	Correctness stabilisation	Complete
Phase 1	API capability exposure	Complete
Phase 2	Context bundle generation	Complete
Phase 3	Feedback loop	Complete
Phase 4	Export and packaging	Complete
Phase 5	Context security scanning	Complete
Phase 6	Documentation and positioning	Complete
Phase 7a	Deterministic lexical search	Complete
Phase 8a	Demo vault completion	Complete
Phase 8b	Schema data demo improvements	Complete
Phase 9	Public presentation pass	Complete
Phase 10	Local Web UI Foundation	Complete
Phase 11A	Guided Vault Bootstrap Backend API	Complete
Phase 11B	Guided Vault Bootstrap UI Form	Complete
Phase 11	Guided Vault Bootstrap (full)	Complete
Future
Phase	Name	Priority
Phase 12	Vault Dashboard and Issue Review	Highest
Phase 13	Bundle, Export, and Security UI	High
Phase 14	Feedback and Task Workflow UI	Medium
Phase 15	Note Browser and Safe Editing UI	Medium
Phase 16	Visual Graph and Missing Concepts UI	Medium
Phase 17	Distribution and Packaging	Medium
Phase 18	CI and Release Hardening	Medium
Phase 19	Optional Semantic Retrieval	Deferred
Phase 20	Registry and Reuse Layer	Deferred
5. Completed Phases Summary
Phase 0 - Correctness Stabilisation

Status: Complete

Delivered:

Query filter safety
Index freshness fixes
Fail-closed invalid filters
Regression tests
CLI/API behaviour verified
Phase 1 - API Surface

Status: Complete

Delivered:

Validation endpoint
Tasks endpoint
Notes endpoint
Quality endpoint
Missing endpoint
Compare endpoint
Graph routes
Full paths and constraints in task output
Phase 2 - Context Bundles

Status: Complete

Delivered:

py run.py bundle
POST /context/bundle
Deterministic bundle ID
Note selection
Section extraction
Budget tracking
Validation state
Feedback block
Manifest source paths
Phase 3 - Feedback Loop

Status: Complete

Delivered:

feedback.md
Feedback parser
Feedback validation
py run.py feedback
GET /feedback
Task priority weighting via include_feedback=true
Bundle feedback inclusion
Phase 4 - Export and Packaging

Status: Complete

Delivered:

py run.py export
POST /context/export
Exported package directory
context.json
context.md
manifest.json
validation.json
graph.json
feedback-summary.json
SHA-256 hashes
Overwrite protection
Phase 5 - Security Scanner

Status: Complete

Delivered:

py run.py security
POST /context/security
Credential leak scanning
Prompt-injection pattern detection
Suspicious script/code detection
Security severity levels
Optional export gate with require_security_pass
Phase 6 - Documentation

Status: Complete

Delivered:

README
QUICKSTART
ARCHITECTURE
ROADMAP
API docs
TESTING docs
Context bundle spec
Phase 7a - Deterministic Lexical Search

Status: Complete

Delivered:

q parameter on POST /query
q_fields
Body/path/frontmatter lexical search
Deterministic TF scoring
Timeout handling
Invalid query validation
No embeddings
Phase 8a - Demo Vault Completion

Status: Complete

Delivered:

8 partial notes completed
Vault moved to 19/19 complete
0 improvement targets
Phase 8b - Schema Data Demo Improvements

Status: Complete

Delivered:

SCHEMA_VERSION = "3.0.0"
EXPECTED_CONCEPTS["fundamentals"]
/missing now returns meaningful gaps
Exported manifest schema version fixed
Phase 9 - Public Presentation

Status: Complete

Delivered:

README repositioned around deterministic content security pipeline
GitHub repo renamed to context-vault-engine
GitHub About section updated
Security controls surfaced publicly
Sample output added
6. New Roadmap
Phase 10 - Local Web UI Foundation
Purpose

Create the first real user interface.

This phase should not attempt to expose every feature. It should establish the UI shell, navigation, API connection, and basic status views.

Recommended Architecture

Use the existing FastAPI server as the backend.

Frontend options:

Option A - Server-rendered HTML with HTMX

Best for simplicity.

Pros:

Low dependency burden
Easy to serve from FastAPI
Good for forms and dashboards
No separate frontend build pipeline

Cons:

Less polished than React for complex state
Harder to build rich graph visualisation later
Option B - React/Vite frontend served separately or built into FastAPI

Best for long-term UI quality.

Pros:

Better for dashboards, forms, tabs, charts
Better portfolio presentation
Easier to expand into a desktop shell later

Cons:

More dependencies
More project complexity
Requires frontend build tooling
Recommendation

Use React + Vite + TypeScript for the UI, but keep it small.

Reason: the user explicitly wants “UI, buttons, fields etc.” and this project is now portfolio-facing. A clean React interface will show better than a terminal or basic HTML admin page.

Target UI Shell

Pages:

Dashboard
Vault Setup
Notes
Validation
Tasks
Bundles
Security
Exports
Feedback
API/Raw Output
Required Backend Work

Add route:

GET /app

or serve static frontend from:

ui/dist/

Add dev documentation:

cd ui
npm install
npm run dev

Production build:

npm run build
Acceptance Criteria
UI starts locally
UI can call /health
UI can list vaults
UI can show current vault summary
UI can run validation
UI has navigation
UI does not break existing CLI/API/tests
Documentation explains how to run the UI
Tests
Existing 180 tests still pass
Add at least one backend test proving UI static route exists if served by FastAPI
Frontend tests optional at this stage
Suggested Commit
feat(ui): add local web interface foundation

Phase 11A - Guided Vault Bootstrap Backend API
Status: Complete

Purpose: Provide a non-interactive, HTTP-accessible vault bootstrap pathway that the CLI and the future UI form can both use.

Delivered:
- core/shared/bootstrap_service.py — shared vault bootstrap service (validate, create, rollback, config update)
- core/bootstrap_vault.py — refactored _update_config() to delegate to service; interactive CLI unchanged
- mcp/core/vault_registry.py — reload_config() for in-process registry refresh after bootstrap
- mcp/server/mcp_server.py — POST /vault/bootstrap endpoint, VaultBootstrapRequest model, _BOOTSTRAP_REPO_ROOT override for tests
- mcp/test_verify.py — 14 Phase 11A tests added (202 total)
- API.md — documented POST /vault/bootstrap, request/response shapes, error codes
- QUICKSTART.md — section 6c covers API-based vault bootstrap
- TESTING.md — Phase 11A test descriptions added

Acceptance criteria met:
- POST /vault/bootstrap creates vault, schema, templates, updates config
- CLI py run.py bootstrap still works
- All prior 188 tests still pass
- expected_concepts accepted with warning; not written to schema yet

Suggested Commit
feat(bootstrap): add POST /vault/bootstrap API endpoint (Phase 11A)

Phase 11B - Guided Vault Bootstrap UI Form
Purpose

Make vault creation low-friction.

The existing py run.py bootstrap flow prompts for domain, note type, and sections in the terminal. The Quickstart currently recommends py run.py bootstrap for custom vaults. That is usable for developers but not ideal for the intended product.

This phase should make vault creation guided, visual, and recoverable.

User Story

As a user, I want to create a new vault by filling in a form, previewing the schema, and clicking “Create Vault”, without needing to understand the terminal bootstrap flow.

UI Flow
User opens Vault Setup
Selects:
vault name
domain name
note type slug
required sections
optional expected concepts
UI validates inputs live
UI previews:
folder structure
schema fields
generated template
User clicks Create Vault
App writes vault files and updates config
User lands on dashboard
Backend Additions

Add API route:

POST /vault/bootstrap

Request shape:

{
  "vault_name": "dogs-vault",
  "domain": "dogs",
  "note_type": "breed-profile",
  "sections": ["Overview", "Care Requirements", "Health Risks"],
  "expected_concepts": ["Labrador Retriever", "German Shepherd"]
}

Response:

{
  "status": "ok",
  "vault": "dogs-vault",
  "created": ["..."],
  "warnings": []
}
Important Rules
Do not expose arbitrary file writes
Validate vault name strictly
Prevent path traversal
Do not overwrite existing vault without explicit confirmation
Reuse existing bootstrap/generate schema logic where possible
Keep terminal bootstrap working
Acceptance Criteria
User can create a vault from the UI
Generated vault validates immediately
Generated templates are created
Config updates safely
Existing py run.py bootstrap still works
Tests cover invalid names, duplicate vaults, and successful bootstrap
Suggested Commit
feat(ui): add guided vault bootstrap UI form (Phase 11B)

Phase 12 - Vault Dashboard and Issue Review
Purpose

Give users an immediate understanding of vault health.

The dashboard should answer:

Is my vault valid?
How many notes do I have?
How many are complete?
What needs work?
Are there security findings?
Are there missing expected concepts?
Can I export safely?
Dashboard Panels

Recommended panels:

Panel	Source
Vault status	/summary, /validation
Completion	/summary
Current tasks	/tasks
Security status	/context/security
Missing concepts	/missing
Latest export	local package directory
Feedback count	/feedback
Test status	optional, manually run
UI Requirements
Clear pass/fail/warning badges
Clickable task cards
Validation error list
Security findings table
Missing concepts list
Export package summary
“Run pipeline” button
Acceptance Criteria
Dashboard loads in under 2 seconds for demo vault
User can run validation from UI
User can run security scan from UI
User can see incomplete or missing work
No raw JSON shown by default
Raw JSON available in expandable panel
Suggested Commit
feat(ui): add vault health dashboard
Phase 13 - Bundle, Export, and Security UI
Purpose

Make the strongest backend features visible and usable.

Current CLI/API export is strong, but users should not need to read JSON to understand it.

UI Pages
Bundle Builder

Fields:

vault
filters
include sections
include body
include related
max notes
max chars
allow partial

Actions:

Preview bundle
Show budget usage
Show included notes
Show warnings
Export Package

Actions:

Export package
Overwrite existing
Require security pass
Open package summary
Security Scan

Display:

status: pass / warning / fail
findings grouped by severity
finding path
rule
field
explanation
affected note
Acceptance Criteria
User can generate bundle from UI
User can export package from UI
User can require security pass
User can inspect warnings
User can inspect manifest hashes
UI clearly distinguishes warning vs fail
Suggested Commit
feat(ui): add bundle export and security scan screens
Phase 14 - Feedback and Task Workflow UI
Purpose

Make the Observe and Adapt layer usable without manually editing feedback.md.

User Story

As a user, I want to add feedback to a note from the UI and see task priorities update.

UI Features
Feedback list
Add feedback form
Edit feedback entry
Delete feedback entry
Filter feedback by source/signal/severity/path
Toggle “include feedback in task priority”
Show before/after priority scores
Backend Additions

Currently feedback is read from feedback.md. Add safe write operations:

POST /feedback
PUT /feedback/{id}
DELETE /feedback/{id}

Only if feedback entries receive stable IDs.

Alternative simpler approach:

Keep file-based feedback
UI edits whole feedback document through a controlled textarea
Validate before save

Recommended approach:

Add generated stable IDs to feedback entries
Use structured add/edit/delete routes
Acceptance Criteria
User can add feedback from UI
Invalid feedback is rejected before write
Feedback file remains human-readable
Task priority changes are visible
Existing manual feedback file editing remains valid
Suggested Commit
feat(ui): add feedback review workflow
Phase 15 - Note Browser and Safe Editing UI
Purpose

Allow users to browse and lightly edit notes without leaving the app.

This should be conservative. The system should not become a full Obsidian clone.

Features
Note list
Filter by status/domain/type
Search using lexical q
View note frontmatter
View note body
Edit frontmatter fields through form controls
Edit sections in text areas
Validate before save
Save writes Markdown file
Show diff preview before save
Safety Rules
No arbitrary file path writes
Only edit files inside the active vault
Preserve frontmatter order where practical
Preserve headings
Validate after save
Show validation errors immediately
No automatic AI rewriting
Acceptance Criteria
User can view notes
User can search notes
User can edit a section
Save triggers validation
Invalid edits are rejected or clearly warned
CLI validation still passes after UI edits
Suggested Commit
feat(ui): add note browser and safe editing
Phase 16 - Visual Graph and Missing Concepts UI
Purpose

Make graph and missing concepts visible.

The graph backend exists, but graph output is not visually compelling yet.

Features
Graph view
Domain/subdomain/topic nodes
Note nodes
Missing concept nodes
Click node to inspect related notes
Click missing concept to create draft note or task
Filter graph by relationship type
Important Constraint

Do not overbuild graph visualisation before there is enough graph data.

The demo vault currently has one primary domain. A visual graph becomes more valuable after:

multiple subdomains
richer expected concepts
more notes
explicit concept hierarchy
Acceptance Criteria
Missing concepts are visible
User can see which concepts are absent
User can create an improvement task from a missing concept
Graph view does not imply semantic relationships if only schema relationships exist
Suggested Commit
feat(ui): add missing concept and graph visualisation
Phase 17 - Distribution and Packaging
Purpose

Make the app easier to run.

A local web app still requires commands. This phase should reduce install friction.

Options
Option A - Keep Python project, add launcher

Add:

py run.py app

This starts backend and opens browser.

Option B - Package with PyInstaller

Produces executable for Windows.

Pros:

easier for non-dev users
stronger demo story

Cons:

packaging complexity
antivirus false positives possible
larger build artefacts
Option C - Desktop shell with Tauri

Frontend packaged as desktop app, Python backend launched locally.

Pros:

polished user experience

Cons:

significant complexity
Rust/Tauri dependency
overkill for current stage
Recommendation

Do Option A first.

Add:

py run.py app

Behaviour:

start FastAPI server
open browser
show dashboard
handle already-running server gracefully
Acceptance Criteria
One command starts app
Browser opens automatically
Failure messages are clear
Existing API server command remains available
Suggested Commit
feat(app): add local browser launcher
Phase 18 - CI and Release Hardening
Purpose

Make the project easier to trust publicly.

Add GitHub Actions

Workflow:

python -m pip install -r requirements.txt
python -m pip install -r mcp/requirements.txt
python mcp/test_verify.py
python run.py validate
python run.py security

Optional:

export test
bundle test
docs consistency test
Add Release Checklist

Create:

RELEASE_CHECKLIST.md

Include:

tests pass
validate pass
security pass
export works
README updated
tag created
GitHub release notes written
Acceptance Criteria
CI runs on push and PR
Main branch badge added to README
Release checklist exists
No generated dist/ files committed
Suggested Commit
ci: add verification workflow
Phase 19 - Optional Semantic Retrieval
Status

Deferred.

Semantic retrieval should wait until:

UI is usable
vault creation is easy
user can browse/search/edit notes
the system has multiple real vaults or larger note sets
deterministic lexical search is insufficient
Do Not Start Until
At least 75+ notes exist in a real vault
There is a clear retrieval problem lexical search cannot solve
Embedding model choice is justified
Cache invalidation design is clear
Security scanner handles query input surfaces
Tests can avoid brittle ranking assertions
Possible Future Features
local embedding index
hybrid lexical + semantic search
semantic bundle selection
explainable ranking metadata
embedding cache invalidation
model/version hash in bundle metadata
Suggested Commit Eventually
feat(search): add optional semantic retrieval
Phase 20 - Registry and Reuse Layer
Status

Deferred.

Purpose

Manage exported packages over time.

Features
package registry
package list
package verification
package tags
stale package detection
archive/delete package
compare package manifests
package signing, maybe later
Do Not Start Until
package export is used frequently
UI package browser exists
there are multiple bundles worth managing
Suggested Commit Eventually
feat(registry): add local context package registry
7. Immediate Next Step
Recommended Next Phase

Start with:

Phase 12 - Vault Dashboard and Issue Review

Phase 11B (Guided Vault Bootstrap UI Form) is complete:

- ui/src/components/VaultSetup.svelte — full form, live validation, preview panel, submit, success/error/warning handling
- ui/src/pages/vault-setup.astro — functional Vault Setup page (replaced PlaceholderPage)
- ui/src/lib/api.ts — VaultBootstrapRequest/Response types; bootstrapVault() function
- ui/src/layouts/AppLayout.astro — Vault Setup active in sidebar; phase footer updated
- npm run build passes with no TypeScript errors

Phase 11A (Guided Vault Bootstrap Backend API) is complete:

- POST /vault/bootstrap endpoint added to FastAPI server
- core/shared/bootstrap_service.py — shared service (validate, create, rollback, config update)
- CLI py run.py bootstrap unchanged; _update_config() now delegates to shared service
- vault_registry.reload_config() for in-process registry refresh
- 14 backend tests added (202 total passing)

Phase 10 (Local Web UI Foundation) is complete:

- Astro 5 + TypeScript + Tailwind CSS 4 + Svelte 5 islands
- FastAPI serves built UI at GET /app (ui/dist/), returns 503 UI_NOT_BUILT if not built
- Dashboard: server health, vault selector, completion summary, validation status, security scan
- CORS enabled for dev server (localhost:4321)
- 8 backend tests added (188 total passing)

Do not start with semantic retrieval.

Do not start with a desktop binary.

Do not start with graph visualisation.
8. UI Architecture Recommendation
Recommended Stack
Frontend: React + Vite + TypeScript
Backend: existing FastAPI app
Communication: existing JSON API
Serving:
  - dev: Vite dev server
  - production: built static files served by FastAPI
Why This Is Ideal

React/Vite gives:

real forms
buttons
tabs
cards
validation states
structured tables
future graph visualisation
good portfolio optics

FastAPI remains:

backend API
local server
security scanner host
export engine host

CLI remains:

automation layer
testable workflow
CI layer
fallback for advanced users
Avoid For Now
Electron
Tauri
semantic retrieval
database
cloud sync
authentication
multi-user permissions
AI writing assistant

These are premature.

9. Updated Non-Goals

Do not turn the project into:

a generic note-taking app
an Obsidian replacement
a generic RAG wrapper
a cloud SaaS
an autonomous AI writer
a heavy desktop suite
a database-backed enterprise CMS
an embedding-first retrieval system

The UI should expose the pipeline. It should not replace the vault.

10. Updated Success Criteria

The project becomes “user friendly enough” when a user can:

Launch the app locally with one command.
Create or select a vault without editing config manually.
See whether the vault is valid.
See what needs work.
Run security scanning with a button.
Generate and export a context package with a button.
Inspect package files and hashes.
Add feedback without hand-editing YAML.
Search notes from the UI.
Understand the system without reading every Markdown doc.
11. Risks Going Forward
Risk	Mitigation
UI becomes bigger than backend	Build in thin phases
React app adds dependency noise	Keep UI isolated in /ui
UI bypasses validation	All writes must validate
UI writes unsafe paths	Reuse existing path traversal protections
User edits generated artefacts	UI should clearly mark dist/ as generated
Too much AI framing returns	Keep public language security/pipeline-focused
Semantic retrieval distracts	Defer until after UI usability
Desktop packaging causes complexity	Start with browser UI first
12. Memory Replacement Note

This roadmap supersedes the previous master roadmap.

Crucial information transferred from the old roadmap:

Context Vault Engine identity
Local-first principle
Deterministic-first principle
Markdown source-of-truth principle
Schema-as-contract principle
Bundles as generated artefacts
Validation before packaging
Feedback influences priority but does not mutate notes
Avoid hidden state
Prefer small composable primitives
Semantic retrieval remains optional and deferred
Registry remains future work
Forensic reports are historical snapshots, not permanent truth

New strategic direction added:

The next product frontier is user experience: a local web UI, guided vault bootstrap, dashboard, bundle/export/security screens, feedback workflow, and safe note browsing.