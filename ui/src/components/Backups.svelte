<script lang="ts">
  /*
    Backups.svelte - Phase 38

    Local backup and restore UI.  All operations are local files only.
    The page never displays note bodies, only file paths, sizes, and
    redacted manifest metadata.  Restore is preview-first and always
    requires a typed confirmation phrase before applying.
  */

  import { onMount } from 'svelte';
  import {
    fetchBackups,
    buildBackupPlan,
    createBackup,
    previewRestore,
    applyRestore,
    isOk,
    type BackupSummary,
    type BackupPlan,
    type BackupCreateResult,
    type RestorePreview,
    type RestoreApplyResult,
  } from '../lib/api.ts';

  type Phase = 'idle' | 'loading' | 'ok' | 'error';

  let listPhase: Phase = 'idle';
  let listError = '';
  let backups: BackupSummary[] = [];

  let planPhase: Phase = 'idle';
  let planError = '';
  let plan: BackupPlan | null = null;

  let createPhase: Phase = 'idle';
  let createError = '';
  let lastCreated: BackupCreateResult | null = null;

  let selectedBackup = '';
  let previewPhase: Phase = 'idle';
  let previewError = '';
  let preview: RestorePreview | null = null;

  let confirmInput = '';
  let allowOverwrite = false;
  let restoreConfig = false;
  let applyPhase: Phase = 'idle';
  let applyError = '';
  let applyResult: RestoreApplyResult | null = null;

  async function loadList(): Promise<void> {
    listPhase = 'loading';
    listError = '';
    const result = await fetchBackups();
    if (isOk(result)) {
      backups = result.data.backups ?? [];
      listPhase = 'ok';
    } else {
      backups = [];
      listError = result.error?.message ?? 'Failed to load backups';
      listPhase = 'error';
    }
  }

  async function loadPlan(): Promise<void> {
    planPhase = 'loading';
    planError = '';
    plan = null;
    const result = await buildBackupPlan();
    if (isOk(result)) {
      plan = result.data;
      planPhase = 'ok';
    } else {
      planError = result.error?.message ?? 'Failed to build backup plan';
      planPhase = 'error';
    }
  }

  async function runCreate(): Promise<void> {
    createPhase = 'loading';
    createError = '';
    lastCreated = null;
    const result = await createBackup();
    if (isOk(result)) {
      lastCreated = result.data;
      createPhase = 'ok';
      await loadList();
    } else {
      createError = result.error?.message ?? 'Failed to create backup';
      createPhase = 'error';
    }
  }

  async function runPreview(): Promise<void> {
    if (!selectedBackup) return;
    previewPhase = 'loading';
    previewError = '';
    preview = null;
    applyResult = null;
    const result = await previewRestore(selectedBackup);
    if (isOk(result)) {
      preview = result.data;
      previewPhase = 'ok';
    } else {
      previewError = result.error?.message ?? 'Failed to preview restore';
      previewPhase = 'error';
    }
  }

  async function runApply(): Promise<void> {
    if (!preview || !preview.ok || !preview.confirmation_phrase) return;
    if (confirmInput.trim() !== preview.confirmation_phrase) {
      applyError = 'Confirmation phrase does not match.';
      applyPhase = 'error';
      return;
    }
    applyPhase = 'loading';
    applyError = '';
    applyResult = null;
    const result = await applyRestore({
      backup: preview.backup_id ?? selectedBackup,
      confirmation: confirmInput.trim(),
      overwrite: allowOverwrite,
      restore_config: restoreConfig,
    });
    if (isOk(result)) {
      applyResult = result.data;
      applyPhase = 'ok';
    } else {
      applyError = result.error?.message ?? 'Restore failed';
      applyPhase = 'error';
    }
  }

  function formatBytes(n: number | null | undefined): string {
    if (n === null || n === undefined) return '—';
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / 1024 / 1024).toFixed(2)} MB`;
  }

  onMount(() => {
    loadList();
  });
</script>

<div class="cve-page">
  <header class="cve-toolbar">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Backups</h1>
      <p class="cve-toolbar__subtitle">
        Local backups of vaults, config, feedback, state and templates.
        Generated artefacts are excluded by default.  Backups are local
        files only and are never uploaded.
      </p>
    </div>
  </header>

  <section class="cve-card">
    <h2 class="cve-card__title">Existing backups</h2>
    {#if listPhase === 'loading'}
      <p>Loading backups…</p>
    {:else if listPhase === 'error'}
      <p class="cve-error">Failed to load: {listError}</p>
    {:else if backups.length === 0}
      <p>No local backups yet.  Use “Create backup” below to make one.</p>
    {:else}
      <table class="cve-table">
        <thead>
          <tr>
            <th>Backup ID</th>
            <th>Created</th>
            <th>Files</th>
            <th>Size</th>
            <th>Vaults</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each backups as b}
            <tr>
              <td><code>{b.backup_id}</code></td>
              <td>{b.generated_at ?? b.modified_at ?? '—'}</td>
              <td>{b.file_count ?? '—'}</td>
              <td>{formatBytes(b.archive_size)}</td>
              <td>{(b.vaults ?? []).join(', ') || '—'}</td>
              <td>
                <button
                  type="button"
                  class="cve-button"
                  on:click={() => {
                    selectedBackup = b.backup_id;
                    runPreview();
                  }}
                >
                  Preview restore
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
    <button type="button" class="cve-button" on:click={loadList}>Refresh</button>
  </section>

  <section class="cve-card">
    <h2 class="cve-card__title">Create backup</h2>
    <p>
      Plan first to see what would be included.  Generated artefacts
      under <code>dist/</code>, <code>ui/dist/</code>, vault reports, caches and
      VCS metadata are always excluded.
    </p>
    <div class="cve-actions">
      <button type="button" class="cve-button" on:click={loadPlan}>
        Plan backup
      </button>
      <button
        type="button"
        class="cve-button cve-button--primary"
        on:click={runCreate}
        disabled={createPhase === 'loading'}
      >
        {createPhase === 'loading' ? 'Creating…' : 'Create backup now'}
      </button>
    </div>

    {#if planPhase === 'error'}
      <p class="cve-error">Plan failed: {planError}</p>
    {/if}
    {#if plan}
      <div class="cve-subcard">
        <p><strong>Format version:</strong> {plan.format_version}</p>
        <p><strong>Files:</strong> {plan.file_count}</p>
        <p><strong>Total size:</strong> {formatBytes(plan.total_bytes)}</p>
        <p><strong>Config included:</strong> {plan.config_included ? 'yes' : 'no'}</p>
        <p><strong>Vaults:</strong></p>
        <ul>
          {#each plan.vaults as v}
            <li>
              {v.name} — {v.file_count} files, {formatBytes(v.total_bytes)}
              (schema {v.schema_version ?? '?'})
            </li>
          {/each}
        </ul>
        {#if plan.warnings.length > 0}
          <p><strong>Warnings:</strong></p>
          <ul>
            {#each plan.warnings as w}
              <li>{w.code}: {w.message}</li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}

    {#if createPhase === 'error'}
      <p class="cve-error">Create failed: {createError}</p>
    {/if}
    {#if lastCreated}
      <div class="cve-subcard">
        <p>
          <strong>Created:</strong> <code>{lastCreated.backup_id}</code>
          ({formatBytes(lastCreated.archive_size)},
          {lastCreated.file_count} files)
        </p>
        <p><strong>Path:</strong> <code>{lastCreated.archive_path}</code></p>
      </div>
    {/if}
  </section>

  <section class="cve-card">
    <h2 class="cve-card__title">Restore</h2>
    <p>
      Restore is preview-first.  Files that already exist will not be
      overwritten unless you tick the overwrite box AND type the exact
      confirmation phrase below.
    </p>

    <label class="cve-field">
      <span>Backup id or path</span>
      <input
        type="text"
        class="cve-input"
        bind:value={selectedBackup}
        placeholder="cve-backup-YYYYMMDDTHHMMSSZ-xxxxxxxx"
      />
    </label>
    <div class="cve-actions">
      <button
        type="button"
        class="cve-button"
        on:click={runPreview}
        disabled={!selectedBackup || previewPhase === 'loading'}
      >
        {previewPhase === 'loading' ? 'Loading…' : 'Preview restore'}
      </button>
    </div>

    {#if previewPhase === 'error'}
      <p class="cve-error">Preview failed: {previewError}</p>
    {/if}
    {#if preview}
      <div class="cve-subcard">
        <p>
          <strong>Status:</strong>
          {preview.ok ? 'preview clean' : 'has blocking errors'}
        </p>
        {#if preview.errors.length > 0}
          <p><strong>Errors:</strong></p>
          <ul>
            {#each preview.errors as e}
              <li>{e.code}: {e.message}</li>
            {/each}
          </ul>
        {/if}
        {#if preview.warnings.length > 0}
          <p><strong>Warnings:</strong></p>
          <ul>
            {#each preview.warnings as w}
              <li>{w.code}: {w.message}</li>
            {/each}
          </ul>
        {/if}
        <p>
          <strong>Files in archive:</strong> {preview.summary?.entry_count ?? 0}
          ({preview.summary?.targets_existing ?? 0} already exist locally)
        </p>
        {#if preview.entries.length > 0}
          <details>
            <summary>Show file list</summary>
            <table class="cve-table">
              <thead>
                <tr>
                  <th>Archive path</th>
                  <th>Target path</th>
                  <th>Kind</th>
                  <th>Exists</th>
                </tr>
              </thead>
              <tbody>
                {#each preview.entries as e}
                  <tr>
                    <td><code>{e.archive_path}</code></td>
                    <td><code>{e.target_path ?? '—'}</code></td>
                    <td>{e.kind ?? '—'}</td>
                    <td>{e.target_exists ? 'yes' : 'no'}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </details>
        {/if}
      </div>

      {#if preview.ok && preview.confirmation_phrase}
        <div class="cve-subcard cve-warning">
          <p>
            <strong>Apply this restore.</strong>  Type the phrase
            <code>{preview.confirmation_phrase}</code> exactly to confirm.
          </p>
          <label class="cve-field">
            <span>Confirmation phrase</span>
            <input
              type="text"
              class="cve-input"
              bind:value={confirmInput}
              placeholder={preview.confirmation_phrase}
            />
          </label>
          <label class="cve-checkbox">
            <input type="checkbox" bind:checked={allowOverwrite} />
            Allow overwriting existing files
          </label>
          <label class="cve-checkbox">
            <input type="checkbox" bind:checked={restoreConfig} />
            Also restore config/config.yaml
          </label>
          <div class="cve-actions">
            <button
              type="button"
              class="cve-button cve-button--danger"
              on:click={runApply}
              disabled={confirmInput.trim() !== preview.confirmation_phrase
                || applyPhase === 'loading'}
            >
              {applyPhase === 'loading' ? 'Restoring…' : 'Apply restore'}
            </button>
          </div>
          {#if applyPhase === 'error'}
            <p class="cve-error">Restore failed: {applyError}</p>
          {/if}
          {#if applyResult}
            <p>
              <strong>Restored:</strong> {applyResult.written.length} file(s);
              skipped {applyResult.skipped.length}.
            </p>
          {/if}
        </div>
      {/if}
    {/if}
  </section>
</div>
