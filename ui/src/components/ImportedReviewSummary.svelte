<script lang="ts">
  /**
   * ImportedReviewSummary.svelte — Phase 26C
   *
   * Compact triage panel for imported Markdown notes.
   *
   * Derives counts from data the parent already fetched
   * (notes, validation, tasks, trust). No network calls are made here
   * and no automatic trust promotion or rewriting happens.
   *
   * Used by:
   *   - ImportReview.svelte (after a successful write)
   *   - NoteBrowser.svelte  (when the Imported filter is active)
   */

  import {
    buildImportedReviewSummary,
    buildNotesLink,
    type ImportedReviewSummary,
    type NoteListItem,
    type TasksData,
    type TrustSummaryData,
    type ValidationData,
  } from '../lib/api.ts';

  export let vault: string = '';
  export let notes: NoteListItem[] | null = null;
  export let validation: ValidationData | null = null;
  export let tasks: TasksData | null = null;
  export let trust: TrustSummaryData | null = null;
  export let compact: boolean = false;

  $: summary = buildImportedReviewSummary(vault, notes, validation, tasks, trust) as ImportedReviewSummary;

  $: notesImportedLink = buildNotesLink({ vault, filter: 'imported' });
  $: notesDraftLink = buildNotesLink({ vault, filter: 'draft' });
  $: notesImportedDraftLink = buildNotesLink({ vault, filter: 'imported-draft' });
</script>

<section class="bg-zinc-900 border border-zinc-800 rounded-lg p-4" data-testid="imported-review-summary">
  <div class="flex items-center justify-between mb-3">
    <h2 class="text-sm font-semibold text-zinc-200">Imported content review</h2>
    {#if vault}
      <span class="text-[11px] text-zinc-500 font-mono">vault: {vault}</span>
    {/if}
  </div>

  {#if summary.imported_total === 0}
    <p class="text-sm text-zinc-400">
      No imported notes detected in this vault.
      <span class="block text-xs text-zinc-500 mt-1">
        Notes are recognised by frontmatter <code class="text-zinc-300">source_type: imported</code>.
      </span>
    </p>
  {:else}
    <dl class="grid grid-cols-2 sm:grid-cols-3 gap-y-2 gap-x-4 text-xs">
      <dt class="text-zinc-500">Imported notes</dt>
      <dd class="text-sky-300 font-mono">{summary.imported_total}</dd>
      <dt class="text-zinc-500">Imported draft</dt>
      <dd class="text-amber-300 font-mono">{summary.imported_draft}</dd>
      <dt class="text-zinc-500">Validation issues</dt>
      <dd class="text-rose-300 font-mono">{summary.imported_with_validation_issues}</dd>
      <dt class="text-zinc-500">Active tasks</dt>
      <dd class="text-amber-300 font-mono">{summary.imported_with_tasks}</dd>
      <dt class="text-zinc-500">Stale</dt>
      <dd class="text-amber-300 font-mono">{summary.imported_stale}</dd>
      <dt class="text-zinc-500">Deprecated</dt>
      <dd class="text-zinc-300 font-mono">{summary.imported_deprecated}</dd>
    </dl>
  {/if}

  {#if !compact}
    <div class="mt-4 pt-3 border-t border-zinc-800 text-xs text-zinc-400">
      <div class="font-medium text-zinc-200 mb-1.5">Next review steps</div>
      <ul class="flex flex-wrap gap-x-3 gap-y-1">
        <li><a class="text-sky-400 hover:underline" href={notesImportedLink}>Review imported notes</a></li>
        <li><a class="text-sky-400 hover:underline" href={notesDraftLink}>Review draft trust</a></li>
        <li><a class="text-sky-400 hover:underline" href={notesImportedDraftLink}>Imported + draft</a></li>
        <li><a class="text-sky-400 hover:underline" href="/app/validation">Run validation</a></li>
        <li><a class="text-sky-400 hover:underline" href="/app/tasks">Review tasks</a></li>
        <li><a class="text-sky-400 hover:underline" href="/app/trust">Trust and evidence</a></li>
        <li><a class="text-sky-400 hover:underline" href="/app/security">Scan security</a></li>
        <li><a class="text-sky-400 hover:underline" href="/app/">Dashboard</a></li>
      </ul>
      <p class="text-[11px] text-zinc-500 mt-2">
        Promote or update imported content through the existing safe editing
        and review workflow. Trust metadata is not promoted automatically,
        and no LLM rewriting is performed.
      </p>
    </div>
  {/if}
</section>
