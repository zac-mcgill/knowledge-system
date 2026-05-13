<script lang="ts">
  // Phase 30E2 - Vault Setup polish.
  //
  // The page is split into two clearly separated surfaces:
  //   1. Onboarding / Setup - the grouped Create a Vault form.
  //   2. Vault Management - listing existing vaults and the destructive
  //      delete action, which lives behind a cve-slide-over launched
  //      from the management panel. The delete control no longer appears
  //      inside the primary setup form.
  //
  // Destructive deletion requires the exact typed phrase "DELETE <vault>"
  // (deterministic, matches backend semantics in mcp/core/vault_delete.py)
  // and the submit button is disabled until the phrase matches. The
  // confirmation panel explicitly states that the vault directory will be
  // removed from disk and that the action is not reversible.

  import { onMount } from 'svelte';
  import {
    bootstrapVault,
    deleteVault,
    fetchVaults,
    isOk,
    type VaultBootstrapResponse,
    type VaultDeleteResponse,
  } from '../lib/api.ts';
  import {
    deleteConfirmPhrase,
    isDeleteConfirmed,
    VAULT_DELETE_PROTECTED,
    VAULT_DELETE_SEMANTICS,
  } from '../lib/phase30e2.ts';
  import { setStoredVault, getStoredVault, clearStoredVault } from '../lib/vaultState.ts';

  // ── Setup form state ─────────────────────────────────────────────────────
  let vaultName = '';
  let domain = '';
  let noteType = '';
  let sections: string[] = ['Overview', 'Key Principles', 'How It Works', 'Trade-offs'];
  let newSection = '';
  let expectedConcepts: string[] = [];
  let newConcept = '';

  type SubmitState = 'idle' | 'loading' | 'success' | 'error';
  let submitState: SubmitState = 'idle';
  let successData: VaultBootstrapResponse | null = null;
  let errorCode = '';
  let errorMsg = '';

  // ── Management state ─────────────────────────────────────────────────────
  let availableVaults: string[] = [];
  let vaultsLoaded = false;
  let vaultsLoadError = '';

  let deleteSlideOpen = false;
  let deleteVaultName = '';
  let deleteConfirmInput = '';

  type DeleteState = 'idle' | 'loading' | 'success' | 'error';
  let deleteState: DeleteState = 'idle';
  let deleteSuccessData: VaultDeleteResponse | null = null;
  let deleteErrorCode = '';
  let deleteErrorMsg = '';

  onMount(() => {
    void loadVaults();
  });

  async function loadVaults(): Promise<void> {
    vaultsLoadError = '';
    const result = await fetchVaults();
    if (isOk(result)) {
      availableVaults = result.data.vaults;
    } else {
      vaultsLoadError = result.error?.message ?? 'Could not load vaults.';
    }
    vaultsLoaded = true;
  }

  // ── Setup validation ─────────────────────────────────────────────────────
  const VAULT_NAME_RE = /^[A-Za-z0-9_-]+$/;
  const NOTE_TYPE_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  const FORBIDDEN_DOMAIN_RE = /[/\\<>:"|?*\u0000-\u001f]/;

  $: vaultNameError = vaultName === ''
    ? 'Required'
    : !VAULT_NAME_RE.test(vaultName)
      ? 'Only letters, numbers, underscores, and hyphens (no spaces or slashes).'
      : '';

  $: domainError = domain.trim() === ''
    ? 'Required'
    : FORBIDDEN_DOMAIN_RE.test(domain) || domain.includes('..')
      ? 'Must not contain path separators, traversal markers, or control characters.'
      : '';

  $: noteTypeError = noteType === ''
    ? 'Required'
    : !NOTE_TYPE_RE.test(noteType)
      ? 'Must be lowercase hyphen-separated words (e.g. breed-profile).'
      : '';

  $: sectionsError = (() => {
    const trimmed = sections.map(s => s.trim()).filter(Boolean);
    if (trimmed.length < 2) return 'At least 2 sections required.';
    const lower = trimmed.map(s => s.toLowerCase());
    if (new Set(lower).size !== lower.length) return 'Sections must not have duplicates.';
    return '';
  })();

  $: conceptsDupeError = (() => {
    const trimmed = expectedConcepts.map(c => c.trim()).filter(Boolean);
    const lower = trimmed.map(c => c.toLowerCase());
    return new Set(lower).size !== lower.length
      ? 'Expected concepts must not have duplicates.'
      : '';
  })();

  $: formValid =
    !vaultNameError && !domainError && !noteTypeError && !sectionsError && !conceptsDupeError;
  $: canSubmit = formValid && submitState !== 'loading';

  // ── Section management ──────────────────────────────────────────────────
  function addSection() {
    const val = newSection.trim();
    if (!val) return;
    if (sections.map(s => s.trim().toLowerCase()).includes(val.toLowerCase())) return;
    sections = [...sections, val];
    newSection = '';
  }
  function removeSection(i: number) { sections = sections.filter((_, j) => j !== i); }
  function onSectionKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); addSection(); }
  }

  function addConcept() {
    const val = newConcept.trim();
    if (!val) return;
    if (expectedConcepts.map(c => c.trim().toLowerCase()).includes(val.toLowerCase())) return;
    expectedConcepts = [...expectedConcepts, val];
    newConcept = '';
  }
  function removeConcept(i: number) { expectedConcepts = expectedConcepts.filter((_, j) => j !== i); }
  function onConceptKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); addConcept(); }
  }

  // ── Setup submit ────────────────────────────────────────────────────────
  async function handleSubmit() {
    if (!canSubmit) return;
    submitState = 'loading';
    successData = null;
    errorCode = '';
    errorMsg = '';

    const result = await bootstrapVault({
      vault_name: vaultName,
      domain: domain.trim(),
      note_type: noteType,
      sections: sections.map(s => s.trim()).filter(Boolean),
      expected_concepts: expectedConcepts.map(c => c.trim()).filter(Boolean),
    });

    if (isOk(result)) {
      successData = result.data;
      submitState = 'success';
      setStoredVault(result.data.vault);
      await loadVaults();
    } else {
      errorCode = result.error?.code ?? 'UNKNOWN';
      errorMsg = result.error?.message ?? 'An unexpected error occurred.';
      submitState = 'error';
    }
  }

  function resetForm() {
    vaultName = '';
    domain = '';
    noteType = '';
    sections = ['Overview', 'Key Principles', 'How It Works', 'Trade-offs'];
    newSection = '';
    expectedConcepts = [];
    newConcept = '';
    submitState = 'idle';
    successData = null;
    errorCode = '';
    errorMsg = '';
  }

  $: previewName = vaultName || '<vault-name>';
  $: previewNoteType = noteType || '<note-type>';
  $: previewSections = sections.map(s => s.trim()).filter(Boolean);
  $: previewConcepts = expectedConcepts.map(c => c.trim()).filter(Boolean);

  function errorTitle(code: string): string {
    if (code === 'VAULT_EXISTS') return 'Vault already exists';
    if (code === 'PATH_TRAVERSAL') return 'Security violation';
    if (code === 'INVALID_INPUT' || code === 'VALIDATION_ERROR') return 'Invalid input';
    if (code === 'NETWORK_ERROR') return 'Backend unavailable';
    if (code === 'BOOTSTRAP_FAILED') return 'Bootstrap failed';
    if (code === 'CONFIG_UPDATE_FAILED') return 'Config update failed';
    return 'Error';
  }

  // ── Management / destructive delete ─────────────────────────────────────
  $: deletableVaults = availableVaults.filter(v => v !== VAULT_DELETE_PROTECTED);
  $: expectedDeletePhrase = deleteConfirmPhrase(deleteVaultName);
  $: deleteConfirmValid = isDeleteConfirmed(deleteVaultName, deleteConfirmInput);
  $: canDelete =
    deleteVaultName !== '' &&
    deleteVaultName !== VAULT_DELETE_PROTECTED &&
    deleteConfirmValid &&
    deleteState !== 'loading';

  function openDeleteSlide(vault: string): void {
    if (vault === VAULT_DELETE_PROTECTED) return;
    deleteVaultName = vault;
    deleteConfirmInput = '';
    deleteState = 'idle';
    deleteSuccessData = null;
    deleteErrorCode = '';
    deleteErrorMsg = '';
    deleteSlideOpen = true;
  }

  function closeDeleteSlide(): void {
    deleteSlideOpen = false;
  }

  async function handleDelete(): Promise<void> {
    if (!canDelete) return;
    deleteState = 'loading';
    deleteSuccessData = null;
    deleteErrorCode = '';
    deleteErrorMsg = '';

    const result = await deleteVault(deleteVaultName, deleteConfirmInput.trim());

    if (isOk(result)) {
      deleteSuccessData = result.data;
      deleteState = 'success';
      const stored = getStoredVault();
      if (stored === deleteVaultName) {
        clearStoredVault();
        setStoredVault(result.data.active_vault);
      }
      availableVaults = result.data.remaining_vaults;
      deleteVaultName = '';
      deleteConfirmInput = '';
    } else {
      deleteErrorCode = result.error?.code ?? 'UNKNOWN';
      deleteErrorMsg = result.error?.message ?? 'An unexpected error occurred.';
      deleteState = 'error';
    }
  }

  function deleteErrorTitle(code: string): string {
    if (code === 'INVALID_VAULT') return 'Unknown vault';
    if (code === 'PROTECTED_VAULT') return 'Protected vault';
    if (code === 'LAST_VAULT') return 'Cannot delete last vault';
    if (code === 'CONFIRMATION_REQUIRED') return 'Confirmation required';
    if (code === 'CONFIRMATION_MISMATCH') return 'Confirmation mismatch';
    if (code === 'PATH_TRAVERSAL') return 'Security violation';
    if (code === 'DELETE_FAILED') return 'Delete failed';
    if (code === 'CONFIG_UPDATE_FAILED') return 'Config update failed';
    if (code === 'NETWORK_ERROR') return 'Backend unavailable';
    return 'Error';
  }

  // ── State pill ──────────────────────────────────────────────────────────
  $: statePillLabel = (() => {
    if (submitState === 'loading') return 'Creating';
    if (submitState === 'error') return 'Error';
    if (submitState === 'success') return 'Created';
    if (!vaultsLoaded) return 'Loading';
    if (vaultsLoadError) return 'Error';
    return 'Idle';
  })();

  $: statePillClass = (() => {
    switch (statePillLabel) {
      case 'Created': return 'cve-p30e2-pill cve-p30e2-pill--ready';
      case 'Error':   return 'cve-p30e2-pill cve-p30e2-pill--blocked';
      case 'Creating':return 'cve-p30e2-pill cve-p30e2-pill--action';
      default:        return 'cve-p30e2-pill';
    }
  })();
</script>

<!-- ============================================================
     Toolbar
     ============================================================ -->
<div class="cve-page cve-p30e2-page">
  <header class="cve-toolbar" data-testid="vault-setup-toolbar">
    <div class="cve-toolbar__main">
      <div class="cve-toolbar__title">Vault Setup</div>
      <span
        class={statePillClass}
        data-testid="vault-setup-state-pill"
        aria-live="polite"
      >
        {statePillLabel}
      </span>
      <div class="cve-toolbar__meta">
        Create or connect a vault. Destructive vault management lives in a separate panel below.
      </div>
      <div class="cve-toolbar__actions">
        <button
          type="button"
          on:click={() => void loadVaults()}
          class="cve-p30e2-btn"
          data-testid="vault-setup-refresh"
        >
          Refresh vaults
        </button>
      </div>
    </div>
  </header>

  <!-- Headline banner -->
  {#if submitState === 'success' && successData}
    <section
      class="cve-banner cve-banner--success"
      data-testid="vault-setup-headline-banner"
      role="status"
    >
      <div>
        <p class="cve-banner__title">Vault created</p>
        <p class="cve-banner__body">
          <span class="cve-p30e2-mono">{successData.vault}</span> was bootstrapped and is now the active vault.
        </p>
      </div>
    </section>
  {:else if submitState === 'error'}
    <section
      class="cve-banner cve-banner--danger"
      data-testid="vault-setup-headline-banner"
      role="status"
    >
      <div>
        <p class="cve-banner__title">{errorTitle(errorCode)}</p>
        <p class="cve-banner__body">{errorMsg}</p>
      </div>
    </section>
  {:else if vaultsLoadError}
    <section class="cve-banner cve-banner--warning" data-testid="vault-setup-headline-banner">
      <div>
        <p class="cve-banner__title">Could not load existing vaults</p>
        <p class="cve-banner__body">{vaultsLoadError}</p>
      </div>
    </section>
  {:else}
    <section class="cve-banner cve-banner--info" data-testid="vault-setup-headline-banner">
      <div>
        <p class="cve-banner__title">Create or connect a vault</p>
        <p class="cve-banner__body">
          Fill in the grouped setup form below. Existing vaults are listed in the management panel.
        </p>
      </div>
    </section>
  {/if}

  <!-- ============================================================
       Success follow-up (replaces form when the last submit succeeded)
       ============================================================ -->
  {#if submitState === 'success' && successData}
    <article class="cve-p30e2-panel cve-p30e2-panel--success" data-testid="vault-setup-success-panel">
      <h2 class="cve-p30e2-panel__title">Vault created</h2>
      <p class="cve-p30e2-helper-text">
        <span class="cve-p30e2-mono">{successData.vault}</span> was bootstrapped successfully.
      </p>

      {#if successData.created.length > 0}
        <div class="cve-p30e2-success-section">
          <p class="cve-p30e2-section-label">Files created:</p>
          <ul class="cve-p30e2-file-list">
            {#each successData.created as path}
              <li class="cve-p30e2-mono">{path}</li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if successData.expected_concepts && successData.expected_concepts.written > 0}
        <p class="cve-p30e2-helper-text">
          <strong>{successData.expected_concepts.written}</strong>
          expected concept{successData.expected_concepts.written === 1 ? '' : 's'} written into
          <span class="cve-p30e2-mono">EXPECTED_CONCEPTS</span> in
          <span class="cve-p30e2-mono">vault_schema.py</span>.
        </p>
      {/if}

      {#if successData.warnings.length > 0}
        <div class="cve-p30e2-success-section">
          <p class="cve-p30e2-section-label">Backend warnings:</p>
          <ul class="cve-p30e2-issue-list">
            {#each successData.warnings as warning}
              <li class="cve-p30e2-issue cve-p30e2-issue--warning">
                <span class="cve-p30e2-issue__label">Warning</span>
                <span class="cve-p30e2-issue__text">{warning}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      <div class="cve-p30e2-action-row">
        <a
          href={`/app/?vault=${encodeURIComponent(successData.vault)}`}
          class="cve-p30e2-btn cve-p30e2-btn--primary"
          data-testid="vault-setup-go-dashboard"
        >
          Go to Dashboard
        </a>
        <button type="button" on:click={resetForm} class="cve-p30e2-btn">
          Create another vault
        </button>
      </div>
    </article>

  {:else}
    <!-- ============================================================
         Primary onboarding / setup form (one grouped panel)
         ============================================================ -->
    <article class="cve-p30e2-panel cve-p30e2-setup-form" data-testid="vault-setup-form-panel">
      <h2 class="cve-p30e2-panel__title">Create a new vault</h2>
      <p class="cve-p30e2-helper-text">
        Define the vault directory name, domain, primary note type, and starter
        sections. The destructive delete action lives in the Vault Management
        panel below.
      </p>

      <div class="cve-p30e2-form-grid">

        <!-- Vault name -->
        <div class="cve-p30e2-field" data-testid="vault-setup-field-name">
          <label for="vault-name" class="cve-p30e2-field__label">
            Vault name <span class="cve-p30e2-required">*</span>
          </label>
          <p class="cve-p30e2-field__help">
            Directory name. Letters, numbers, underscores, and hyphens only.
          </p>
          <input
            id="vault-name"
            type="text"
            bind:value={vaultName}
            placeholder="e.g. dogs-vault"
            autocomplete="off"
            spellcheck="false"
            class="cve-p30e2-input cve-p30e2-mono"
            data-invalid={vaultName !== '' && !!vaultNameError}
          />
          {#if vaultName && vaultNameError}
            <p class="cve-p30e2-field__error" data-testid="vault-setup-error-name">{vaultNameError}</p>
          {/if}
        </div>

        <!-- Domain -->
        <div class="cve-p30e2-field" data-testid="vault-setup-field-domain">
          <label for="vault-domain" class="cve-p30e2-field__label">
            Domain <span class="cve-p30e2-required">*</span>
          </label>
          <p class="cve-p30e2-field__help">
            Human-readable label (e.g. "Dogs", "Software Engineering").
          </p>
          <input
            id="vault-domain"
            type="text"
            bind:value={domain}
            placeholder="e.g. Dogs"
            autocomplete="off"
            class="cve-p30e2-input"
            data-invalid={domain !== '' && !!domainError}
          />
          {#if domain && domainError}
            <p class="cve-p30e2-field__error" data-testid="vault-setup-error-domain">{domainError}</p>
          {/if}
        </div>

        <!-- Note type -->
        <div class="cve-p30e2-field" data-testid="vault-setup-field-note-type">
          <label for="vault-note-type" class="cve-p30e2-field__label">
            Note type <span class="cve-p30e2-required">*</span>
          </label>
          <p class="cve-p30e2-field__help">
            Slug for the primary note type (e.g. breed-profile, core-concept).
          </p>
          <input
            id="vault-note-type"
            type="text"
            bind:value={noteType}
            placeholder="e.g. breed-profile"
            autocomplete="off"
            spellcheck="false"
            class="cve-p30e2-input cve-p30e2-mono"
            data-invalid={noteType !== '' && !!noteTypeError}
          />
          {#if noteType && noteTypeError}
            <p class="cve-p30e2-field__error" data-testid="vault-setup-error-note-type">{noteTypeError}</p>
          {/if}
        </div>

        <!-- Sections -->
        <div class="cve-p30e2-field cve-p30e2-field--wide" data-testid="vault-setup-field-sections">
          <label for="vault-section-input" class="cve-p30e2-field__label">
            Required sections <span class="cve-p30e2-required">*</span>
            <span class="cve-p30e2-field__hint">{sections.length} section{sections.length === 1 ? '' : 's'}</span>
          </label>
          <p class="cve-p30e2-field__help">
            Canonical section headings for notes in this vault. Minimum 2.
          </p>

          {#if sections.length > 0}
            <ul class="cve-p30e2-chip-list">
              {#each sections as section, i}
                <li class="cve-p30e2-chip">
                  <span>{section}</span>
                  <button type="button" on:click={() => removeSection(i)} aria-label={`Remove section ${section}`}>x</button>
                </li>
              {/each}
            </ul>
          {/if}

          <div class="cve-p30e2-inline-row">
            <input
              id="vault-section-input"
              type="text"
              bind:value={newSection}
              on:keydown={onSectionKeydown}
              placeholder="Add a section..."
              class="cve-p30e2-input"
            />
            <button type="button" on:click={addSection} class="cve-p30e2-btn">Add</button>
          </div>
          {#if sectionsError}
            <p class="cve-p30e2-field__error" data-testid="vault-setup-error-sections">{sectionsError}</p>
          {/if}
        </div>

        <!-- Expected concepts -->
        <div class="cve-p30e2-field cve-p30e2-field--wide" data-testid="vault-setup-field-concepts">
          <label for="vault-concept-input" class="cve-p30e2-field__label">
            Expected concepts
            <span class="cve-p30e2-field__hint">optional</span>
          </label>
          <p class="cve-p30e2-field__help">
            Concepts written into <span class="cve-p30e2-mono">EXPECTED_CONCEPTS</span>
            in <span class="cve-p30e2-mono">vault_schema.py</span> so Missing Concepts
            works immediately after bootstrap.
          </p>

          {#if expectedConcepts.length > 0}
            <ul class="cve-p30e2-chip-list">
              {#each expectedConcepts as concept, i}
                <li class="cve-p30e2-chip">
                  <span>{concept}</span>
                  <button type="button" on:click={() => removeConcept(i)} aria-label={`Remove concept ${concept}`}>x</button>
                </li>
              {/each}
            </ul>
          {/if}

          <div class="cve-p30e2-inline-row">
            <input
              id="vault-concept-input"
              type="text"
              bind:value={newConcept}
              on:keydown={onConceptKeydown}
              placeholder="Add a concept..."
              class="cve-p30e2-input"
            />
            <button type="button" on:click={addConcept} class="cve-p30e2-btn">Add</button>
          </div>
          {#if conceptsDupeError}
            <p class="cve-p30e2-field__error" data-testid="vault-setup-error-concepts">{conceptsDupeError}</p>
          {/if}
        </div>

        <!-- Validation summary -->
        <div class="cve-p30e2-field cve-p30e2-field--wide" data-testid="vault-setup-validation-panel">
          <p class="cve-p30e2-section-label">Validation</p>
          <ul class="cve-p30e2-validation-list">
            {#each [
              { label: 'Vault name', ok: !vaultNameError, pending: vaultName === '' },
              { label: 'Domain',     ok: !domainError,   pending: domain.trim() === '' },
              { label: 'Note type',  ok: !noteTypeError, pending: noteType === '' },
              { label: 'Sections (minimum 2)', ok: !sectionsError, pending: sections.length < 2 },
              { label: 'Concepts (optional)',  ok: !conceptsDupeError, pending: false },
            ] as check}
              <li class="cve-p30e2-validation-row">
                {#if check.pending && check.label !== 'Concepts (optional)'}
                  <span class="cve-p30e2-validation-dot cve-p30e2-validation-dot--pending" aria-hidden="true"></span>
                  <span class="cve-p30e2-validation-text">Pending: {check.label}</span>
                {:else if check.ok}
                  <span class="cve-p30e2-validation-dot cve-p30e2-validation-dot--ok" aria-hidden="true"></span>
                  <span class="cve-p30e2-validation-text">OK: {check.label}</span>
                {:else}
                  <span class="cve-p30e2-validation-dot cve-p30e2-validation-dot--bad" aria-hidden="true"></span>
                  <span class="cve-p30e2-validation-text">Issue: {check.label}</span>
                {/if}
              </li>
            {/each}
          </ul>
        </div>

        <!-- Preview -->
        <div class="cve-p30e2-field cve-p30e2-field--wide" data-testid="vault-setup-preview-panel">
          <p class="cve-p30e2-section-label">Preview</p>
          <dl class="cve-p30e2-preview-list">
            <div class="cve-kv-row">
              <dt class="cve-kv-row__key">Vault dir</dt>
              <dd class="cve-kv-row__value">{previewName}/</dd>
            </div>
            <div class="cve-kv-row">
              <dt class="cve-kv-row__key">Domain</dt>
              <dd class="cve-kv-row__value">{domain.trim() || '-'}</dd>
            </div>
            <div class="cve-kv-row">
              <dt class="cve-kv-row__key">Note type</dt>
              <dd class="cve-kv-row__value">{previewNoteType}</dd>
            </div>
            {#if previewSections.length > 0}
              <div class="cve-kv-row">
                <dt class="cve-kv-row__key">Sections</dt>
                <dd class="cve-kv-row__value">{previewSections.join(', ')}</dd>
              </div>
            {/if}
            {#if previewConcepts.length > 0}
              <div class="cve-kv-row">
                <dt class="cve-kv-row__key">Concepts</dt>
                <dd class="cve-kv-row__value">{previewConcepts.join(', ')}</dd>
              </div>
            {/if}
          </dl>

          <p class="cve-p30e2-section-label" style="margin-top: var(--cve-space-3)">Files</p>
          <pre class="cve-p30e2-preview-tree">
{previewName}/
  Vault Files/
    Scripts/
      vault_schema.py
    Templates/
      {previewNoteType}.md
  config/config.yaml (updated)</pre>
        </div>

        <div class="cve-p30e2-action-row cve-p30e2-field--wide">
          <button
            type="button"
            on:click={handleSubmit}
            disabled={!canSubmit}
            class="cve-p30e2-btn cve-p30e2-btn--primary"
            data-testid="vault-setup-submit"
          >
            {submitState === 'loading' ? 'Creating vault...' : 'Create vault'}
          </button>
          {#if !formValid && submitState === 'idle'}
            <span class="cve-p30e2-helper-text">Complete the required fields above to enable Create.</span>
          {/if}
        </div>
      </div>
    </article>
  {/if}

  <!-- ============================================================
       Vault management panel (destructive actions live here)
       ============================================================ -->
  <article
    class="cve-p30e2-panel cve-p30e2-panel--management"
    data-testid="vault-setup-management-panel"
  >
    <div class="cve-p30e2-panel__head">
      <h2 class="cve-p30e2-panel__title">Vault management</h2>
      <p class="cve-p30e2-helper-text">
        Existing vaults registered in <span class="cve-p30e2-mono">config/config.yaml</span>.
        Destructive deletion is gated behind a typed confirmation in a separate slide-over panel.
      </p>
    </div>

    {#if deleteState === 'success' && deleteSuccessData}
      <div class="cve-banner cve-banner--success" data-testid="vault-setup-delete-success">
        <div>
          <p class="cve-banner__title">Vault deleted</p>
          <p class="cve-banner__body">
            <span class="cve-p30e2-mono">{deleteSuccessData.deleted}</span> was permanently removed from disk.
            Active vault set to <span class="cve-p30e2-mono">{deleteSuccessData.active_vault}</span>.
          </p>
        </div>
      </div>
    {/if}

    {#if !vaultsLoaded}
      <p class="cve-p30e2-empty">Loading vaults...</p>
    {:else if availableVaults.length === 0}
      <p class="cve-p30e2-empty">No vaults registered yet. Use the form above to create one.</p>
    {:else}
      <div class="cve-table-wrap">
        <table class="cve-table" data-testid="vault-setup-management-table">
          <thead>
            <tr>
              <th scope="col">Vault</th>
              <th scope="col">Status</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each availableVaults as v}
              <tr data-testid={`vault-setup-management-row-${v}`}>
                <td class="cve-p30e2-mono">{v}</td>
                <td>
                  {#if v === VAULT_DELETE_PROTECTED}
                    <span class="cve-p30e2-pill cve-p30e2-pill--protected">Protected</span>
                  {:else}
                    <span class="cve-p30e2-pill">Active</span>
                  {/if}
                </td>
                <td>
                  <a
                    href={`/app/?vault=${encodeURIComponent(v)}`}
                    class="cve-link"
                  >
                    Open dashboard
                  </a>
                  <button
                    type="button"
                    class="cve-p30e2-btn cve-p30e2-btn--danger"
                    disabled={v === VAULT_DELETE_PROTECTED}
                    on:click={() => openDeleteSlide(v)}
                    data-testid={`vault-setup-delete-trigger-${v}`}
                  >
                    Delete...
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </article>
</div>

<!-- ============================================================
     Destructive delete slide-over
     ============================================================ -->
<div
  class="cve-slide-over"
  data-open={deleteSlideOpen ? 'true' : 'false'}
  data-testid="vault-setup-delete-slide-over"
  aria-hidden={!deleteSlideOpen}
>
  <button
    type="button"
    class="cve-slide-over__backdrop"
    aria-label="Close delete confirmation"
    on:click={closeDeleteSlide}
  ></button>

  <div class="cve-slide-over__panel" role="dialog" aria-modal="true" aria-labelledby="vault-delete-title">
    <header class="cve-slide-over__header">
      <span id="vault-delete-title">Delete vault</span>
      <button
        type="button"
        class="cve-p30e2-btn"
        on:click={closeDeleteSlide}
        data-testid="vault-setup-delete-close"
      >
        Close
      </button>
    </header>

    <div class="cve-slide-over__body">
      {#if deleteVaultName}
        <p class="cve-p30e2-helper-text">
          Target vault:
          <span class="cve-p30e2-mono" data-testid="vault-setup-delete-target">{deleteVaultName}</span>
        </p>

        <section
          class="cve-banner cve-banner--danger cve-danger-zone"
          data-testid="vault-setup-delete-warning"
          role="status"
        >
          <div>
            <p class="cve-banner__title">This action cannot be undone</p>
            <p class="cve-banner__body">
              The entire
              <span class="cve-p30e2-mono">{deleteVaultName}/</span>
              folder will be deleted from disk and removed from
              <span class="cve-p30e2-mono">config/config.yaml</span>.
              {#if VAULT_DELETE_SEMANTICS.files_deleted}
                Vault files are permanently removed.
              {/if}
              {#if !VAULT_DELETE_SEMANTICS.reversible}
                This action is not reversible by the app. Exported packages are not the source of truth.
              {/if}
            </p>
          </div>
        </section>

        <div class="cve-p30e2-field">
          <label for="vault-delete-confirm" class="cve-p30e2-field__label">
            Type the confirmation phrase
          </label>
          <p class="cve-p30e2-field__help">
            To proceed, type exactly:
            <span class="cve-p30e2-mono" data-testid="vault-setup-delete-phrase">{expectedDeletePhrase}</span>
          </p>
          <input
            id="vault-delete-confirm"
            type="text"
            bind:value={deleteConfirmInput}
            autocomplete="off"
            spellcheck="false"
            placeholder={expectedDeletePhrase}
            class="cve-p30e2-input cve-p30e2-mono"
            data-testid="vault-setup-delete-confirm-input"
            data-invalid={deleteConfirmInput !== '' && !deleteConfirmValid}
          />
          {#if deleteConfirmInput && !deleteConfirmValid}
            <p class="cve-p30e2-field__error">
              Phrase must be exactly:
              <span class="cve-p30e2-mono">{expectedDeletePhrase}</span>
            </p>
          {/if}
        </div>

        {#if deleteState === 'error'}
          <section class="cve-banner cve-banner--danger" data-testid="vault-setup-delete-error">
            <div>
              <p class="cve-banner__title">{deleteErrorTitle(deleteErrorCode)}</p>
              <p class="cve-banner__body">{deleteErrorMsg}</p>
            </div>
          </section>
        {/if}
      {:else}
        <p class="cve-p30e2-empty">Select a vault from the management table to begin.</p>
      {/if}
    </div>

    <footer class="cve-slide-over__footer">
      <button
        type="button"
        class="cve-p30e2-btn"
        on:click={closeDeleteSlide}
      >
        Cancel
      </button>
      <button
        type="button"
        class="cve-p30e2-btn cve-p30e2-btn--danger"
        disabled={!canDelete}
        on:click={handleDelete}
        data-testid="vault-setup-delete-submit"
      >
        {deleteState === 'loading' ? 'Deleting...' : `Delete ${deleteVaultName || 'vault'}`}
      </button>
    </footer>
  </div>
</div>
