# Context Vault Engine - UI/UX Audit (Phase 29A)

This audit is the planning artefact for Phase 29 (UI/UX Quality and Design System). It is documentation only. It does not change runtime behaviour, backend contracts, or any existing route. It defines what Phase 29B, 29C, 29D, and 29E should implement.

The project stack is Astro 5, Svelte 5, Vite, Tailwind CSS 4, and TypeScript. There is no React in the project today. Source of truth for the current layout is [ui/src/layouts/AppLayout.astro](ui/src/layouts/AppLayout.astro).

---

## 1. Executive Verdict

The current UI is functionally complete for Phases 0 to 26. Every backend capability has a page, and the pages work. However the UI lacks:

- A coherent information architecture. The sidebar is a flat list of fifteen items with no grouping and no hierarchy.
- A consistent design system. Each Svelte island has its own ad hoc Tailwind utility composition, with no shared tokens for surface, border, text, accent, danger, warning, success, or info.
- Reusable UI primitives. Cards, page headers, raw JSON expanders, dangerous action confirmations, empty/loading/error states, and trust/security warnings are reimplemented in each component instead of imported from a shared library.
- Page-level rhythm. Heading sizes, spacing, table styles, and form field styles drift between pages.
- Accessibility minimums. Focus-visible states, contrast on muted text, and labels on icon-only controls are inconsistent.

The verdict is: the UI is a usable application baseline, not a designed product. Phase 29 should fix this in four steps (29B, 29C, 29D, 29E) without changing backend behaviour or starting Phase 27 or Phase 28.

---

## 2. Screenshot Findings (Sidebar)

The current sidebar is defined in [ui/src/layouts/AppLayout.astro](ui/src/layouts/AppLayout.astro). Findings are derived from the source and from the user-supplied sidebar screenshot.

- **Brand/header clarity**: the brand block reads "Context Vault" with the strap "Engine" stacked beneath. The padlock icon does not communicate "context vault" or "knowledge". The header has no active vault indication, which forces every page to render its own vault selector.
- **Sidebar spacing**: vertical rhythm is dense. `py-2` rows with `space-y-0.5` create a wall of items with no visual breathing room. The footer reads "Phase 18 - Stable" which is stale (Phases 0 to 26 are complete, v1.0.1 has shipped).
- **Navigation density**: fifteen first-level items (Dashboard, Vault Setup, Notes, Validation, Tasks, Bundles, Security, Exports, Import, Feedback, Graph, Controller, Pending, Trust, API / Raw). The user must scan the whole list to find anything.
- **Lack of grouping**: there are no section headers. Review-style pages (Validation, Tasks, Pending, Trust) sit next to context generation pages (Bundles, Exports, Controller) sit next to setup pages (Vault Setup, Import) sit next to developer pages (API / Raw). Mental model leaks into the user.
- **Active state**: the active item uses `bg-zinc-800 text-zinc-100 font-medium`. It is detectable but visually weak against the `bg-zinc-950` shell. There is no left accent rail, no icon variation, and no hover state difference beyond a slightly lighter background.
- **Hover/focus state**: hover sets `text-zinc-200 hover:bg-zinc-900`. There is no explicit `focus-visible` ring, which fails keyboard accessibility on every nav item.
- **Page label clarity**: "API / Raw" is jargon. "Controller" is opaque to a new user. "Bundles" and "Exports" sound similar but mean different things. "Pending" does not communicate that this is the human review queue for proposed memory writes.
- **First-level placement**: not every item deserves first-level placement. `API / Raw` is a developer surface and should sit under a Developer group. `Pending` and `Trust` are governance surfaces and should sit under a Review/Governance/Safety group.
- **API / Raw placement**: belongs under a Developer or Advanced group, not at the top of navigation.
- **Pending and Trust placement**: both should live under a Review/Governance/Safety group. They are not part of the day-to-day vault editing loop; they are the human gate for trust-sensitive operations.
- **Bundles, Exports, Graph, Controller comprehensibility**: a new user cannot guess what these do from the labels alone. They need descriptive labels, optional helper text on the page header, or grouping under a "Context" section that explains the family.

---

## 3. Route Inventory

Routes are read from [ui/src/pages/](ui/src/pages/) and the sidebar in `AppLayout.astro`.

| Route | Page file | Main component | Purpose | API dependencies | Recommendation | Reason |
|---|---|---|---|---|---|---|
| `/app/` | [ui/src/pages/index.astro](ui/src/pages/index.astro) | `Dashboard.svelte` | Vault overview, health row, summary cards | `/health`, `/vaults`, `/summary`, `/validation`, `/tasks`, `/missing`, `/feedback`, `/context/security` | Keep | Strong landing surface, needs visual polish only. |
| `/app/vault-setup` | [ui/src/pages/vault-setup.astro](ui/src/pages/vault-setup.astro) | `VaultSetup.svelte` | Bootstrap new vault, delete vault | `POST /vault/bootstrap`, `DELETE /vault/{name}` | Keep, rename | Rename group label to "Vault" with Setup as the entry. Move Danger Zone under shared dangerous-action primitive. |
| `/app/notes` | [ui/src/pages/notes.astro](ui/src/pages/notes.astro) | `NoteBrowser.svelte` | Browse, query, edit notes | `/notes`, `/note`, `PUT /note`, `/query` | Keep | Largest single component; needs to consume shared primitives in 29D. |
| `/app/validation` | [ui/src/pages/validation.astro](ui/src/pages/validation.astro) | `PlaceholderPage.astro` shim | Validation surface | `/validation` | Redesign in 29D | Currently a placeholder; should render real validation review using shared table primitive. |
| `/app/tasks` | [ui/src/pages/tasks.astro](ui/src/pages/tasks.astro) | `PlaceholderPage.astro` shim | Improvement tasks | `/tasks` | Redesign in 29D | Same placeholder pattern; tasks already render inside Dashboard issue review. Decide whether to keep a dedicated page or surface tasks under Review group only. |
| `/app/bundles` | [ui/src/pages/bundles.astro](ui/src/pages/bundles.astro) | `BundleBuilder.svelte` | Build a deterministic context bundle | `POST /context/bundle`, `/context/profiles` | Keep | Belongs under a Context group with Exports. |
| `/app/security` | [ui/src/pages/security.astro](ui/src/pages/security.astro) | `SecurityScan.svelte` | Security scan of context | `POST /context/security` | Keep | Belongs under Review/Governance group. |
| `/app/exports` | [ui/src/pages/exports.astro](ui/src/pages/exports.astro) | `ExportPackage.svelte` | Write portable context package | `POST /context/export` | Keep | Belongs under Context group with Bundles. |
| `/app/import` | [ui/src/pages/import.astro](ui/src/pages/import.astro) | `ImportReview.svelte`, `ImportedReviewSummary.svelte` | Markdown/Obsidian import review and write | `POST /import/markdown-folder`, `POST /import/obsidian-vault` | Keep | Belongs under Vault group, not floating in the middle of the sidebar. |
| `/app/feedback` | [ui/src/pages/feedback.astro](ui/src/pages/feedback.astro) | `FeedbackWorkflow.svelte` | View, add, edit, delete feedback | `/feedback`, `POST /feedback`, `PUT /feedback/{id}`, `DELETE /feedback/{id}` | Keep | Belongs under Review group. |
| `/app/graph` | [ui/src/pages/graph.astro](ui/src/pages/graph.astro) | `GraphExplorer.svelte` | Graph + missing concepts | `/graph/{vault}`, `/graph/{vault}/neighbours`, `/graph/{vault}/related`, `/graph/{vault}/missing` | Keep | Belongs under Context or Review group. Decide in 29B. |
| `/app/controller` | [ui/src/pages/controller.astro](ui/src/pages/controller.astro) | `ContextController.svelte` | Vault state and recommendation plan | `/context/state`, `POST /context/plan` | Keep, rename label | Rename surface label to "Context Plan" or similar; "Controller" is opaque. Belongs under Context group. |
| `/app/pending` | [ui/src/pages/pending.astro](ui/src/pages/pending.astro) | `PendingChanges.svelte` | Review LLM-proposed pending changes | `/memory/pending`, `POST /memory/pending/{id}/accept`, `POST /memory/pending/{id}/reject` | Keep | Belongs under Review/Governance group. Dangerous action surface. |
| `/app/trust` | [ui/src/pages/trust.astro](ui/src/pages/trust.astro) | `TrustEvidence.svelte` | Trust, staleness, evidence | `/trust`, `/stale`, `POST /evidence` | Keep | Belongs under Review/Governance group. |
| `/app/raw` | [ui/src/pages/raw.astro](ui/src/pages/raw.astro) | `PlaceholderPage.astro` shim | Developer / raw API surface | (informational) | Keep, rename, hide under Developer group | "API / Raw" is jargon. Rename to "Developer" or "API Console". Move under an Advanced group at the bottom of the sidebar. |

No routes are removed in Phase 29. Renames and grouping are visual only. Backend route contracts are untouched.

---

## 4. Component Inventory

Components are read from [ui/src/components/](ui/src/components/).

| Component file | Used by | Purpose | Reuse quality | Problem | Recommendation |
|---|---|---|---|---|---|
| [Dashboard.svelte](ui/src/components/Dashboard.svelte) | `/app/` | Vault overview, health row, summary cards, issue review tabs | Single-page island | Card markup is inline; raw JSON expanders are inline; tab styling is inline. | Migrate to shared `Card`, `Badge`, `RawDetails` primitives in 29D. |
| [VaultSetup.svelte](ui/src/components/VaultSetup.svelte) | `/app/vault-setup` | Bootstrap form + Danger Zone delete | Single-page island | Danger Zone styling is inline; typed-confirm pattern is inline. | Replace Danger Zone with shared `DangerousActionConfirm` primitive in 29D. |
| [NoteBrowser.svelte](ui/src/components/NoteBrowser.svelte) | `/app/notes` | Browse, query, edit notes | Single-page island | Largest island; edit-mode UI, validation panel, and search panel all inline. | Migrate to shared `Card`, `Badge`, `FormField`, `RawDetails`, `EmptyState` in 29D. |
| [BundleBuilder.svelte](ui/src/components/BundleBuilder.svelte) | `/app/bundles` | Build a context bundle | Single-page island | Filter and section editor are inline. Profile selector is inline. | Migrate to shared primitives in 29D. |
| [ExportPackage.svelte](ui/src/components/ExportPackage.svelte) | `/app/exports` | Write a context package | Single-page island | Similar to BundleBuilder; significant inline overlap. | Migrate to shared primitives, share form controls with BundleBuilder in 29D. |
| [SecurityScan.svelte](ui/src/components/SecurityScan.svelte) | `/app/security` | Security scan | Single-page island | Finding cards and severity badges are inline. | Migrate to shared `Badge` and `StatusIndicator` primitives in 29D. |
| [FeedbackWorkflow.svelte](ui/src/components/FeedbackWorkflow.svelte) | `/app/feedback` | CRUD on feedback entries | Single-page island | Inline filter panel; inline add/edit/delete forms. | Migrate to shared `Card`, `FormField`, `Badge` in 29D. |
| [GraphExplorer.svelte](ui/src/components/GraphExplorer.svelte) | `/app/graph` | Graph + missing concepts | Single-page island | Tab styling is inline; ranked table is inline. | Migrate to shared `Tabs`, `Table`, `Badge` in 29D. |
| [ContextController.svelte](ui/src/components/ContextController.svelte) | `/app/controller` | Context state + plan | Single-page island | Readiness grid and recommendation list are inline. | Migrate to shared `Card`, `StatusIndicator`, `Badge` in 29D. |
| [PendingChanges.svelte](ui/src/components/PendingChanges.svelte) | `/app/pending` | Review pending changes | Single-page island | Accept/reject confirmation is inline; diff display is inline. | Migrate to shared `DangerousActionConfirm` (for accept), `RawDetails` (for diff). |
| [TrustEvidence.svelte](ui/src/components/TrustEvidence.svelte) | `/app/trust` | Trust, stale, evidence | Single-page island | Trust badges and confidence chips are inline. | Migrate to shared `Badge` with trust variants and shared `Disclaimer` for the confidence-disclaimer pattern. |
| [ImportReview.svelte](ui/src/components/ImportReview.svelte) | `/app/import` | Markdown/Obsidian import preview and write | Single-page island | Confirm-to-write pattern is inline; per-item error/warning blocks are inline. | Migrate to shared `DangerousActionConfirm` for the write step, shared `Badge` for security/validation status. |
| [ImportedReviewSummary.svelte](ui/src/components/ImportedReviewSummary.svelte) | `/app/import` | Post-import summary block | Already small | Inline counts; no real problem. | Keep, restyle in 29D using shared `Card`. |
| [PlaceholderPage.astro](ui/src/components/PlaceholderPage.astro) | `/app/validation`, `/app/tasks`, `/app/raw` | Placeholder shim for routes that still call a placeholder | Reused | Real validation/tasks/raw surfaces are still placeholders today. | Replace with real implementations using new primitives in 29D, or repurpose as a generic "Coming soon" primitive. |

There are no shared UI primitives today. Every component reimplements its own card, badge, and details pattern. This is the central design system gap.

---

## 5. Information Architecture Recommendation

Replace the flat 15-item sidebar with grouped sections. Recommended groups and order, top to bottom:

1. **Overview**
   - Dashboard (`/app/`)
2. **Vault**
   - Setup (`/app/vault-setup`)
   - Notes (`/app/notes`)
   - Import (`/app/import`)
3. **Context**
   - Bundles (`/app/bundles`)
   - Exports (`/app/exports`)
   - Context Plan (formerly Controller) (`/app/controller`)
   - Graph (`/app/graph`)
4. **Review and Governance**
   - Validation (`/app/validation`)
   - Tasks (`/app/tasks`)
   - Feedback (`/app/feedback`)
   - Security (`/app/security`)
   - Trust (`/app/trust`)
   - Pending Changes (`/app/pending`)
5. **Developer**
   - API Console (formerly API / Raw) (`/app/raw`)

The chrome should also surface the active vault as a persistent selector at the top of the sidebar (or in the top bar), so every page can stop rendering its own vault selector and read from a shared store. Today every component duplicates that selector.

---

## 6. Proposed Sidebar Grouping

The Phase 29B implementation should render the sidebar with section headers, indent items under each header, and persist the active group. Example structure:

```
Overview
  Dashboard
Vault
  Setup
  Notes
  Import
Context
  Bundles
  Exports
  Context Plan
  Graph
Review and Governance
  Validation
  Tasks
  Feedback
  Security
  Trust
  Pending Changes
Developer
  API Console
```

Active vault selector lives above Overview, persistent across pages.

---

## 7. Page Consolidation Recommendations

Phase 29A does not consolidate any pages. The following are recommendations for Phase 29D to evaluate:

- **Bundles and Exports**: heavy overlap in form controls (filters, sections, profile, budget). Consider extracting a shared `ContextRequestForm` primitive used by both pages. Routes remain distinct.
- **Validation and Tasks**: today both are placeholder pages that point back to Dashboard issue review. Either fully implement them as standalone surfaces in 29D, or keep them as deep-link landing pages that mount the relevant Dashboard tab.
- **Trust and Pending Changes**: keep as distinct routes but co-locate under the same group in the sidebar so the governance surfaces are discoverable together.
- **API Console (raw)**: keep as a single developer surface. Do not split.

No routes are removed in Phase 29.

---

## 8. Design System Proposal

The design system should be implemented in Phase 29C. This audit defines the target shape.

### 8.1 Tokens

Express tokens as CSS custom properties in `ui/src/styles/global.css` or as a Tailwind theme extension. The current colour palette is implicit (zinc-950, zinc-900, zinc-800, zinc-100, sky-500). Make it explicit.

- `--surface-page`: page background (current `zinc-950`).
- `--surface-card`: card background (current `zinc-900`).
- `--surface-elevated`: secondary card or hover surface (current `zinc-800`).
- `--border-subtle`: hairline border (current `zinc-800`).
- `--border-strong`: emphasised border (for cards in active state).
- `--text-primary`: primary text (current `zinc-100`).
- `--text-muted`: secondary text (current `zinc-400`).
- `--text-faint`: tertiary text or placeholders (current `zinc-600`).
- `--accent`: primary accent (current `sky-500`).
- `--accent-strong`: hover/active accent.
- `--danger`: destructive action (current `red-500`/`red-600`).
- `--warning`: warning (current `amber-500`).
- `--success`: success (current `emerald-500`).
- `--info`: info (current `sky-400`).
- `--focus-ring`: visible focus ring colour.

### 8.2 Typography Scale

- `text-xs` (12px) for muted helper text and badges.
- `text-sm` (14px) for body copy and table cells.
- `text-base` (15px) for primary body.
- `text-lg` (17px) for sub-section headings.
- `text-xl` (20px) for page section headings.
- `text-2xl` (24px) for page titles.

### 8.3 Spacing Scale

Tailwind defaults (`1`, `2`, `3`, `4`, `6`, `8`) are sufficient. Standardise card inner padding at `p-4` (mobile) and `p-6` (desktop). Standardise section gap at `gap-6`.

### 8.4 Card Style

- Background: `--surface-card`.
- Border: `1px solid --border-subtle`.
- Radius: `rounded-lg` (8px).
- Padding: `p-4` mobile, `p-6` desktop.
- Optional header row with title (`text-lg font-semibold`) and optional description (`text-sm text-muted`).

### 8.5 Button Variants

- `primary`: accent background, white text, used for the single most important action per page.
- `secondary`: surface background, primary text, subtle border. Used for ordinary actions.
- `ghost`: transparent, primary text, hover background. Used in dense rows.
- `danger`: red background, white text. Used only after typed confirmation in dangerous actions.
- Disabled state: reduced opacity and `cursor: not-allowed`.
- Focus state: visible ring using `--focus-ring`.

### 8.6 Badge Variants

- `status-complete` (success), `status-partial` (warning), `status-invalid` (danger).
- `trust-verified` (success), `trust-working` (info), `trust-draft` (muted), `trust-external` (info subtle), `trust-deprecated` (danger).
- `severity-fail` (danger), `severity-warning` (warning), `severity-info` (info).
- `source-imported`, `source-authored`, `source-obsidian-vault`.

### 8.7 Status Indicators

A `StatusIndicator` primitive renders a small coloured dot plus a label. Used for readiness flags on the Context Plan page and on security scan results.

### 8.8 Form Fields

- Label above the field, `text-sm font-medium`.
- Helper text below, `text-xs text-muted`.
- Error text below, `text-xs text-danger`.
- Input: `--surface-elevated` background, `--border-subtle` border, `--text-primary` text.
- Focus: `--focus-ring`.
- Tag editor (used by Bundle/Export pages) has its own primitive.

### 8.9 Tables

- Header row: `text-xs uppercase tracking-wider text-muted`, `--border-subtle` bottom border.
- Body row: `text-sm`, `--border-subtle` bottom border, hover surface `--surface-elevated`.
- Sticky header optional.

### 8.10 Empty States

A shared `EmptyState` primitive with title, description, and optional action button. Used wherever a list could be empty (Notes, Pending Changes, Feedback, Tasks).

### 8.11 Loading States

A shared `LoadingState` primitive with a small spinner or skeleton block. Replaces the inline loading text used by every component today.

### 8.12 Error States

A shared `ErrorState` primitive that renders the structured error envelope (`code`, `message`, optional `details`). Used wherever an API call can fail.

### 8.13 Success States

A shared `SuccessPanel` primitive used after a successful write (note edit, import, vault bootstrap, feedback create). Includes a clear summary and optional follow-up links.

### 8.14 Raw JSON / Details Pattern

A shared `RawDetails` primitive wrapping `<details>` with a consistent summary label ("Show raw response"), monospace font, and copy-friendly text selection. Today every component does this inline.

### 8.15 Dangerous Action Pattern

A shared `DangerousActionConfirm` primitive that:

- Requires the user to type an exact confirmation phrase (the existing vault delete pattern).
- Disables the danger button until the phrase matches.
- Uses the `danger` button variant.
- Shows a short explanation of what will be removed or written.

Used by: vault delete, accept pending change, write import (already typed confirm), reject pending change.

### 8.16 Trust / Security Warning Pattern

A shared `TrustWarning` primitive used wherever trust or evidence is surfaced. Carries the standing disclaimer that trust metadata reflects review and maintenance state only and does not prove factual correctness. Used by: Trust page, Evidence builder result, Notes Trust panel.

### 8.17 Page Header Pattern

A shared `PageHeader` primitive with:

- Page title (`text-2xl`).
- Optional description (`text-sm text-muted`).
- Optional right-side action buttons.
- Optional breadcrumb (already exists in the top bar but not in the page content area).

### 8.18 Sidebar Pattern

Implemented in Phase 29B. Grouped sections, active state with left accent rail, hover state, visible focus ring, persistent vault selector at the top.

### 8.19 Keyboard Focus States

Every interactive element must have a visible `:focus-visible` ring using `--focus-ring`. Today only browser defaults apply, which fail on the dark theme.

### 8.20 Minimum Accessibility Expectations

- Semantic landmarks: `header`, `nav`, `main`, `aside`.
- Labels on every form field.
- Labels on icon-only buttons (`aria-label`).
- Colour contrast: muted text must reach at least 4.5:1 against page background. Today some muted text uses `text-zinc-600` against `bg-zinc-950`, which is below 4.5:1 and should be raised to `text-zinc-400` or `text-zinc-500`.
- Keyboard reachability for every interactive control.
- Status badges must not rely on colour alone; pair with an icon or letter where possible.

---

## 9. React Decision

**No React needed.**

Reasoning:

- The existing UI is Astro + Svelte + Tailwind. Every page is a Svelte island. All current and Phase 29 work (sidebar grouping, design tokens, shared primitives, page-level consistency, accessibility) is well within Svelte's capabilities.
- There is no component or interaction in Phase 29B to 29E that requires a React-only library. No virtualised giant table, no React-only diagramming library, no React-only WYSIWYG editor is in scope.
- Introducing React would double the framework surface and complicate the design system without delivering user-visible value.
- If a future phase identifies a concrete component where Svelte is materially worse, that decision can be revisited per the strategic constraint. Phase 29 should not pre-empt it.

---

## 10. Recommended Implementation Sequence for 29B to 29E

1. **Phase 29B - Navigation and IA**
   - Implement grouped sidebar exactly as proposed in section 6.
   - Add persistent vault selector to the layout chrome.
   - Update active/hover/focus states.
   - Update the stale footer in `AppLayout.astro` to reflect current status without claiming Phase 29 is complete.
   - No new primitives yet; raw Tailwind is acceptable for this sub-phase.

2. **Phase 29C - Design tokens and primitives**
   - Define tokens in `global.css` or `tailwind.config` extension.
   - Build the shared Svelte primitives listed in section 8.
   - Migrate one page (recommend Dashboard) end-to-end to validate the primitive set.

3. **Phase 29D - Page-level consistency pass**
   - Migrate every remaining page to the primitives.
   - Standardise empty/loading/error/success states.
   - Standardise dangerous actions and trust warnings.
   - Replace placeholder pages with real implementations or with the new "Coming soon" primitive.

4. **Phase 29E - Polish, accessibility, docs**
   - Pass at common breakpoints.
   - Pass accessibility minimums on every page.
   - Update README and QUICKSTART to reflect implemented UI only.
   - Mark Phase 29 complete in ROADMAP.

Each sub-phase is independently shippable and reversible.

---

## 11. Risks and Non-Goals

### Risks

- **Scope creep into Phase 27 or Phase 28.** The biggest risk is a contributor treating "UI redesign" as licence to add a registry view, semantic search, or LLM-driven UI. Phase 29 explicitly forbids this.
- **Tailwind 4 token strategy drift.** Tailwind 4 uses a different theme extension model from Tailwind 3. The primitive layer must commit to either CSS custom properties or Tailwind theme extension and stay consistent.
- **Svelte 5 runes adoption drift.** Svelte 5 introduces runes. The primitive layer should pick one style (legacy stores or runes) and apply it consistently. Phase 29A does not mandate which, but Phase 29C should decide.
- **Backend regression by accident.** Any UI change that accidentally calls a new route or drops a route is a regression. Phase 29 must not modify [ui/src/lib/api.ts](ui/src/lib/api.ts) call shapes.
- **Accessibility checked at the end instead of throughout.** Phase 29E is the formal accessibility pass, but every sub-phase should keep focus rings visible.

### Non-Goals

- No backend route changes.
- No registry (Phase 27 stays deferred).
- No semantic retrieval (Phase 28 stays deferred).
- No cloud, SaaS, or remote-only features.
- No autonomous note writing or LLM-driven UI.
- No React.
- No removal of existing pages.
- No change to CLI, API, or MCP behaviour.
- No change to deterministic-first, Markdown-source-of-truth, schema-as-contract principles.
- No softening of safety language around security, import, trust, pending changes, or destructive actions.

---

## 12. Audit Status

Phase 29A is documentation and audit only. This file is the authoritative input for Phase 29B. No UI code has been modified in Phase 29A.
