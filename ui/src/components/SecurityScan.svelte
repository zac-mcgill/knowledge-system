<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchVaults,
    scanContextSecurity,
    isOk,
    type ContextSecurityRequest,
    type ContextSecurityResponse,
    type SecurityFinding,
  } from '../lib/api.ts';

  // ---------------------------------------------------------------------------
  // Vault state
  // ---------------------------------------------------------------------------

  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';

  // ---------------------------------------------------------------------------
  // Form state
  // ---------------------------------------------------------------------------

  let selectedVault = '';

  type StatusFilter = 'complete' | 'partial' | 'all';
  let statusFilter: StatusFilter = 'complete';
  let filterDomain = '';
  let filterType = '';
  let filterDifficulty = '';

  const DEFAULT_SECTIONS = ['Key Principles', 'How It Works', 'Trade-offs'];
  let includeSections: string[] = [...DEFAULT_SECTIONS];
  let newSectionInput = '';
  let sectionInputError = '';

  let includeBody = true;
  let allowPartial = false;

  let maxNotes = 10;
  let maxChars = 20000;

  // ---------------------------------------------------------------------------
  // Submit state
  // ---------------------------------------------------------------------------

  type SubmitState = 'idle' | 'loading' | 'ok' | 'error';
  let submitState: SubmitState = 'idle';
  let scanResult: ContextSecurityResponse | null = null;
  let submitError = '';
  let submitErrorCode = '';

  // ---------------------------------------------------------------------------
  // Result UI state
  // ---------------------------------------------------------------------------

  type SeverityFilter = 'all' | 'fail' | 'warning' | 'info';
  let severityFilter: SeverityFilter = 'all';
  let findingTextFilter = '';
  let showRawJson = false;
  let expandedFindings = new Set<number>();

  // ---------------------------------------------------------------------------
  // Derived / reactive
  // ---------------------------------------------------------------------------

  $: partialConflict = statusFilter === 'partial' && !allowPartial;

  $: canSubmit =
    selectedVault !== '' &&
    includeSections.length > 0 &&
    submitState !== 'loading';

  $: previewFilters = (() => {
    const f: Record<string, string> = {};
    if (statusFilter === 'complete') f.status = 'complete';
    if (statusFilter === 'partial') f.status = 'partial';
    const d = filterDomain.trim();
    if (d) f.domain = d;
    const t = filterType.trim();
    if (t) f.type = t;
    const diff = filterDifficulty.trim();
    if (diff) f.difficulty = diff;
    return f;
  })();

  $: filteredFindings = (() => {
    if (!scanResult) return [];
    let findings = scanResult.findings ?? [];
    if (severityFilter !== 'all') {
      findings = findings.filter(f => f.severity === severityFilter);
    }
    const q = findingTextFilter.trim().toLowerCase();
    if (q) {
      findings = findings.filter(
        f =>
          f.path.toLowerCase().includes(q) ||
          f.rule.toLowerCase().includes(q) ||
          f.detail.toLowerCase().includes(q) ||
          f.field.toLowerCase().includes(q),
      );
    }
    return findings;
  })();

  // Rule summary derived from ALL findings (not filtered)
  $: ruleSummary = (() => {
    if (!scanResult) return [];
    const map = new Map<string, { count: number; highestSeverity: string }>();
    const order = ['fail', 'warning', 'info'];
    for (const f of scanResult.findings ?? []) {
      const entry = map.get(f.rule);
      if (!entry) {
        map.set(f.rule, { count: 1, highestSeverity: f.severity });
      } else {
        entry.count++;
        if (order.indexOf(f.severity) < order.indexOf(entry.highestSeverity)) {
          entry.highestSeverity = f.severity;
        }
      }
    }
    return [...map.entries()]
      .map(([rule, v]) => ({ rule, ...v }))
      .sort((a, b) => order.indexOf(a.highestSeverity) - order.indexOf(b.highestSeverity));
  })();

  // Affected notes: source_paths with finding counts
  $: affectedNotes = (() => {
    if (!scanResult) return [];
    const paths = scanResult.scanned?.source_paths ?? [];
    const findings = scanResult.findings ?? [];
    return paths.map(path => {
      const pathFindings = findings.filter(f => f.path === path);
      const severityCounts = { fail: 0, warning: 0, info: 0 };
      for (const f of pathFindings) {
        if (f.severity === 'fail') severityCounts.fail++;
        else if (f.severity === 'warning') severityCounts.warning++;
        else if (f.severity === 'info') severityCounts.info++;
      }
      return { path, count: pathFindings.length, severityCounts };
    });
  })();

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  onMount(async () => {
    vaultsLoading = true;
    vaultsError = '';
    const result = await fetchVaults();
    if (isOk(result)) {
      vaultList = result.data.vaults ?? [];
      if (vaultList.length > 0) selectedVault = vaultList[0];
    } else {
      vaultsError = result.error?.message ?? 'Failed to load vaults';
    }
    vaultsLoading = false;
  });

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

  function buildRequest(): ContextSecurityRequest {
    const filters: Record<string, string> = {};
    if (statusFilter === 'complete') filters.status = 'complete';
    if (statusFilter === 'partial') filters.status = 'partial';
    const domain = filterDomain.trim();
    if (domain) filters.domain = domain;
    const type = filterType.trim();
    if (type) filters.type = type;
    const difficulty = filterDifficulty.trim();
    if (difficulty) filters.difficulty = difficulty;

    return {
      vault: selectedVault,
      filters: Object.keys(filters).length > 0 ? filters : {},
      include_sections: includeSections.map(s => s.trim()).filter(Boolean),
      include_body: includeBody,
      allow_partial: statusFilter === 'partial' ? true : allowPartial,
      max_notes: Math.max(1, Math.min(100, maxNotes)),
      max_chars: Math.max(100, Math.min(500000, maxChars)),
    };
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  async function handleScan() {
    if (!canSubmit) return;

    const trimmed = includeSections.map(s => s.trim()).filter(Boolean);
    const lower = trimmed.map(s => s.toLowerCase());
    if (new Set(lower).size !== lower.length) {
      submitError = 'Duplicate section names detected. Remove duplicates before scanning.';
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
    scanResult = null;
    submitError = '';
    submitErrorCode = '';
    showRawJson = false;
    severityFilter = 'all';
    findingTextFilter = '';
    expandedFindings = new Set();

    const req = buildRequest();
    const result = await scanContextSecurity(req);

    if (isOk(result)) {
      scanResult = result.data;
      submitState = 'ok';
    } else {
      submitErrorCode = result.error?.code ?? 'UNKNOWN';
      submitError = result.error?.message ?? 'An unexpected error occurred.';
      submitState = 'error';
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function toggleFinding(index: number) {
    const s = new Set(expandedFindings);
    if (s.has(index)) s.delete(index);
    else s.add(index);
    expandedFindings = s;
  }

  function errorTitle(code: string): string {
    if (code === 'INVALID_VAULT') return 'Vault Not Found';
    if (code === 'INVALID_FILTER') return 'Invalid Filter';
    if (code === 'VALIDATION_ERROR') return 'Validation Error';
    if (code === 'NETWORK_ERROR') return 'Backend Unavailable';
    if (code === 'DUPLICATE_SECTIONS') return 'Duplicate Sections';
    if (code === 'NO_SECTIONS') return 'No Sections';
    return 'Scan Error';
  }

  function statusBadgeClass(status: string): string {
    if (status === 'fail') return 'bg-red-900 text-red-300 border border-red-700';
    if (status === 'warning') return 'bg-amber-900 text-amber-300 border border-amber-700';
    if (status === 'pass') return 'bg-emerald-900 text-emerald-300 border border-emerald-700';
    return 'bg-zinc-800 text-zinc-400 border border-zinc-700';
  }

  function severityClass(sev: string): string {
    if (sev === 'fail') return 'bg-red-900 text-red-300 border border-red-700';
    if (sev === 'warning') return 'bg-amber-900 text-amber-300 border border-amber-700';
    if (sev === 'info') return 'bg-sky-900 text-sky-300 border border-sky-700';
    return 'bg-zinc-800 text-zinc-400 border border-zinc-700';
  }

  function filterDescription(filters: Record<string, string>): string {
    const parts = Object.entries(filters).map(([k, v]) => `${k}=${v}`);
    return parts.length > 0 ? parts.join(', ') : 'none';
  }
</script>

<!-- =========================================================
     Page header
     ========================================================= -->
<div class="mb-5">
  <h1 class="text-xl font-semibold text-zinc-100">Security Scan</h1>
  <p class="text-sm text-zinc-500 mt-0.5">
    Scan vault notes for credential leaks, injection patterns, and policy violations.
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
       Two-column layout: config left, result right
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
        <h2 class="text-sm font-semibold text-zinc-300 mb-3">Sections to Scan</h2>

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

      <!-- Content options -->
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
              Max notes <span class="text-zinc-600 font-normal">(1–100)</span>
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
              Max chars <span class="text-zinc-600 font-normal">(100–500,000)</span>
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

      <!-- Request preview -->
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <h2 class="text-sm font-semibold text-zinc-300 mb-3">Request Preview</h2>
        <dl class="space-y-1.5 text-xs">
          <div class="flex gap-2">
            <dt class="text-zinc-500 w-28 shrink-0">Vault</dt>
            <dd class="text-zinc-200 font-mono">{selectedVault || '—'}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-zinc-500 w-28 shrink-0">Filters</dt>
            <dd class="text-zinc-200 font-mono">{filterDescription(previewFilters)}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-zinc-500 w-28 shrink-0">Sections</dt>
            <dd class="text-zinc-200">{includeSections.length > 0 ? includeSections.join(', ') : '—'}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-zinc-500 w-28 shrink-0">Include body</dt>
            <dd class="text-zinc-200">{includeBody ? 'yes' : 'no'}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-zinc-500 w-28 shrink-0">Allow partial</dt>
            <dd class="text-zinc-200">{statusFilter === 'partial' || allowPartial ? 'yes' : 'no'}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-zinc-500 w-28 shrink-0">Max notes</dt>
            <dd class="text-zinc-200">{Math.max(1, Math.min(100, maxNotes))}</dd>
          </div>
          <div class="flex gap-2">
            <dt class="text-zinc-500 w-28 shrink-0">Max chars</dt>
            <dd class="text-zinc-200">{Math.max(100, Math.min(500000, maxChars)).toLocaleString()}</dd>
          </div>
          <div class="flex gap-2 pt-1 border-t border-zinc-800 mt-1">
            <dt class="text-zinc-500 w-28 shrink-0">Scope note</dt>
            <dd class="text-zinc-400 italic">Backend will determine actual note count from your filters.</dd>
          </div>
        </dl>
      </div>

      <!-- Submit button -->
      <button
        type="button"
        on:click={handleScan}
        disabled={!canSubmit}
        class="w-full py-2.5 px-4 rounded-lg text-sm font-medium transition-colors
          {canSubmit
            ? 'bg-sky-700 hover:bg-sky-600 text-white'
            : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'}"
      >
        {#if submitState === 'loading'}
          Scanning...
        {:else}
          Run security scan
        {/if}
      </button>

    </div>

    <!-- ── Right: Result panel ────────────────────────────────── -->
    <div class="space-y-4">

      <!-- Loading -->
      {#if submitState === 'loading'}
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-6 flex items-center gap-3">
          <div class="w-4 h-4 border-2 border-sky-500 border-t-transparent rounded-full animate-spin shrink-0"></div>
          <span class="text-sm text-zinc-400">Running security scan...</span>
        </div>
      {/if}

      <!-- Error panel -->
      {#if submitState === 'error'}
        <div class="bg-red-950 border border-red-800 rounded-lg p-4">
          <p class="text-sm font-semibold text-red-300 mb-1">{errorTitle(submitErrorCode)}</p>
          <p class="text-sm text-red-400">{submitError}</p>
          {#if submitErrorCode === 'NETWORK_ERROR'}
            <p class="text-xs text-red-500 mt-2">Ensure the backend is running on <span class="font-mono">http://127.0.0.1:8000</span>.</p>
          {/if}
        </div>
      {/if}

      <!-- Idle state -->
      {#if submitState === 'idle'}
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
          <p class="text-sm text-zinc-500">Configure the scan on the left, then click <span class="font-medium text-zinc-300">Run security scan</span>.</p>
        </div>
      {/if}

      <!-- Success: scan result -->
      {#if submitState === 'ok' && scanResult}

        <!-- Overview panel -->
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <h2 class="text-sm font-semibold text-zinc-300">Scan Overview</h2>
            <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide {statusBadgeClass(scanResult.status)}">
              {scanResult.status}
            </span>
          </div>

          {#if scanResult.status === 'pass' && (scanResult.findings ?? []).length === 0}
            <div class="bg-emerald-950 border border-emerald-800 rounded-md p-3 mb-3">
              <p class="text-sm font-medium text-emerald-300">All checks passed. No findings.</p>
              <p class="text-xs text-emerald-500 mt-0.5">No credential leaks, injection patterns, or policy violations detected.</p>
            </div>
          {/if}

          <div class="grid grid-cols-2 gap-3">
            <div class="bg-zinc-800 rounded-md p-3">
              <p class="text-xs text-zinc-500 mb-1">Total findings</p>
              <p class="text-lg font-semibold text-zinc-100">{(scanResult.findings ?? []).length}</p>
            </div>
            <div class="bg-zinc-800 rounded-md p-3">
              <p class="text-xs text-zinc-500 mb-1">Notes scanned</p>
              <p class="text-lg font-semibold text-zinc-100">{scanResult.scanned?.note_count ?? 0}</p>
            </div>
            <div class="bg-red-950 border border-red-900 rounded-md p-3">
              <p class="text-xs text-red-500 mb-1">Fail</p>
              <p class="text-lg font-semibold text-red-300">{scanResult.summary?.fail ?? 0}</p>
            </div>
            <div class="bg-amber-950 border border-amber-900 rounded-md p-3">
              <p class="text-xs text-amber-500 mb-1">Warning</p>
              <p class="text-lg font-semibold text-amber-300">{scanResult.summary?.warning ?? 0}</p>
            </div>
            <div class="bg-sky-950 border border-sky-900 rounded-md p-3">
              <p class="text-xs text-sky-500 mb-1">Info</p>
              <p class="text-lg font-semibold text-sky-300">{scanResult.summary?.info ?? 0}</p>
            </div>
            <div class="bg-zinc-800 rounded-md p-3">
              <p class="text-xs text-zinc-500 mb-1">Source paths</p>
              <p class="text-lg font-semibold text-zinc-100">{(scanResult.scanned?.source_paths ?? []).length}</p>
            </div>
          </div>
        </div>

        <!-- Findings review -->
        {#if (scanResult.findings ?? []).length > 0}
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 class="text-sm font-semibold text-zinc-300 mb-3">
              Findings
              <span class="text-zinc-500 font-normal ml-1">({(scanResult.findings ?? []).length} total)</span>
            </h2>

            <!-- Severity filter -->
            <div class="flex flex-wrap gap-2 mb-3">
              {#each ['all', 'fail', 'warning', 'info'] as sev}
                <button
                  type="button"
                  on:click={() => { severityFilter = sev as SeverityFilter; }}
                  class:bg-sky-700={severityFilter === sev}
                  class:text-sky-100={severityFilter === sev}
                  class:border-sky-600={severityFilter === sev}
                  class:bg-zinc-800={severityFilter !== sev}
                  class:text-zinc-400={severityFilter !== sev}
                  class:border-zinc-700={severityFilter !== sev}
                  class="px-2.5 py-1 rounded-md text-xs font-medium border transition-colors"
                >
                  {sev}
                  {#if sev !== 'all'}
                    {#if sev === 'fail'}
                      <span class="text-red-400 ml-0.5">({scanResult.summary?.fail ?? 0})</span>
                    {:else if sev === 'warning'}
                      <span class="text-amber-400 ml-0.5">({scanResult.summary?.warning ?? 0})</span>
                    {:else if sev === 'info'}
                      <span class="text-sky-400 ml-0.5">({scanResult.summary?.info ?? 0})</span>
                    {/if}
                  {/if}
                </button>
              {/each}
            </div>

            <!-- Text filter -->
            <input
              bind:value={findingTextFilter}
              type="text"
              placeholder="Filter by path, rule, or detail..."
              class="w-full bg-zinc-800 border border-zinc-700 rounded-md px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-sky-600 mb-3"
            />

            <!-- Findings list -->
            {#if filteredFindings.length === 0}
              <p class="text-xs text-zinc-500 py-2">No findings match the current filter.</p>
            {:else}
              <div class="space-y-2">
                {#each filteredFindings as finding, i}
                  <div class="bg-zinc-800 border border-zinc-700 rounded-md overflow-hidden">
                    <!-- Finding header (always visible) -->
                    <button
                      type="button"
                      on:click={() => toggleFinding(i)}
                      class="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-zinc-750 transition-colors"
                    >
                      <span class="inline-flex shrink-0 items-center px-1.5 py-0.5 rounded text-xs font-semibold uppercase {severityClass(finding.severity)}">
                        {finding.severity}
                      </span>
                      <span class="text-xs text-zinc-200 font-mono truncate flex-1">{finding.path}</span>
                      <span class="text-xs text-zinc-500 shrink-0 font-mono">{finding.rule}</span>
                      <svg
                        class="w-3.5 h-3.5 text-zinc-500 shrink-0 transition-transform {expandedFindings.has(i) ? 'rotate-180' : ''}"
                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>

                    <!-- Expanded details -->
                    {#if expandedFindings.has(i)}
                      <div class="px-3 pb-3 border-t border-zinc-700 pt-2 space-y-1.5">
                        <div class="flex gap-2 text-xs">
                          <span class="text-zinc-500 w-16 shrink-0">Field</span>
                          <span class="text-zinc-200 font-mono">{finding.field}</span>
                        </div>
                        <div class="flex gap-2 text-xs">
                          <span class="text-zinc-500 w-16 shrink-0">Rule</span>
                          <span class="text-zinc-200 font-mono">{finding.rule}</span>
                        </div>
                        <div class="flex gap-2 text-xs">
                          <span class="text-zinc-500 w-16 shrink-0">Detail</span>
                          <span class="text-zinc-300">{finding.detail}</span>
                        </div>
                        <div class="flex gap-2 text-xs">
                          <span class="text-zinc-500 w-16 shrink-0">Path</span>
                          <span class="text-zinc-200 font-mono break-all">{finding.path}</span>
                        </div>
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}

        <!-- Affected notes panel -->
        {#if (scanResult.scanned?.source_paths ?? []).length > 0}
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 class="text-sm font-semibold text-zinc-300 mb-3">
              Scanned Notes
              <span class="text-zinc-500 font-normal ml-1">({(scanResult.scanned?.source_paths ?? []).length})</span>
            </h2>
            <div class="space-y-1">
              {#each affectedNotes as note}
                <div class="flex items-center gap-2 py-1.5 border-b border-zinc-800 last:border-0">
                  <span class="text-xs text-zinc-300 font-mono flex-1 truncate">{note.path}</span>
                  {#if note.count > 0}
                    <span class="text-xs text-zinc-500 shrink-0">{note.count} finding{note.count !== 1 ? 's' : ''}</span>
                    {#if note.severityCounts.fail > 0}
                      <span class="text-xs font-semibold text-red-400 shrink-0">{note.severityCounts.fail}F</span>
                    {/if}
                    {#if note.severityCounts.warning > 0}
                      <span class="text-xs font-semibold text-amber-400 shrink-0">{note.severityCounts.warning}W</span>
                    {/if}
                    {#if note.severityCounts.info > 0}
                      <span class="text-xs font-semibold text-sky-400 shrink-0">{note.severityCounts.info}I</span>
                    {/if}
                  {:else}
                    <span class="text-xs text-emerald-500 shrink-0">clean</span>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Rule summary panel -->
        {#if ruleSummary.length > 0}
          <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h2 class="text-sm font-semibold text-zinc-300 mb-3">Rule Summary</h2>
            <div class="space-y-1.5">
              {#each ruleSummary as item}
                <div class="flex items-center gap-2 text-xs">
                  <span class="inline-flex shrink-0 items-center px-1.5 py-0.5 rounded font-semibold uppercase {severityClass(item.highestSeverity)}">
                    {item.highestSeverity}
                  </span>
                  <span class="text-zinc-200 font-mono flex-1">{item.rule}</span>
                  <span class="text-zinc-500 shrink-0">{item.count}×</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Raw JSON (collapsed by default) -->
        <div class="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <button
            type="button"
            on:click={() => { showRawJson = !showRawJson; }}
            class="w-full flex items-center justify-between px-4 py-3 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
          >
            <span class="font-medium">Raw JSON response</span>
            <svg
              class="w-4 h-4 transition-transform {showRawJson ? 'rotate-180' : ''}"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {#if showRawJson}
            <div class="border-t border-zinc-800 p-4">
              <pre class="text-xs text-zinc-400 font-mono overflow-x-auto whitespace-pre-wrap break-all">{JSON.stringify(scanResult, null, 2)}</pre>
            </div>
          {/if}
        </div>

      {/if}
      <!-- end ok state -->

    </div>
    <!-- end right column -->

  </div>
  <!-- end grid -->

{/if}
