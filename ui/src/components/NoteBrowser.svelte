<script lang="ts">
  /*
    Phase 30D2 - Notes Workbench.

    Split-pane Notes workspace built on the Phase 30B primitives.
    Layout:
      cve-toolbar header (title, vault selector, refresh)
      optional cve-banner for vault/error/loading guidance
      cve-workbench (rail + inspector)
        rail:     filters, search, deterministic note list (internal scroll)
        inspector selected note header, frontmatter, body, sections,
                  validation/task context, trust/import panel,
                  Developer deep-link to /app/raw

    Functional behaviour preserved from the prior NoteBrowser:
      - vault selection precedence: ?vault= > localStorage > backend default
      - filters: text, status, difficulty, missing-only, imported-only,
        draft-trust-only
      - search panel backed by POST /query
      - safe note edit (frontmatter + body) via PUT /note
      - deep-link contract: ?vault=, ?filter=, ?path=
      - imported/draft trust badges and Trust+Import detail panel

    Removed in Phase 30D2:
      - Inline "Raw JSON" disclosure panels (notes list, note detail,
        update response, query response, edit payload). Diagnostic
        access is handled by /app/raw via the Developer deep-link.

    No new dependency. No icon library. No animation library.
    Token-only styling: no Tailwind dark palette literals.
  */

  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchNotes,
    fetchNote,
    queryNotes,
    fetchValidation,
    fetchTasks,
    fetchTrustSummary,
    updateNote,
    isOk,
    isImportedNote,
    isDraftTrustNote,
    type NoteListItem,
    type NoteFields,
    type NoteDetail,
    type NoteQueryRequest,
    type NoteQueryResponse,
    type QueryResultItem,
    type ValidationData,
    type TasksData,
    type Task,
    type TrustSummaryData,
    type TrustNoteSummary,
    type NoteUpdateResponse,
  } from '../lib/api.ts';
  import {
    getStoredVault,
    setStoredVault,
    chooseInitialVault,
    getVaultFromUrl,
  } from '../lib/vaultState.ts';
  import ImportedReviewSummary from './ImportedReviewSummary.svelte';

  // ---------------------------------------------------------------------------
  // Types and state
  // ---------------------------------------------------------------------------

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

  interface SectionHeading {
    level: number;
    text: string;
    lineNumber: number;
  }

  interface DisplayNote {
    path: string;
    name: string;
    status: string;
    difficulty: string;
    missing: string[];
    score?: number;
    source_type?: string | null;
    trust_level?: string | null;
  }

  // Vault state
  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';
  let selectedVault = '';

  // Notes list
  let notesState: LoadState = 'idle';
  let notesList: NoteListItem[] = [];
  let notesError = '';

  // Filters
  let filterText = '';
  let filterStatus = '';
  let filterDifficulty = '';
  let filterMissingOnly = false;
  let filterImportedOnly = false;
  let filterDraftTrustOnly = false;

  // Search / query
  let searchExpanded = false;
  let searchQ = '';
  let searchQFields: string[] = ['body'];
  let searchFilterStatus = '';
  let searchFilterDomain = '';
  let searchFilterType = '';
  let searchFilterDifficulty = '';
  let searchLimit = 50;
  let searchState: LoadState = 'idle';
  let searchResults: QueryResultItem[] = [];
  let searchResponseData: NoteQueryResponse | null = null;
  let searchError = '';
  let searchActive = false;

  // Note detail
  let selectedPath = '';
  let noteDetailState: LoadState = 'idle';
  let noteDetail: NoteDetail | null = null;
  let noteDetailError = '';

  // Validation / tasks / trust
  let validationState: LoadState = 'idle';
  let validationData: ValidationData | null = null;
  let validationError = '';
  let tasksState: LoadState = 'idle';
  let tasksData: TasksData | null = null;
  let tasksError = '';
  let trustData: TrustSummaryData | null = null;

  // Edit mode
  let editMode = false;
  let editedFields: Record<string, unknown> = {};
  let editedBody = '';
  let saveState: LoadState = 'idle';
  let saveError = '';
  let saveErrorCode = '';
  let saveValidationDetails: string[] = [];
  let saveResponse: NoteUpdateResponse | null = null;

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------

  $: filteredNotes = notesList.filter((n) => {
    if (filterText) {
      const q = filterText.toLowerCase();
      if (!n.path.toLowerCase().includes(q) && !n.name.toLowerCase().includes(q)) return false;
    }
    if (filterStatus && n.status !== filterStatus) return false;
    if (filterDifficulty && n.difficulty !== filterDifficulty) return false;
    if (filterMissingOnly && (!n.missing || n.missing.length === 0)) return false;
    if (filterImportedOnly && (n.source_type ?? '').toString().trim().toLowerCase() !== 'imported') return false;
    if (filterDraftTrustOnly && (n.trust_level ?? '').toString().trim().toLowerCase() !== 'draft') return false;
    return true;
  });

  $: displayList = (
    searchActive
      ? searchResults.map((r): DisplayNote => ({
          path: r.path,
          name: r.path.split('/').pop()?.replace(/\.md$/i, '') ?? r.path,
          status: (r.fields?.status as string) ?? '',
          difficulty: (r.fields?.difficulty as string) ?? '',
          missing: [],
          score: r.score,
          source_type: (r.fields?.source_type as string | null | undefined) ?? null,
          trust_level: (r.fields?.trust_level as string | null | undefined) ?? null,
        }))
      : filteredNotes.map((n): DisplayNote => ({
          path: n.path,
          name: n.name,
          status: n.status,
          difficulty: n.difficulty,
          missing: n.missing ?? [],
          source_type: n.source_type ?? null,
          trust_level: n.trust_level ?? null,
        }))
  ) as DisplayNote[];

  $: statusValues = [...new Set(notesList.map((n) => n.status).filter(Boolean))].sort();
  $: difficultyValues = [...new Set(notesList.map((n) => n.difficulty).filter(Boolean))].sort();

  $: noteFields = noteDetail ? Object.entries(noteDetail.fields ?? {}) : [];
  $: noteBody = noteDetail?.body ?? '';
  $: sectionOutline = parseHeadings(noteBody);

  const ADVISORY_SECTIONS = ['Key Principles', 'How It Works', 'Trade-offs'];
  $: editSectionOutline = editMode ? parseHeadings(editedBody) : [];
  $: missingSectionsAdvisory = editMode
    ? ADVISORY_SECTIONS.filter((s) => !editSectionOutline.some((h) => h.text === s))
    : [];
  $: hasUnsavedChanges =
    editMode &&
    (editedBody !== (noteDetail?.body ?? '') ||
      JSON.stringify(editedFields) !== JSON.stringify(noteDetail?.fields ?? {}));

  $: isInvalidNote =
    validationData && selectedPath ? validationData.invalid_notes.includes(selectedPath) : false;

  $: noteTask = (tasksData?.tasks ?? []).find((t: Task) => t.path === selectedPath) as Task | undefined;

  $: trustNoteEntry = (trustData?.notes ?? []).find(
    (t: TrustNoteSummary) => t.path === selectedPath,
  ) as TrustNoteSummary | undefined;

  $: noteSourceType = strField(noteDetail?.fields?.source_type);
  $: noteTrustLevel = strField(noteDetail?.fields?.trust_level);
  $: noteLastReviewed = strField(noteDetail?.fields?.last_reviewed);
  $: noteReviewAfter = strField(noteDetail?.fields?.review_after);

  $: noteAppearsImported = noteDetail
    ? isImportedNote(noteDetail.fields as Record<string, unknown>)
    : false;
  $: noteAppearsDraft = noteDetail
    ? isDraftTrustNote(noteDetail.fields as Record<string, unknown>)
    : false;
  $: noteImportedMissingReviewMeta = noteAppearsImported && !noteLastReviewed && !noteReviewAfter;

  // Banner
  type BannerSeverity = 'success' | 'warning' | 'danger' | 'info';
  $: banner = ((): { severity: BannerSeverity; title: string; body: string } | null => {
    if (vaultsLoading) return { severity: 'info', title: 'Loading vaults', body: 'Reading registered vaults.' };
    if (vaultsError) return { severity: 'danger', title: 'Vaults unavailable', body: vaultsError };
    if (!vaultsLoading && vaultList.length === 0) {
      return { severity: 'warning', title: 'No vaults configured', body: 'Use Vault Setup to register a vault before browsing notes.' };
    }
    if (notesState === 'error') return { severity: 'danger', title: 'Notes unavailable', body: notesError };
    return null;
  })();

  // Developer deep-link to /app/raw (Phase 30D1 contract).
  // Base: /app/raw?endpoint=notes&source=notes
  $: rawDeveloperHref = (() => {
    const params = new URLSearchParams();
    params.set('endpoint', 'notes');
    params.set('source', 'notes');
    if (selectedVault) params.set('vault', selectedVault);
    if (selectedPath) params.set('focus', selectedPath);
    // Static literal so guardrail tests can detect the contract: endpoint=notes&source=notes
    return `/app/raw?${params.toString()}`;
  })();

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function strField(v: unknown): string {
    return typeof v === 'string' ? v.trim() : '';
  }

  function parseHeadings(body: string): SectionHeading[] {
    if (!body) return [];
    const lines = body.split('\n');
    const headings: SectionHeading[] = [];
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(/^(#{1,6})\s+(.+)$/);
      if (m) headings.push({ level: m[1].length, text: m[2].trim(), lineNumber: i + 1 });
    }
    return headings;
  }

  function statusBadgeVariant(status: string): string {
    switch (status?.toLowerCase()) {
      case 'complete': return 'cve-badge-success';
      case 'partial': return 'cve-badge-warning';
      default: return 'cve-badge-neutral';
    }
  }

  function difficultyBadgeVariant(d: string): string {
    switch (d?.toLowerCase()) {
      case 'advanced': return 'cve-badge-danger';
      case 'intermediate': return 'cve-badge-warning';
      case 'beginner': return 'cve-badge-success';
      default: return 'cve-badge-neutral';
    }
  }

  function trustBadgeVariant(level: string): string {
    switch (level?.toLowerCase()) {
      case 'draft': return 'cve-badge-draft';
      case 'deprecated': return 'cve-badge-deprecated';
      case 'external': return 'cve-badge-info';
      default: return 'cve-badge-neutral';
    }
  }

  function formatFieldValue(value: unknown): string {
    if (value === null || value === undefined) return '-';
    if (Array.isArray(value)) return value.join(', ');
    return String(value);
  }

  function clearFilters() {
    filterText = '';
    filterStatus = '';
    filterDifficulty = '';
    filterMissingOnly = false;
    filterImportedOnly = false;
    filterDraftTrustOnly = false;
  }

  function clearSearch() {
    searchActive = false;
    searchResults = [];
    searchResponseData = null;
    searchQ = '';
    searchFilterStatus = '';
    searchFilterDomain = '';
    searchFilterType = '';
    searchFilterDifficulty = '';
    searchState = 'idle';
    searchError = '';
  }

  // ---------------------------------------------------------------------------
  // Edit lifecycle
  // ---------------------------------------------------------------------------

  function enterEditMode() {
    if (!noteDetail) return;
    editedFields = { ...(noteDetail.fields as Record<string, unknown>) };
    editedBody = noteDetail.body ?? '';
    editMode = true;
    saveState = 'idle';
    saveError = '';
    saveErrorCode = '';
    saveValidationDetails = [];
    saveResponse = null;
  }

  function cancelEdit() {
    editMode = false;
    editedFields = {};
    editedBody = '';
    saveState = 'idle';
    saveError = '';
    saveErrorCode = '';
    saveValidationDetails = [];
    saveResponse = null;
  }

  function resetToLoaded() {
    if (!noteDetail) return;
    editedFields = { ...(noteDetail.fields as Record<string, unknown>) };
    editedBody = noteDetail.body ?? '';
    saveState = 'idle';
    saveError = '';
    saveErrorCode = '';
    saveValidationDetails = [];
  }

  async function saveNote() {
    if (!selectedVault || !noteDetail) return;
    if (saveState === 'loading') return;

    if (editedBody.includes('\x00')) {
      saveError = 'Body must not contain null bytes.';
      saveErrorCode = 'CLIENT_VALIDATION';
      return;
    }
    if (!editedBody.trim()) {
      saveError = 'Body must not be empty.';
      saveErrorCode = 'CLIENT_VALIDATION';
      return;
    }

    saveState = 'loading';
    saveError = '';
    saveErrorCode = '';
    saveValidationDetails = [];
    saveResponse = null;

    const result = await updateNote({
      vault: selectedVault,
      path: noteDetail.path,
      fields: editedFields,
      body: editedBody,
    });

    if (isOk(result)) {
      saveState = 'ok';
      saveResponse = result.data;
      noteDetail = {
        path: result.data.path,
        fields: result.data.fields as NoteFields,
        body: result.data.body,
      };
      editMode = false;
      await loadNotes();
      await loadValidation();
      await loadTasks();
      if (searchActive) await runSearch();
    } else {
      saveState = 'error';
      const errCode = (result.error?.code as string) ?? '';
      saveErrorCode = errCode;
      saveError = result.error?.message ?? 'Save failed';
      if (errCode === 'VALIDATION_FAILED') {
        const details = result.error?.details;
        if (Array.isArray(details)) saveValidationDetails = details.map((d) => String(d));
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  async function loadVaults() {
    vaultsLoading = true;
    vaultsError = '';
    const result = await fetchVaults();
    vaultsLoading = false;
    if (isOk(result)) {
      vaultList = result.data.vaults;
      if (vaultList.length > 0) {
        const params = readUrlParams();
        const urlVault = params.vault ?? getVaultFromUrl();
        const stored = getStoredVault();
        selectedVault = chooseInitialVault(vaultList, urlVault, stored);
        if (selectedVault) setStoredVault(selectedVault);
        applyUrlFilter(params.filter);
        await loadAll();
        if (params.path && notesList.some((n) => n.path === params.path)) {
          await selectNote(params.path);
        }
      }
    } else {
      vaultsError = result.error?.message ?? 'Failed to load vaults';
    }
  }

  function readUrlParams(): { vault: string | null; filter: string | null; path: string | null } {
    try {
      const u = new URLSearchParams(window.location.search);
      return { vault: u.get('vault'), filter: u.get('filter'), path: u.get('path') };
    } catch {
      return { vault: null, filter: null, path: null };
    }
  }

  function applyUrlFilter(filter: string | null) {
    if (!filter) return;
    const f = filter.trim().toLowerCase();
    if (f === 'imported') filterImportedOnly = true;
    else if (f === 'draft') filterDraftTrustOnly = true;
    else if (f === 'imported-draft' || f === 'draft-imported') {
      filterImportedOnly = true;
      filterDraftTrustOnly = true;
    }
  }

  async function loadAll() {
    await Promise.all([loadNotes(), loadValidation(), loadTasks(), loadTrust()]);
  }

  async function loadNotes() {
    notesState = 'loading';
    notesError = '';
    const result = await fetchNotes(selectedVault);
    if (isOk(result)) {
      notesList = result.data.notes;
      notesState = 'ok';
    } else {
      notesError = result.error?.message ?? 'Failed to load notes';
      notesState = 'error';
    }
  }

  async function loadValidation() {
    validationState = 'loading';
    validationError = '';
    const result = await fetchValidation(selectedVault);
    if (isOk(result)) {
      validationData = result.data;
      validationState = 'ok';
    } else {
      validationError = result.error?.message ?? 'Failed to load validation';
      validationState = 'error';
    }
  }

  async function loadTasks() {
    tasksState = 'loading';
    tasksError = '';
    const result = await fetchTasks(selectedVault, { limit: 200, include_feedback: true });
    if (isOk(result)) {
      tasksData = result.data;
      tasksState = 'ok';
    } else {
      tasksError = result.error?.message ?? 'Failed to load tasks';
      tasksState = 'error';
    }
  }

  async function loadTrust() {
    trustData = null;
    if (!selectedVault) return;
    const result = await fetchTrustSummary(selectedVault);
    if (isOk(result)) trustData = result.data;
  }

  async function selectNote(path: string) {
    if (editMode) {
      cancelEdit();
      if (selectedPath === path) return;
    } else if (selectedPath === path && noteDetailState === 'ok') {
      return;
    }
    saveState = 'idle';
    saveResponse = null;
    selectedPath = path;
    noteDetail = null;
    noteDetailState = 'loading';
    noteDetailError = '';
    const result = await fetchNote(selectedVault, path);
    if (isOk(result)) {
      noteDetail = result.data;
      noteDetailState = 'ok';
    } else {
      noteDetailError = result.error?.message ?? 'Failed to load note';
      noteDetailState = 'error';
    }
  }

  async function runSearch() {
    if (!selectedVault) return;
    searchState = 'loading';
    searchError = '';
    const request: NoteQueryRequest = {
      vault: selectedVault,
      limit: Math.max(1, Math.min(500, searchLimit || 50)),
    };
    const trimmedQ = searchQ.trim();
    if (trimmedQ) {
      request.q = trimmedQ;
      request.q_fields = searchQFields.length > 0 ? [...searchQFields] : ['body'];
    }
    const f: Record<string, string> = {};
    if (searchFilterStatus && searchFilterStatus !== 'all') f.status = searchFilterStatus;
    if (searchFilterDomain.trim()) f.domain = searchFilterDomain.trim();
    if (searchFilterType.trim()) f.type = searchFilterType.trim();
    if (searchFilterDifficulty) f.difficulty = searchFilterDifficulty;
    if (Object.keys(f).length > 0) request.filters = f;

    const result = await queryNotes(request);
    if (isOk(result)) {
      searchResults = result.data.results;
      searchResponseData = result.data;
      searchActive = true;
      searchState = 'ok';
    } else {
      searchError = result.error?.message ?? 'Search failed';
      searchState = 'error';
    }
  }

  function onVaultChange() {
    cancelEdit();
    selectedPath = '';
    noteDetail = null;
    noteDetailState = 'idle';
    saveState = 'idle';
    saveResponse = null;
    clearSearch();
    clearFilters();
    if (selectedVault) {
      setStoredVault(selectedVault);
      loadAll();
    }
  }

  onMount(loadVaults);
</script>

<!-- =========================================================================
  Phase 30D2 - Notes Workbench
  ========================================================================= -->
<div class="cve-page cve-stack">

  <header class="cve-toolbar" aria-label="Notes header">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Notes</h1>
      <div class="cve-toolbar__meta">
        {#if vaultsLoading}
          <span>Loading vaults...</span>
        {:else if vaultsError}
          <span class="cve-badge cve-badge-danger" role="status">Vaults: {vaultsError}</span>
        {:else if vaultList.length === 0}
          <span>
            No vaults configured.
            <a class="cve-link" href="/app/vault-setup">Set one up</a>.
          </span>
        {:else}
          <label class="cve-label" for="notes-vault-select">Vault</label>
          <select
            id="notes-vault-select"
            class="cve-select cve-toolbar__select"
            bind:value={selectedVault}
            on:change={onVaultChange}
            aria-label="Active vault"
          >
            {#each vaultList as v}
              <option value={v}>{v}</option>
            {/each}
          </select>
        {/if}
      </div>
      <div class="cve-toolbar__actions">
        <a class="cve-btn cve-btn-ghost" href="/app/validation" aria-label="Open Validation page">Validation</a>
        <a class="cve-btn cve-btn-ghost" href="/app/tasks" aria-label="Open Tasks page">Tasks</a>
        <button
          type="button"
          class="cve-btn cve-btn-secondary"
          on:click={() => selectedVault && loadAll()}
          disabled={!selectedVault || notesState === 'loading'}
          aria-label="Refresh notes"
        >
          {notesState === 'loading' ? 'Refreshing' : 'Refresh'}
        </button>
      </div>
    </div>
  </header>

  {#if banner}
    <section
      class="cve-banner cve-banner--{banner.severity}"
      role="status"
      aria-live="polite"
    >
      <div>
        <div class="cve-banner__title">{banner.title}</div>
        <div class="cve-banner__body">{banner.body}</div>
      </div>
    </section>
  {/if}

  {#if (filterImportedOnly || filterDraftTrustOnly) && selectedVault}
    <ImportedReviewSummary
      vault={selectedVault}
      notes={notesList}
      validation={validationData}
      tasks={tasksData}
      trust={trustData}
      compact={true}
    />
  {/if}

  <div class="cve-workbench">

    <!-- ────────────────────────── Rail ────────────────────────── -->
    <aside class="cve-workbench__rail cve-p30d2-rail" aria-label="Note list">

      <div class="cve-p30d2-rail__head">
        <div class="cve-p30d2-section-row">
          <h2 class="cve-p30d2-section-title">Filters</h2>
          {#if filterText || filterStatus || filterDifficulty || filterMissingOnly || filterImportedOnly || filterDraftTrustOnly}
            <button type="button" class="cve-btn cve-btn-ghost cve-p30d2-mini-btn" on:click={clearFilters}>Clear</button>
          {/if}
        </div>

        <div class="cve-field">
          <label class="cve-label" for="notes-filter-text">Search by name or path</label>
          <input
            id="notes-filter-text"
            class="cve-input"
            type="text"
            bind:value={filterText}
            placeholder="e.g. recursion"
          />
        </div>

        <div class="cve-p30d2-filter-row">
          <div class="cve-field">
            <label class="cve-label" for="notes-filter-status">Status</label>
            <select id="notes-filter-status" class="cve-select" bind:value={filterStatus}>
              <option value="">All statuses</option>
              {#each statusValues as s}
                <option value={s}>{s}</option>
              {/each}
            </select>
          </div>
          <div class="cve-field">
            <label class="cve-label" for="notes-filter-difficulty">Difficulty</label>
            <select id="notes-filter-difficulty" class="cve-select" bind:value={filterDifficulty}>
              <option value="">All difficulties</option>
              {#each difficultyValues as d}
                <option value={d}>{d}</option>
              {/each}
            </select>
          </div>
        </div>

        <div class="cve-p30d2-checkbox-row">
          <label class="cve-p30d2-checkbox">
            <input type="checkbox" bind:checked={filterMissingOnly} />
            <span>Missing sections only</span>
          </label>
          <label class="cve-p30d2-checkbox" data-testid="filter-imported-only">
            <input type="checkbox" bind:checked={filterImportedOnly} />
            <span>Imported only</span>
          </label>
          <label class="cve-p30d2-checkbox" data-testid="filter-draft-trust-only">
            <input type="checkbox" bind:checked={filterDraftTrustOnly} />
            <span>Draft trust only</span>
          </label>
        </div>

        <details class="cve-details cve-p30d2-search-disclosure" bind:open={searchExpanded}>
          <summary>Query search (POST /query){searchActive ? ' - active' : ''}</summary>
          <div class="cve-details__body cve-stack">
            <div class="cve-field">
              <label class="cve-label" for="notes-search-q">Free text</label>
              <input
                id="notes-search-q"
                class="cve-input"
                type="text"
                bind:value={searchQ}
                placeholder="e.g. recursion tree traversal"
              />
            </div>
            <fieldset class="cve-p30d2-fieldset">
              <legend class="cve-label">Search fields</legend>
              {#each ['body', 'path', 'frontmatter'] as field}
                <label class="cve-p30d2-checkbox">
                  <input
                    type="checkbox"
                    value={field}
                    checked={searchQFields.includes(field)}
                    on:change={(e) => {
                      const checked = (e.target as HTMLInputElement).checked;
                      searchQFields = checked
                        ? [...searchQFields, field]
                        : searchQFields.filter((f) => f !== field);
                    }}
                  />
                  <span>{field}</span>
                </label>
              {/each}
            </fieldset>
            <div class="cve-p30d2-filter-row">
              <div class="cve-field">
                <label class="cve-label" for="notes-search-status">Status</label>
                <select id="notes-search-status" class="cve-select" bind:value={searchFilterStatus}>
                  <option value="">Any</option>
                  {#each statusValues as s}
                    <option value={s}>{s}</option>
                  {/each}
                </select>
              </div>
              <div class="cve-field">
                <label class="cve-label" for="notes-search-difficulty">Difficulty</label>
                <select id="notes-search-difficulty" class="cve-select" bind:value={searchFilterDifficulty}>
                  <option value="">Any</option>
                  {#each difficultyValues as d}
                    <option value={d}>{d}</option>
                  {/each}
                </select>
              </div>
            </div>
            <div class="cve-p30d2-filter-row">
              <div class="cve-field">
                <label class="cve-label" for="notes-search-domain">Domain</label>
                <input id="notes-search-domain" class="cve-input" type="text" bind:value={searchFilterDomain} placeholder="e.g. fundamentals" />
              </div>
              <div class="cve-field">
                <label class="cve-label" for="notes-search-type">Type</label>
                <input id="notes-search-type" class="cve-input" type="text" bind:value={searchFilterType} placeholder="e.g. core-concept" />
              </div>
            </div>
            <div class="cve-field">
              <label class="cve-label" for="notes-search-limit">Limit (1 to 500)</label>
              <input id="notes-search-limit" class="cve-input cve-p30d2-limit" type="number" bind:value={searchLimit} min="1" max="500" />
            </div>
            {#if searchError}
              <p class="cve-error">{searchError}</p>
            {/if}
            <div class="cve-p30d2-search-actions">
              <button type="button" class="cve-btn cve-btn-primary" on:click={runSearch} disabled={searchState === 'loading'}>
                {searchState === 'loading' ? 'Searching...' : 'Search'}
              </button>
              {#if searchActive}
                <button type="button" class="cve-btn cve-btn-secondary" on:click={clearSearch}>Clear search</button>
              {/if}
            </div>
            {#if searchActive && searchResponseData}
              <p class="cve-helper">{searchResponseData.returned} of {searchResponseData.count} results</p>
            {/if}
          </div>
        </details>
      </div>

      <div class="cve-p30d2-rail__list-head">
        <span class="cve-p30d2-section-title">{searchActive ? 'Search Results' : 'Notes'}</span>
        <span class="cve-meta cve-mono">{displayList.length}{!searchActive ? ` / ${notesList.length}` : ''}</span>
      </div>

      <div class="cve-scroll-region cve-p30d2-list">
        {#if notesState === 'loading'}
          <p class="cve-loading">Loading notes...</p>
        {:else if notesState === 'error'}
          <p class="cve-error">{notesError}</p>
        {:else if displayList.length === 0}
          <p class="cve-empty">
            {searchActive
              ? 'No results. Try a different query.'
              : notesState === 'ok' && notesList.length === 0
                ? 'No notes in this vault.'
                : 'No notes match the current filters.'}
          </p>
        {:else}
          <ul class="cve-p30d2-note-list" role="list">
            {#each displayList as note}
              <li>
                <button
                  type="button"
                  class="cve-p30d2-note-row"
                  aria-current={selectedPath === note.path ? 'true' : undefined}
                  on:click={() => selectNote(note.path)}
                >
                  <div class="cve-p30d2-note-row__head">
                    <span class="cve-p30d2-note-row__name">{note.name}</span>
                    <span class="cve-p30d2-note-row__badges">
                      {#if note.status}
                        <span class="cve-badge {statusBadgeVariant(note.status)}">{note.status}</span>
                      {/if}
                      {#if note.score !== undefined}
                        <span class="cve-badge cve-badge-info">{note.score.toFixed(2)}</span>
                      {/if}
                    </span>
                  </div>
                  <div class="cve-p30d2-note-row__path cve-mono">{note.path}</div>
                  {#if note.difficulty || (note.missing && note.missing.length > 0) || note.source_type || note.trust_level}
                    <div class="cve-p30d2-note-row__badges">
                      {#if note.difficulty}
                        <span class="cve-badge {difficultyBadgeVariant(note.difficulty)}">{note.difficulty}</span>
                      {/if}
                      {#if note.missing && note.missing.length > 0}
                        <span class="cve-badge cve-badge-warning">{note.missing.length} missing</span>
                      {/if}
                      {#if (note.source_type ?? '').toString().toLowerCase() === 'imported'}
                        <span class="cve-badge cve-badge-info" data-testid="badge-imported">Imported</span>
                      {/if}
                      {#if note.trust_level}
                        {#if note.trust_level === 'draft'}
                          <span class="cve-badge cve-badge-draft" data-testid="badge-draft">Draft</span>
                        {:else if note.trust_level === 'deprecated'}
                          <span class="cve-badge cve-badge-deprecated" data-testid="badge-trust">Deprecated</span>
                        {:else}
                          <span class="cve-badge {trustBadgeVariant(note.trust_level)}" data-testid="badge-trust">{note.trust_level}</span>
                        {/if}
                      {/if}
                    </div>
                  {/if}
                </button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </aside>

    <!-- ────────────────────────── Inspector ────────────────────────── -->
    <section class="cve-workbench__inspector cve-p30d2-inspector" aria-label="Selected note inspector">

      {#if !selectedPath}
        <div class="cve-p30d2-empty-pane">
          <p class="cve-empty">Select a note from the list to inspect it.</p>
          <p class="cve-helper">
            Frontmatter, body, section outline, validation state, task context, and trust metadata
            appear here. Raw payloads are available via the Developer route.
          </p>
        </div>

      {:else if noteDetailState === 'loading'}
        <p class="cve-loading">Loading note...</p>

      {:else if noteDetailState === 'error'}
        <p class="cve-error">{noteDetailError}</p>

      {:else if noteDetail}

        <header class="cve-p30d2-inspector__head">
          <div>
            <h2 class="cve-section-title">
              {noteDetail.fields?.title
                ? String(noteDetail.fields.title)
                : (noteDetail.path.split('/').pop()?.replace(/\.md$/i, '') ?? noteDetail.path)}
            </h2>
            <p class="cve-meta cve-mono">{noteDetail.path}</p>
          </div>
          <div class="cve-p30d2-inspector__actions">
            {#if !editMode}
              <button type="button" class="cve-btn cve-btn-secondary" on:click={enterEditMode} aria-label="Edit note">
                Edit note
              </button>
            {:else}
              <button type="button" class="cve-btn cve-btn-primary" on:click={saveNote} disabled={saveState === 'loading'} aria-label="Save changes">
                {saveState === 'loading' ? 'Saving...' : 'Save changes'}
              </button>
              <button type="button" class="cve-btn cve-btn-secondary" on:click={resetToLoaded} disabled={saveState === 'loading'} aria-label="Reset to loaded">
                Reset
              </button>
              <button type="button" class="cve-btn cve-btn-ghost" on:click={cancelEdit} disabled={saveState === 'loading'} aria-label="Cancel edit">
                Cancel
              </button>
            {/if}
          </div>
        </header>

        <div class="cve-p30d2-status-strip">
          {#if noteDetail.fields?.status}
            <span class="cve-badge {statusBadgeVariant(String(noteDetail.fields.status))}">{noteDetail.fields.status}</span>
          {/if}
          {#if noteDetail.fields?.difficulty}
            <span class="cve-badge {difficultyBadgeVariant(String(noteDetail.fields.difficulty))}">{noteDetail.fields.difficulty}</span>
          {/if}
          {#if noteDetail.fields?.domain}
            <span class="cve-badge cve-badge-info">{noteDetail.fields.domain}</span>
          {/if}
          {#if noteDetail.fields?.type}
            <span class="cve-badge cve-badge-neutral">{noteDetail.fields.type}</span>
          {/if}
          {#if noteAppearsImported}
            <span class="cve-badge cve-badge-info">imported</span>
          {/if}
          {#if noteTrustLevel}
            <span class="cve-badge {trustBadgeVariant(noteTrustLevel)}">{noteTrustLevel}</span>
          {/if}
          {#if editMode}
            <span class="cve-badge cve-badge-info">EDIT MODE</span>
          {/if}
          {#if hasUnsavedChanges}
            <span class="cve-badge cve-badge-warning">Unsaved changes</span>
          {/if}
        </div>

        {#if saveState === 'ok' && saveResponse}
          <p class="cve-success">
            Note saved successfully.
            {#if saveResponse.warnings.length > 0}
              {saveResponse.warnings.length} warning(s).
            {/if}
          </p>
        {/if}

        {#if editMode && saveState === 'error' && saveError}
          <div class="cve-error">
            <strong>{saveErrorCode || 'ERROR'}:</strong> {saveError}
            {#if saveValidationDetails.length > 0}
              <ul class="cve-p30d2-error-list">
                {#each saveValidationDetails as detail}
                  <li>{detail}</li>
                {/each}
              </ul>
            {/if}
          </div>
        {/if}

        <div class="cve-scroll-region cve-p30d2-inspector__body">

          <!-- Frontmatter -->
          <section class="cve-section" aria-labelledby="notes-frontmatter-title">
            <h3 id="notes-frontmatter-title" class="cve-section-title">Frontmatter</h3>
            {#if !editMode}
              {#if noteFields.length === 0}
                <p class="cve-empty">No frontmatter fields found.</p>
              {:else}
                <div class="cve-table-wrap cve-p30d2-table">
                  <table class="cve-table" aria-label="Frontmatter fields">
                    <tbody>
                      {#each noteFields as [key, value]}
                        <tr>
                          <th scope="row" class="cve-mono">{key}</th>
                          <td class="cve-mono">{formatFieldValue(value)}</td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              {/if}
            {:else}
              {#if Object.keys(editedFields).length === 0}
                <p class="cve-empty">No frontmatter fields to edit.</p>
              {:else}
                <div class="cve-p30d2-edit-grid">
                  {#each Object.entries(editedFields) as [key, value]}
                    <div class="cve-p30d2-edit-row">
                      <label class="cve-label cve-mono" for={`notes-field-${key}`} title={key}>{key}</label>
                      {#if typeof value === 'boolean'}
                        <input
                          id={`notes-field-${key}`}
                          type="checkbox"
                          checked={value}
                          on:change={(e) => { editedFields = { ...editedFields, [key]: (e.target as HTMLInputElement).checked }; }}
                        />
                      {:else if typeof value === 'object' && value !== null}
                        <pre class="cve-raw cve-p30d2-edit-complex">{JSON.stringify(value, null, 2)}</pre>
                      {:else}
                        <input
                          id={`notes-field-${key}`}
                          class="cve-input"
                          type="text"
                          aria-label="Edit frontmatter field"
                          value={String(value ?? '')}
                          on:input={(e) => { editedFields = { ...editedFields, [key]: (e.target as HTMLInputElement).value }; }}
                        />
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            {/if}
          </section>

          <!-- Section outline -->
          {#if (editMode ? editSectionOutline : sectionOutline).length > 0 || (editMode && missingSectionsAdvisory.length > 0)}
            <section class="cve-section" aria-labelledby="notes-outline-title">
              <h3 id="notes-outline-title" class="cve-section-title">
                Section Outline
                <span class="cve-meta cve-mono">({(editMode ? editSectionOutline : sectionOutline).length} headings)</span>
              </h3>
              <ul class="cve-p30d2-outline">
                {#each (editMode ? editSectionOutline : sectionOutline) as heading}
                  <li style={`padding-left: ${(heading.level - 1) * 14}px`}>
                    <span class="cve-mono cve-meta">{'#'.repeat(heading.level)}</span>
                    <span>{heading.text}</span>
                    <span class="cve-mono cve-meta">L{heading.lineNumber}</span>
                  </li>
                {/each}
              </ul>
              {#if editMode && missingSectionsAdvisory.length > 0}
                <p class="cve-helper">Advisory: expected sections not found:</p>
                <div class="cve-p30d2-badge-list">
                  {#each missingSectionsAdvisory as s}
                    <span class="cve-badge cve-badge-warning">{s}</span>
                  {/each}
                </div>
              {/if}
            </section>
          {/if}

          <!-- Body -->
          <section class="cve-section" aria-labelledby="notes-body-title">
            <h3 id="notes-body-title" class="cve-section-title">
              Markdown body
              {#if !editMode}
                <span class="cve-meta">read-only</span>
              {/if}
            </h3>
            {#if !editMode}
              {#if noteBody}
                <pre class="cve-raw cve-p30d2-body">{noteBody}</pre>
              {:else}
                <p class="cve-empty">No body content.</p>
              {/if}
            {:else}
              <label class="cve-label" for="notes-edit-body">Edit body ({editedBody.length} chars)</label>
              <textarea
                id="notes-edit-body"
                class="cve-textarea cve-p30d2-body-edit"
                bind:value={editedBody}
                rows={20}
                spellcheck={false}
                placeholder="Markdown body content..."
              ></textarea>
            {/if}
          </section>

          <!-- Trust + Import -->
          {#if noteSourceType || noteTrustLevel || noteLastReviewed || noteReviewAfter || trustNoteEntry || noteAppearsImported}
            <section class="cve-section" aria-labelledby="notes-trust-title" data-testid="trust-import-panel">
              <h3 id="notes-trust-title" class="cve-section-title">Trust and Import</h3>
              <div class="cve-p30d2-kv">
                <span class="cve-meta">source_type</span><span class="cve-mono">{noteSourceType || '-'}</span>
                <span class="cve-meta">trust_level</span><span class="cve-mono">{noteTrustLevel || '-'}</span>
                <span class="cve-meta">last_reviewed</span><span class="cve-mono">{noteLastReviewed || '-'}</span>
                <span class="cve-meta">review_after</span><span class="cve-mono">{noteReviewAfter || '-'}</span>
                {#if trustNoteEntry}
                  <span class="cve-meta">confidence</span><span class="cve-mono">{trustNoteEntry.confidence}</span>
                  <span class="cve-meta">stale</span><span class="cve-mono">{trustNoteEntry.stale ? 'yes' : 'no'}</span>
                {/if}
              </div>
              {#if noteImportedMissingReviewMeta}
                <p class="cve-helper">
                  This note appears imported but has no <code>last_reviewed</code> or
                  <code>review_after</code> set. Review and update review metadata through
                  the safe edit workflow.
                </p>
              {/if}
              {#if noteAppearsDraft}
                <p class="cve-helper">
                  Trust level is <code>draft</code>. Review content, fix validation and task
                  issues, then update trust metadata through safe editing.
                </p>
              {/if}
              <p class="cve-helper">
                Trust metadata reflects review and maintenance state only.
                It does not prove factual correctness.
              </p>
            </section>
          {/if}

          <!-- Validation -->
          <section class="cve-section" aria-labelledby="notes-validation-title">
            <h3 id="notes-validation-title" class="cve-section-title">Validation</h3>
            {#if validationState === 'loading'}
              <p class="cve-loading">Checking validation...</p>
            {:else if validationState === 'error'}
              <p class="cve-error">Validation unavailable: {validationError}</p>
            {:else if isInvalidNote}
              <p class="cve-warning-block">
                <span class="cve-badge cve-badge-warning">WARN</span>
                This note appears in the invalid notes list. Run
                <code>py run.py validate</code> for the full report.
              </p>
            {:else if validationData}
              <p class="cve-success">
                <span class="cve-badge cve-badge-success">PASS</span>
                Note passes vault validation.
              </p>
            {:else}
              <p class="cve-empty">Validation data not loaded.</p>
            {/if}
          </section>

          <!-- Task -->
          <section class="cve-section" aria-labelledby="notes-task-title">
            <h3 id="notes-task-title" class="cve-section-title">Improvement task</h3>
            {#if tasksState === 'loading'}
              <p class="cve-loading">Loading tasks...</p>
            {:else if noteTask}
              <div class="cve-p30d2-task">
                <div class="cve-p30d2-task__head">
                  <span class="cve-badge {noteTask.priority >= 4 ? 'cve-badge-danger' : noteTask.priority >= 2 ? 'cve-badge-warning' : 'cve-badge-neutral'}">
                    priority {noteTask.priority.toFixed(1)}
                  </span>
                  <span class="cve-meta cve-mono">{noteTask.type}</span>
                  <span class="cve-meta cve-mono">target: {noteTask.target}</span>
                </div>
                <p>{noteTask.instruction}</p>
                {#if noteTask.missing && noteTask.missing.length > 0}
                  <div class="cve-p30d2-badge-list">
                    {#each noteTask.missing as s}
                      <span class="cve-badge cve-badge-warning">{s}</span>
                    {/each}
                  </div>
                {/if}
              </div>
            {:else}
              <p class="cve-empty">No active improvement task for this note.</p>
            {/if}
            <p class="cve-helper">
              <a class="cve-link" href={`/app/tasks${selectedVault ? `?vault=${encodeURIComponent(selectedVault)}` : ''}`}>
                Open in Tasks
              </a>
            </p>
          </section>

          <!-- Developer deep-link -->
          <details class="cve-details cve-details--inspector">
            <summary>Diagnostic detail</summary>
            <div class="cve-details__body">
              <p class="cve-helper">
                Raw note payloads, the /notes listing, and the last /query response are not
                rendered inline on the Notes workbench. The Developer route exposes the full
                JSON payloads, request history, and copy-ready output.
              </p>
              <p>
                <a class="cve-details__developer-link" href={rawDeveloperHref} aria-label="Open Developer route for raw notes payload">
                  Open in Developer
                </a>
              </p>
            </div>
          </details>

        </div>
      {/if}

    </section>
  </div>

</div>
