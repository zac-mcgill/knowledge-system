<script lang="ts">
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
  import { getStoredVault } from '../lib/vaultState.ts';
  import ImportedReviewSummary from './ImportedReviewSummary.svelte';
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
    /** Phase 26C: surface trust/source for badges in the row. */
    source_type?: string | null;
    trust_level?: string | null;
  }

  // ---------------------------------------------------------------------------
  // Vault state
  // ---------------------------------------------------------------------------

  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';
  let selectedVault = '';

  // ---------------------------------------------------------------------------
  // Notes list state
  // ---------------------------------------------------------------------------

  let notesState: LoadState = 'idle';
  let notesList: NoteListItem[] = [];
  let notesError = '';
  let notesRaw: unknown = null;

  // ---------------------------------------------------------------------------
  // Filter state (applied to base note list only)
  // ---------------------------------------------------------------------------

  let filterText = '';
  let filterStatus = '';
  let filterDifficulty = '';
  let filterMissingOnly = false;
  // Phase 26C: imported-content triage filters.
  let filterImportedOnly = false;
  let filterDraftTrustOnly = false;

  // ---------------------------------------------------------------------------
  // Search / query panel state
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // Note detail state
  // ---------------------------------------------------------------------------

  let selectedPath = '';
  let noteDetailState: LoadState = 'idle';
  let noteDetail: NoteDetail | null = null;
  let noteDetailError = '';
  let noteDetailRaw: unknown = null;

  // ---------------------------------------------------------------------------
  // Validation state
  // ---------------------------------------------------------------------------

  let validationState: LoadState = 'idle';
  let validationData: ValidationData | null = null;
  let validationError = '';

  // ---------------------------------------------------------------------------
  // Tasks state
  // ---------------------------------------------------------------------------

  let tasksState: LoadState = 'idle';
  let tasksData: TasksData | null = null;
  let tasksError = '';

  // ---------------------------------------------------------------------------
  // Trust state (Phase 26C — used to enrich note detail + review summary)
  // ---------------------------------------------------------------------------

  let trustData: TrustSummaryData | null = null;

  // ---------------------------------------------------------------------------
  // Edit mode state
  // ---------------------------------------------------------------------------

  let editMode = false;
  let editedFields: Record<string, unknown> = {};
  let editedBody = '';
  let saveState: LoadState = 'idle';
  let saveError = '';
  let saveErrorCode = '';
  let saveValidationDetails: string[] = [];
  let saveResponse: NoteUpdateResponse | null = null;
  let saveRaw: unknown = null;

  // ---------------------------------------------------------------------------
  // Derived: filtered base note list
  // ---------------------------------------------------------------------------

  $: filteredNotes = notesList.filter((n) => {
    if (filterText) {
      const q = filterText.toLowerCase();
      if (!n.path.toLowerCase().includes(q) && !n.name.toLowerCase().includes(q)) return false;
    }
    if (filterStatus && n.status !== filterStatus) return false;
    if (filterDifficulty && n.difficulty !== filterDifficulty) return false;
    if (filterMissingOnly && (!n.missing || n.missing.length === 0)) return false;
    if (filterImportedOnly && (n.source_type ?? '').toString().trim().toLowerCase() !== 'imported') {
      return false;
    }
    if (filterDraftTrustOnly && (n.trust_level ?? '').toString().trim().toLowerCase() !== 'draft') {
      return false;
    }
    return true;
  });

  $: displayList = (
    searchActive
      ? searchResults.map(
          (r): DisplayNote => ({
            path: r.path,
            name: r.path.split('/').pop()?.replace(/\.md$/i, '') ?? r.path,
            status: (r.fields?.status as string) ?? '',
            difficulty: (r.fields?.difficulty as string) ?? '',
            missing: [],
            score: r.score,
            source_type: (r.fields?.source_type as string | null | undefined) ?? null,
            trust_level: (r.fields?.trust_level as string | null | undefined) ?? null,
          }),
        )
      : filteredNotes.map(
          (n): DisplayNote => ({
            path: n.path,
            name: n.name,
            status: n.status,
            difficulty: n.difficulty,
            missing: n.missing ?? [],
            source_type: n.source_type ?? null,
            trust_level: n.trust_level ?? null,
          }),
        )
  ) as DisplayNote[];

  // ---------------------------------------------------------------------------
  // Derived: unique dropdown values
  // ---------------------------------------------------------------------------

  $: statusValues = [...new Set(notesList.map((n) => n.status).filter(Boolean))].sort();
  $: difficultyValues = [...new Set(notesList.map((n) => n.difficulty).filter(Boolean))].sort();

  // ---------------------------------------------------------------------------
  // Derived: note detail fields
  // ---------------------------------------------------------------------------

  $: noteFields = noteDetail ? Object.entries(noteDetail.fields ?? {}) : [];
  $: noteBody = noteDetail?.body ?? '';
  $: sectionOutline = parseHeadings(noteBody);

  // ---------------------------------------------------------------------------
  // Derived: edit mode helpers
  // ---------------------------------------------------------------------------

  const ADVISORY_SECTIONS = ['Key Principles', 'How It Works', 'Trade-offs'];

  $: editSectionOutline = editMode ? parseHeadings(editedBody) : [];
  $: missingSectionsAdvisory = editMode
    ? ADVISORY_SECTIONS.filter((s) => !editSectionOutline.some((h) => h.text === s))
    : [];
  $: hasUnsavedChanges =
    editMode &&
    (editedBody !== (noteDetail?.body ?? '') ||
      JSON.stringify(editedFields) !== JSON.stringify(noteDetail?.fields ?? {}));

  // ---------------------------------------------------------------------------
  // Derived: validation context
  // ---------------------------------------------------------------------------

  $: isInvalidNote =
    validationData && selectedPath
      ? validationData.invalid_notes.includes(selectedPath)
      : false;

  // ---------------------------------------------------------------------------
  // Derived: task context
  // ---------------------------------------------------------------------------

  $: noteTask = (tasksData?.tasks ?? []).find((t: Task) => t.path === selectedPath) as
    | Task
    | undefined;

  // ---------------------------------------------------------------------------
  // Derived: trust/import panel (Phase 26C)
  //
  // Notes carry source_type/trust_level via frontmatter where the schema
  // allows.  We surface them in the detail panel so users can triage
  // imported content quickly, but we never auto-promote trust or rewrite
  // the body.  Trust metadata reflects review/maintenance state only.
  // ---------------------------------------------------------------------------

  $: trustNoteEntry = (trustData?.notes ?? []).find(
    (t: TrustNoteSummary) => t.path === selectedPath,
  ) as TrustNoteSummary | undefined;

  $: noteSourceType = (() => {
    const v = noteDetail?.fields?.source_type;
    return typeof v === 'string' ? v.trim() : '';
  })();

  $: noteTrustLevel = (() => {
    const v = noteDetail?.fields?.trust_level;
    return typeof v === 'string' ? v.trim() : '';
  })();

  $: noteLastReviewed = (() => {
    const v = noteDetail?.fields?.last_reviewed;
    return typeof v === 'string' ? v.trim() : '';
  })();

  $: noteReviewAfter = (() => {
    const v = noteDetail?.fields?.review_after;
    return typeof v === 'string' ? v.trim() : '';
  })();

  $: noteAppearsImported = noteDetail
    ? isImportedNote(noteDetail.fields as Record<string, unknown>)
    : false;

  $: noteAppearsDraft = noteDetail
    ? isDraftTrustNote(noteDetail.fields as Record<string, unknown>)
    : false;

  $: noteImportedMissingReviewMeta =
    noteAppearsImported && !noteLastReviewed && !noteReviewAfter;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function parseHeadings(body: string): SectionHeading[] {
    if (!body) return [];
    const lines = body.split('\n');
    const headings: SectionHeading[] = [];
    for (let i = 0; i < lines.length; i++) {
      const m = lines[i].match(/^(#{1,6})\s+(.+)$/);
      if (m) {
        headings.push({ level: m[1].length, text: m[2].trim(), lineNumber: i + 1 });
      }
    }
    return headings;
  }

  function statusBadgeClass(status: string): string {
    switch (status?.toLowerCase()) {
      case 'complete':
        return 'text-emerald-400 bg-emerald-950 border border-emerald-800';
      case 'partial':
        return 'text-amber-400 bg-amber-950 border border-amber-800';
      case 'stub':
        return 'text-zinc-400 bg-zinc-800 border border-zinc-700';
      default:
        return 'text-zinc-400 bg-zinc-800 border border-zinc-700';
    }
  }

  function difficultyBadgeClass(d: string): string {
    switch (d?.toLowerCase()) {
      case 'advanced':
        return 'text-red-400 bg-red-950 border border-red-800';
      case 'intermediate':
        return 'text-amber-400 bg-amber-950 border border-amber-800';
      case 'beginner':
        return 'text-emerald-400 bg-emerald-950 border border-emerald-800';
      default:
        return 'text-zinc-400 bg-zinc-800 border border-zinc-700';
    }
  }

  function formatFieldValue(value: unknown): string {
    if (value === null || value === undefined) return '—';
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
  // Edit mode helpers
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
    saveRaw = null;
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
    saveRaw = null;
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

    // Client-side validation
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

    saveRaw = result;

    if (isOk(result)) {
      saveState = 'ok';
      saveResponse = result.data;
      // Update note detail with response data (canonical round-trip values)
      noteDetail = {
        path: result.data.path,
        fields: result.data.fields as NoteFields,
        body: result.data.body,
      };
      noteDetailRaw = result;
      editMode = false;
      // Refresh list, validation, and tasks context
      await loadNotes();
      await loadValidation();
      await loadTasks();
      // Refresh search results if active
      if (searchActive) {
        await runSearch();
      }
    } else {
      saveState = 'error';
      const errCode = (result.error?.code as string) ?? '';
      saveErrorCode = errCode;
      saveError = result.error?.message ?? 'Save failed';
      if (errCode === 'VALIDATION_FAILED') {
        const details = result.error?.details;
        if (Array.isArray(details)) {
          saveValidationDetails = details.map((d) => String(d));
        }
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Load functions
  // ---------------------------------------------------------------------------

  async function loadVaults() {
    vaultsLoading = true;
    vaultsError = '';
    const result = await fetchVaults();
    vaultsLoading = false;
    if (isOk(result)) {
      vaultList = result.data.vaults;
      if (vaultList.length > 0) {
        // Phase 26C deep-link: ?vault=, ?filter=, ?path= are advisory hints.
        const params = readUrlParams();
        const urlVault = params.vault;
        const stored = getStoredVault();
        if (urlVault && vaultList.includes(urlVault)) {
          selectedVault = urlVault;
        } else if (stored && vaultList.includes(stored)) {
          selectedVault = stored;
        } else {
          selectedVault = vaultList[0];
        }
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
      return {
        vault: u.get('vault'),
        filter: u.get('filter'),
        path: u.get('path'),
      };
    } catch {
      return { vault: null, filter: null, path: null };
    }
  }

  function applyUrlFilter(filter: string | null) {
    if (!filter) return;
    const f = filter.trim().toLowerCase();
    if (f === 'imported') {
      filterImportedOnly = true;
    } else if (f === 'draft') {
      filterDraftTrustOnly = true;
    } else if (f === 'imported-draft' || f === 'draft-imported') {
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
    notesRaw = null;
    const result = await fetchNotes(selectedVault);
    if (isOk(result)) {
      notesList = result.data.notes;
      notesRaw = result;
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
    // Trust data is best-effort: failures here never block the Notes UI.
    trustData = null;
    if (!selectedVault) return;
    const result = await fetchTrustSummary(selectedVault);
    if (isOk(result)) {
      trustData = result.data;
    }
  }

  async function selectNote(path: string) {
    if (editMode) {
      cancelEdit();
      if (selectedPath === path) return; // same note — just exit edit mode
    } else if (selectedPath === path && noteDetailState === 'ok') {
      return;
    }
    saveState = 'idle';
    saveResponse = null;
    selectedPath = path;
    noteDetail = null;
    noteDetailState = 'loading';
    noteDetailError = '';
    noteDetailRaw = null;
    const result = await fetchNote(selectedVault, path);
    if (isOk(result)) {
      noteDetail = result.data;
      noteDetailRaw = result;
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
    noteDetailRaw = null;
    notesRaw = null;
    saveState = 'idle';
    saveResponse = null;
    clearSearch();
    clearFilters();
    if (selectedVault) loadAll();
  }

  // ---------------------------------------------------------------------------
  // Mount
  // ---------------------------------------------------------------------------

  onMount(loadVaults);
</script>

<!-- =========================================================================
  Note Browser
  ========================================================================= -->
<div class="flex flex-col gap-4">

  <!-- Header + vault selector -->
  <div class="flex flex-col sm:flex-row sm:items-center gap-3">
    <div>
      <h1 class="text-lg font-semibold text-zinc-100">Note Browser</h1>
      <p class="text-xs text-zinc-500 mt-0.5">Select a note to inspect or edit frontmatter, body, and context.</p>
    </div>
    <div class="flex items-center gap-2 sm:ml-auto">
      {#if vaultsLoading}
        <span class="text-xs text-zinc-500">Loading vaults...</span>
      {:else if vaultsError}
        <span class="text-xs text-red-400">{vaultsError}</span>
      {:else if vaultList.length === 0}
        <span class="text-xs text-zinc-500">No vaults found. Run vault setup first.</span>
      {:else}
        <label for="nb-vault-select" class="text-xs text-zinc-500 shrink-0">Vault:</label>
        <select
          id="nb-vault-select"
          bind:value={selectedVault}
          on:change={onVaultChange}
          class="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-sky-500"
        >
          {#each vaultList as v}
            <option value={v}>{v}</option>
          {/each}
        </select>
      {/if}
    </div>
  </div>

  <!-- Empty state: no vaults -->
  {#if !vaultsLoading && vaultList.length === 0}
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-8 text-center">
      <p class="text-sm text-zinc-500">No vaults are registered. Use Vault Setup to create one.</p>
    </div>

  {:else if !vaultsLoading && vaultList.length > 0}

    <!-- Two-column layout: list left, detail right -->
    <div class="flex flex-col lg:flex-row gap-4 items-start">

      <!-- ── Left column: filters + search + note list ──────────── -->
      <div class="w-full lg:w-96 xl:w-[420px] shrink-0 flex flex-col gap-3">

        <!-- Filter controls -->
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-3 flex flex-col gap-2">
          <div class="flex items-center justify-between min-h-[20px]">
            <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">Filters</span>
            {#if filterText || filterStatus || filterDifficulty || filterMissingOnly || filterImportedOnly || filterDraftTrustOnly}
              <button
                on:click={clearFilters}
                class="text-xs text-sky-400 hover:text-sky-300 transition-colors"
              >
                Clear
              </button>
            {/if}
          </div>
          <input
            type="text"
            bind:value={filterText}
            placeholder="Search by name or path..."
            class="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2.5 py-1.5 w-full focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder-zinc-600"
          />
          <div class="flex gap-2">
            <select
              bind:value={filterStatus}
              class="bg-zinc-800 border border-zinc-700 text-zinc-400 text-xs rounded px-2 py-1.5 flex-1 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="">All statuses</option>
              {#each statusValues as s}
                <option value={s}>{s}</option>
              {/each}
            </select>
            <select
              bind:value={filterDifficulty}
              class="bg-zinc-800 border border-zinc-700 text-zinc-400 text-xs rounded px-2 py-1.5 flex-1 focus:outline-none focus:ring-1 focus:ring-sky-500"
            >
              <option value="">All difficulties</option>
              {#each difficultyValues as d}
                <option value={d}>{d}</option>
              {/each}
            </select>
          </div>
          <label class="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none">
            <input
              type="checkbox"
              bind:checked={filterMissingOnly}
              class="rounded border-zinc-600 bg-zinc-800 text-sky-500 focus:ring-sky-500"
            />
            Missing sections only
          </label>
          <!-- Phase 26C: Imported-content triage filters -->
          <label class="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none" data-testid="filter-imported-only">
            <input
              type="checkbox"
              bind:checked={filterImportedOnly}
              class="rounded border-zinc-600 bg-zinc-800 text-sky-500 focus:ring-sky-500"
            />
            Imported only (source_type: imported)
          </label>
          <label class="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none" data-testid="filter-draft-trust-only">
            <input
              type="checkbox"
              bind:checked={filterDraftTrustOnly}
              class="rounded border-zinc-600 bg-zinc-800 text-sky-500 focus:ring-sky-500"
            />
            Draft trust only (trust_level: draft)
          </label>
        </div>

        <!-- Search / query panel (collapsible) -->
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <button
            on:click={() => (searchExpanded = !searchExpanded)}
            class="w-full flex items-center justify-between px-3 py-2.5 text-xs font-medium text-zinc-400 uppercase tracking-wide hover:text-zinc-200 transition-colors"
          >
            <span>Query Search (POST /query){searchActive ? ' — active' : ''}</span>
            <span class="text-zinc-600 font-mono text-[10px]">{searchExpanded ? '▲' : '▼'}</span>
          </button>

          {#if searchExpanded}
            <div class="px-3 pb-3 flex flex-col gap-2.5 border-t border-zinc-800">
              <div class="pt-2">
                <label for="nb-search-q" class="text-xs text-zinc-500 block mb-1">Free text (q)</label>
                <input
                  id="nb-search-q"
                  type="text"
                  bind:value={searchQ}
                  placeholder="e.g. recursion tree traversal"
                  class="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2.5 py-1.5 w-full focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder-zinc-600"
                />
              </div>

              <div>
                <span class="text-xs text-zinc-500 block mb-1">Search fields</span>
                <div class="flex gap-4">
                  {#each ['body', 'path', 'frontmatter'] as field}
                    <label class="flex items-center gap-1.5 text-xs text-zinc-400 cursor-pointer select-none">
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
                        class="rounded border-zinc-600 bg-zinc-800 text-sky-500 focus:ring-sky-500"
                      />
                      {field}
                    </label>
                  {/each}
                </div>
              </div>

              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label for="sq-status" class="text-xs text-zinc-500 block mb-1">Status</label>
                  <select
                    id="sq-status"
                    bind:value={searchFilterStatus}
                    class="bg-zinc-800 border border-zinc-700 text-zinc-400 text-xs rounded px-2 py-1.5 w-full focus:outline-none focus:ring-1 focus:ring-sky-500"
                  >
                    <option value="">Any</option>
                    {#each statusValues as s}
                      <option value={s}>{s}</option>
                    {/each}
                  </select>
                </div>
                <div>
                  <label for="sq-difficulty" class="text-xs text-zinc-500 block mb-1">Difficulty</label>
                  <select
                    id="sq-difficulty"
                    bind:value={searchFilterDifficulty}
                    class="bg-zinc-800 border border-zinc-700 text-zinc-400 text-xs rounded px-2 py-1.5 w-full focus:outline-none focus:ring-1 focus:ring-sky-500"
                  >
                    <option value="">Any</option>
                    {#each difficultyValues as d}
                      <option value={d}>{d}</option>
                    {/each}
                  </select>
                </div>
                <div>
                  <label for="sq-domain" class="text-xs text-zinc-500 block mb-1">Domain</label>
                  <input
                    id="sq-domain"
                    type="text"
                    bind:value={searchFilterDomain}
                    placeholder="e.g. fundamentals"
                    class="bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs rounded px-2 py-1.5 w-full focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder-zinc-600"
                  />
                </div>
                <div>
                  <label for="sq-type" class="text-xs text-zinc-500 block mb-1">Type</label>
                  <input
                    id="sq-type"
                    type="text"
                    bind:value={searchFilterType}
                    placeholder="e.g. core-concept"
                    class="bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs rounded px-2 py-1.5 w-full focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder-zinc-600"
                  />
                </div>
              </div>

              <div>
                <label for="nb-search-limit" class="text-xs text-zinc-500 block mb-1">Limit (1–500)</label>
                <input
                  id="nb-search-limit"
                  type="number"
                  bind:value={searchLimit}
                  min="1"
                  max="500"
                  class="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2.5 py-1.5 w-24 focus:outline-none focus:ring-1 focus:ring-sky-500"
                />
              </div>

              {#if searchError}
                <p class="text-xs text-red-400 bg-red-950 border border-red-900 rounded px-2 py-1.5">{searchError}</p>
              {/if}

              <div class="flex gap-2 pt-0.5">
                <button
                  on:click={runSearch}
                  disabled={searchState === 'loading'}
                  class="px-3 py-1.5 text-xs font-medium rounded bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {searchState === 'loading' ? 'Searching...' : 'Search'}
                </button>
                {#if searchActive}
                  <button
                    on:click={clearSearch}
                    class="px-3 py-1.5 text-xs font-medium rounded border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 transition-colors"
                  >
                    Clear search
                  </button>
                {/if}
              </div>

              {#if searchActive && searchResponseData}
                <p class="text-xs text-zinc-600">
                  {searchResponseData.returned} of {searchResponseData.count} results
                </p>
              {/if}
            </div>
          {/if}
        </div>

        <!-- Imported review summary (Phase 26C) — only shown when an
             imported filter is active, so the regular Notes view stays clean. -->
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

        <!-- Note list -->
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <div class="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
            <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">
              {searchActive ? 'Search Results' : 'Notes'}
            </span>
            <span class="text-xs text-zinc-600 font-mono">
              {displayList.length}{!searchActive ? ` / ${notesList.length}` : ''}
            </span>
          </div>

          {#if notesState === 'loading'}
            <div class="px-3 py-8 text-center text-sm text-zinc-500">Loading notes...</div>
          {:else if notesState === 'error'}
            <div class="px-3 py-4 text-sm text-red-400">{notesError}</div>
          {:else if displayList.length === 0}
            <div class="px-3 py-8 text-center text-sm text-zinc-500">
              {searchActive
                ? 'No results. Try a different query.'
                : notesState === 'ok' && notesList.length === 0
                  ? 'No notes in this vault.'
                  : 'No notes match the current filters.'}
            </div>
          {:else}
            <ul class="divide-y divide-zinc-800/60 overflow-y-auto max-h-[520px]">
              {#each displayList as note}
                <li>
                  <button
                    on:click={() => selectNote(note.path)}
                    class="w-full text-left px-3 py-2.5 hover:bg-zinc-800 transition-colors {selectedPath === note.path ? 'bg-zinc-800 border-l-2 border-sky-500' : 'border-l-2 border-transparent'}"
                  >
                    <div class="flex items-start justify-between gap-2">
                      <span class="text-sm text-zinc-200 font-medium truncate leading-tight">{note.name}</span>
                      <div class="flex items-center gap-1 shrink-0 pt-0.5">
                        {#if note.status}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono {statusBadgeClass(note.status)}">{note.status}</span>
                        {/if}
                        {#if note.score !== undefined}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-sky-400 bg-sky-950 border border-sky-800">{note.score.toFixed(2)}</span>
                        {/if}
                      </div>
                    </div>
                    <div class="mt-0.5 text-[11px] text-zinc-600 truncate font-mono">{note.path}</div>
                    {#if note.difficulty || (note.missing && note.missing.length > 0) || note.source_type || note.trust_level}
                      <div class="mt-1 flex flex-wrap gap-1">
                        {#if note.difficulty}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono {difficultyBadgeClass(note.difficulty)}">{note.difficulty}</span>
                        {/if}
                        {#if note.missing && note.missing.length > 0}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-orange-400 bg-orange-950 border border-orange-800">{note.missing.length} missing</span>
                        {/if}
                        <!-- Phase 26C: trust/source badges for fast triage of imported content. -->
                        {#if (note.source_type ?? '').toString().toLowerCase() === 'imported'}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-sky-300 bg-sky-950 border border-sky-800" data-testid="badge-imported">Imported</span>
                        {/if}
                        {#if (note.trust_level ?? '').toString().toLowerCase() === 'draft'}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-amber-300 bg-amber-950 border border-amber-800" data-testid="badge-draft">Draft</span>
                        {/if}
                        {#if (note.trust_level ?? '').toString().toLowerCase() === 'external'}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-zinc-300 bg-zinc-800 border border-zinc-700">External</span>
                        {/if}
                        {#if (note.trust_level ?? '').toString().toLowerCase() === 'deprecated'}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-rose-300 bg-rose-950 border border-rose-800">Deprecated</span>
                        {/if}
                      </div>
                    {/if}
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>

        <!-- Notes list raw JSON (hidden by default) -->
        {#if notesState === 'ok' && notesRaw}
          <details class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden group">
            <summary class="px-3 py-2.5 text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 list-none flex items-center justify-between">
              <span class="uppercase tracking-wide font-medium">Notes list response</span>
              <span class="text-zinc-700 font-mono text-[10px]">
                <span class="group-open:hidden">Show JSON</span>
                <span class="hidden group-open:inline">Hide JSON</span>
              </span>
            </summary>
            <pre class="px-3 pb-3 text-[11px] text-zinc-400 font-mono whitespace-pre-wrap break-words overflow-auto max-h-64 bg-zinc-950">{JSON.stringify(notesRaw, null, 2)}</pre>
          </details>
        {/if}

      </div><!-- end left column -->

      <!-- ── Right column: note detail ──────────────────────────── -->
      <div class="flex-1 min-w-0 flex flex-col gap-4">

        <!-- Empty state: no note selected -->
        {#if !selectedPath}
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg flex flex-col items-center justify-center p-12 min-h-[240px]">
            <p class="text-sm text-zinc-500">Select a note from the list to inspect it.</p>
            <p class="text-xs text-zinc-700 mt-2">Frontmatter, body, section outline, validation state, and task context will appear here.</p>
          </div>

        <!-- Loading state -->
        {:else if noteDetailState === 'loading'}
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg flex items-center justify-center p-12 min-h-[240px]">
            <p class="text-sm text-zinc-500">Loading note...</p>
          </div>

        <!-- Error state -->
        {:else if noteDetailState === 'error'}
          <div class="bg-zinc-900 border border-red-900 rounded-lg p-4">
            <p class="text-xs font-semibold text-red-400 mb-1">Failed to load note</p>
            <p class="text-sm text-zinc-400">{noteDetailError}</p>
          </div>

        <!-- Loaded: note detail -->
        {:else if noteDetail}

          <!-- Note header -->
          <div class="bg-zinc-900 border {editMode ? 'border-sky-800/60' : 'border-zinc-800'} rounded-lg p-4">
            <div class="flex flex-col gap-3">
              <div class="flex flex-wrap items-start gap-3">
                <div class="flex-1 min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <h2 class="text-base font-semibold text-zinc-100 break-all leading-snug">
                      {noteDetail.fields?.title
                        ? String(noteDetail.fields.title)
                        : (noteDetail.path.split('/').pop()?.replace(/\.md$/i, '') ?? noteDetail.path)}
                    </h2>
                    {#if editMode}
                      <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-sky-400 bg-sky-950 border border-sky-800 shrink-0">EDIT MODE</span>
                    {/if}
                    {#if hasUnsavedChanges}
                      <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-amber-400 bg-amber-950 border border-amber-800 shrink-0">Unsaved changes</span>
                    {/if}
                  </div>
                  <p class="text-[11px] text-zinc-600 mt-0.5 font-mono break-all">{noteDetail.path}</p>
                </div>
                <div class="flex flex-wrap gap-1.5 shrink-0">
                  {#if noteDetail.fields?.status}
                    <span class="text-xs px-2 py-0.5 rounded font-mono {statusBadgeClass(String(noteDetail.fields.status))}">{noteDetail.fields.status}</span>
                  {/if}
                  {#if noteDetail.fields?.difficulty}
                    <span class="text-xs px-2 py-0.5 rounded font-mono {difficultyBadgeClass(String(noteDetail.fields.difficulty))}">{noteDetail.fields.difficulty}</span>
                  {/if}
                  {#if noteDetail.fields?.domain}
                    <span class="text-xs px-2 py-0.5 rounded font-mono text-sky-400 bg-sky-950 border border-sky-800">{noteDetail.fields.domain}</span>
                  {/if}
                  {#if noteDetail.fields?.type}
                    <span class="text-xs px-2 py-0.5 rounded font-mono text-violet-400 bg-violet-950 border border-violet-800">{noteDetail.fields.type}</span>
                  {/if}
                </div>
              </div>

              <!-- Action bar -->
              <div class="flex flex-wrap gap-2 pt-0.5 border-t border-zinc-800/60">
                {#if !editMode}
                  <button
                    on:click={enterEditMode}
                    class="px-3 py-1.5 text-xs font-medium rounded border border-zinc-700 text-zinc-300 hover:text-zinc-100 hover:border-zinc-500 transition-colors"
                  >
                    Edit note
                  </button>
                {:else}
                  <button
                    on:click={saveNote}
                    disabled={saveState === 'loading'}
                    class="px-3 py-1.5 text-xs font-medium rounded bg-sky-600 hover:bg-sky-500 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {saveState === 'loading' ? 'Saving...' : 'Save changes'}
                  </button>
                  <button
                    on:click={resetToLoaded}
                    disabled={saveState === 'loading'}
                    class="px-3 py-1.5 text-xs font-medium rounded border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Reset to loaded
                  </button>
                  <button
                    on:click={cancelEdit}
                    disabled={saveState === 'loading'}
                    class="px-3 py-1.5 text-xs font-medium rounded border border-zinc-700 text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Cancel
                  </button>
                {/if}
              </div>
            </div>
          </div>

          <!-- Save success panel -->
          {#if saveState === 'ok' && saveResponse}
            <div class="bg-emerald-950 border border-emerald-800 rounded-lg p-3">
              <p class="text-xs font-semibold text-emerald-400">Note saved successfully.</p>
              {#if saveResponse.warnings.length > 0}
                <ul class="mt-1 space-y-0.5">
                  {#each saveResponse.warnings as w}
                    <li class="text-xs text-zinc-400">{w}</li>
                  {/each}
                </ul>
              {/if}
            </div>
          {/if}

          <!-- Save error panel (shown while in edit mode) -->
          {#if editMode && saveState === 'error' && saveError}
            <div class="bg-red-950 border border-red-800 rounded-lg p-3">
              <div class="flex items-start gap-2">
                <span class="text-[11px] font-bold text-red-400 border border-red-700 px-1.5 py-0.5 rounded font-mono shrink-0 mt-0.5">{saveErrorCode || 'ERROR'}</span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-red-300">{saveError}</p>
                  {#if saveValidationDetails.length > 0}
                    <ul class="mt-2 space-y-1">
                      {#each saveValidationDetails as detail}
                        <li class="text-xs text-zinc-400 pl-2 border-l border-red-800">{detail}</li>
                      {/each}
                    </ul>
                  {/if}
                </div>
              </div>
            </div>
          {/if}

          <!-- Frontmatter fields: inspect or edit -->
          {#if !editMode}
            <!-- Inspect mode: read-only table -->
            <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
              <div class="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between">
                <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">Frontmatter Fields</span>
                <span class="text-xs text-zinc-600 font-mono">{noteFields.length} fields</span>
              </div>
              {#if noteFields.length === 0}
                <p class="px-4 py-3 text-sm text-zinc-500">No frontmatter fields found.</p>
              {:else}
                <div class="divide-y divide-zinc-800/60">
                  {#each noteFields as [key, value]}
                    <div class="flex items-baseline gap-4 px-4 py-2">
                      <span class="text-xs text-zinc-500 font-mono w-32 shrink-0 truncate">{key}</span>
                      <span class="text-sm text-zinc-300 font-mono break-all flex-1">{formatFieldValue(value)}</span>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {:else}
            <!-- Edit mode: structured field editor -->
            <div class="bg-zinc-900 border border-sky-800/50 rounded-lg overflow-hidden">
              <div class="px-4 py-2.5 border-b border-sky-800/50 bg-sky-950/20 flex items-center justify-between">
                <span class="text-xs font-medium text-sky-400 uppercase tracking-wide">Edit Frontmatter Fields</span>
                <span class="text-xs text-zinc-600 font-mono">{Object.keys(editedFields).length} fields</span>
              </div>
              {#if Object.keys(editedFields).length === 0}
                <p class="px-4 py-3 text-sm text-zinc-500">No frontmatter fields to edit.</p>
              {:else}
                <div class="divide-y divide-zinc-800/60">
                  {#each Object.entries(editedFields) as [key, value]}
                    <div class="flex items-start gap-3 px-4 py-2.5">
                      <label
                        for="field-{key}"
                        class="text-xs text-zinc-500 font-mono w-32 shrink-0 pt-1.5 truncate"
                        title={key}
                      >{key}</label>
                      {#if typeof value === 'boolean'}
                        <input
                          id="field-{key}"
                          type="checkbox"
                          checked={value}
                          on:change={(e) => {
                            const checked = (e.target as HTMLInputElement).checked;
                            editedFields = { ...editedFields, [key]: checked };
                          }}
                          class="mt-1.5 rounded border-zinc-600 bg-zinc-800 text-sky-500 focus:ring-sky-500"
                        />
                      {:else if typeof value === 'object' && value !== null}
                        <div class="flex-1 min-w-0">
                          <pre class="text-xs text-zinc-400 font-mono bg-zinc-800/60 border border-zinc-700 rounded px-2.5 py-1.5 overflow-auto max-h-24 whitespace-pre-wrap break-words">{JSON.stringify(value, null, 2)}</pre>
                          <p class="text-[10px] text-zinc-600 mt-0.5">Complex value — not editable in this view.</p>
                        </div>
                      {:else}
                        <input
                          id="field-{key}"
                          type="text"
                          value={String(value ?? '')}
                          on:input={(e) => {
                            editedFields = { ...editedFields, [key]: (e.target as HTMLInputElement).value };
                          }}
                          class="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2.5 py-1.5 flex-1 focus:outline-none focus:ring-1 focus:ring-sky-500"
                        />
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          <!-- Section outline (derived from Markdown headings) -->
          {#if (editMode ? editSectionOutline : sectionOutline).length > 0 || (editMode && missingSectionsAdvisory.length > 0)}
            <div class="bg-zinc-900 border {editMode ? 'border-sky-800/50' : 'border-zinc-800'} rounded-lg overflow-hidden">
              <div class="px-4 py-2.5 border-b {editMode ? 'border-sky-800/50 bg-sky-950/20' : 'border-zinc-800'} flex items-center justify-between">
                <span class="text-xs font-medium {editMode ? 'text-sky-400' : 'text-zinc-400'} uppercase tracking-wide">
                  {editMode ? 'Section Outline (edit preview)' : 'Section Outline'}
                </span>
                <span class="text-xs text-zinc-600 font-mono">{(editMode ? editSectionOutline : sectionOutline).length} headings</span>
              </div>
              {#if (editMode ? editSectionOutline : sectionOutline).length > 0}
                <ul class="px-4 py-3 space-y-1">
                  {#each (editMode ? editSectionOutline : sectionOutline) as heading}
                    <li
                      class="text-sm text-zinc-300 flex items-baseline gap-2"
                      style="padding-left: {(heading.level - 1) * 14}px"
                    >
                      <span class="text-zinc-700 font-mono text-[11px] shrink-0">{'#'.repeat(heading.level)}</span>
                      <span class="flex-1 truncate">{heading.text}</span>
                      <span class="text-[11px] text-zinc-700 font-mono shrink-0">L{heading.lineNumber}</span>
                    </li>
                  {/each}
                </ul>
              {/if}
              {#if editMode && missingSectionsAdvisory.length > 0}
                <div class="px-4 pb-3 border-t border-sky-900/40 pt-2.5">
                  <p class="text-xs text-zinc-500 mb-1.5">Advisory — expected sections not found:</p>
                  <div class="flex flex-wrap gap-1">
                    {#each missingSectionsAdvisory as s}
                      <span class="text-[11px] px-1.5 py-0.5 rounded font-mono text-amber-400 bg-amber-950 border border-amber-800">{s}</span>
                    {/each}
                  </div>
                  <p class="text-[10px] text-zinc-600 mt-1.5">These are advisory only. Backend validation is authoritative.</p>
                </div>
              {/if}
            </div>
          {/if}

          <!-- Markdown body: inspect or edit -->
          {#if !editMode}
            <!-- Inspect mode: read-only body -->
            <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
              <div class="px-4 py-2.5 border-b border-zinc-800 flex items-center gap-2">
                <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">Markdown Body</span>
                <span class="text-[11px] text-zinc-700 ml-1">(read-only)</span>
              </div>
              {#if noteBody}
                <pre class="px-4 py-3 text-xs text-zinc-300 font-mono whitespace-pre-wrap break-words overflow-auto max-h-[480px] leading-relaxed">{noteBody}</pre>
              {:else}
                <p class="px-4 py-3 text-sm text-zinc-500">No body content.</p>
              {/if}
            </div>
          {:else}
            <!-- Edit mode: body textarea -->
            <div class="bg-zinc-900 border border-sky-800/50 rounded-lg overflow-hidden">
              <div class="px-4 py-2.5 border-b border-sky-800/50 bg-sky-950/20 flex items-center justify-between">
                <span class="text-xs font-medium text-sky-400 uppercase tracking-wide">Edit Markdown Body</span>
                <span class="text-xs text-zinc-600 font-mono">{editedBody.length} chars</span>
              </div>
              <div class="p-3">
                <textarea
                  bind:value={editedBody}
                  rows={20}
                  spellcheck={false}
                  class="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs font-mono rounded px-3 py-2.5 resize-y focus:outline-none focus:ring-1 focus:ring-sky-500 leading-relaxed"
                  placeholder="Markdown body content..."
                ></textarea>
              </div>
            </div>
          {/if}

          <!-- Trust and Import panel (Phase 26C) -->
          {#if noteSourceType || noteTrustLevel || noteLastReviewed || noteReviewAfter || trustNoteEntry || noteAppearsImported}
            <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden" data-testid="trust-import-panel">
              <div class="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between">
                <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">Trust and Import</span>
                {#if noteAppearsImported}
                  <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-sky-300 bg-sky-950 border border-sky-800">imported</span>
                {/if}
              </div>
              <div class="px-4 py-3 text-xs text-zinc-300 space-y-1.5">
                <div class="grid grid-cols-2 gap-y-1 gap-x-4">
                  <span class="text-zinc-500">source_type</span>
                  <span class="font-mono">{noteSourceType || '—'}</span>
                  <span class="text-zinc-500">trust_level</span>
                  <span class="font-mono">{noteTrustLevel || '—'}</span>
                  <span class="text-zinc-500">last_reviewed</span>
                  <span class="font-mono">{noteLastReviewed || '—'}</span>
                  <span class="text-zinc-500">review_after</span>
                  <span class="font-mono">{noteReviewAfter || '—'}</span>
                  {#if trustNoteEntry}
                    <span class="text-zinc-500">confidence</span>
                    <span class="font-mono">{trustNoteEntry.confidence}</span>
                    <span class="text-zinc-500">stale</span>
                    <span class="font-mono">{trustNoteEntry.stale ? 'yes' : 'no'}</span>
                  {/if}
                </div>
                {#if noteImportedMissingReviewMeta}
                  <p class="text-amber-300 mt-2">
                    This note appears to be imported but has no
                    <code class="text-zinc-200">last_reviewed</code> or
                    <code class="text-zinc-200">review_after</code> set.
                    Review the content and add review metadata through
                    the existing safe editing workflow.
                  </p>
                {/if}
                {#if noteAppearsDraft}
                  <p class="text-zinc-400 mt-2">
                    Trust level is <code class="text-zinc-200">draft</code>.
                    Review content, fix validation/task issues, then update
                    trust metadata through safe editing.
                  </p>
                {/if}
                <p class="text-[11px] text-zinc-500 mt-2">
                  Trust metadata reflects review and maintenance state only.
                  It does not prove factual correctness.
                </p>
              </div>
            </div>
          {/if}

          <!-- Validation context -->
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
            <div class="px-4 py-2.5 border-b border-zinc-800">
              <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">Validation</span>
            </div>
            <div class="px-4 py-3">
              {#if validationState === 'loading'}
                <p class="text-sm text-zinc-500">Checking validation...</p>
              {:else if validationState === 'error'}
                <p class="text-sm text-zinc-500">Validation unavailable: {validationError}</p>
              {:else if isInvalidNote}
                <div class="flex items-start gap-2.5">
                  <span class="text-[11px] font-bold text-amber-400 bg-amber-950 border border-amber-800 px-1.5 py-0.5 rounded font-mono shrink-0 mt-0.5">WARN</span>
                  <div>
                    <p class="text-sm text-amber-300">This note appears in the invalid notes list.</p>
                    <p class="text-xs text-zinc-500 mt-1">
                      Detailed validation messages are available via
                      <code class="font-mono text-zinc-400">py run.py validate</code>.
                    </p>
                  </div>
                </div>
              {:else if validationData}
                <div class="flex items-center gap-2">
                  <span class="text-[11px] font-bold text-emerald-400 bg-emerald-950 border border-emerald-800 px-1.5 py-0.5 rounded font-mono">PASS</span>
                  <p class="text-sm text-emerald-400">Note passes vault validation.</p>
                </div>
              {:else}
                <p class="text-sm text-zinc-500">Validation data not loaded.</p>
              {/if}
            </div>
          </div>

          <!-- Task / improvement context -->
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
            <div class="px-4 py-2.5 border-b border-zinc-800">
              <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">Improvement Task</span>
            </div>
            <div class="px-4 py-3">
              {#if tasksState === 'loading'}
                <p class="text-sm text-zinc-500">Loading tasks...</p>
              {:else if noteTask}
                <div class="flex flex-col gap-2.5">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span
                      class="text-xs px-2 py-0.5 rounded font-mono {noteTask.priority >= 4
                        ? 'text-red-400 bg-red-950 border border-red-800'
                        : noteTask.priority >= 2
                          ? 'text-amber-400 bg-amber-950 border border-amber-800'
                          : 'text-zinc-400 bg-zinc-800 border border-zinc-700'}"
                    >
                      priority {noteTask.priority.toFixed(1)}
                    </span>
                    <span class="text-xs text-zinc-500 font-mono">{noteTask.type}</span>
                    <span class="text-xs text-zinc-600 font-mono">target: {noteTask.target}</span>
                  </div>
                  <p class="text-sm text-zinc-300">{noteTask.instruction}</p>
                  {#if noteTask.missing && noteTask.missing.length > 0}
                    <div>
                      <span class="text-xs text-zinc-500">Missing sections:</span>
                      <div class="flex flex-wrap gap-1 mt-1">
                        {#each noteTask.missing as s}
                          <span class="text-[11px] px-1.5 py-0.5 rounded font-mono text-orange-400 bg-orange-950 border border-orange-800">{s}</span>
                        {/each}
                      </div>
                    </div>
                  {/if}
                  {#if noteTask.constraints && noteTask.constraints.length > 0}
                    <details>
                      <summary class="text-xs text-zinc-500 cursor-pointer hover:text-zinc-400 select-none">Constraints ({noteTask.constraints.length})</summary>
                      <ul class="mt-1 pl-3 border-l border-zinc-700 space-y-0.5">
                        {#each noteTask.constraints as c}
                          <li class="text-xs text-zinc-400">{c}</li>
                        {/each}
                      </ul>
                    </details>
                  {/if}
                  {#if noteTask.feedback_weight}
                    <details>
                      <summary class="text-xs text-zinc-500 cursor-pointer hover:text-zinc-400 select-none">Feedback weight</summary>
                      <div class="mt-1 pl-3 border-l border-zinc-700 flex flex-col gap-1">
                        <p class="text-xs text-zinc-400">Score delta: <span class="font-mono">{noteTask.feedback_weight.score_delta.toFixed(2)}</span></p>
                        <p class="text-xs text-zinc-400">{noteTask.feedback_weight.entry_summary}</p>
                      </div>
                    </details>
                  {/if}
                </div>
              {:else}
                <p class="text-sm text-zinc-500">No active improvement task for this note.</p>
              {/if}
            </div>
          </div>

          <!-- Raw JSON expanders -->
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
            <div class="px-4 py-2.5 border-b border-zinc-800">
              <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">Raw JSON</span>
            </div>
            <div class="divide-y divide-zinc-800">

              <!-- Note detail response -->
              <details class="group">
                <summary class="px-4 py-2.5 text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 list-none flex items-center justify-between select-none">
                  <span>Note detail response (GET /note)</span>
                  <span class="text-zinc-700 font-mono text-[10px]">
                    <span class="group-open:hidden">Show</span>
                    <span class="hidden group-open:inline">Hide</span>
                  </span>
                </summary>
                <pre class="px-4 pb-3 text-[11px] text-zinc-400 font-mono whitespace-pre-wrap break-words overflow-auto max-h-72 bg-zinc-950">{JSON.stringify(noteDetailRaw, null, 2)}</pre>
              </details>

              <!-- Update response (shown after save attempt) -->
              {#if saveRaw !== null}
                <details class="group">
                  <summary class="px-4 py-2.5 text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 list-none flex items-center justify-between select-none">
                    <span>Last update response (PUT /note)</span>
                    <span class="text-zinc-700 font-mono text-[10px]">
                      <span class="group-open:hidden">Show</span>
                      <span class="hidden group-open:inline">Hide</span>
                    </span>
                  </summary>
                  <pre class="px-4 pb-3 text-[11px] text-zinc-400 font-mono whitespace-pre-wrap break-words overflow-auto max-h-72 bg-zinc-950">{JSON.stringify(saveRaw, null, 2)}</pre>
                </details>
              {/if}

              <!-- Edit payload preview (shown only in edit mode) -->
              {#if editMode}
                <details class="group">
                  <summary class="px-4 py-2.5 text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 list-none flex items-center justify-between select-none">
                    <span>Current edit payload preview</span>
                    <span class="text-zinc-700 font-mono text-[10px]">
                      <span class="group-open:hidden">Show</span>
                      <span class="hidden group-open:inline">Hide</span>
                    </span>
                  </summary>
                  <pre class="px-4 pb-3 text-[11px] text-zinc-400 font-mono whitespace-pre-wrap break-words overflow-auto max-h-72 bg-zinc-950">{JSON.stringify({ vault: selectedVault, path: noteDetail?.path, fields: editedFields, body: editedBody }, null, 2)}</pre>
                </details>
              {/if}

              <!-- Query response (only when search was run) -->
              {#if searchResponseData}
                <details class="group">
                  <summary class="px-4 py-2.5 text-xs text-zinc-500 cursor-pointer hover:text-zinc-300 list-none flex items-center justify-between select-none">
                    <span>Last query response (POST /query)</span>
                    <span class="text-zinc-700 font-mono text-[10px]">
                      <span class="group-open:hidden">Show</span>
                      <span class="hidden group-open:inline">Hide</span>
                    </span>
                  </summary>
                  <pre class="px-4 pb-3 text-[11px] text-zinc-400 font-mono whitespace-pre-wrap break-words overflow-auto max-h-72 bg-zinc-950">{JSON.stringify(searchResponseData, null, 2)}</pre>
                </details>
              {/if}

            </div>
          </div>

        {/if}<!-- end note detail states -->
      </div><!-- end right column -->

    </div><!-- end two-column layout -->
  {/if}<!-- end vault check -->
</div>
