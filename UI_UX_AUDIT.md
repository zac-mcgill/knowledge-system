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

## 13. Phase 29B Implementation Note

Phase 29B has now landed. `ui/src/layouts/AppLayout.astro` has been rewritten with a data-driven `navGroups` array implementing the grouping recommended in sections 5 and 6: Overview, Vault, Context, Review and Governance, Developer. All 15 existing `/app/*` routes are preserved (no renames, no removals, no consolidation). The route originally listed as `/app/api` in the audit corresponds to the existing `raw.astro` page, so it is surfaced as "API / Raw" under Developer at `/app/raw` rather than being renamed.

Accessibility markers added in Phase 29B: a semantic `<nav aria-label="Primary">` landmark, `aria-current="page"` on the active link with a visible left accent rail, and a plain CSS `:focus-visible` outline on every nav link for keyboard users. Brand hierarchy now shows "Context Vault" as the primary label with "Engine" as a secondary uppercase strap.

The full design system (tokens, shared primitives, table/card components) and page consolidation remain out of scope for 29B. They are deferred to Phase 29C and Phase 29D respectively, exactly as recommended in section 10.

## 14. Phase 29C Implementation Note

Phase 29C has now landed the design system foundation. `ui/src/styles/global.css` defines a token layer using CSS custom properties for surfaces (`--cve-bg`, `--cve-surface`, `--cve-surface-muted`), borders (`--cve-border`, `--cve-border-soft`), text (`--cve-text-strong`, `--cve-text`, `--cve-text-muted`, `--cve-text-faint`), accent (`--cve-accent`, `--cve-accent-soft`), status (`--cve-success`, `--cve-warning`, `--cve-danger`, `--cve-info`), and the focus ring (`--cve-focus`). A documented radius and spacing scale rounds out the token set.

A `cve-*` class layer adds shared primitives for typography, page shell and header, content stacks, card grids, cards, buttons (primary, secondary, ghost, danger), badges (neutral, success, warning, danger, info, draft, deprecated), alerts (info, success, warning, danger), form fields with label, helper, input, select, and textarea baseline styling, tables and lists, empty/loading/error/success state blocks, a raw JSON block and collapsible details, plus dangerous-action, warning, and trust/security warning blocks. A single `:focus-visible` rule targets every interactive primitive and references the `--cve-focus` token, so keyboard focus remains visible without removing native focus rings. A `prefers-reduced-motion` guard is in place even though Phase 29C introduces no animations.

The audit's existing decision that no React is needed is unchanged. Astro plus Svelte plus Tailwind remains the right stack for this UI, and the new tokens and primitives are framework-agnostic CSS so both Astro pages and Svelte components can adopt them.

Phase 29B's grouped navigation in `AppLayout.astro` is preserved verbatim. All 15 existing `/app/*` routes still resolve, and `/app/raw` continues to appear under Developer as `API / Raw`. Phase 29C does not migrate page content to the new primitives; that work belongs to Phase 29D, in line with the staged plan in section 10.

## 15. Phase 29D Implementation Note

Phase 29D applies the Phase 29C design system primitives to the existing pages and components. Every Astro page under `ui/src/pages/` continues to mount its existing Svelte island. Each major Svelte component (`Dashboard`, `VaultSetup`, `NoteBrowser`, `BundleBuilder`, `ExportPackage`, `SecurityScan`, `FeedbackWorkflow`, `GraphExplorer`, `ContextController`, `PendingChanges`, `TrustEvidence`, `ImportReview`) together with the `PlaceholderPage.astro` shim now adopts the `cve-*` primitives: a `cve-page` shell, a `cve-page-header` containing a `cve-page-title`, plus targeted use of `cve-card`, `cve-btn`, `cve-badge`, `cve-input` / `cve-select`, `cve-table`, `cve-list`, `cve-details` / `cve-raw`, `cve-empty` / `cve-loading` / `cve-error`, `cve-danger-zone`, `cve-warning-block`, and `cve-trust-warning` where each pattern applies.

`VaultSetup.svelte` flags its vault-delete surface with `cve-danger-zone` and applies `cve-btn-danger` to the confirmation button; the typed-confirmation phrase, audit copy, and disabled-until-match behaviour are unchanged. `TrustEvidence.svelte` carries an explicit `cve-trust-warning` block that restates the standing disclaimer: trust metadata reflects review and maintenance state only and does not prove factual correctness. `ImportReview.svelte` wraps its write-confirmation block with `cve-warning-block` so import safety wording remains visually prominent; the typed checkbox and dry-run / write gating are preserved.

The audit's existing decision that no React is needed is unchanged. No new dependencies, no new pages, no removed pages, and no backend route changes are introduced. Phase 29B's grouped sidebar in `AppLayout.astro` is preserved verbatim. All 15 existing `/app/*` routes still resolve, and `/app/raw` still appears under Developer as `API / Raw`. Phase 29D does not deliver accessibility minimums, responsive review, or final release-readiness documentation; that work belongs to Phase 29E, in line with the staged plan in section 10.

## 16. Phase 29E Implementation Note

Phase 29E is the final polish, accessibility, and release-readiness pass that closes Phase 29. It does not introduce new features, new pages, new routes, new dependencies, or new backend behaviour. It targets the rough edges exposed by the Phase 29D primitive rollout and finishes the documentation set.

The `cve-details` summary now carries an explicit textual disclosure cue. A pseudo-element chevron and a `Show details` / `Hide details` label make every collapsed block visibly interactive without relying on the native triangle that `list-style: none` removed. The `:focus-visible` rule has been broadened to cover ordinary anchor links and native buttons inside `.cve-page`, in addition to the existing `cve-*` primitives, so keyboard focus is visible everywhere the user can land. `cve-btn:disabled`, `cve-btn[aria-disabled=true]`, and the new `cve-btn-disabled` class share a clearly distinct visual state; disabled form controls share the same treatment. `cve-raw` and `cve-table-wrap` are pinned to `max-width: 100%` and scroll internally so long JSON payloads and wide tables stay inside the block rather than pushing the page into horizontal overflow. A small responsive guard caps `.cve-page` at the viewport width and constrains descendant images/svgs/videos to their parent. The `prefers-reduced-motion` guard remains in place; the new chevron transition is short enough to stay under the reduced-motion ceiling.

`ui/src/layouts/AppLayout.astro` keeps the Phase 29B grouped sidebar (Overview, Vault, Context, Review and Governance, Developer). All 15 `/app/*` routes remain reachable. `/app/raw` is still labelled `API / Raw` under Developer. The only AppLayout change in Phase 29E is the footer label, which moves from the stale `Phase 29B - Navigation` to `Phase 29 - Stable` so the visible chrome no longer claims an old sub-phase is active.

Mobile navigation deliberately remains a slim top bar rather than a full drawer. Building a mobile drawer would require either a JavaScript dependency or new client-only Svelte islands wired into the layout, which is out of scope for a polish phase and explicitly disallowed by the Phase 29E constraints. The mobile drawer is recorded here as an honest post-Phase 29 enhancement.

## 17. Phase 29 Closure Note

Phase 29 is now complete. Phase 29A produced this audit. Phase 29B grouped the sidebar by intent without renaming or removing any route. Phase 29C introduced the design system tokens and the `cve-*` primitive layer in `ui/src/styles/global.css`. Phase 29D applied those primitives across every existing Svelte component and the placeholder shim. Phase 29E hardened accessibility (disclosure cue, focus-visible coverage, disabled states), pinned raw/table blocks against overflow, refreshed the AppLayout footer, and closed the documentation set.

No React was introduced. The audit's `No React needed` decision from section 9 still holds: every Phase 29 deliverable was achievable with Astro plus Svelte plus Tailwind plus framework-agnostic CSS, without adding a second component framework. No new dependency was added in any sub-phase. No backend route was added, removed, or renamed. Phase 27 (Registry and Reuse Layer) and Phase 28 (Optional Semantic Retrieval) remain explicitly deferred and were not started by Phase 29.


## 18. Phase 30A Audit Consolidation

Phase 30A is a screenshot-driven audit of the entire `/app` surface delivered on top of the Phase 29 design system. It is documentation only. No UI code, no backend route, no dependency, and no test is added or changed by Phase 30A. The audit consolidates fourteen per-page reports captured under `UIReport1.txt` through `UIReport14.txt` in the repository root.

### 18.1 Purpose

Phase 29 delivered grouped navigation, semantic primitives, and a `cve-*` token layer. It did not deliver a release-quality UI. Phase 30A confirms that observation against real screenshots, identifies the cross-page root causes, and produces an actionable brief that Phase 30B can implement without scope creep. Phase 30A explicitly does not start Phase 27, Phase 28, or any LLM/semantic/SaaS workstream.

### 18.2 Audited Routes

The following routes were audited:

- `/app/` (Dashboard)
- `/app/notes` (Notes)
- `/app/vault-setup` (Vault Setup)
- `/app/import` (Import)
- `/app/bundles` (Bundles)
- `/app/exports` (Exports)
- `/app/graph` (Graph)
- `/app/controller` (Controller / Context Plan)
- `/app/validation` (Validation, placeholder)
- `/app/tasks` (Tasks, placeholder)
- `/app/security` (Security)
- `/app/feedback` (Feedback)
- `/app/pending` (Pending Changes)
- `/app/trust` (Trust)
- `/app/raw` (API / Raw, placeholder)

### 18.3 Severity Summary

| Severity | Count of findings across pages | Examples |
|---|---|---|
| Critical (structural) | ~10 | Validation/Tasks/Raw are placeholders; Security scan defaults to a scoped bundle request; Exports duplicates Bundles plus adds disk-writing risk; vault delete co-hosted with onboarding; Pending accept friction; Trust page lacks summary/queue. |
| High | ~60 | Ultrawide space wasted on every page; whole-page scroll instead of internal scroll; raw JSON disclosures everywhere; hard-coded Tailwind dark palette literals; Graph uses tabs instead of split-pane; Notes detail panel stacks full-width sub-panels. |
| Medium | ~70 | Duplicated information across panels; uniform card weight removing hierarchy; opaque copy ("Controller", "Raw"); footer phase chip leaking into chrome; default checkbox states. |
| Low | ~20 | Idle illustrations; native control chrome; minor typography drift. |

### 18.4 Cross-Page Root Causes

The audits converge on a small set of foundation gaps. Phase 30B exists to fix these once instead of fixing them fifteen times.

1. **Layout shell does not support workbench pages.** `AppLayout.astro` constrains main content to a single bounded reading column. Workflow pages (Notes, Graph, Pending, Feedback, Bundles, Exports, Security) need a wide or workspace mode with split panes and internal scroll regions.
2. **No semantic light/dark token layer in use.** Pages still mix `cve-*` primitives with raw `bg-zinc-*` / `text-zinc-*` / `bg-emerald-9xx` / `bg-amber-9xx` Tailwind utilities. Light mode is not real today.
3. **No shared workbench/split/toolbar/status-strip/table/banner/disclosure/slide-over primitives.** Every page reimplements two-column layouts, sticky toolbars, KPI strips, and raw JSON expanders inline.
4. **Raw JSON is overexposed.** Workflow pages embed `Show raw JSON` disclosures next to user-facing content. The Developer surface (`/app/raw`) does not exist as a destination yet.
5. **Whole-page scroll instead of internal scroll.** Long lists (Feedback, Notes list, Graph nodes, Pending queue) push primary actions and adjacent context off-screen.
6. **Destructive and write-safety affordances are visually weak.** Vault delete, import write, export overwrite, pending accept, and reject all rely on logical gating rather than visual separation.
7. **Several pages are placeholders, not implementations.** Validation, Tasks, and Raw render the shared `PlaceholderPage.astro` shim with a CLI hint.
8. **Some pages are structurally wrong, not just unpolished.** Security defaults read like a scoped bundle request; Exports is a 85% duplicate of Bundles; Graph is a label list under a tab named "Graph"; Trust leads with an evidence-builder form; Feedback is a 52-row triage inbox trapped in a narrow two-column grid.

### 18.5 Page-by-Page Verdict Table

| Page | Verdict | Primary issue |
|---|---|---|
| Dashboard | Weak. Needs redesign after foundation. | Six uniform cards, triple-shown vault state, raw JSON everywhere, status tiles non-actionable. |
| Notes | Weak. Needs split-pane workbench. | Fixed 420 px list column; detail stack scrolls the whole page; metadata duplicated. |
| Vault Setup | Close to release. Structural fix needed. | Danger Zone hosted on onboarding page; per-field cards inflate length; preview tokens render as literal text. |
| Import | Weak. Write safety logically correct, visually weak. | Preview and Write buttons share a row; mode badge invisible; right column dead pre-preview. |
| Bundles | Weak. Builder needs hierarchy. | Six identical cards; Generate Preview below the fold; right column empty pre-preview. |
| Exports | Weak. Plus structural duplication. | ~85% duplicate of Bundles; overwrite and security-pass styled like harmless toggles; security gate defaults to off. |
| Graph | Weak. Wrong layout model. | Tabbed Graph/Inspector/Missing instead of split-pane; "Graph" tab is a label list; ultrawide unused. |
| Controller | Weak. Needs command-centre layout. | Single column on wide viewport; readiness polarity wrong on "HAS MISSING CONCEPTS"; recommendation duplicated. |
| Validation | Placeholder. Not release-quality. | Renders `PlaceholderPage.astro` with a CLI hint. No data, no vault selector. |
| Tasks | Placeholder. Not release-quality. | Same as Validation. |
| Security | Weak. Structurally wrong defaults. | Page behaves like a scoped context bundle request; "Max notes" capped at 100; security gate not on by default. |
| Feedback | Weak. Narrow layout for a triage inbox. | 6-tile KPI strip dominated by zeros; Add Feedback below 52 rows; right pane empty when no tasks. |
| Pending | Acceptable concept, weak polish. | 320 px fixed rail; empty-state cards twin; provenance limited to "LLM"; accept friction light. |
| Trust | Weak, placeholder-like in practice. | Summary cards and stale queue not rendered on first view; Evidence Builder dominates a governance page. |
| Raw / Developer | Placeholder. Not release-quality. | `PlaceholderPage.astro` with a CLI hint; no endpoint catalogue, no JSON viewer. |

### 18.6 Pages Requiring Real Implementation

These pages are not migrations. They must be built. Phase 30D scope:

- `/app/validation` - real validation review backed by `fetchValidation`, severity grouping, invalid-note list, vault selector, last-checked timestamp.
- `/app/tasks` - real task table backed by `fetchTasks`, priority/sort/filter, source provenance, links to Notes.
- `/app/raw` - developer endpoint explorer / JSON viewer with vault selector, request form, copy and download affordances, explicit Developer framing.

### 18.7 Pages Requiring Structural Redesign

Not polish. These pages are wrong in shape and need workflow changes within Phase 30D / 30E:

- `/app/security` - default to full-vault scan; demote sampling/filter knobs into an "Advanced scope" disclosure; surface count of notes that will be scanned before run; security gate on by default.
- `/app/exports` - reconcile with Bundles via a shared form composable or merge into a single workflow with preview/export actions; overwrite and security-pass require visible warning treatment and confirmation.
- `/app/graph` - rename / restructure to a split-pane relationship browser (node list left, inspector right, missing concepts surfaced inline), drop the misnamed Graph tab.
- `/app/trust` - lead with summary band + stale/low-trust queue + per-row links to Notes/Pending/Feedback; demote Evidence Builder to a secondary tab or under Developer.
- `/app/feedback` - full-width filterable table top, Tasks side-panel pinned right, Add Feedback as slide-over from a fixed action, severity-driven sort and grouping.
- `/app/import` - state-aware layout (setup, preview, write-confirmation) with the Write action physically separated from Preview.
- `/app/vault-setup` - move vault deletion off the onboarding page (separate `/app/vault-setup/manage` tab or a slide-over launched from the vault switcher); collapse per-field cards into a single grouped form panel.
- `/app/pending` - widen layout, expose accept/reject provenance and trust impact, raise accept friction in line with the existing typed-confirmation pattern, add internal scroll to the queue.
- `/app/controller` - two-column command-centre at xl+; correct readiness polarity for negative flags; deep-link recommendations to authoritative pages instead of inventing routes.

### 18.8 Pages Requiring Only Secondary Polish

After the foundation lands and the structural pages are reshaped, these need targeted polish:

- `/app/` Dashboard - canonical status band, demote raw JSON, single CTA per status tile, progress promotion.
- `/app/notes` - resizable left rail, sticky filters, detail inspector with internal scroll body.
- `/app/bundles` - sectioned builder with sticky action, state-aware right pane.

### 18.9 Deferred / Non-Goals

Phase 30 does not start, prepare, or imply work on:

- Phase 27 (Registry and Reuse Layer).
- Phase 28 (Optional Semantic Retrieval).
- Any LLM-driven UI, RAG layer, embedding workflow, or autonomous note writing.
- Any cloud, SaaS, or multi-tenant feature.
- Any React, Vue, or third-party component framework.
- Any charting or data-visualisation library.
- Any new icon set or animation library.
- Any backend route, schema, or contract change.
- Any page removal or route consolidation.

### 18.10 Acceptance Criteria for Moving to Phase 30B

Phase 30A is closed when:

- This `UI_UX_AUDIT.md` Phase 30A consolidation section exists with the audited route list, severity summary, root causes, verdict table, real-implementation list, structural-redesign list, and deferred items above.
- `ROADMAP.md` records Phase 30A as Complete, lists Phase 30B through 30F as planned with explicit scope boundaries, and keeps Phase 27 and Phase 28 Deferred.
- `TESTING.md` documents the planned Phase 30 UI guardrail families (no Tailwind dark literals on migrated pages, light/dark token coverage, placeholder-removal guardrails, write-safety guardrails, deterministic route/deep-link checks).
- `RELEASE_CHECKLIST.md` no longer implies the UI is release-quality today and lists the UI release-readiness criteria Phase 30 must meet before tagging the next release.
- The verification suite (`py mcp/test_verify.py`, `py run.py validate`, `py run.py security`, `py run.py feedback`, `py run.py export --overwrite`, `cd ui && npm run build`) still passes unchanged.
- `git status --short` shows no generated artefacts staged.

---

## 19. Phase 30B Implementation Brief

Phase 30B is foundation-only. It exists to give Phase 30C, 30D, 30E, and 30F a stable substrate so they do not have to re-invent layout, theme, and shared primitives per page. Phase 30B must not redesign any user-facing page beyond the minimum needed to prove the primitives compile and render.

### 19.1 In Scope

1. **App shell layout modes.** `AppLayout.astro` gains a layout-mode contract so individual routes can opt into `standard`, `wide`, `workspace`, or `developer` shells. `standard` keeps the bounded reading column. `wide` removes the max-width cap. `workspace` introduces a split-pane area (list rail + inspector) with internal scroll regions. `developer` marks the surface as a developer / diagnostics page.
2. **Workflow page max-width opt-out.** Provide a deterministic way for workflow pages (Notes, Graph, Pending, Feedback, Bundles, Exports, Security) to consume the full content width without per-component overrides.
3. **`cve-workbench` / split-pane primitive.** A two-pane workbench primitive with a resizable or breakpoint-aware list rail (default ~360 px on lg, ~420 px on xl, ~480 px on 2xl) and an inspector pane that grows to fill remaining width.
4. **`cve-toolbar` / sticky header primitive.** A consistent sticky toolbar primitive that hosts a vault selector slot, page title slot, status pill slot, and trailing action slot. Replaces the per-page header drift surfaced in the audits.
5. **`cve-status-strip` / metric-strip primitive.** A compact horizontal strip for KPI / readiness rows that scales down to fewer columns at narrower widths and tolerates zero-value tiles without inflating to card grids.
6. **`cve-table` primitive.** A semantic table with sticky header, internal scroll, hover row state, status column, and a deterministic empty state. Targets Feedback, Validation, Tasks, Pending, and Trust queues in later sub-phases.
7. **`cve-banner` primitive.** A top-of-page banner with `info`, `warning`, `danger` variants. Used for warnings the audits called out as "too quiet" (Controller missing concepts, Security gate off, Pending stale, Trust stale).
8. **`cve-details` / disclosure primitive evolution.** Keep the existing `cve-details` but introduce a section-level inspector disclosure that replaces the per-card "Show raw JSON" pattern. Raw JSON belongs on the Developer route once it exists; the disclosure primitive must support a "Open in Developer" deep link.
9. **`cve-slide-over` primitive.** A right-anchored slide-over for "create" or "destructive" flows: Feedback Add, Vault Setup Manage / Delete (later), Notes Edit (later).
10. **`cve-diff` primitive stub or design contract.** Either a working coloured diff block for Pending Changes (added, removed, hunk header) or a documented contract that 30E can implement. Phase 30B may ship the contract only; it must not block Pending redesign.
11. **Semantic colour tokens for dark and light mode.** Extend `global.css` so every `cve-*` token has both a dark-mode and a light-mode value. Add `data-theme="dark"` and `data-theme="light"` selectors and a `color-scheme` declaration on the root.
12. **`data-theme` support and `color-scheme` declaration.** Add the `data-theme` attribute contract on `<html>`, default to dark to preserve current appearance, and declare `color-scheme: dark light` at the root. No user-facing toggle is required in 30B; the toggle is a 30F deliverable once tokens cover every primitive.
13. **Tokenised `:focus-visible` rules.** Confirm the Phase 29E focus-visible coverage uses the new tokens and survives in light mode.
14. **Developer nav group definition.** Confirm `/app/raw` lives under a Developer group with explicit "developer / diagnostics" framing in the sidebar. Phase 30B does not implement the Raw page itself; that work belongs to Phase 30D.
15. **Route-level layout modes wired in `AppLayout.astro`.** Each page declares its mode via a frontmatter prop or layout slot contract. Phase 30B may default every page to `standard` so existing visuals do not regress; later sub-phases flip pages to `wide` / `workspace` as they migrate.

### 19.2 Out of Scope for Phase 30B

- No Dashboard redesign.
- No Validation, Tasks, or Raw implementation.
- No Bundles or Exports refactor.
- No change to Security scan defaults.
- No vault-delete relocation.
- No user-facing light-mode toggle if the token foundation is not yet complete. It is acceptable to land the `data-theme` contract and token sets first and defer the toggle to Phase 30F.
- No React or third-party UI library.
- No charting library.
- No semantic retrieval, registry, LLM, RAG, SaaS, or cloud functionality.
- No new backend route. No change to existing routes, schema, or MCP contract.

### 19.3 Phase 30B Acceptance Criteria

Phase 30B is complete when:

- `AppLayout.astro` supports `standard`, `wide`, `workspace`, and `developer` modes via a deterministic contract.
- `global.css` defines a semantic token set with both dark and light values for surfaces, borders, text, accent, status, focus, and raw/code blocks; `data-theme` and `color-scheme` are declared.
- The new primitives (`cve-workbench`, `cve-toolbar`, `cve-status-strip`, `cve-table`, `cve-banner`, `cve-slide-over`) are defined and render in isolation.
- Existing pages still render correctly under the `standard` default; no visible regression on Dashboard, Notes, Vault Setup, Import, Bundles, Exports, Graph, Controller, Validation, Tasks, Security, Feedback, Pending, Trust, Raw.
- `ui/package.json` has no new runtime dependency.
- Deterministic guardrail tests are added in `mcp/test_verify.py` covering the primitive class definitions, the `data-theme` contract, the layout-mode contract, and the absence of net-new Tailwind dark literals in the primitive layer (per-page literal removal is enforced as later sub-phases migrate each page).
- `py mcp/test_verify.py`, `py run.py validate`, `py run.py security`, `py run.py feedback`, `py run.py export --overwrite`, and `cd ui && npm run build` all pass.
- `git status --short` shows no generated artefacts staged.

## 20. Phase 30B Implementation Note

Phase 30B (2026-05-12) shipped the foundation-only slice defined in section 19. Concretely:

- `ui/src/layouts/AppLayout.astro` now accepts a `layoutMode` prop with values `standard` (default), `wide`, `workspace`, and `developer`. The shell main and content containers emit a `data-layout-mode` attribute so later sub-phases and tests can assert which mode is in use without parsing class strings.
- `ui/src/styles/global.css` defines `html[data-theme="dark"]` and `html[data-theme="light"]` token blocks with full token parity (18 `--cve-*` tokens in each), declares `color-scheme: dark light`, and adds the new layout-mode containers and primitive classes: `cve-workbench` (with `__rail`, `__inspector`, `cve-scroll-region`), `cve-toolbar` (`__main`, `__title`, `__meta`, `__actions`), `cve-status-strip` / `cve-status-tile`, `cve-table` sticky-header + hover + `cve-table-empty`, `cve-banner` with info/warning/danger/success variants, `cve-details--inspector` and `cve-details__developer-link`, `cve-slide-over` (`__panel`, `__backdrop`, `__header`, `__body`, `__footer`), and `cve-diff` (`__line`, `--add`, `--remove`, `--hunk`). Tokenised `:focus-visible` rules cover every new primitive.
- Workflow pages now declare a non-`standard` layout mode: Notes / Graph / Pending / Feedback use `workspace`; Bundles / Exports / Security / Import / Controller / Trust / Validation / Tasks use `wide`; Raw uses `developer`. Dashboard and Vault Setup remain on `standard`.
- `mcp/test_verify.py` adds 13 deterministic guardrail tests; total test count rises from 787 to 800.

Deferred to later sub-phases:

- Phase 30C ships the Dashboard redesign on top of this foundation.
- Phase 30D ships the Notes / Import / Bundles / Exports / Security / Graph / Validation / Tasks / Raw redesigns (and replaces PlaceholderPage on Validation, Tasks, Raw).
- Phase 30E ships the Review / Governance / Developer polish, including the full `cve-diff` implementation on Pending.
- Phase 30F wires the user-facing light-mode toggle, finishes responsive and accessibility passes, and adds the final Tailwind-literal scan across migrated pages.

## 21. Phase 30C Implementation Note

Phase 30C (2026-05-12) ships the first page-level redesign on top of the Phase 30B foundation: the `/app/` Dashboard. Concretely:

- `/app/` now mounts AppLayout with `layoutMode="wide"`. The Dashboard fills the wide content column instead of the narrower `standard` shell.
- `ui/src/components/Dashboard.svelte` was rewritten around the Phase 30B primitives. The new structure is: a `cve-toolbar` header (title, vault selector, refresh action), a single `cve-banner` readiness headline whose severity is derived from the actual blocker / warning state (success / warning / danger / info, never colour-only), a five-tile `cve-status-strip` covering Validation, Security, Coverage, Missing concepts, and Feedback (each with a value, hint, deterministic last-checked text, and one CTA deep-linking to `/app/validation`, `/app/security`, `/app/notes`, `/app/graph`, and `/app/feedback` respectively), and a `cve-dashboard-grid` two-column body with Next best actions (top three tasks deep-linking to `/app/tasks`) and Vault health (key / value rows for uptime, requests served, average latency, rate limit, notes indexed, schema hash, and index size).
- Raw JSON is no longer rendered inline. The previous `Show raw JSON` disclosures and `<pre>{JSON.stringify(...)}</pre>` blocks have been removed. A single `cve-details--inspector` block at the foot of the Dashboard exposes a `cve-details__developer-link` to `/app/raw?vault=<id>`, matching the Phase 30B Developer deep-link contract.
- The old Issue Review section that duplicated Missing Concepts and tabbed analysis content has been removed. The Dashboard surfaces a single Missing concepts status tile and delegates the detailed queue to `/app/graph` and `/app/notes`.
- Last-checked text is deterministic. Because the JSON API does not expose per-call timestamps, the Dashboard renders `Checked this session` / `Not yet checked` / `No timestamp exposed by API` rather than synthesising clock values at render time.
- `ui/src/styles/global.css` gained a Phase 30C primitive block defining `.cve-link`, `.cve-status-tile--success/--warning/--danger/--info/--neutral`, `.cve-status-tile__cta`, `.cve-status-tile__meta`, `.cve-dashboard-grid` (responsive 2fr/1fr at 1024px+), `.cve-kv-row*`, and `.cve-next-action*`. All declarations use `var(--cve-*)` tokens only - no Tailwind dark literals, no light-mode literals.
- `mcp/test_verify.py` adds 18 deterministic guardrail tests; total test count rises from 800 to 818.

Deferred to later sub-phases:

- Phase 30D ships the Notes / Import / Bundles / Exports / Security / Graph / Validation / Tasks / Raw redesigns and replaces `PlaceholderPage` on Validation, Tasks, and Raw.
- Phase 30E ships the Review / Governance / Developer polish, including the full `cve-diff` implementation on Pending.
- Phase 30F wires the user-facing light-mode toggle, finishes responsive and accessibility passes, and adds the final Tailwind-literal scan across migrated pages.
