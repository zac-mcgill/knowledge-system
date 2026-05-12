<script lang="ts">
  /**
   * ImportReview.svelte — Phase 26B
   *
   * Browser UI for the Phase 26A Markdown folder import backend.
   *
   * Workflow:
   *   1. Choose a registered vault.
   *   2. Enter a server-local Markdown source folder path.
   *   3. Choose a vault-relative destination folder (default: Imported).
   *   4. Run a dry-run preview (dry_run: true).
   *   5. Review every planned item, security/validation result, warnings, errors.
   *   6. Explicitly confirm before writing.
   *   7. Execute the import (dry_run: false) and show the final result.
   *
   * Markdown folder import only. PDF, GitHub repo, browser article,
   * Obsidian-specific, chat transcript, semantic, and LLM extraction
   * imports remain deferred and are NOT exposed by this component.
   */

  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchNotes,
    fetchValidation,
    fetchTasks,
    fetchTrustSummary,
    importMarkdownFolder,
    isOk,
    buildNotesLink,
    type ImportMarkdownFolderRequest,
    type ImportMarkdownFolderResponse,
    type ImportMarkdownItem,
    type NoteListItem,
    type TasksData,
    type TrustSummaryData,
    type ValidationData,
  } from '../lib/api.ts';
  import { getStoredVault } from '../lib/vaultState.ts';
  import ImportedReviewSummary from './ImportedReviewSummary.svelte';

  // ── Vault list ─────────────────────────────────────────────────────────────
  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';

  // ── Form state ─────────────────────────────────────────────────────────────
  let selectedVault = '';
  let sourceDir = '';
  let destination = 'Imported';
  let overwrite = false;

  // Snapshot of the form values at the moment the preview succeeded.
  // Used to detect "stale preview" when the user edits the form afterwards.
  let previewedVault = '';
  let previewedSourceDir = '';
  let previewedDestination = '';
  let previewedOverwrite = false;

  // ── Operation state ────────────────────────────────────────────────────────
  type OpState = 'idle' | 'previewing' | 'preview_ok' | 'writing' | 'write_ok' | 'error';
  let opState: OpState = 'idle';
  let opErrorCode = '';
  let opErrorMsg = '';

  let preview: ImportMarkdownFolderResponse | null = null;
  let writeResult: ImportMarkdownFolderResponse | null = null;

  // ── Phase 26C: post-write review data ──────────────────────────────────────
  // Populated after a successful write so the result panel can render the
  // ImportedReviewSummary derived from existing endpoints (no new backend
  // tables, no async background jobs).
  let postWriteNotes: NoteListItem[] | null = null;
  let postWriteValidation: ValidationData | null = null;
  let postWriteTasks: TasksData | null = null;
  let postWriteTrust: TrustSummaryData | null = null;
  let postWriteLoading = false;

  // ── Confirmation state ─────────────────────────────────────────────────────
  let confirmReviewed = false;
  let showRawJson = false;
  let expandedItem: number | null = null;

  // ── Reactive helpers ───────────────────────────────────────────────────────
  $: previewStale =
    preview !== null && (
      selectedVault !== previewedVault ||
      sourceDir.trim() !== previewedSourceDir ||
      destination.trim() !== previewedDestination ||
      overwrite !== previewedOverwrite
    );

  $: previewHasBlockers =
    preview !== null && (
      preview.summary.errors > 0 ||
      preview.summary.planned === 0
    );

  $: canPreview =
    selectedVault !== '' &&
    sourceDir.trim() !== '' &&
    destination.trim() !== '' &&
    opState !== 'previewing' &&
    opState !== 'writing';

  $: canWrite =
    preview !== null &&
    !previewStale &&
    !previewHasBlockers &&
    confirmReviewed &&
    opState !== 'previewing' &&
    opState !== 'writing';

  $: dryRunIndicator = opState === 'write_ok' ? 'Write completed' :
                       preview !== null && !previewStale ? 'Preview ready' :
                       preview !== null && previewStale ? 'Preview stale' :
                       'Preview not run';

  // ── Lifecycle ──────────────────────────────────────────────────────────────
  onMount(async () => {
    vaultsLoading = true;
    vaultsError = '';
    const result = await fetchVaults();
    if (isOk(result)) {
      vaultList = result.data.vaults ?? [];
      if (vaultList.length > 0) {
        const stored = getStoredVault();
        selectedVault =
          stored && vaultList.includes(stored) ? stored : vaultList[0];
      }
    } else {
      vaultsError = result.error?.message ?? 'Failed to load vaults';
    }
    vaultsLoading = false;
  });

  // ── Request builder ────────────────────────────────────────────────────────
  function buildRequest(dryRun: boolean): ImportMarkdownFolderRequest {
    return {
      vault: selectedVault,
      source_dir: sourceDir.trim(),
      destination: destination.trim() || 'Imported',
      dry_run: dryRun,
      overwrite,
    };
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async function handlePreview(): Promise<void> {
    if (!canPreview) return;
    opState = 'previewing';
    opErrorCode = '';
    opErrorMsg = '';
    writeResult = null;
    confirmReviewed = false;

    const result = await importMarkdownFolder(buildRequest(true));
    if (isOk(result)) {
      preview = result.data;
      previewedVault = selectedVault;
      previewedSourceDir = sourceDir.trim();
      previewedDestination = destination.trim();
      previewedOverwrite = overwrite;
      opState = 'preview_ok';
    } else {
      preview = null;
      opErrorCode = result.error?.code ?? 'UNKNOWN';
      opErrorMsg = result.error?.message ?? 'Preview failed.';
      opState = 'error';
    }
  }

  async function handleWrite(): Promise<void> {
    if (!canWrite) return;
    opState = 'writing';
    opErrorCode = '';
    opErrorMsg = '';

    const result = await importMarkdownFolder(buildRequest(false));
    if (isOk(result)) {
      writeResult = result.data;
      opState = 'write_ok';
      await loadPostWriteData();
    } else {
      opErrorCode = result.error?.code ?? 'UNKNOWN';
      opErrorMsg = result.error?.message ?? 'Import failed.';
      opState = 'error';
    }
  }

  /**
   * Phase 26C: after a successful write, fetch notes/validation/tasks/trust
   * so the result panel can render the imported review summary derived from
   * existing endpoints.  Failures here never block the write result; the
   * summary simply falls back to the zero/missing-data state.
   */
  async function loadPostWriteData(): Promise<void> {
    if (!writeResult) return;
    postWriteLoading = true;
    postWriteNotes = null;
    postWriteValidation = null;
    postWriteTasks = null;
    postWriteTrust = null;
    const vault = writeResult.vault;
    const [nRes, vRes, tRes, trRes] = await Promise.all([
      fetchNotes(vault),
      fetchValidation(vault),
      fetchTasks(vault, { limit: 500, include_feedback: false }),
      fetchTrustSummary(vault),
    ]);
    if (isOk(nRes)) postWriteNotes = nRes.data.notes;
    if (isOk(vRes)) postWriteValidation = vRes.data;
    if (isOk(tRes)) postWriteTasks = tRes.data;
    if (isOk(trRes)) postWriteTrust = trRes.data;
    postWriteLoading = false;
  }

  function resetAll(): void {
    preview = null;
    writeResult = null;
    confirmReviewed = false;
    expandedItem = null;
    showRawJson = false;
    opState = 'idle';
    opErrorCode = '';
    opErrorMsg = '';
    postWriteNotes = null;
    postWriteValidation = null;
    postWriteTasks = null;
    postWriteTrust = null;
    postWriteLoading = false;
  }

  function errorTitle(code: string): string {
    if (code === 'INVALID_VAULT') return 'Unknown vault';
    if (code === 'INVALID_SOURCE') return 'Source folder is not valid';
    if (code === 'UNSAFE_SOURCE') return 'Unsafe source folder';
    if (code === 'UNSAFE_DESTINATION') return 'Unsafe destination folder';
    if (code === 'IMPORT_FAILED') return 'Import failed';
    if (code === 'READ_ONLY') return 'Remote read-only mode';
    if (code === 'NETWORK_ERROR') return 'Backend unavailable';
    return 'Error';
  }

  function errorHelp(code: string): string {
    if (code === 'INVALID_SOURCE')
      return 'Check that the path exists on the machine running the backend, points to a folder, and does not contain null bytes.';
    if (code === 'UNSAFE_DESTINATION')
      return 'Destination must be vault-relative. It cannot be absolute, cannot contain "..", and cannot be inside Vault Files/.';
    if (code === 'UNSAFE_SOURCE')
      return 'The source folder must not be inside the target vault.';
    if (code === 'READ_ONLY')
      return 'Imports are disabled in remote read-only mode.';
    if (code === 'NETWORK_ERROR')
      return 'Could not reach the backend. Is the server running on the expected port?';
    return '';
  }

  // Phase 26D: per-item error code labels.  Keep wording short, concrete,
  // and aligned with the error codes returned by the backend importer.
  function itemErrorLabel(code: string): string {
    if (code === 'READ_FAILED') return 'Could not read source file';
    if (code === 'SOURCE_TOO_LARGE') return 'Source file exceeds the 5 MB size cap';
    if (code === 'NULL_BYTE') return 'Source file contains a null byte and was blocked';
    if (code === 'INVALID_FRONTMATTER') return 'YAML frontmatter is malformed';
    if (code === 'FRONTMATTER_NOT_OBJECT') return 'YAML frontmatter is not a mapping';
    if (code === 'DUPLICATE_YAML_KEY') return 'YAML frontmatter has a duplicate key';
    if (code === 'DESTINATION_EXISTS')
      return 'A note already exists at the destination; re-run with overwrite to replace it';
    if (code === 'UNSAFE_DESTINATION') return 'Destination path is unsafe';
    if (code === 'SECURITY_FAIL') return 'Security scan blocked the import';
    if (code === 'VALIDATION_FAILED') return 'Validation rejected the imported note';
    if (code === 'SERIALISE_FAILED') return 'Could not serialise the imported note';
    if (code === 'WRITE_FAILED') return 'Filesystem write failed';
    return code;
  }

  function itemStatusClass(status: string): string {
    if (status === 'written') return 'bg-emerald-950 text-emerald-300 border-emerald-800';
    if (status === 'planned') return 'bg-sky-950 text-sky-300 border-sky-800';
    if (status === 'skipped') return 'bg-amber-950 text-amber-300 border-amber-800';
    if (status === 'blocked') return 'bg-rose-950 text-rose-300 border-rose-800';
    if (status === 'error') return 'bg-rose-950 text-rose-300 border-rose-800';
    return 'bg-zinc-800 text-zinc-300 border-zinc-700';
  }

  function securityClass(status: string): string {
    if (status === 'pass') return 'bg-emerald-950 text-emerald-300 border-emerald-800';
    if (status === 'warning') return 'bg-amber-950 text-amber-300 border-amber-800';
    if (status === 'fail') return 'bg-rose-950 text-rose-300 border-rose-800';
    return 'bg-zinc-800 text-zinc-300 border-zinc-700';
  }

  function validationClass(status: string): string {
    if (status === 'pass') return 'bg-emerald-950 text-emerald-300 border-emerald-800';
    if (status === 'fail') return 'bg-rose-950 text-rose-300 border-rose-800';
    return 'bg-zinc-800 text-zinc-300 border-zinc-700';
  }

  function toggleItem(idx: number): void {
    expandedItem = expandedItem === idx ? null : idx;
  }

  function activeItems(resp: ImportMarkdownFolderResponse | null): ImportMarkdownItem[] {
    return resp?.items ?? [];
  }

  function blockedCount(resp: ImportMarkdownFolderResponse | null): number {
    if (!resp) return 0;
    return resp.items.filter(i => i.status === 'blocked').length;
  }

  // Phase 26D: per-item banner helpers so users see the specific failure
  // modes (collision, malformed frontmatter) called out near the items list.
  function hasCollisionErrors(resp: ImportMarkdownFolderResponse | null): boolean {
    if (!resp) return false;
    return resp.items.some(i =>
      (i.errors ?? []).some(e => e.code === 'DESTINATION_EXISTS')
    );
  }

  function hasFrontmatterErrors(resp: ImportMarkdownFolderResponse | null): boolean {
    if (!resp) return false;
    return resp.items.some(i =>
      (i.errors ?? []).some(
        e => e.code === 'INVALID_FRONTMATTER'
          || e.code === 'FRONTMATTER_NOT_OBJECT'
          || e.code === 'DUPLICATE_YAML_KEY'
      )
    );
  }
</script>

<!-- ── Page header ─────────────────────────────────────────────────────────── -->
<div class="mb-5">
  <h1 class="text-xl font-semibold text-zinc-100">Import Markdown Folder</h1>
  <p class="text-sm text-zinc-500 mt-0.5">
    Imports Markdown files from a server-local folder into an existing vault.
    Preview is required before writing. Markdown folder import only. No PDF,
    GitHub repo, browser article, semantic, or LLM import yet.
  </p>
</div>

{#if vaultsLoading}
  <div class="text-sm text-zinc-500 py-6">Loading vaults...</div>
{:else if vaultsError}
  <div class="bg-red-950 border border-red-800 rounded-lg p-4 text-sm text-red-300 mb-4">
    <span class="font-medium">Could not load vaults:</span> {vaultsError}
  </div>
{:else if vaultList.length === 0}
  <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-6 max-w-lg">
    <p class="text-sm text-zinc-400">
      No vaults registered. Use <a href="/app/vault-setup" class="text-sky-400 hover:underline">Vault Setup</a> to create one.
    </p>
  </div>
{:else}

<div class="grid grid-cols-1 lg:grid-cols-2 gap-5">

  <!-- ── Left column: form ─────────────────────────────────────────────── -->
  <div class="space-y-4">
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
      <h2 class="text-sm font-semibold text-zinc-200 mb-3">Import settings</h2>

      <label class="block text-xs text-zinc-400 mb-1" for="import-vault">Vault</label>
      <select
        id="import-vault"
        bind:value={selectedVault}
        disabled={opState === 'previewing' || opState === 'writing'}
        class="w-full bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-1.5 text-sm text-zinc-100 mb-3"
      >
        {#each vaultList as v}
          <option value={v}>{v}</option>
        {/each}
      </select>

      <label class="block text-xs text-zinc-400 mb-1" for="import-source">
        Source folder path
      </label>
      <input
        id="import-source"
        type="text"
        bind:value={sourceDir}
        placeholder="C:\path\to\markdown-folder"
        disabled={opState === 'previewing' || opState === 'writing'}
        class="w-full bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-1.5 text-sm text-zinc-100 font-mono mb-1"
      />
      <p class="text-xs text-zinc-500 mb-3">
        This path is resolved on the backend host (server-local path).
        For the local app, that is your own machine. Browsers cannot pick
        server filesystem folders, so type or paste the path here.
      </p>

      <label class="block text-xs text-zinc-400 mb-1" for="import-destination">
        Destination folder (vault-relative)
      </label>
      <input
        id="import-destination"
        type="text"
        bind:value={destination}
        placeholder="Imported"
        disabled={opState === 'previewing' || opState === 'writing'}
        class="w-full bg-zinc-950 border border-zinc-800 rounded-md px-2.5 py-1.5 text-sm text-zinc-100 font-mono mb-1"
      />
      <p class="text-xs text-zinc-500 mb-3">
        Defaults to <code class="text-zinc-300">Imported</code>. Cannot be
        absolute, cannot contain <code class="text-zinc-300">..</code>, and
        cannot be inside <code class="text-zinc-300">Vault Files/</code>.
      </p>

      <label class="flex items-start gap-2 text-sm text-zinc-300 mb-4">
        <input
          type="checkbox"
          bind:checked={overwrite}
          disabled={opState === 'previewing' || opState === 'writing'}
          class="mt-0.5"
        />
        <span>
          Overwrite existing files at destination paths.
          <span class="block text-xs text-zinc-500">
            By default, existing files are skipped. Imported notes are marked
            as imported/draft via trust metadata when the schema supports it.
          </span>
        </span>
      </label>

      <div class="flex items-center gap-2 text-xs text-zinc-500 mb-3">
        <span class="px-2 py-0.5 border border-zinc-700 rounded">
          Mode: {dryRunIndicator}
        </span>
        {#if previewStale}
          <span class="px-2 py-0.5 border border-amber-700 text-amber-300 rounded">
            Stale - re-run preview
          </span>
        {/if}
      </div>

      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          on:click={handlePreview}
          disabled={!canPreview}
          class="px-3 py-1.5 text-sm font-medium rounded-md bg-sky-700 hover:bg-sky-600 disabled:bg-zinc-800 disabled:text-zinc-500 text-white"
        >
          {opState === 'previewing' ? 'Previewing...' : 'Preview Import (dry-run)'}
        </button>
        <button
          type="button"
          on:click={handleWrite}
          disabled={!canWrite}
          class="px-3 py-1.5 text-sm font-medium rounded-md bg-emerald-700 hover:bg-emerald-600 disabled:bg-zinc-800 disabled:text-zinc-500 text-white"
        >
          {opState === 'writing' ? 'Writing...' : 'Write Import'}
        </button>
        <button
          type="button"
          on:click={resetAll}
          disabled={opState === 'previewing' || opState === 'writing'}
          class="px-3 py-1.5 text-sm rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800"
        >
          Reset
        </button>
      </div>
    </div>

    <!-- ── Write confirmation ───────────────────────────────────────────── -->
    {#if preview !== null}
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
        <h2 class="text-sm font-semibold text-zinc-200 mb-3">Confirm write</h2>
        <label class="flex items-start gap-2 text-sm text-zinc-300">
          <input
            type="checkbox"
            bind:checked={confirmReviewed}
            disabled={previewStale || previewHasBlockers || opState === 'writing'}
            class="mt-0.5"
          />
          <span>
            I have reviewed the import preview and want to write these files.
          </span>
        </label>

        {#if previewStale}
          <p class="text-xs text-amber-300 mt-2">
            Preview is stale because source folder, vault, destination, or
            overwrite changed. Re-run preview before writing.
          </p>
        {:else if previewHasBlockers}
          <p class="text-xs text-rose-300 mt-2">
            Preview has blocking errors or zero planned writes. Resolve before
            writing.
          </p>
        {/if}
      </div>
    {/if}

    <!-- ── Error panel ──────────────────────────────────────────────────── -->
    {#if opState === 'error'}
      <div class="bg-red-950 border border-red-800 rounded-lg p-4 text-sm">
        <div class="font-medium text-red-200">{errorTitle(opErrorCode)}</div>
        <div class="text-red-300 mt-1 break-words">{opErrorMsg}</div>
        {#if errorHelp(opErrorCode)}
          <div class="text-red-400 text-xs mt-2">{errorHelp(opErrorCode)}</div>
        {/if}
      </div>
    {/if}
  </div>

  <!-- ── Right column: preview/write result ─────────────────────────────── -->
  <div class="space-y-4">
    {#if writeResult !== null || preview !== null}
      {@const display = writeResult ?? preview}
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold text-zinc-200">
            {writeResult ? 'Write result' : 'Preview summary'}
          </h2>
          <span class="text-xs px-2 py-0.5 border rounded {display?.dry_run ? 'border-sky-700 text-sky-300' : 'border-emerald-700 text-emerald-300'}">
            {display?.dry_run ? 'dry-run' : 'write'}
          </span>
        </div>

        <dl class="grid grid-cols-2 gap-y-1.5 gap-x-4 text-xs">
          <dt class="text-zinc-500">Vault</dt><dd class="text-zinc-200 font-mono break-all">{display?.vault}</dd>
          <dt class="text-zinc-500">Source folder</dt><dd class="text-zinc-200 font-mono break-all">{display?.source_dir}</dd>
          <dt class="text-zinc-500">Destination folder</dt><dd class="text-zinc-200 font-mono break-all">{display?.destination}</dd>
          <dt class="text-zinc-500">Discovered</dt><dd class="text-zinc-200">{display?.summary.discovered}</dd>
          <dt class="text-zinc-500">Planned</dt><dd class="text-sky-300">{display?.summary.planned}</dd>
          <dt class="text-zinc-500">Written</dt><dd class="text-emerald-300">{display?.summary.written}</dd>
          <dt class="text-zinc-500">Skipped</dt><dd class="text-amber-300">{display?.summary.skipped}</dd>
          <dt class="text-zinc-500">Blocked</dt><dd class="text-rose-300">{blockedCount(display)}</dd>
          <dt class="text-zinc-500">Errors</dt><dd class="text-rose-300">{display?.summary.errors}</dd>
          <dt class="text-zinc-500">Warnings</dt><dd class="text-amber-300">{display?.summary.warnings}</dd>
        </dl>

        {#if writeResult !== null}
          <div class="mt-4 pt-3 border-t border-zinc-800 text-xs text-zinc-400">
            <div class="font-medium text-zinc-200 mb-2">Follow up:</div>
            <ul class="flex flex-wrap gap-x-3 gap-y-1">
              <li>
                <a class="text-sky-400 hover:underline"
                   href={buildNotesLink({ vault: writeResult.vault, filter: 'imported' })}>
                  Notes (imported only)
                </a>
              </li>
              <li>
                <a class="text-sky-400 hover:underline"
                   href={buildNotesLink({ vault: writeResult.vault, filter: 'draft' })}>
                  Notes (draft trust)
                </a>
              </li>
              <li><a class="text-sky-400 hover:underline" href="/app/validation">Validation</a></li>
              <li><a class="text-sky-400 hover:underline" href="/app/tasks">Tasks</a></li>
              <li><a class="text-sky-400 hover:underline" href="/app/trust">Trust and evidence</a></li>
              <li><a class="text-sky-400 hover:underline" href="/app/security">Security</a></li>
              <li><a class="text-sky-400 hover:underline" href="/app/">Dashboard</a></li>
            </ul>
            <p class="text-[11px] text-zinc-500 mt-2">
              Imported notes carry <code class="text-zinc-300">source_type: imported</code>
              (and <code class="text-zinc-300">trust_level: draft</code> when the schema allows it).
              Promote or update them through the existing safe editing workflow.
              Trust metadata is never promoted automatically.
            </p>
          </div>
        {/if}
      </div>

      {#if writeResult !== null}
        <ImportedReviewSummary
          vault={writeResult.vault}
          notes={postWriteNotes}
          validation={postWriteValidation}
          tasks={postWriteTasks}
          trust={postWriteTrust}
        />
        {#if postWriteLoading}
          <p class="text-xs text-zinc-500 -mt-2">Loading post-import review data...</p>
        {/if}
      {/if}

      <!-- Item review -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold text-zinc-200">
            Items ({activeItems(display).length})
          </h2>
          <button
            type="button"
            on:click={() => (showRawJson = !showRawJson)}
            class="text-xs text-sky-400 hover:underline"
          >
            {showRawJson ? 'Hide raw JSON' : 'Show raw JSON'}
          </button>
        </div>

        {#if activeItems(display).length === 0}
          <p class="text-sm text-zinc-500" data-testid="empty-items-message">
            No Markdown files were discovered in the source folder.
            Confirm that the folder contains files with the
            <code class="text-zinc-300">.md</code> extension and that the path
            is correct on the backend host. Non-Markdown files (PDF, DOCX,
            HTML, etc.) are intentionally ignored: Phase 26D supports
            Markdown folder import only.
          </p>
        {:else}
          {#if hasCollisionErrors(display)}
            <p class="mb-3 text-xs text-amber-300" data-testid="collision-banner">
              One or more items would overwrite existing notes (code
              <code class="text-amber-200">DESTINATION_EXISTS</code>).
              Re-run with overwrite enabled to replace them, or rename the
              source file to import alongside the existing note.
            </p>
          {/if}
          {#if hasFrontmatterErrors(display)}
            <p class="mb-3 text-xs text-amber-300" data-testid="frontmatter-banner">
              One or more items had malformed YAML frontmatter and were
              blocked at the item level. The rest of the batch was processed
              normally.
            </p>
          {/if}
          <ul class="space-y-2">
            {#each activeItems(display) as item, idx}
              <li class="border border-zinc-800 rounded-md bg-zinc-950">
                <button
                  type="button"
                  class="w-full text-left px-3 py-2 hover:bg-zinc-900"
                  on:click={() => toggleItem(idx)}
                >
                  <div class="flex items-center flex-wrap gap-2 text-xs">
                    <span class="px-1.5 py-0.5 border rounded {itemStatusClass(item.status)}">
                      {item.status}
                    </span>
                    <span class="px-1.5 py-0.5 border rounded {securityClass(item.security?.status ?? '')}">
                      security: {item.security?.status ?? 'unknown'}
                    </span>
                    <span class="px-1.5 py-0.5 border rounded {validationClass(item.validation?.status ?? '')}">
                      validation: {item.validation?.status ?? 'unknown'}
                    </span>
                    <span class="text-zinc-500">action: {item.action}</span>
                    {#if item.warnings.length > 0}
                      <span class="text-amber-400">{item.warnings.length} warning{item.warnings.length === 1 ? '' : 's'}</span>
                    {/if}
                    {#if item.errors.length > 0}
                      <span class="text-rose-400">{item.errors.length} error{item.errors.length === 1 ? '' : 's'}</span>
                    {/if}
                  </div>
                  <div class="mt-1.5 text-xs font-mono text-zinc-300 break-all">
                    {item.source_path}
                  </div>
                  <div class="text-xs font-mono text-zinc-500 break-all">
                    → {item.destination_path || '(no destination)'}
                  </div>
                </button>

                {#if expandedItem === idx}
                  <div class="px-3 pb-3 pt-1 border-t border-zinc-800 text-xs space-y-2">
                    {#if item.warnings.length > 0}
                      <div>
                        <div class="text-amber-300 font-medium">Warnings</div>
                        <ul class="list-disc pl-5 text-zinc-300">
                          {#each item.warnings as w}
                            <li class="break-words">{w}</li>
                          {/each}
                        </ul>
                      </div>
                    {/if}
                    {#if item.errors.length > 0}
                      <div>
                        <div class="text-rose-300 font-medium">Errors</div>
                        <ul class="list-disc pl-5 text-zinc-300" data-testid="item-errors">
                          {#each item.errors as e}
                            <li class="break-words">
                              <code class="text-rose-200">{e.code}</code>
                              <span class="text-rose-200"> — {itemErrorLabel(e.code)}</span>
                              <span class="text-zinc-400"> ({e.message})</span>
                            </li>
                          {/each}
                        </ul>
                      </div>
                    {/if}
                    {#if item.security?.findings?.length}
                      <div>
                        <div class="text-amber-300 font-medium">Security findings</div>
                        <ul class="list-disc pl-5 text-zinc-300">
                          {#each item.security.findings as f}
                            <li class="break-words">
                              <code class="text-zinc-200">{f.rule ?? 'rule'}</code>
                              ({f.severity ?? 'severity'}) — {f.detail ?? ''}
                            </li>
                          {/each}
                        </ul>
                      </div>
                    {/if}
                    {#if item.validation?.errors?.length}
                      <div>
                        <div class="text-rose-300 font-medium">Validation errors</div>
                        <ul class="list-disc pl-5 text-zinc-300">
                          {#each item.validation.errors as ve}
                            <li class="break-words">{ve}</li>
                          {/each}
                        </ul>
                      </div>
                    {/if}
                    {#if item.fields && Object.keys(item.fields).length > 0}
                      <div>
                        <div class="text-zinc-300 font-medium">Mapped fields</div>
                        <pre class="bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto text-zinc-300">{JSON.stringify(item.fields, null, 2)}</pre>
                      </div>
                    {/if}
                  </div>
                {/if}
              </li>
            {/each}
          </ul>
        {/if}

        {#if showRawJson}
          <pre class="mt-4 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto text-xs text-zinc-300">{JSON.stringify(display, null, 2)}</pre>
        {/if}
      </div>
    {:else}
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-5 text-sm text-zinc-400">
        <p class="mb-2 font-medium text-zinc-200">No preview yet.</p>
        <p>
          Fill in the form on the left and run <span class="text-sky-300">Preview Import (dry-run)</span>
          to see exactly what would be imported. Nothing is written until you
          confirm and click <span class="text-emerald-300">Write Import</span>.
        </p>
      </div>
    {/if}
  </div>
</div>
{/if}
