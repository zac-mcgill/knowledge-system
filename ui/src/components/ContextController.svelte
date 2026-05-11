<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchContextState,
    fetchContextPlan,
    isOk,
    type ContextStateData,
    type ContextPlanData,
    type ContextRecommendation,
  } from '../lib/api.ts';
  import { getStoredVault, setStoredVault } from '../lib/vaultState.ts';

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

  type Intent = 'review' | 'export' | 'agent-context' | 'quality' | 'security';
  const INTENTS: { value: Intent; label: string; description: string }[] = [
    { value: 'review', label: 'Review', description: 'General vault health and completeness' },
    { value: 'export', label: 'Export', description: 'Readiness for context bundle export' },
    { value: 'agent-context', label: 'Agent Context', description: 'Readiness for LLM agent use' },
    { value: 'quality', label: 'Quality', description: 'Content quality and coverage gaps' },
    { value: 'security', label: 'Security', description: 'Security findings and risks' },
  ];
  let selectedIntent: Intent = 'review';

  // ---------------------------------------------------------------------------
  // Load state
  // ---------------------------------------------------------------------------

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';
  let stateLoadState: LoadState = 'idle';
  let planLoadState: LoadState = 'idle';

  let stateData: ContextStateData | null = null;
  let planData: ContextPlanData | null = null;

  let stateError = '';
  let planError = '';

  // ---------------------------------------------------------------------------
  // UI state
  // ---------------------------------------------------------------------------

  let showRawStateJson = false;
  let showRawPlanJson = false;

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  onMount(async () => {
    const vr = await fetchVaults();
    vaultsLoading = false;
    if (!isOk(vr)) {
      vaultsError = vr.error.message;
      return;
    }
    vaultList = vr.data.vaults;
    const stored = getStoredVault();
    if (stored && vaultList.includes(stored)) {
      selectedVault = stored;
    } else if (vaultList.length > 0) {
      selectedVault = vaultList[0];
    }
    if (selectedVault) {
      await loadAll();
    }
  });

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  async function loadAll() {
    if (!selectedVault) return;
    await Promise.all([loadState(), loadPlan()]);
  }

  async function loadState() {
    stateLoadState = 'loading';
    stateData = null;
    stateError = '';
    const result = await fetchContextState(selectedVault);
    if (!isOk(result)) {
      stateLoadState = 'error';
      stateError = result.error.message;
      return;
    }
    stateData = result.data;
    stateLoadState = 'ok';
  }

  async function loadPlan() {
    planLoadState = 'loading';
    planData = null;
    planError = '';
    const result = await fetchContextPlan(selectedVault, selectedIntent);
    if (!isOk(result)) {
      planLoadState = 'error';
      planError = result.error.message;
      return;
    }
    planData = result.data;
    planLoadState = 'ok';
  }

  async function handleVaultChange() {
    if (selectedVault) {
      setStoredVault(selectedVault);
      await loadAll();
    }
  }

  async function handleIntentChange() {
    if (selectedVault) {
      await loadPlan();
    }
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  const SEVERITY_COLOUR: Record<string, string> = {
    critical: 'text-red-600',
    high: 'text-orange-600',
    medium: 'text-yellow-600',
    low: 'text-blue-500',
    info: 'text-gray-500',
  };

  const SEVERITY_BG: Record<string, string> = {
    critical: 'bg-red-50 border-red-200',
    high: 'bg-orange-50 border-orange-200',
    medium: 'bg-yellow-50 border-yellow-200',
    low: 'bg-blue-50 border-blue-200',
    info: 'bg-gray-50 border-gray-200',
  };

  function readinessBadge(ok: boolean): string {
    return ok ? '✅' : '❌';
  }
</script>

<!-- ======================================================================
     Layout
     ====================================================================== -->

<div class="max-w-5xl mx-auto px-4 py-8 space-y-8">

  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-gray-900">Context Controller</h1>
    <p class="mt-1 text-sm text-gray-500">
      The controller is deterministic. It does not call an LLM or make semantic judgements.
      All output is derived from the current state of your vault.
    </p>
  </div>

  <!-- ---- Controls ---- -->
  <div class="bg-white border border-gray-200 rounded-lg p-5 space-y-4">
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">

      <!-- Vault selector -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="vault-select">
          Vault
        </label>
        {#if vaultsLoading}
          <p class="text-sm text-gray-400">Loading vaults…</p>
        {:else if vaultsError}
          <p class="text-sm text-red-500">{vaultsError}</p>
        {:else}
          <select
            id="vault-select"
            bind:value={selectedVault}
            on:change={handleVaultChange}
            class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {#each vaultList as v}
              <option value={v}>{v}</option>
            {/each}
          </select>
        {/if}
      </div>

      <!-- Intent selector -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="intent-select">
          Planning Intent
        </label>
        <select
          id="intent-select"
          bind:value={selectedIntent}
          on:change={handleIntentChange}
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {#each INTENTS as intent}
            <option value={intent.value}>{intent.label} — {intent.description}</option>
          {/each}
        </select>
      </div>
    </div>

    <button
      on:click={loadAll}
      disabled={!selectedVault || stateLoadState === 'loading' || planLoadState === 'loading'}
      class="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {stateLoadState === 'loading' || planLoadState === 'loading' ? 'Loading…' : 'Refresh'}
    </button>
  </div>

  <!-- ========== State snapshot ========== -->
  <section>
    <h2 class="text-lg font-semibold text-gray-800 mb-3">Vault State</h2>

    {#if stateLoadState === 'idle'}
      <p class="text-sm text-gray-400">Select a vault to load the state snapshot.</p>
    {:else if stateLoadState === 'loading'}
      <p class="text-sm text-gray-400">Loading state…</p>
    {:else if stateLoadState === 'error'}
      <p class="text-sm text-red-500">Error: {stateError}</p>
    {:else if stateData}

      <!-- Readiness cards -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 mb-4">
        {#each Object.entries(stateData.readiness) as [key, val]}
          <div class="border rounded-lg p-3 bg-white flex items-start gap-2">
            <span class="text-lg leading-none">{readinessBadge(val)}</span>
            <div>
              <p class="text-xs font-medium text-gray-700">{key.replace(/_/g, ' ')}</p>
              <p class="text-xs text-gray-500">{val ? 'Yes' : 'No'}</p>
            </div>
          </div>
        {/each}
      </div>

      <!-- Service summary table -->
      <div class="bg-white border border-gray-200 rounded-lg overflow-hidden mb-4">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="text-left px-4 py-2 font-medium text-gray-600">Service</th>
              <th class="text-left px-4 py-2 font-medium text-gray-600">Status / Value</th>
            </tr>
          </thead>
          <tbody>
            <tr class="border-b border-gray-100">
              <td class="px-4 py-2 text-gray-700">Validation</td>
              <td class="px-4 py-2">
                <span class="font-mono text-xs {stateData.state.summary.validation_status === 'pass' ? 'text-green-600' : 'text-red-600'}">
                  {stateData.state.summary.validation_status}
                </span>
              </td>
            </tr>
            <tr class="border-b border-gray-100">
              <td class="px-4 py-2 text-gray-700">Security</td>
              <td class="px-4 py-2">
                <span class="font-mono text-xs {stateData.state.summary.security_status === 'pass' ? 'text-green-600' : stateData.state.summary.security_status === 'warning' ? 'text-yellow-600' : 'text-red-600'}">
                  {stateData.state.summary.security_status}
                </span>
              </td>
            </tr>
            <tr class="border-b border-gray-100">
              <td class="px-4 py-2 text-gray-700">Pending Tasks</td>
              <td class="px-4 py-2 font-mono text-xs">{stateData.state.summary.total_tasks}</td>
            </tr>
            <tr class="border-b border-gray-100">
              <td class="px-4 py-2 text-gray-700">Missing Concepts</td>
              <td class="px-4 py-2 font-mono text-xs">{stateData.state.summary.total_missing}</td>
            </tr>
            <tr class="border-b border-gray-100">
              <td class="px-4 py-2 text-gray-700">Feedback Entries</td>
              <td class="px-4 py-2 font-mono text-xs">{stateData.state.summary.feedback_entry_count}</td>
            </tr>
            <tr>
              <td class="px-4 py-2 text-gray-700">Graph Nodes</td>
              <td class="px-4 py-2 font-mono text-xs">{stateData.state.summary.graph_node_count}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Blockers -->
      {#if stateData.blockers.length > 0}
        <div class="mb-3">
          <h3 class="text-sm font-semibold text-red-700 mb-1">Blockers</h3>
          <ul class="space-y-1">
            {#each stateData.blockers as b}
              <li class="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">⛔ {b}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- Warnings -->
      {#if stateData.warnings.length > 0}
        <div class="mb-3">
          <h3 class="text-sm font-semibold text-yellow-700 mb-1">Warnings</h3>
          <ul class="space-y-1">
            {#each stateData.warnings as w}
              <li class="text-sm text-yellow-700 bg-yellow-50 border border-yellow-200 rounded px-3 py-2">⚠ {w}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- Raw JSON toggle -->
      <button
        on:click={() => showRawStateJson = !showRawStateJson}
        class="text-xs text-gray-400 hover:text-gray-600 underline"
      >
        {showRawStateJson ? 'Hide' : 'Show'} raw JSON
      </button>
      {#if showRawStateJson}
        <pre class="mt-2 text-xs bg-gray-50 border border-gray-200 rounded p-3 overflow-auto max-h-64">{JSON.stringify(stateData, null, 2)}</pre>
      {/if}
    {/if}
  </section>

  <!-- ========== Recommendation plan ========== -->
  <section>
    <h2 class="text-lg font-semibold text-gray-800 mb-3">
      Recommendation Plan
      <span class="ml-2 text-sm font-normal text-gray-400">({selectedIntent})</span>
    </h2>

    {#if planLoadState === 'idle'}
      <p class="text-sm text-gray-400">Select a vault and intent to generate a plan.</p>
    {:else if planLoadState === 'loading'}
      <p class="text-sm text-gray-400">Building plan…</p>
    {:else if planLoadState === 'error'}
      <p class="text-sm text-red-500">Error: {planError}</p>
    {:else if planData}

      <!-- Next best action banner -->
      {#if planData.next_best_action}
        <div class="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p class="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">Next Best Action</p>
          <p class="text-sm font-medium text-blue-900">{planData.next_best_action.title}</p>
          <p class="text-xs text-blue-600 font-mono">{planData.next_best_action.action}</p>
        </div>
      {:else}
        <div class="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p class="text-sm text-green-800">✅ No actions required for this intent.</p>
        </div>
      {/if}

      <!-- Recommendations list -->
      {#if planData.recommendations.length > 0}
        <div class="space-y-3 mb-4">
          {#each planData.recommendations as rec}
            <div class="border rounded-lg p-4 {SEVERITY_BG[rec.severity] ?? 'bg-white border-gray-200'}">
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1">
                  <div class="flex items-center gap-2 mb-1">
                    <span class="text-xs font-bold text-gray-400">#{rec.rank}</span>
                    <span class="text-sm font-semibold text-gray-800">{rec.title}</span>
                    <span class="text-xs px-1.5 py-0.5 rounded font-medium {SEVERITY_COLOUR[rec.severity] ?? 'text-gray-500'} bg-white border border-current">
                      {rec.severity}
                    </span>
                  </div>
                  <p class="text-sm text-gray-600 mb-2">{rec.reason}</p>
                  <div class="flex gap-3 text-xs">
                    <a href={rec.links.ui} class="text-blue-600 hover:underline">Open in UI</a>
                    <span class="text-gray-300">|</span>
                    <span class="text-gray-400 font-mono">{rec.links.api}</span>
                  </div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}

      <!-- Raw JSON toggle -->
      <button
        on:click={() => showRawPlanJson = !showRawPlanJson}
        class="text-xs text-gray-400 hover:text-gray-600 underline"
      >
        {showRawPlanJson ? 'Hide' : 'Show'} raw JSON
      </button>
      {#if showRawPlanJson}
        <pre class="mt-2 text-xs bg-gray-50 border border-gray-200 rounded p-3 overflow-auto max-h-64">{JSON.stringify(planData, null, 2)}</pre>
      {/if}
    {/if}
  </section>

</div>
