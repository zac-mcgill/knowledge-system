<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchTrustSummary,
    fetchStaleSummary,
    buildEvidence,
    isOk,
    type TrustSummaryData,
    type StaleSummaryData,
    type EvidenceData,
    type EvidenceNote,
    type TrustNoteSummary,
  } from '../lib/api.ts';
  import { getStoredVault } from '../lib/vaultState.ts';

  // ---------------------------------------------------------------------------
  // Vault selector state
  // ---------------------------------------------------------------------------

  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';
  let selectedVault = '';

  // ---------------------------------------------------------------------------
  // Trust / Stale state
  // ---------------------------------------------------------------------------

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

  let trustState: LoadState = 'idle';
  let trustData: TrustSummaryData | null = null;
  let trustError = '';

  let staleState: LoadState = 'idle';
  let staleData: StaleSummaryData | null = null;
  let staleError = '';

  // ---------------------------------------------------------------------------
  // Evidence builder form state
  // ---------------------------------------------------------------------------

  let evidenceQuery = '';
  let evidencePreferVerified = true;
  let evidenceIncludeDeprecated = false;
  let evidenceIncludeStale = true;
  let evidenceMaxNotes = 20;

  let evidenceState: LoadState = 'idle';
  let evidenceData: EvidenceData | null = null;
  let evidenceError = '';
  let showEvidenceRaw = false;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  onMount(async () => {
    const stored = getStoredVault();
    const resp = await fetchVaults();
    vaultsLoading = false;
    if (!isOk(resp)) {
      vaultsError = resp.error?.message ?? 'Failed to load vaults';
      return;
    }
    vaultList = resp.data.vaults;
    selectedVault = stored && vaultList.includes(stored) ? stored : (vaultList[0] ?? '');
    if (selectedVault) await loadTrustData();
  });

  // ---------------------------------------------------------------------------
  // Loaders
  // ---------------------------------------------------------------------------

  async function loadTrustData() {
    if (!selectedVault) return;
    trustState = 'loading';
    staleState = 'loading';
    trustData = null;
    staleData = null;
    trustError = '';
    staleError = '';

    const [tr, sr] = await Promise.all([
      fetchTrustSummary(selectedVault),
      fetchStaleSummary(selectedVault),
    ]);

    if (isOk(tr)) {
      trustData = tr.data;
      trustState = 'ok';
    } else {
      trustError = tr.error?.message ?? 'Failed to load trust summary';
      trustState = 'error';
    }

    if (isOk(sr)) {
      staleData = sr.data;
      staleState = 'ok';
    } else {
      staleError = sr.error?.message ?? 'Failed to load stale notes';
      staleState = 'error';
    }
  }

  async function runBuildEvidence() {
    if (!selectedVault) return;
    evidenceState = 'loading';
    evidenceData = null;
    evidenceError = '';
    showEvidenceRaw = false;

    const resp = await buildEvidence({
      vault: selectedVault,
      q: evidenceQuery.trim() || undefined,
      prefer_verified: evidencePreferVerified,
      include_deprecated: evidenceIncludeDeprecated,
      include_stale: evidenceIncludeStale,
      max_notes: evidenceMaxNotes,
    });

    if (isOk(resp)) {
      evidenceData = resp.data;
      evidenceState = 'ok';
    } else {
      evidenceError = resp.error?.message ?? 'Failed to build evidence';
      evidenceState = 'error';
    }
  }

  function handleVaultChange(e: Event) {
    selectedVault = (e.target as HTMLSelectElement).value;
    trustData = null;
    staleData = null;
    evidenceData = null;
    trustState = 'idle';
    staleState = 'idle';
    evidenceState = 'idle';
    if (selectedVault) loadTrustData();
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function confidenceBadge(c: string): string {
    if (c === 'high') return 'bg-emerald-700 text-emerald-100';
    if (c === 'medium') return 'bg-yellow-700 text-yellow-100';
    if (c === 'low') return 'bg-orange-700 text-orange-100';
    if (c === 'deprecated') return 'bg-red-800 text-red-100';
    return 'bg-zinc-600 text-zinc-200';
  }

  function trustBadge(t: string | null): string {
    if (t === 'verified') return 'bg-emerald-700 text-emerald-100';
    if (t === 'working') return 'bg-blue-700 text-blue-100';
    if (t === 'draft') return 'bg-yellow-700 text-yellow-100';
    if (t === 'external') return 'bg-purple-700 text-purple-100';
    if (t === 'deprecated') return 'bg-red-800 text-red-100';
    return 'bg-zinc-600 text-zinc-200';
  }

  function countBadge(n: number): string {
    return n === 0 ? 'text-zinc-400' : 'text-zinc-100 font-semibold';
  }
</script>

<div class="p-6 space-y-8">

  <!-- Page Header -->
  <div>
    <h1 class="text-2xl font-bold text-zinc-100">Trust &amp; Evidence</h1>
    <p class="mt-1 text-sm text-zinc-400">
      View trust metadata, staleness, and build evidence responses from vault notes.
      Confidence levels reflect note maintenance status — not factual accuracy.
    </p>
  </div>

  <!-- Vault Selector -->
  <div class="flex items-center gap-3">
    <label for="vault-select" class="text-sm font-medium text-zinc-300">Vault:</label>
    {#if vaultsLoading}
      <span class="text-sm text-zinc-500">Loading vaults…</span>
    {:else if vaultsError}
      <span class="text-sm text-red-400">{vaultsError}</span>
    {:else}
      <select
        id="vault-select"
        value={selectedVault}
        on:change={handleVaultChange}
        class="bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        {#each vaultList as vault}
          <option value={vault}>{vault}</option>
        {/each}
      </select>
    {/if}
  </div>

  <!-- Trust Summary Cards -->
  {#if trustState === 'loading'}
    <p class="text-sm text-zinc-400">Loading trust summary…</p>
  {:else if trustState === 'error'}
    <div class="rounded bg-red-900/40 border border-red-700 p-4 text-sm text-red-300">{trustError}</div>
  {:else if trustState === 'ok' && trustData}
    <section>
      <h2 class="text-lg font-semibold text-zinc-200 mb-3">Trust Summary</h2>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="rounded bg-zinc-800 border border-zinc-700 p-4">
          <div class="text-2xl font-bold text-zinc-100">{trustData.total_notes}</div>
          <div class="text-xs text-zinc-400 mt-1">Total Notes</div>
        </div>
        <div class="rounded bg-zinc-800 border border-zinc-700 p-4">
          <div class="text-2xl font-bold text-red-400">{trustData.stale_count}</div>
          <div class="text-xs text-zinc-400 mt-1">Stale</div>
        </div>
        <div class="rounded bg-zinc-800 border border-zinc-700 p-4">
          <div class="text-2xl font-bold text-orange-400">{trustData.deprecated_count}</div>
          <div class="text-xs text-zinc-400 mt-1">Deprecated</div>
        </div>
        <div class="rounded bg-zinc-800 border border-zinc-700 p-4">
          <div class="text-2xl font-bold text-zinc-400">{trustData.missing_trust_metadata}</div>
          <div class="text-xs text-zinc-400 mt-1">Missing Metadata</div>
        </div>
      </div>

      <!-- By Trust Level -->
      <div class="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3">
        {#each Object.entries(trustData.by_trust_level) as [level, count]}
          <div class="rounded bg-zinc-800 border border-zinc-700 p-3 flex items-center gap-2">
            <span class="text-xs px-2 py-0.5 rounded-full font-medium {trustBadge(level)}">{level}</span>
            <span class="{countBadge(count)}">{count}</span>
          </div>
        {/each}
      </div>

      <!-- By Confidence -->
      <div class="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-3">
        {#each Object.entries(trustData.by_confidence) as [conf, count]}
          <div class="rounded bg-zinc-800 border border-zinc-700 p-3 flex items-center gap-2">
            <span class="text-xs px-2 py-0.5 rounded-full font-medium {confidenceBadge(conf)}">{conf}</span>
            <span class="{countBadge(count)}">{count}</span>
          </div>
        {/each}
      </div>
    </section>
  {/if}

  <!-- Stale Notes Table -->
  {#if staleState === 'ok' && staleData}
    <section>
      <h2 class="text-lg font-semibold text-zinc-200 mb-3">
        Stale Notes
        <span class="text-sm font-normal text-zinc-400 ml-2">({staleData.stale.length} stale)</span>
      </h2>

      {#if staleData.stale.length === 0}
        <p class="text-sm text-zinc-500">No stale notes — all notes are within their review dates.</p>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm border-collapse">
            <thead>
              <tr class="border-b border-zinc-700 text-left text-zinc-400">
                <th class="py-2 pr-4 font-medium">Path</th>
                <th class="py-2 pr-4 font-medium">Trust</th>
                <th class="py-2 pr-4 font-medium">Confidence</th>
                <th class="py-2 pr-4 font-medium">Review After</th>
                <th class="py-2 font-medium">Last Reviewed</th>
              </tr>
            </thead>
            <tbody>
              {#each staleData.stale as note}
                <tr class="border-b border-zinc-800 hover:bg-zinc-800/50">
                  <td class="py-2 pr-4 text-zinc-300 font-mono text-xs">{note.path}</td>
                  <td class="py-2 pr-4">
                    <span class="text-xs px-1.5 py-0.5 rounded {trustBadge(note.trust_level)}">{note.trust_level ?? '—'}</span>
                  </td>
                  <td class="py-2 pr-4">
                    <span class="text-xs px-1.5 py-0.5 rounded {confidenceBadge(note.confidence)}">{note.confidence}</span>
                  </td>
                  <td class="py-2 pr-4 text-red-400 text-xs">{note.review_after ?? '—'}</td>
                  <td class="py-2 text-zinc-400 text-xs">{note.last_reviewed ?? '—'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      <!-- Missing review_after -->
      {#if staleData.freshness_unknown.length > 0}
        <div class="mt-4">
          <h3 class="text-sm font-semibold text-zinc-300 mb-2">
            Freshness Unknown ({staleData.freshness_unknown.length})
            <span class="text-xs font-normal text-zinc-500 ml-1">— no review_after set</span>
          </h3>
          <ul class="space-y-1">
            {#each staleData.freshness_unknown as note}
              <li class="text-xs text-zinc-400 font-mono">{note.path}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- Deprecated -->
      {#if staleData.deprecated.length > 0}
        <div class="mt-4">
          <h3 class="text-sm font-semibold text-zinc-300 mb-2">
            Deprecated ({staleData.deprecated.length})
          </h3>
          <ul class="space-y-1">
            {#each staleData.deprecated as note}
              <li class="text-xs font-mono">
                <span class="text-red-400">{note.path}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    </section>
  {:else if staleState === 'error'}
    <div class="rounded bg-red-900/40 border border-red-700 p-4 text-sm text-red-300">{staleError}</div>
  {/if}

  <!-- Evidence Builder -->
  <section>
    <h2 class="text-lg font-semibold text-zinc-200 mb-3">Evidence Builder</h2>
    <p class="text-sm text-zinc-400 mb-4">
      Build a trust-ranked evidence response. Notes are sorted by trust score (verified first) when prefer_verified is on.
    </p>

    <div class="grid gap-4 sm:grid-cols-2">
      <div>
        <label class="block text-xs font-medium text-zinc-400 mb-1" for="ev-query">Query (optional)</label>
        <input
          id="ev-query"
          type="text"
          bind:value={evidenceQuery}
          placeholder="e.g. sorting algorithms"
          class="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>
      <div>
        <label class="block text-xs font-medium text-zinc-400 mb-1" for="ev-max-notes">Max Notes</label>
        <input
          id="ev-max-notes"
          type="number"
          min="1"
          max="100"
          bind:value={evidenceMaxNotes}
          class="w-full bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>
    </div>

    <div class="flex flex-wrap gap-4 mt-4">
      <label class="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
        <input type="checkbox" bind:checked={evidencePreferVerified} class="rounded" />
        Prefer verified
      </label>
      <label class="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
        <input type="checkbox" bind:checked={evidenceIncludeStale} class="rounded" />
        Include stale
      </label>
      <label class="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
        <input type="checkbox" bind:checked={evidenceIncludeDeprecated} class="rounded" />
        Include deprecated
      </label>
    </div>

    <div class="mt-4">
      <button
        on:click={runBuildEvidence}
        disabled={!selectedVault || evidenceState === 'loading'}
        class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded font-medium transition-colors"
      >
        {evidenceState === 'loading' ? 'Building…' : 'Build Evidence'}
      </button>
    </div>

    {#if evidenceState === 'error'}
      <div class="mt-4 rounded bg-red-900/40 border border-red-700 p-4 text-sm text-red-300">{evidenceError}</div>
    {/if}

    {#if evidenceState === 'ok' && evidenceData}
      <div class="mt-6 space-y-4">
        <!-- Disclaimer -->
        <div class="rounded bg-yellow-900/30 border border-yellow-700/50 px-4 py-3 text-xs text-yellow-300">
          <strong>Confidence Disclaimer:</strong> {evidenceData.confidence_disclaimer}
        </div>

        <!-- Summary -->
        <div class="flex flex-wrap gap-3 text-sm">
          <span class="text-zinc-400">
            <span class="font-semibold text-zinc-200">{evidenceData.summary.total_notes}</span> note(s)
          </span>
          {#if evidenceData.summary.deprecated_excluded > 0}
            <span class="text-orange-400">{evidenceData.summary.deprecated_excluded} deprecated excluded</span>
          {/if}
          {#if evidenceData.summary.stale_excluded > 0}
            <span class="text-red-400">{evidenceData.summary.stale_excluded} stale excluded</span>
          {/if}
          {#each Object.entries(evidenceData.summary.by_confidence) as [conf, count]}
            <span class="text-xs px-2 py-0.5 rounded-full {confidenceBadge(conf)}">{conf}: {count}</span>
          {/each}
        </div>

        <!-- Evidence notes list -->
        <div class="space-y-3">
          {#each evidenceData.evidence as note}
            <div class="rounded bg-zinc-800 border border-zinc-700 p-4">
              <div class="flex flex-wrap items-center gap-2 mb-2">
                <span class="font-mono text-sm text-zinc-200 font-semibold">{note.path}</span>
                {#if note.trust_level}
                  <span class="text-xs px-1.5 py-0.5 rounded {trustBadge(note.trust_level)}">{note.trust_level}</span>
                {/if}
                <span class="text-xs px-1.5 py-0.5 rounded {confidenceBadge(note.confidence)}">{note.confidence}</span>
                {#if note.stale}
                  <span class="text-xs px-1.5 py-0.5 rounded bg-red-800 text-red-200">stale</span>
                {/if}
                {#if note.source_type}
                  <span class="text-xs text-zinc-500">{note.source_type}</span>
                {/if}
              </div>

              {#if Object.keys(note.sections).length > 0}
                <div class="mt-2 space-y-2">
                  {#each Object.entries(note.sections) as [sectionName, sectionBody]}
                    <div>
                      <div class="text-xs font-semibold text-zinc-400 mb-0.5">{sectionName}</div>
                      <div class="text-xs text-zinc-300 whitespace-pre-wrap line-clamp-4">{sectionBody}</div>
                    </div>
                  {/each}
                </div>
              {:else if note.body_excerpt}
                <p class="mt-1 text-xs text-zinc-400 line-clamp-3">{note.body_excerpt}</p>
              {/if}

              <div class="mt-2 text-xs text-zinc-500">
                Trust score: {note.trust_score}
                {#if note.last_reviewed} · last reviewed: {note.last_reviewed}{/if}
                {#if note.review_after} · review after: {note.review_after}{/if}
              </div>
            </div>
          {/each}
        </div>

        <!-- Raw JSON toggle -->
        <div class="mt-4">
          <button
            on:click={() => (showEvidenceRaw = !showEvidenceRaw)}
            class="text-xs text-zinc-500 hover:text-zinc-300 underline"
          >
            {showEvidenceRaw ? 'Hide' : 'Show'} raw JSON
          </button>
          {#if showEvidenceRaw}
            <pre class="mt-2 text-xs bg-zinc-900 border border-zinc-700 rounded p-4 overflow-x-auto text-zinc-300">{JSON.stringify(evidenceData, null, 2)}</pre>
          {/if}
        </div>
      </div>
    {/if}
  </section>

</div>
