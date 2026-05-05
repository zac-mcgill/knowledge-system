<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchNotes,
    fetchNote,
    queryNotes,
    fetchValidation,
    fetchTasks,
    isOk,
    type NoteListItem,
    type NoteDetail,
    type NoteQueryRequest,
    type NoteQueryResponse,
    type QueryResultItem,
    type ValidationData,
    type TasksData,
    type Task,
  } from '../lib/api.ts';

  // ---------------------------------------------------------------------------
  // Types
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
          }),
        )
      : filteredNotes.map(
          (n): DisplayNote => ({
            path: n.path,
            name: n.name,
            status: n.status,
            difficulty: n.difficulty,
            missing: n.missing ?? [],
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
        selectedVault = vaultList[0];
        await loadAll();
      }
    } else {
      vaultsError = result.error?.message ?? 'Failed to load vaults';
    }
  }

  async function loadAll() {
    await Promise.all([loadNotes(), loadValidation(), loadTasks()]);
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

  async function selectNote(path: string) {
    if (selectedPath === path && noteDetailState === 'ok') return;
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
    selectedPath = '';
    noteDetail = null;
    noteDetailState = 'idle';
    noteDetailRaw = null;
    notesRaw = null;
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
      <p class="text-xs text-zinc-500 mt-0.5">Read-only inspector — select a note to view frontmatter, body, and context.</p>
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
            {#if filterText || filterStatus || filterDifficulty || filterMissingOnly}
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
                  <label class="text-xs text-zinc-500 block mb-1">Status</label>
                  <select
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
                  <label class="text-xs text-zinc-500 block mb-1">Difficulty</label>
                  <select
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
                  <label class="text-xs text-zinc-500 block mb-1">Domain</label>
                  <input
                    type="text"
                    bind:value={searchFilterDomain}
                    placeholder="e.g. fundamentals"
                    class="bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs rounded px-2 py-1.5 w-full focus:outline-none focus:ring-1 focus:ring-sky-500 placeholder-zinc-600"
                  />
                </div>
                <div>
                  <label class="text-xs text-zinc-500 block mb-1">Type</label>
                  <input
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
                    {#if note.difficulty || (note.missing && note.missing.length > 0)}
                      <div class="mt-1 flex flex-wrap gap-1">
                        {#if note.difficulty}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono {difficultyBadgeClass(note.difficulty)}">{note.difficulty}</span>
                        {/if}
                        {#if note.missing && note.missing.length > 0}
                          <span class="text-[10px] px-1.5 py-0.5 rounded font-mono text-orange-400 bg-orange-950 border border-orange-800">{note.missing.length} missing</span>
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
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <div class="flex flex-wrap items-start gap-3">
              <div class="flex-1 min-w-0">
                <h2 class="text-base font-semibold text-zinc-100 break-all leading-snug">
                  {noteDetail.fields?.title
                    ? String(noteDetail.fields.title)
                    : (noteDetail.path.split('/').pop()?.replace(/\.md$/i, '') ?? noteDetail.path)}
                </h2>
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
          </div>

          <!-- Frontmatter fields table -->
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

          <!-- Section outline (derived from Markdown headings) -->
          {#if sectionOutline.length > 0}
            <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
              <div class="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between">
                <span class="text-xs font-medium text-zinc-400 uppercase tracking-wide">Section Outline</span>
                <span class="text-xs text-zinc-600 font-mono">{sectionOutline.length} headings</span>
              </div>
              <ul class="px-4 py-3 space-y-1">
                {#each sectionOutline as heading}
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
            </div>
          {/if}

          <!-- Markdown body (read-only) -->
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
