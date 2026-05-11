<script lang="ts">
  import {
    bootstrapVault,
    isOk,
    type VaultBootstrapResponse,
  } from '../lib/api.ts';

  // ── Form state ─────────────────────────────────────────────────────────────
  let vaultName = '';
  let domain = '';
  let noteType = '';
  let sections: string[] = ['Overview', 'Key Principles', 'How It Works', 'Trade-offs'];
  let newSection = '';
  let expectedConcepts: string[] = [];
  let newConcept = '';

  // ── Submit state ───────────────────────────────────────────────────────────
  type SubmitState = 'idle' | 'loading' | 'success' | 'error';
  let submitState: SubmitState = 'idle';
  let successData: VaultBootstrapResponse | null = null;
  let errorCode = '';
  let errorMsg = '';

  // ── Validation patterns ────────────────────────────────────────────────────
  const VAULT_NAME_RE = /^[A-Za-z0-9_-]+$/;
  const NOTE_TYPE_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  // Reject path separators, common shell meta, and C0 control characters
  const FORBIDDEN_DOMAIN_RE = /[/\\<>:"|?*\u0000-\u001f]/;

  $: vaultNameError = vaultName === ''
    ? 'Required'
    : !VAULT_NAME_RE.test(vaultName)
      ? 'Only letters, numbers, underscores, and hyphens — no spaces or slashes'
      : '';

  $: domainError = domain.trim() === ''
    ? 'Required'
    : FORBIDDEN_DOMAIN_RE.test(domain) || domain.includes('..')
      ? 'Must not contain path separators, traversal markers, or control characters'
      : '';

  $: noteTypeError = noteType === ''
    ? 'Required'
    : !NOTE_TYPE_RE.test(noteType)
      ? 'Must be lowercase hyphen-separated words (e.g. breed-profile, core-concept)'
      : '';

  $: sectionsError = (() => {
    const trimmed = sections.map(s => s.trim()).filter(Boolean);
    if (trimmed.length < 2) return 'At least 2 sections required';
    const lower = trimmed.map(s => s.toLowerCase());
    if (new Set(lower).size !== lower.length) return 'Sections must not have duplicates';
    return '';
  })();

  $: conceptsDupeError = (() => {
    const trimmed = expectedConcepts.map(c => c.trim()).filter(Boolean);
    const lower = trimmed.map(c => c.toLowerCase());
    return new Set(lower).size !== lower.length
      ? 'Expected concepts must not have duplicates'
      : '';
  })();

  $: formValid =
    !vaultNameError && !domainError && !noteTypeError && !sectionsError && !conceptsDupeError;
  $: canSubmit = formValid && submitState !== 'loading';

  // ── Section management ─────────────────────────────────────────────────────
  function addSection() {
    const val = newSection.trim();
    if (!val) return;
    if (sections.map(s => s.trim().toLowerCase()).includes(val.toLowerCase())) return;
    sections = [...sections, val];
    newSection = '';
  }

  function removeSection(index: number) {
    sections = sections.filter((_, i) => i !== index);
  }

  function onSectionKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); addSection(); }
  }

  // ── Concept management ─────────────────────────────────────────────────────
  function addConcept() {
    const val = newConcept.trim();
    if (!val) return;
    if (expectedConcepts.map(c => c.trim().toLowerCase()).includes(val.toLowerCase())) return;
    expectedConcepts = [...expectedConcepts, val];
    newConcept = '';
  }

  function removeConcept(index: number) {
    expectedConcepts = expectedConcepts.filter((_, i) => i !== index);
  }

  function onConceptKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); addConcept(); }
  }

  // ── Submit ─────────────────────────────────────────────────────────────────
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

  // ── Preview derivations ────────────────────────────────────────────────────
  $: previewName = vaultName || '<vault-name>';
  $: previewNoteType = noteType || '<note-type>';
  $: previewSections = sections.map(s => s.trim()).filter(Boolean);
  $: previewConcepts = expectedConcepts.map(c => c.trim()).filter(Boolean);

  // Human-readable error title
  function errorTitle(code: string): string {
    if (code === 'VAULT_EXISTS') return 'Vault Already Exists';
    if (code === 'PATH_TRAVERSAL') return 'Security Violation';
    if (code === 'INVALID_INPUT' || code === 'VALIDATION_ERROR') return 'Invalid Input';
    if (code === 'NETWORK_ERROR') return 'Backend Unavailable';
    if (code === 'BOOTSTRAP_FAILED') return 'Bootstrap Failed';
    if (code === 'CONFIG_UPDATE_FAILED') return 'Config Update Failed';
    return 'Error';
  }
</script>

<!-- =========================================================
     Page header
     ========================================================= -->
<div class="mb-6">
  <h1 class="text-xl font-semibold text-zinc-100">Vault Setup</h1>
  <p class="text-sm text-zinc-500 mt-0.5">
    Guided vault bootstrap — define your domain, schema, and generate starter files.
  </p>
</div>

<!-- =========================================================
     Success panel (replaces form after successful creation)
     ========================================================= -->
{#if submitState === 'success' && successData}
  <div class="bg-emerald-950 border border-emerald-800 rounded-lg p-5 mb-6">
    <div class="flex items-start gap-3">
      <div class="w-8 h-8 bg-emerald-900 border border-emerald-700 rounded-full flex items-center justify-center shrink-0 mt-0.5">
        <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <h2 class="text-sm font-semibold text-emerald-300">Vault Created</h2>
        <p class="text-sm text-emerald-200 mt-0.5">
          <span class="font-mono font-medium">{successData.vault}</span> was successfully bootstrapped.
        </p>

        {#if successData.created.length > 0}
          <div class="mt-3">
            <p class="text-xs font-medium text-emerald-400 mb-1.5">Files created:</p>
            <ul class="space-y-1">
              {#each successData.created as path}
                <li class="text-xs font-mono text-emerald-300 bg-emerald-900/50 px-2 py-1 rounded">{path}</li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if successData.expected_concepts && successData.expected_concepts.written > 0}
          <div class="mt-3 bg-sky-950/40 border border-sky-800/60 rounded p-3">
            <p class="text-xs text-sky-300">
              <strong>{successData.expected_concepts.written}</strong> expected concept{successData.expected_concepts.written === 1 ? '' : 's'} written into
              <span class="font-mono">EXPECTED_CONCEPTS</span> in <span class="font-mono">vault_schema.py</span>.
              <strong>Missing Concepts</strong> is ready to use.
            </p>
          </div>
        {/if}

        {#if successData.warnings.length > 0}
          <div class="mt-3 bg-amber-950/60 border border-amber-800 rounded p-3">
            <p class="text-xs font-medium text-amber-400 mb-1.5">Backend warnings:</p>
            <ul class="space-y-1">
              {#each successData.warnings as warning}
                <li class="text-xs text-amber-300">{warning}</li>
              {/each}
            </ul>
          </div>
        {/if}

        <p class="text-xs text-emerald-600 mt-3">
          The Dashboard vault list will update on next visit or refresh.
        </p>

        <div class="mt-4 flex flex-wrap gap-3">
          <a
            href="/app/"
            class="inline-flex items-center gap-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-200 hover:text-zinc-100 px-3 py-1.5 rounded transition-colors"
          >
            Go to Dashboard
          </a>
          <button
            on:click={resetForm}
            class="text-sm text-emerald-400 hover:text-emerald-300 px-3 py-1.5 transition-colors"
          >
            Create another vault
          </button>
        </div>

        <details class="mt-4">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">
            Raw response
          </summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(successData, null, 2)}</pre>
        </details>
      </div>
    </div>
  </div>

{:else}
  <!-- =======================================================
       Two-column form layout
       ======================================================= -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">

    <!-- ── Left column: form fields ─────────────────────────── -->
    <div class="space-y-4">

      <!-- vault_name -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <label for="vault-name" class="block text-sm font-medium text-zinc-200 mb-1">
          Vault Name <span class="text-red-400">*</span>
        </label>
        <p class="text-xs text-zinc-500 mb-2">
          Directory name for the vault. Letters, numbers, underscores, and hyphens only — no spaces or slashes.
        </p>
        <input
          id="vault-name"
          type="text"
          bind:value={vaultName}
          placeholder="e.g. dogs-vault"
          autocomplete="off"
          spellcheck="false"
          class="w-full bg-zinc-950 border {vaultName && vaultNameError ? 'border-red-600 focus:ring-red-500' : 'border-zinc-700 focus:ring-sky-500'} text-zinc-100 text-sm rounded px-3 py-2 focus:outline-none focus:ring-1 font-mono placeholder:text-zinc-700 placeholder:font-sans"
        />
        {#if vaultName && vaultNameError}
          <p class="text-xs text-red-400 mt-1.5">{vaultNameError}</p>
        {:else if vaultName && !vaultNameError}
          <p class="text-xs text-emerald-600 mt-1.5">Looks good.</p>
        {/if}
      </div>

      <!-- domain -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <label for="domain" class="block text-sm font-medium text-zinc-200 mb-1">
          Domain <span class="text-red-400">*</span>
        </label>
        <p class="text-xs text-zinc-500 mb-2">
          Human-readable domain label (e.g. "Dogs", "Software Engineering").
        </p>
        <input
          id="domain"
          type="text"
          bind:value={domain}
          placeholder="e.g. Dogs"
          autocomplete="off"
          class="w-full bg-zinc-950 border {domain && domainError ? 'border-red-600 focus:ring-red-500' : 'border-zinc-700 focus:ring-sky-500'} text-zinc-100 text-sm rounded px-3 py-2 focus:outline-none focus:ring-1 placeholder:text-zinc-700"
        />
        {#if domain && domainError}
          <p class="text-xs text-red-400 mt-1.5">{domainError}</p>
        {:else if domain.trim() && !domainError}
          <p class="text-xs text-emerald-600 mt-1.5">Looks good.</p>
        {/if}
      </div>

      <!-- note_type -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <label for="note-type" class="block text-sm font-medium text-zinc-200 mb-1">
          Note Type <span class="text-red-400">*</span>
        </label>
        <p class="text-xs text-zinc-500 mb-2">
          Slug for the primary note type in this vault.
        </p>
        <input
          id="note-type"
          type="text"
          bind:value={noteType}
          placeholder="e.g. breed-profile"
          autocomplete="off"
          spellcheck="false"
          class="w-full bg-zinc-950 border {noteType && noteTypeError ? 'border-red-600 focus:ring-red-500' : 'border-zinc-700 focus:ring-sky-500'} text-zinc-100 text-sm rounded px-3 py-2 focus:outline-none focus:ring-1 font-mono placeholder:text-zinc-700 placeholder:font-sans"
        />
        {#if noteType && noteTypeError}
          <p class="text-xs text-red-400 mt-1.5">{noteTypeError}</p>
        {:else}
          <p class="text-xs text-zinc-600 mt-1.5">
            Examples: <span class="font-mono">breed-profile</span>,
            <span class="font-mono">core-concept</span>,
            <span class="font-mono">incident-review</span>
          </p>
        {/if}
      </div>

      <!-- sections -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div class="flex items-center justify-between mb-1">
          <label class="block text-sm font-medium text-zinc-200">
            Required Sections <span class="text-red-400">*</span>
          </label>
          <span class="text-xs text-zinc-500">{sections.length} section{sections.length === 1 ? '' : 's'}</span>
        </div>
        <p class="text-xs text-zinc-500 mb-3">
          Canonical section headings for notes in this vault. Minimum 2. Drag-to-reorder not required.
        </p>

        {#if sections.length > 0}
          <ul class="space-y-1.5 mb-3">
            {#each sections as section, i}
              <li class="flex items-center gap-2 bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5">
                <span class="flex-1 text-sm text-zinc-200 truncate">{section}</span>
                <button
                  type="button"
                  on:click={() => removeSection(i)}
                  class="text-zinc-600 hover:text-red-400 transition-colors shrink-0 p-0.5 rounded"
                  title="Remove section"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            {/each}
          </ul>
        {/if}

        <div class="flex gap-2">
          <input
            type="text"
            bind:value={newSection}
            on:keydown={onSectionKeydown}
            placeholder="Add a section…"
            class="flex-1 bg-zinc-950 border border-zinc-700 text-zinc-100 text-sm rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder:text-zinc-700"
          />
          <button
            type="button"
            on:click={addSection}
            class="bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-zinc-100 text-sm px-3 py-1.5 rounded transition-colors shrink-0"
          >
            Add
          </button>
        </div>

        {#if sectionsError}
          <p class="text-xs text-red-400 mt-2">{sectionsError}</p>
        {/if}
      </div>

      <!-- expected_concepts -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div class="flex items-center justify-between mb-1">
          <label class="block text-sm font-medium text-zinc-200">
            Expected Concepts
            <span class="ml-1.5 text-xs font-normal text-zinc-500">optional</span>
          </label>
          {#if expectedConcepts.length > 0}
            <span class="text-xs text-zinc-500">{expectedConcepts.length} concept{expectedConcepts.length === 1 ? '' : 's'}</span>
          {/if}
        </div>
        <p class="text-xs text-zinc-500 mb-2">
          Named concepts expected in this vault's knowledge base. Each concept will be written
          into <span class="font-mono">EXPECTED_CONCEPTS</span> in <span class="font-mono">vault_schema.py</span>
          so that <strong>Missing Concepts</strong> works immediately after bootstrap.
          One concept per line, or add them one at a time.
        </p>

        {#if expectedConcepts.length > 0}
          <ul class="space-y-1.5 mb-3">
            {#each expectedConcepts as concept, i}
              <li class="flex items-center gap-2 bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5">
                <span class="flex-1 text-sm text-zinc-200 truncate">{concept}</span>
                <button
                  type="button"
                  on:click={() => removeConcept(i)}
                  class="text-zinc-600 hover:text-red-400 transition-colors shrink-0 p-0.5 rounded"
                  title="Remove concept"
                >
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </li>
            {/each}
          </ul>
        {/if}

        <div class="flex gap-2">
          <input
            type="text"
            bind:value={newConcept}
            on:keydown={onConceptKeydown}
            placeholder="Add a concept…"
            class="flex-1 bg-zinc-950 border border-zinc-700 text-zinc-100 text-sm rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder:text-zinc-700"
          />
          <button
            type="button"
            on:click={addConcept}
            class="bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-zinc-100 text-sm px-3 py-1.5 rounded transition-colors shrink-0"
          >
            Add
          </button>
        </div>

        {#if conceptsDupeError}
          <p class="text-xs text-red-400 mt-2">{conceptsDupeError}</p>
        {/if}
      </div>

    </div><!-- end left column -->

    <!-- ── Right column: validation + preview + submit ────────── -->
    <div class="space-y-4">

      <!-- Live validation panel -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-3">Validation</h3>
        <ul class="space-y-2">
          {#each [
            { label: 'Vault name', ok: !vaultNameError, pending: vaultName === '' },
            { label: 'Domain', ok: !domainError, pending: domain.trim() === '' },
            { label: 'Note type', ok: !noteTypeError, pending: noteType === '' },
            { label: 'Sections (min 2)', ok: !sectionsError, pending: sections.length < 2 },
            { label: 'Concepts (optional)', ok: !conceptsDupeError, pending: false },
          ] as check}
            <li class="flex items-center gap-2 text-sm">
              {#if check.pending && check.label !== 'Concepts (optional)'}
                <span class="w-4 h-4 flex items-center justify-center shrink-0">
                  <span class="w-2 h-2 rounded-full bg-zinc-700"></span>
                </span>
                <span class="text-zinc-500">{check.label}</span>
              {:else if check.ok}
                <svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
                </svg>
                <span class="text-zinc-300">{check.label}</span>
              {:else}
                <svg class="w-4 h-4 text-red-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
                </svg>
                <span class="text-red-400">{check.label}</span>
              {/if}
            </li>
          {/each}
        </ul>

        {#if formValid}
          <div class="mt-3 pt-3 border-t border-zinc-800 flex items-center gap-2">
            <span class="inline-flex items-center gap-1.5 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Ready to create
            </span>
          </div>
        {/if}
      </div>

      <!-- Preview panel -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h3 class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-3">Preview</h3>

        <div class="space-y-2.5 text-sm">
          <div class="flex gap-3">
            <span class="text-zinc-500 w-28 shrink-0">Vault dir</span>
            <span class="font-mono text-zinc-200 break-all">{previewName}/</span>
          </div>
          <div class="flex gap-3">
            <span class="text-zinc-500 w-28 shrink-0">Domain</span>
            <span class="text-zinc-200">{domain.trim() || '—'}</span>
          </div>
          <div class="flex gap-3">
            <span class="text-zinc-500 w-28 shrink-0">Note type</span>
            <span class="font-mono text-zinc-200">{previewNoteType}</span>
          </div>
          {#if previewSections.length > 0}
            <div class="flex gap-3">
              <span class="text-zinc-500 w-28 shrink-0 pt-0.5">Sections</span>
              <ul class="space-y-0.5 min-w-0">
                {#each previewSections as s}
                  <li class="text-zinc-200">{s}</li>
                {/each}
              </ul>
            </div>
          {/if}
          {#if previewConcepts.length > 0}
            <div class="flex gap-3">
              <span class="text-zinc-500 w-28 shrink-0 pt-0.5">Concepts</span>
              <ul class="space-y-0.5 min-w-0">
                {#each previewConcepts as c}
                  <li class="text-zinc-200">{c}</li>
                {/each}
              </ul>
            </div>
          {/if}
        </div>

        <!-- File tree preview -->
        <div class="mt-4 pt-4 border-t border-zinc-800">
          <p class="text-xs text-zinc-500 mb-2">Files that will be created:</p>
          <div class="font-mono text-xs space-y-0.5 select-none">
            <div class="text-zinc-300">{previewName}/</div>
            <div class="pl-4 text-zinc-500">Vault Files/</div>
            <div class="pl-8 text-zinc-500">Scripts/</div>
            <div class="pl-12 text-sky-400">vault_schema.py</div>
            <div class="pl-8 text-zinc-500">Templates/</div>
            <div class="pl-12 text-sky-400">{previewNoteType}.md</div>
            <div class="mt-1 text-zinc-600">config/config.yaml  ← updated</div>
          </div>
        </div>
      </div>

      <!-- Error panel -->
      {#if submitState === 'error'}
        <div class="bg-red-950 border border-red-800 rounded-lg p-4">
          <div class="flex items-start gap-2.5">
            <svg class="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div class="min-w-0">
              <p class="text-sm font-medium text-red-300">{errorTitle(errorCode)}</p>
              <p class="text-sm text-red-200 mt-0.5 break-words">{errorMsg}</p>
              {#if errorCode === 'NETWORK_ERROR'}
                <p class="text-xs text-red-400 mt-1.5">
                  Is the server running?
                  <span class="font-mono">py mcp/server/mcp_server.py</span>
                </p>
              {/if}
              <p class="text-xs font-mono text-red-700 mt-1.5">{errorCode}</p>
            </div>
          </div>
        </div>
      {/if}

      <!-- Submit button -->
      <button
        type="button"
        on:click={handleSubmit}
        disabled={!canSubmit}
        class="w-full flex items-center justify-center gap-2 bg-sky-600 hover:bg-sky-500 disabled:bg-zinc-800 disabled:text-zinc-600 disabled:cursor-not-allowed text-white disabled:border disabled:border-zinc-700 text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
      >
        {#if submitState === 'loading'}
          <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
          </svg>
          Creating vault…
        {:else}
          Create Vault
        {/if}
      </button>

      {#if !formValid && submitState === 'idle'}
        <p class="text-xs text-zinc-600 text-center">
          Fill in all required fields above to enable the Create button.
        </p>
      {/if}

    </div><!-- end right column -->

  </div><!-- end grid -->
{/if}
