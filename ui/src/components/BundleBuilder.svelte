<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchContextProfiles,
    generateContextBundle,
    isOk,
    type ContextBundleRequest,
    type ContextBundleResponse,
    type BundleNote,
    type ContextProfileDefinition,
    type ContextProfilesData,
  } from '../lib/api.ts';
  import { getStoredVault } from '../lib/vaultState.ts';

  // ---------------------------------------------------------------------------
  // Vault state
  // ---------------------------------------------------------------------------

  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';

  // ---------------------------------------------------------------------------
  // Profile state (Phase 24)
  // ---------------------------------------------------------------------------

  let profilesData: ContextProfilesData | null = null;
  let profilesLoading = true;

  /** All known mode names in display order. */
  const MODE_NAMES = ['tiny', 'small', 'medium', 'large', 'agent'] as const;
  /** All known device profile names. */
  const DEVICE_PROFILE_NAMES = ['phone-local-llm', 'desktop-agent', 'full-review'] as const;

  /** Currently selected profile/mode (or '' for none). */
  let selectedProfile = '';
  let selectedMode = '';

  /** When true, show the effective budget summary from the selected profile/mode. */
  $: activeProfileDef = resolveActiveProfile(selectedProfile, selectedMode, profilesData);

  function resolveActiveProfile(
    prof: string,
    mode: string,
    data: ContextProfilesData | null,
  ): ContextProfileDefinition | null {
    if (!data) return null;
    if (prof && data.profiles[prof]) return data.profiles[prof];
    if (mode && data.modes[mode]) return data.modes[mode];
    return null;
  }

  /** True when a manual control value differs from the active profile default. */
  function isOverride(field: keyof ContextProfileDefinition, value: unknown): boolean {
    if (!activeProfileDef) return false;
    return activeProfileDef[field] !== value;
  }

  // ---------------------------------------------------------------------------
  // Form state
  // ---------------------------------------------------------------------------

  let selectedVault = '';

  // Filters
  type StatusFilter = 'complete' | 'partial' | 'all';
  let statusFilter: StatusFilter = 'complete';
  let filterDomain = '';
  let filterType = '';
  let filterDifficulty = '';

  // Sections
  const DEFAULT_SECTIONS = ['Key Principles', 'How It Works', 'Trade-offs'];
  let includeSections: string[] = [...DEFAULT_SECTIONS];
  let newSectionInput = '';
  let sectionInputError = '';

  // Flags
  let includeBody = true;
  let includeRelated = false;
  let allowPartial = false;

  // Budget
  let maxNotes = 10;
  let maxChars = 20000;

  // ---------------------------------------------------------------------------
  // Submit state
  // ---------------------------------------------------------------------------

  type SubmitState = 'idle' | 'loading' | 'ok' | 'error';
  let submitState: SubmitState = 'idle';
  let bundleResult: ContextBundleResponse | null = null;
  let submitError = '';
  let submitErrorCode = '';

  // ---------------------------------------------------------------------------
  // UI state (expanded notes, panels)
  // ---------------------------------------------------------------------------

  let expandedNoteIds: Set<string> = new Set();
  let expandedNoteSections: Set<string> = new Set();
  let expandedNoteBodies: Set<string> = new Set();
  let expandedNoteRaw: Set<string> = new Set();
  let showRawJson = false;
  let showGraphRaw = false;

  // ---------------------------------------------------------------------------
  // Derived / reactive
  // ---------------------------------------------------------------------------

  $: partialConflict = statusFilter === 'partial' && !allowPartial;

  $: canSubmit =
    selectedVault !== '' &&
    includeSections.length > 0 &&
    submitState !== 'loading';

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  onMount(async () => {
    vaultsLoading = true;
    vaultsError = '';

    // Load vaults and profiles in parallel
    const [vaultsResult, profResult] = await Promise.all([
      fetchVaults(),
      fetchContextProfiles(),
    ]);

    if (isOk(vaultsResult)) {
      vaultList = vaultsResult.data.vaults ?? [];
      if (vaultList.length > 0) {
        const stored = getStoredVault();
        selectedVault = (stored && vaultList.includes(stored)) ? stored : vaultList[0];
      }
    } else {
      vaultsError = vaultsResult.error?.message ?? 'Failed to load vaults';
    }

    if (isOk(profResult)) {
      profilesData = profResult.data;
    }

    vaultsLoading = false;
    profilesLoading = false;
  });

  // ---------------------------------------------------------------------------
  // Profile application
  // ---------------------------------------------------------------------------

  /** Apply a profile/mode's defaults to the manual form controls. */
  function applyProfileDefaults(def: ContextProfileDefinition) {
    includeBody = def.include_body;
    includeRelated = def.include_related;
    allowPartial = def.allow_partial;
    maxNotes = def.max_notes;
    maxChars = def.max_chars;
    if (def.include_sections && def.include_sections.length > 0) {
      includeSections = [...def.include_sections];
    }
  }

  function onProfileChange() {
    selectedMode = ''; // profile takes precedence; clear mode
    const def = resolveActiveProfile(selectedProfile, '', profilesData);
    if (def) applyProfileDefaults(def);
  }

  function onModeChange() {
    selectedProfile = ''; // clear device profile when mode chosen
    const def = resolveActiveProfile('', selectedMode, profilesData);
    if (def) applyProfileDefaults(def);
  }

  // ---------------------------------------------------------------------------
  // Section management
  // ---------------------------------------------------------------------------

  function addSection() {
    const val = newSectionInput.trim();
    sectionInputError = '';
    if (!val) {
      sectionInputError = 'Section name cannot be empty';
      return;
    }
    if (includeSections.map(s => s.trim().toLowerCase()).includes(val.toLowerCase())) {
      sectionInputError = 'Duplicate section name';
      return;
    }
    includeSections = [...includeSections, val];
    newSectionInput = '';
  }

  function removeSection(index: number) {
    includeSections = includeSections.filter((_, i) => i !== index);
  }

  function onSectionKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); addSection(); }
  }

  // ---------------------------------------------------------------------------
  // Request construction
  // ---------------------------------------------------------------------------

  function buildRequest(): ContextBundleRequest {
    const filters: Record<string, string> = {};

    if (statusFilter === 'complete') filters.status = 'complete';
    if (statusFilter === 'partial') filters.status = 'partial';

    const domain = filterDomain.trim();
    if (domain) filters.domain = domain;

    const type = filterType.trim();
    if (type) filters.type = type;

    const difficulty = filterDifficulty.trim();
    if (difficulty) filters.difficulty = difficulty;

    const req: ContextBundleRequest = {
      vault: selectedVault,
      filters: Object.keys(filters).length > 0 ? filters : {},
      include_sections: includeSections.map(s => s.trim()).filter(Boolean),
      include_body: includeBody,
      include_related: includeRelated,
      allow_partial: statusFilter === 'partial' ? true : allowPartial,
      max_notes: Math.max(1, Math.min(100, maxNotes)),
      max_chars: Math.max(100, Math.min(500000, maxChars)),
    };

    // Phase 24: attach profile/mode if selected
    if (selectedProfile) req.profile = selectedProfile;
    else if (selectedMode) req.mode = selectedMode;

    return req;
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  async function handleGenerate() {
    if (!canSubmit) return;

    // Validate sections
    const trimmed = includeSections.map(s => s.trim()).filter(Boolean);
    const lower = trimmed.map(s => s.toLowerCase());
    if (new Set(lower).size !== lower.length) {
      submitError = 'Duplicate section names detected. Remove duplicates before generating.';
      submitErrorCode = 'DUPLICATE_SECTIONS';
      submitState = 'error';
      return;
    }
    if (trimmed.length === 0) {
      submitError = 'At least one section name is required.';
      submitErrorCode = 'NO_SECTIONS';
      submitState = 'error';
      return;
    }

    submitState = 'loading';
    bundleResult = null;
    submitError = '';
    submitErrorCode = '';
    showRawJson = false;
    showGraphRaw = false;
    expandedNoteIds = new Set();
    expandedNoteSections = new Set();
    expandedNoteBodies = new Set();
    expandedNoteRaw = new Set();

    const req = buildRequest();
    const result = await generateContextBundle(req);

    if (isOk(result)) {
      bundleResult = result.data;
      submitState = 'ok';
    } else {
      submitErrorCode = result.error?.code ?? 'UNKNOWN';
      submitError = result.error?.message ?? 'An unexpected error occurred.';
      submitState = 'error';
    }
  }

  // ---------------------------------------------------------------------------
  // Note expand helpers
  // ---------------------------------------------------------------------------

  function toggleNote(path: string) {
    if (expandedNoteIds.has(path)) expandedNoteIds.delete(path);
    else expandedNoteIds.add(path);
    expandedNoteIds = expandedNoteIds;
  }

  function toggleNoteSection(key: string) {
    if (expandedNoteSections.has(key)) expandedNoteSections.delete(key);
    else expandedNoteSections.add(key);
    expandedNoteSections = expandedNoteSections;
  }

  function toggleNoteBody(path: string) {
    if (expandedNoteBodies.has(path)) expandedNoteBodies.delete(path);
    else expandedNoteBodies.add(path);
    expandedNoteBodies = expandedNoteBodies;
  }

  function toggleNoteRaw(path: string) {
    if (expandedNoteRaw.has(path)) expandedNoteRaw.delete(path);
    else expandedNoteRaw.add(path);
    expandedNoteRaw = expandedNoteRaw;
  }

  // ---------------------------------------------------------------------------
  // Error display helpers
  // ---------------------------------------------------------------------------

  function errorTitle(code: string): string {
    if (code === 'INVALID_VAULT') return 'Vault Not Found';
    if (code === 'INVALID_FILTER') return 'Invalid Filter';
    if (code === 'VALIDATION_ERROR') return 'Validation Error';
    if (code === 'BUNDLE_FAILED') return 'Bundle Generation Failed';
    if (code === 'NETWORK_ERROR') return 'Backend Unavailable';
    if (code === 'DUPLICATE_SECTIONS') return 'Duplicate Sections';
    if (code === 'NO_SECTIONS') return 'No Sections';
    return 'Error';
  }

  // ---------------------------------------------------------------------------
  // Formatting helpers
  // ---------------------------------------------------------------------------

  function formatChars(n: number): string {
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
    return String(n);
  }

  function pct(used: number, max: number): number {
    if (max <= 0) return 0;
    return Math.min(100, Math.round((used / max) * 100));
  }

  function noteTitle(note: BundleNote): string {
    return note.fields?.title || note.path.split('/').pop()?.replace(/\.md$/, '') || note.path;
  }

  function sectionNames(sections: Record<string, string>): string[] {
    return Object.entries(sections)
      .filter(([, v]) => v && v.trim().length > 0)
      .map(([k]) => k);
  }
</script>

<!-- =========================================================
     Page header
     ========================================================= -->
<div class="mb-5">
  <h1 class="text-xl font-semibold text-zinc-100">Bundle Builder</h1>
  <p class="text-sm text-zinc-500 mt-0.5">
    Configure filters and sections, then preview a context bundle from your vault.
  </p>
</div>

<!-- =========================================================
     Vault loading states
     ========================================================= -->
{#if vaultsLoading}
  <div class="text-sm text-zinc-500 py-6">Loading vaults...</div>
{:else if vaultsError}
  <div class="bg-red-950 border border-red-800 rounded-lg p-4 text-sm text-red-300 mb-4">
    <span class="font-medium">Could not load vaults:</span> {vaultsError}
  </div>
{:else if vaultList.length === 0}
  <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-6 max-w-lg">
    <p class="text-sm text-zinc-400">No vaults registered. Use Vault Setup to create one.</p>
  </div>
{:else}
  <!-- =======================================================
       Two-column layout: builder left, result right
       ======================================================= -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">

    <!-- ── Left: Configuration form ─────────────────────────── -->
    <div class="space-y-4">

      <!-- Vault selector -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 class="text-sm font-semibold text-zinc-300 mb-3">Vault</h2>
        <select
          bind:value={selectedVault}
          class="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-sky-600"
        >
          {#each vaultList as v}
            <option value={v}>{v}</option>
          {/each}
        </select>
      </div>

      <!-- Phase 24: Profile / Mode selector -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 class="text-sm font-semibold text-zinc-300 mb-1">Context Profile / Mode</h2>
        <p class="text-xs text-zinc-500 mb-3">
          Select a profile or mode to apply deterministic budget defaults for your target client.
          Manual controls below will override profile defaults (labelled with ⚠).
        </p>

        <!-- Mode badges -->
        <div class="mb-3">
          <p class="text-xs font-medium text-zinc-400 mb-1.5">Bundle Modes</p>
          <div class="flex flex-wrap gap-1.5">
            {#each MODE_NAMES as m}
              <button
                type="button"
                on:click={() => { selectedMode = selectedMode === m ? '' : m; if (selectedMode) onModeChange(); else selectedProfile = ''; }}
                class="px-2.5 py-1 rounded-md text-xs font-medium border transition-colors
                  {selectedMode === m
                    ? 'bg-sky-700 text-sky-100 border-sky-600'
                    : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:border-zinc-500'}"
              >{m}</button>
            {/each}
          </div>
        </div>

        <!-- Device profile badges -->
        <div class="mb-3">
          <p class="text-xs font-medium text-zinc-400 mb-1.5">Device Profiles</p>
          <div class="flex flex-wrap gap-1.5">
            {#each DEVICE_PROFILE_NAMES as p}
              <button
                type="button"
                on:click={() => { selectedProfile = selectedProfile === p ? '' : p; if (selectedProfile) onProfileChange(); else selectedMode = ''; }}
                class="px-2.5 py-1 rounded-md text-xs font-medium border transition-colors
                  {selectedProfile === p
                    ? 'bg-violet-700 text-violet-100 border-violet-600'
                    : 'bg-zinc-800 text-zinc-400 border-zinc-700 hover:border-zinc-500'}"
              >{p}</button>
            {/each}
          </div>
        </div>

        <!-- Effective budget summary when a profile/mode is active -->
        {#if activeProfileDef}
          <div class="mt-2 bg-zinc-800/60 border border-zinc-700 rounded-md p-3 text-xs space-y-1">
            <p class="font-medium text-zinc-200 mb-1.5">
              Effective budget:
              <span class="text-zinc-400 font-normal">{activeProfileDef.description}</span>
            </p>
            <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-zinc-400">
              <span>max_notes: <span class="text-zinc-200">{activeProfileDef.max_notes}</span></span>
              <span>max_chars: <span class="text-zinc-200">{activeProfileDef.max_chars.toLocaleString()}</span></span>
              <span>include_body: <span class="text-zinc-200">{activeProfileDef.include_body ? 'yes' : 'no'}</span></span>
              <span>include_related: <span class="text-zinc-200">{activeProfileDef.include_related ? 'yes' : 'no'}</span></span>
              <span>allow_partial: <span class="text-zinc-200">{activeProfileDef.allow_partial ? 'yes' : 'no'}</span></span>
              <span>require_scan: <span class="{activeProfileDef.require_security_scan ? 'text-amber-400' : 'text-zinc-200'}">{activeProfileDef.require_security_scan ? 'yes' : 'no'}</span></span>
            </div>
            <p class="text-zinc-500 mt-1">Sections: {activeProfileDef.include_sections.join(', ')}</p>
          </div>
        {/if}
      </div>

      <!-- Filters -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 class="text-sm font-semibold text-zinc-300 mb-3">Filters</h2>

        <div class="space-y-3">
          <!-- Status -->
          <div>
            <label class="block text-xs font-medium text-zinc-400 mb-1.5">Status</label>
            <div class="flex gap-2">
              {#each ['complete', 'partial', 'all'] as opt}
                <button
                  type="button"
                  on:click={() => { statusFilter = opt as StatusFilter; }}
                  class:bg-sky-700={statusFilter === opt}
                  class:text-sky-100={statusFilter === opt}
                  class:border-sky-600={statusFilter === opt}
                  class:bg-zinc-800={statusFilter !== opt}
                  class:text-zinc-400={statusFilter !== opt}
                  class:border-zinc-700={statusFilter !== opt}
                  class="px-3 py-1.5 rounded-md text-xs font-medium border transition-colors"
                >{opt}</button>
              {/each}
            </div>
            {#if partialConflict}
              <p class="text-xs text-amber-400 mt-1.5">
                Status is "partial" but allow_partial is off. Enable allow_partial below or partial notes may be excluded.
              </p>
            {/if}
          </div>

          <!-- Domain -->
          <div>
            <label class="block text-xs font-medium text-zinc-400 mb-1">Domain <span class="text-zinc-600">(optional)</span></label>
            <input
              bind:value={filterDomain}
              type="text"
              placeholder="e.g. fundamentals"
              class="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-sky-600"
            />
          </div>

          <!-- Type -->
          <div>
            <label class="block text-xs font-medium text-zinc-400 mb-1">Type <span class="text-zinc-600">(optional)</span></label>
            <input
              bind:value={filterType}
              type="text"
              placeholder="e.g. core-concept"
              class="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-sky-600"
            />
          </div>

          <!-- Difficulty -->
          <div>
            <label class="block text-xs font-medium text-zinc-400 mb-1">Difficulty <span class="text-zinc-600">(optional)</span></label>
            <input
              bind:value={filterDifficulty}
              type="text"
              placeholder="e.g. intermediate"
              class="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-sky-600"
            />
          </div>
        </div>
      </div>

      <!-- Sections -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 class="text-sm font-semibold text-zinc-300 mb-3">Sections to Extract</h2>

        <div class="flex flex-wrap gap-1.5 mb-3">
          {#each includeSections as sec, i}
            <span class="inline-flex items-center gap-1 bg-zinc-800 border border-zinc-700 rounded-md px-2 py-1 text-xs text-zinc-200">
              {sec}
              <button
                type="button"
                on:click={() => removeSection(i)}
                class="text-zinc-500 hover:text-red-400 ml-0.5 transition-colors"
                aria-label="Remove section"
              >
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </span>
          {/each}
        </div>

        <div class="flex gap-2">
          <input
            bind:value={newSectionInput}
            on:keydown={onSectionKeydown}
            type="text"
            placeholder="Add section name..."
            class="flex-1 bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-sky-600"
            class:border-red-700={!!sectionInputError}
          />
          <button
            type="button"
            on:click={addSection}
            class="px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 border border-zinc-600 text-zinc-200 text-sm rounded-md transition-colors"
          >Add</button>
        </div>
        {#if sectionInputError}
          <p class="text-xs text-red-400 mt-1">{sectionInputError}</p>
        {/if}
      </div>

      <!-- Content flags -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 class="text-sm font-semibold text-zinc-300 mb-3">Content Options</h2>

        <div class="space-y-3">
          <label class="flex items-start gap-2.5 cursor-pointer select-none">
            <input type="checkbox" bind:checked={includeBody} class="mt-0.5 accent-sky-500" />
            <div>
              <span class="text-sm text-zinc-200">Include body</span>
              <p class="text-xs text-zinc-500 mt-0.5">Include full note text after frontmatter.</p>
            </div>
          </label>

          <label class="flex items-start gap-2.5 cursor-pointer select-none">
            <input type="checkbox" bind:checked={includeRelated} class="mt-0.5 accent-sky-500" />
            <div>
              <span class="text-sm text-zinc-200">Include related notes</span>
              <p class="text-xs text-zinc-500 mt-0.5">Attach graph relationship IDs for each note.</p>
            </div>
          </label>

          <label class="flex items-start gap-2.5 cursor-pointer select-none">
            <input type="checkbox" bind:checked={allowPartial} class="mt-0.5 accent-sky-500" />
            <div>
              <span class="text-sm text-zinc-200">Allow partial notes</span>
              <p class="text-xs text-zinc-500 mt-0.5">
                Include notes with <span class="font-mono text-xs text-zinc-400">status=partial</span>.
                {#if statusFilter === 'partial'}<span class="text-amber-400"> (auto-enabled when status filter is partial)</span>{/if}
              </p>
            </div>
          </label>
        </div>
      </div>

      <!-- Budget -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 class="text-sm font-semibold text-zinc-300 mb-3">Budget</h2>

        <div class="space-y-3">
          <div>
            <label class="block text-xs font-medium text-zinc-400 mb-1">
              Max notes
              <span class="text-zinc-600 font-normal">(1–100)</span>
              {#if activeProfileDef && isOverride('max_notes', maxNotes)}
                <span class="text-amber-400 ml-1">⚠ overrides profile</span>
              {/if}
            </label>
            <input
              bind:value={maxNotes}
              type="number"
              min="1"
              max="100"
              class="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-sky-600"
            />
          </div>

          <div>
            <label class="block text-xs font-medium text-zinc-400 mb-1">
              Max chars
              <span class="text-zinc-600 font-normal">(100–500,000)</span>
              {#if activeProfileDef && isOverride('max_chars', maxChars)}
                <span class="text-amber-400 ml-1">⚠ overrides profile</span>
              {/if}
            </label>
            <input
              bind:value={maxChars}
              type="number"
              min="100"
              max="500000"
              class="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-100 focus:outline-none focus:border-sky-600"
            />
          </div>
        </div>
      </div>

      <!-- Generate button -->
      <button
        type="button"
        on:click={handleGenerate}
        disabled={!canSubmit}
        class="w-full py-2.5 px-4 rounded-lg text-sm font-semibold transition-colors
          {submitState === 'loading'
            ? 'bg-zinc-700 text-zinc-400 cursor-wait'
            : canSubmit
              ? 'bg-sky-600 hover:bg-sky-500 text-white'
              : 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
          }"
      >
        {#if submitState === 'loading'}
          Generating...
        {:else}
          Generate Preview
        {/if}
      </button>

    </div>

    <!-- ── Right: Result panel ──────────────────────────────── -->
    <div>

      <!-- Idle state -->
      {#if submitState === 'idle'}
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-8 flex flex-col items-center text-center">
          <div class="w-10 h-10 bg-zinc-800 border border-zinc-700 rounded-lg flex items-center justify-center mb-3">
            <svg class="w-5 h-5 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p class="text-sm text-zinc-400">Configure the bundle on the left, then click <span class="font-medium text-zinc-300">Generate Preview</span>.</p>
        </div>
      {/if}

      <!-- Loading state -->
      {#if submitState === 'loading'}
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-8 flex flex-col items-center text-center">
          <div class="w-6 h-6 border-2 border-sky-600 border-t-transparent rounded-full animate-spin mb-3"></div>
          <p class="text-sm text-zinc-400">Generating bundle...</p>
        </div>
      {/if}

      <!-- Error state -->
      {#if submitState === 'error'}
        <div class="bg-red-950 border border-red-800 rounded-lg p-4 mb-4">
          <h3 class="text-sm font-semibold text-red-300 mb-1">{errorTitle(submitErrorCode)}</h3>
          <p class="text-sm text-red-400">{submitError}</p>
          <button
            type="button"
            on:click={() => { submitState = 'idle'; }}
            class="mt-3 text-xs text-red-400 hover:text-red-200 underline"
          >Dismiss</button>
        </div>
      {/if}

      <!-- Success: bundle panels -->
      {#if submitState === 'ok' && bundleResult}
        {@const bundle = bundleResult}
        <div class="space-y-4">

          <!-- ── Overview ─────────────────────────────────── -->
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 class="text-sm font-semibold text-zinc-300 mb-3">Bundle Overview</h2>

            <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <div>
                <dt class="text-xs text-zinc-500">Bundle ID</dt>
                <dd class="font-mono text-zinc-200 text-xs mt-0.5">{bundle.bundle_id}</dd>
              </div>
              <div>
                <dt class="text-xs text-zinc-500">Vault</dt>
                <dd class="text-zinc-200 text-xs mt-0.5">{bundle.vault}</dd>
              </div>
              <div>
                <dt class="text-xs text-zinc-500">Created</dt>
                <dd class="text-zinc-400 text-xs mt-0.5 font-mono">{bundle.created_at}</dd>
              </div>
              <div>
                <dt class="text-xs text-zinc-500">Schema version</dt>
                <dd class="text-zinc-400 text-xs mt-0.5 font-mono">{bundle.schema_version ?? 'null'}</dd>
              </div>
              <div>
                <dt class="text-xs text-zinc-500">Validation</dt>
                <dd class="mt-0.5">
                  {#if bundle.validation_status === 'pass'}
                    <span class="inline-block bg-emerald-900 text-emerald-300 border border-emerald-700 rounded px-1.5 py-0.5 text-xs font-medium">pass</span>
                  {:else if bundle.validation_status === 'fail'}
                    <span class="inline-block bg-red-900 text-red-300 border border-red-700 rounded px-1.5 py-0.5 text-xs font-medium">fail</span>
                  {:else}
                    <span class="inline-block bg-zinc-800 text-zinc-400 border border-zinc-700 rounded px-1.5 py-0.5 text-xs font-medium">unknown</span>
                  {/if}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-zinc-500">Notes included</dt>
                <dd class="text-zinc-200 text-xs mt-0.5">{bundle.notes?.length ?? 0}</dd>
              </div>
              <div>
                <dt class="text-xs text-zinc-500">Warnings</dt>
                <dd class="text-zinc-200 text-xs mt-0.5">
                  {#if bundle.warnings?.length > 0}
                    <span class="inline-block bg-amber-900 text-amber-300 border border-amber-700 rounded px-1.5 py-0.5 text-xs font-medium">{bundle.warnings.length}</span>
                  {:else}
                    <span class="text-zinc-500">none</span>
                  {/if}
                </dd>
              </div>
              <div>
                <dt class="text-xs text-zinc-500">Feedback entries</dt>
                <dd class="text-zinc-200 text-xs mt-0.5">{bundle.feedback?.entries?.length ?? 0}</dd>
              </div>
              <div class="col-span-2">
                <dt class="text-xs text-zinc-500">Source paths</dt>
                <dd class="text-zinc-200 text-xs mt-0.5">{bundle.manifest?.source_paths?.length ?? 0} file(s)</dd>
              </div>
            </dl>

            <!-- Phase 24: Profile metadata summary -->
            {#if bundle.profile_metadata && bundle.profile_metadata.profile_source !== 'none'}
              {@const pm = bundle.profile_metadata}
              <div class="mt-3 bg-zinc-800/60 border border-zinc-700 rounded-md p-3 text-xs space-y-1">
                <p class="font-medium text-zinc-300 mb-1">
                  Profile applied:
                  <span class="font-mono text-sky-300">
                    {pm.profile_used ?? pm.mode_used ?? '—'}
                  </span>
                  <span class="text-zinc-500 ml-1">({pm.profile_source})</span>
                </p>
                <div class="grid grid-cols-2 gap-x-4 gap-y-0.5 text-zinc-400">
                  {#if pm.effective_budget.max_notes !== null}
                    <span>max_notes: <span class="text-zinc-200">{pm.effective_budget.max_notes}</span></span>
                  {/if}
                  {#if pm.effective_budget.max_chars !== null}
                    <span>max_chars: <span class="text-zinc-200">{pm.effective_budget.max_chars.toLocaleString()}</span></span>
                  {/if}
                  {#if pm.require_security_scan}
                    <span class="col-span-2 text-amber-400">⚠ security scan required by profile</span>
                  {/if}
                </div>
              </div>
            {/if}
          </div>

          <!-- ── Budget panel ──────────────────────────────── -->
          {#if bundle.budget}
            {@const b = bundle.budget}
            <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <h2 class="text-sm font-semibold text-zinc-300 mb-3">Character Budget</h2>

              <div class="flex items-center justify-between text-xs text-zinc-400 mb-1.5">
                <span>{formatChars(b.used_chars)} used</span>
                <span>{formatChars(b.max_chars)} max</span>
              </div>

              <!-- Progress bar -->
              <div class="h-2 rounded-full bg-zinc-800 overflow-hidden mb-3">
                <div
                  class="h-full rounded-full transition-all
                    {b.truncated ? 'bg-amber-500' : pct(b.used_chars, b.max_chars) > 90 ? 'bg-amber-600' : 'bg-sky-600'}"
                  style="width: {pct(b.used_chars, b.max_chars)}%"
                ></div>
              </div>

              <div class="grid grid-cols-3 gap-3 text-xs">
                <div class="bg-zinc-800 rounded-md p-2 text-center">
                  <div class="text-zinc-400 mb-0.5">Used</div>
                  <div class="text-zinc-200 font-medium">{formatChars(b.used_chars)}</div>
                </div>
                <div class="bg-zinc-800 rounded-md p-2 text-center">
                  <div class="text-zinc-400 mb-0.5">Max</div>
                  <div class="text-zinc-200 font-medium">{formatChars(b.max_chars)}</div>
                </div>
                <div class="bg-zinc-800 rounded-md p-2 text-center">
                  <div class="text-zinc-400 mb-0.5">Notes</div>
                  <div class="text-zinc-200 font-medium">{b.note_count}</div>
                </div>
              </div>

              {#if b.truncated}
                <div class="mt-3 bg-amber-950 border border-amber-800 rounded-md p-2.5 text-xs text-amber-300">
                  <span class="font-medium">Budget truncated</span> — one or more notes were excluded because the character limit was reached.
                </div>
              {/if}

              {#if bundle.warnings?.length > 0}
                <div class="mt-3 space-y-1">
                  {#each bundle.warnings as w}
                    <div class="bg-amber-950/60 border border-amber-800/60 rounded-md px-2.5 py-1.5 text-xs text-amber-400">{w}</div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          <!-- ── Notes preview ─────────────────────────────── -->
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 class="text-sm font-semibold text-zinc-300 mb-3">
              Notes
              <span class="font-normal text-zinc-500 text-xs ml-1">({bundle.notes?.length ?? 0})</span>
            </h2>

            {#if !bundle.notes || bundle.notes.length === 0}
              <p class="text-xs text-zinc-500">No notes matched the filters.</p>
            {:else}
              <div class="space-y-2">
                {#each bundle.notes as note}
                  {@const expanded = expandedNoteIds.has(note.path)}
                  <div class="border border-zinc-800 rounded-md overflow-hidden">
                    <!-- Note header row -->
                    <button
                      type="button"
                      on:click={() => toggleNote(note.path)}
                      class="w-full flex items-start gap-2.5 px-3 py-2.5 text-left bg-zinc-800/60 hover:bg-zinc-800 transition-colors"
                    >
                      <svg
                        class="w-3.5 h-3.5 mt-0.5 shrink-0 text-zinc-500 transition-transform {expanded ? 'rotate-90' : ''}"
                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 flex-wrap">
                          <span class="text-sm text-zinc-200 font-medium truncate">{noteTitle(note)}</span>
                          {#if note.fields?.status}
                            <span class="
                              inline-block rounded px-1.5 py-0 text-xs font-medium
                              {note.fields.status === 'complete' ? 'bg-emerald-900 text-emerald-300 border border-emerald-800' : 'bg-amber-900 text-amber-300 border border-amber-800'}
                            ">{note.fields.status}</span>
                          {/if}
                          {#if note.fields?.difficulty}
                            <span class="inline-block bg-zinc-800 text-zinc-400 border border-zinc-700 rounded px-1.5 py-0 text-xs">{note.fields.difficulty}</span>
                          {/if}
                        </div>
                        <div class="text-xs text-zinc-500 mt-0.5 font-mono truncate">{note.path}</div>
                      </div>
                    </button>

                    <!-- Expanded details -->
                    {#if expanded}
                      <div class="px-3 py-3 space-y-3 bg-zinc-950/40 border-t border-zinc-800">

                        <!-- Fields summary -->
                        <div class="grid grid-cols-2 gap-2 text-xs">
                          {#each Object.entries(note.fields ?? {}) as [k, v]}
                            {#if v}
                              <div class="flex gap-1.5">
                                <span class="text-zinc-500 shrink-0">{k}:</span>
                                <span class="text-zinc-300 truncate">{v}</span>
                              </div>
                            {/if}
                          {/each}
                        </div>

                        <!-- Sections summary -->
                        {#if Object.keys(note.sections ?? {}).length > 0}
                          <div>
                            <div class="text-xs font-medium text-zinc-500 mb-1.5">
                              Sections
                              <span class="font-normal">(found: {sectionNames(note.sections ?? {}).join(', ') || 'none'})</span>
                            </div>
                            <div class="space-y-1.5">
                              {#each Object.entries(note.sections ?? {}) as [sec, content]}
                                {@const secKey = `${note.path}::${sec}`}
                                {@const secExpanded = expandedNoteSections.has(secKey)}
                                <div class="border border-zinc-800 rounded overflow-hidden">
                                  <button
                                    type="button"
                                    on:click={() => toggleNoteSection(secKey)}
                                    class="w-full flex items-center gap-1.5 px-2.5 py-1.5 bg-zinc-800/50 hover:bg-zinc-800 text-left transition-colors"
                                  >
                                    <svg class="w-3 h-3 shrink-0 text-zinc-600 transition-transform {secExpanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                    </svg>
                                    <span class="text-xs text-zinc-300 font-medium">{sec}</span>
                                    {#if !content || content.trim().length === 0}
                                      <span class="text-xs text-zinc-600 ml-auto italic">empty</span>
                                    {:else}
                                      <span class="text-xs text-zinc-600 ml-auto">{content.trim().length} chars</span>
                                    {/if}
                                  </button>
                                  {#if secExpanded && content && content.trim().length > 0}
                                    <div class="px-2.5 py-2 bg-zinc-950/60">
                                      <pre class="text-xs text-zinc-400 whitespace-pre-wrap break-words font-sans max-h-48 overflow-y-auto">{content.trim()}</pre>
                                    </div>
                                  {/if}
                                </div>
                              {/each}
                            </div>
                          </div>
                        {/if}

                        <!-- Body preview -->
                        {#if includeBody && note.body !== undefined}
                          {@const bodyExpanded = expandedNoteBodies.has(note.path)}
                          <div>
                            <div class="text-xs font-medium text-zinc-500 mb-1.5">
                              Body
                              <span class="font-normal">({note.body?.length ?? 0} chars)</span>
                            </div>
                            <div class="border border-zinc-800 rounded overflow-hidden">
                              <button
                                type="button"
                                on:click={() => toggleNoteBody(note.path)}
                                class="w-full flex items-center gap-1.5 px-2.5 py-1.5 bg-zinc-800/50 hover:bg-zinc-800 text-left transition-colors"
                              >
                                <svg class="w-3 h-3 shrink-0 text-zinc-600 transition-transform {bodyExpanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                </svg>
                                <span class="text-xs text-zinc-400">Show body</span>
                              </button>
                              {#if bodyExpanded}
                                <div class="px-2.5 py-2 bg-zinc-950/60 max-h-64 overflow-y-auto">
                                  <pre class="text-xs text-zinc-400 whitespace-pre-wrap break-words font-sans">{(note.body ?? '').trim()}</pre>
                                </div>
                              {/if}
                            </div>
                          </div>
                        {:else if !includeBody}
                          <div class="text-xs text-zinc-600 italic">Body not included (include_body=false)</div>
                        {/if}

                        <!-- Related -->
                        {#if includeRelated && note.related && note.related.length > 0}
                          <div class="text-xs text-zinc-500">
                            <span class="font-medium text-zinc-400">Related ({note.related.length}):</span>
                            <span class="ml-1 font-mono text-zinc-500">{note.related.join(', ')}</span>
                          </div>
                        {/if}

                        <!-- Raw note JSON -->
                        <details class="group">
                          <summary
                            class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none"
                            on:click|preventDefault={() => toggleNoteRaw(note.path)}
                          >
                            {expandedNoteRaw.has(note.path) ? 'Hide' : 'Show'} raw note JSON
                          </summary>
                          {#if expandedNoteRaw.has(note.path)}
                            <pre class="mt-2 text-xs text-zinc-500 bg-zinc-950/60 rounded p-2 overflow-x-auto max-h-48 whitespace-pre-wrap break-words">{JSON.stringify(note, null, 2)}</pre>
                          {/if}
                        </details>

                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>

          <!-- ── Feedback panel ────────────────────────────── -->
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 class="text-sm font-semibold text-zinc-300 mb-3">
              Feedback
              <span class="font-normal text-zinc-500 text-xs ml-1">({bundle.feedback?.entries?.length ?? 0} entries)</span>
            </h2>

            {#if !bundle.feedback?.entries || bundle.feedback.entries.length === 0}
              <p class="text-xs text-zinc-500">No feedback entries linked to the selected notes.</p>
            {:else}
              <div class="space-y-2">
                {#each bundle.feedback.entries as entry}
                  <div class="bg-zinc-800/60 border border-zinc-700 rounded-md px-3 py-2.5 text-xs">
                    <div class="flex items-start gap-2 flex-wrap">
                      <span class="font-mono text-zinc-400 shrink-0">{entry.path}</span>
                      <span class="
                        inline-block rounded px-1.5 py-0 font-medium
                        {entry.severity === 'high' ? 'bg-red-900 text-red-300 border border-red-800' :
                         entry.severity === 'medium' ? 'bg-amber-900 text-amber-300 border border-amber-800' :
                         'bg-zinc-800 text-zinc-400 border border-zinc-700'}
                      ">{entry.severity}</span>
                      <span class="text-zinc-500">{entry.signal}</span>
                      <span class="text-zinc-600 ml-auto font-mono">{entry.source}</span>
                    </div>
                    {#if entry.comment}
                      <p class="text-zinc-400 mt-1.5">{entry.comment}</p>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}

            {#if bundle.feedback?.warnings?.length > 0}
              <div class="mt-3 space-y-1">
                {#each bundle.feedback.warnings as w}
                  <div class="bg-amber-950/60 border border-amber-800/60 rounded px-2.5 py-1.5 text-xs text-amber-400">{w}</div>
                {/each}
              </div>
            {/if}
          </div>

          <!-- ── Graph relationship summary ────────────────── -->
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 class="text-sm font-semibold text-zinc-300 mb-2">Graph Relationships</h2>

            {#if !includeRelated}
              <p class="text-xs text-zinc-500">Graph relationships not requested <span class="font-mono">(include_related=false)</span>. Enable above and regenerate to see graph data.</p>
            {:else if !bundle.graph?.related || Object.keys(bundle.graph.related).length === 0}
              <p class="text-xs text-zinc-500">No graph relationships found for the selected notes.</p>
            {:else}
              {@const relatedEntries = Object.entries(bundle.graph.related)}
              <div class="space-y-1.5 mb-3">
                {#each relatedEntries as [node, related]}
                  <div class="flex items-center gap-2 text-xs">
                    <span class="font-mono text-zinc-300 truncate flex-1">{node}</span>
                    <span class="text-zinc-500 shrink-0">{(related as string[]).length} related</span>
                  </div>
                {/each}
              </div>

              <!-- Raw graph JSON -->
              <button
                type="button"
                on:click={() => { showGraphRaw = !showGraphRaw; }}
                class="text-xs text-zinc-600 hover:text-zinc-400 underline"
              >
                {showGraphRaw ? 'Hide' : 'Show'} raw graph JSON
              </button>
              {#if showGraphRaw}
                <pre class="mt-2 text-xs text-zinc-500 bg-zinc-950/60 rounded p-2 overflow-x-auto max-h-48 whitespace-pre-wrap break-words">{JSON.stringify(bundle.graph, null, 2)}</pre>
              {/if}
            {/if}
          </div>

          <!-- ── Raw JSON ──────────────────────────────────── -->
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-semibold text-zinc-300">Raw Bundle JSON</h2>
              <button
                type="button"
                on:click={() => { showRawJson = !showRawJson; }}
                class="text-xs text-zinc-500 hover:text-zinc-300 border border-zinc-700 rounded px-2 py-1 transition-colors"
              >
                {showRawJson ? 'Hide' : 'Show'}
              </button>
            </div>
            {#if showRawJson}
              <pre class="mt-3 text-xs text-zinc-500 bg-zinc-950/60 rounded p-3 overflow-x-auto max-h-96 whitespace-pre-wrap break-words">{JSON.stringify(bundle, null, 2)}</pre>
            {/if}
          </div>

        </div>
      {/if}
    </div>

  </div>
{/if}
