<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchHealth,
    fetchVaults,
    fetchSummary,
    fetchValidation,
    fetchTasks,
    fetchMissing,
    fetchFeedback,
    fetchSecurity,
    isOk,
    errorMessage,
    type HealthData,
    type SummaryData,
    type ValidationData,
    type TasksData,
    type MissingData,
    type FeedbackData,
    type SecurityData,
  } from '../lib/api.ts';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  type LoadState = 'idle' | 'loading' | 'ok' | 'error' | 'warning';

  // Health
  let healthState: LoadState = 'loading';
  let healthData: HealthData | null = null;
  let healthError = '';

  // Vaults
  let vaultsState: LoadState = 'loading';
  let vaultList: string[] = [];
  let selectedVault = '';
  let vaultsError = '';

  // Summary
  let summaryState: LoadState = 'idle';
  let summaryData: SummaryData | null = null;
  let summaryError = '';

  // Validation
  let validationState: LoadState = 'idle';
  let validationData: ValidationData | null = null;
  let validationError = '';

  // Tasks
  let tasksState: LoadState = 'idle';
  let tasksData: TasksData | null = null;
  let tasksError = '';

  // Missing concepts
  let missingState: LoadState = 'idle';
  let missingData: MissingData | null = null;
  let missingError = '';

  // Feedback
  let feedbackState: LoadState = 'idle';
  let feedbackData: FeedbackData | null = null;
  let feedbackError = '';

  // Security
  let securityState: LoadState = 'idle';
  let securityData: SecurityData | null = null;
  let securityError = '';

  // Issue Review section
  type IssueTab = 'validation' | 'tasks' | 'security' | 'missing' | 'feedback';
  let activeIssueTab: IssueTab = 'validation';
  let expandedTaskIds: Set<number> = new Set();

  function toggleTask(idx: number) {
    if (expandedTaskIds.has(idx)) {
      expandedTaskIds.delete(idx);
    } else {
      expandedTaskIds.add(idx);
    }
    expandedTaskIds = expandedTaskIds; // trigger Svelte reactivity
  }

  $: isLoading =
    healthState === 'loading' ||
    summaryState === 'loading' ||
    validationState === 'loading' ||
    tasksState === 'loading' ||
    missingState === 'loading' ||
    feedbackState === 'loading' ||
    securityState === 'loading';

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function formatUptime(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  }

  function severityClass(sev: string): string {
    const s = sev.toLowerCase();
    if (s === 'error' || s === 'critical' || s === 'high' || s === 'fail')
      return 'text-red-400 bg-red-950 border border-red-800';
    if (s === 'warning' || s === 'medium')
      return 'text-amber-400 bg-amber-950 border border-amber-800';
    return 'text-zinc-400 bg-zinc-800 border border-zinc-700';
  }

  function priorityColor(p: number): string {
    if (p >= 4) return 'text-red-400 bg-red-950 border border-red-800';
    if (p >= 2) return 'text-amber-400 bg-amber-950 border border-amber-800';
    return 'text-zinc-400 bg-zinc-800 border border-zinc-700';
  }

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  async function loadHealth() {
    healthState = 'loading';
    const result = await fetchHealth();
    if (isOk(result)) {
      healthData = result.data;
      healthState = 'ok';
    } else {
      healthError = errorMessage(result);
      healthState = 'error';
    }
  }

  async function loadVaults() {
    vaultsState = 'loading';
    const result = await fetchVaults();
    if (isOk(result)) {
      vaultList = result.data.vaults;
      if (vaultList.length > 0 && !selectedVault) {
        selectedVault = vaultList[0];
      }
      vaultsState = 'ok';
    } else {
      vaultsError = errorMessage(result);
      vaultsState = 'error';
    }
  }

  async function loadVaultData(vault: string) {
    if (!vault) return;

    summaryState    = 'loading'; summaryData    = null; summaryError    = '';
    validationState = 'loading'; validationData = null; validationError = '';
    tasksState      = 'loading'; tasksData      = null; tasksError      = '';
    missingState    = 'loading'; missingData    = null; missingError    = '';
    feedbackState   = 'loading'; feedbackData   = null; feedbackError   = '';
    securityState   = 'loading'; securityData   = null; securityError   = '';
    expandedTaskIds = new Set();

    const [sResult, vResult, tResult, mResult, fbResult, secResult] = await Promise.all([
      fetchSummary(vault),
      fetchValidation(vault),
      fetchTasks(vault, { limit: 5, include_feedback: true }),
      fetchMissing(vault),
      fetchFeedback(vault),
      fetchSecurity(vault),
    ]);

    if (isOk(sResult)) { summaryData = sResult.data; summaryState = 'ok'; }
    else { summaryError = errorMessage(sResult); summaryState = 'error'; }

    if (isOk(vResult)) { validationData = vResult.data; validationState = 'ok'; }
    else { validationError = errorMessage(vResult); validationState = 'error'; }

    if (isOk(tResult)) { tasksData = tResult.data; tasksState = 'ok'; }
    else { tasksError = errorMessage(tResult); tasksState = 'error'; }

    if (isOk(mResult)) {
      missingData = mResult.data;
      missingState = 'ok';
    } else {
      if (mResult.error?.code === 'MISSING_CONCEPTS_EMPTY') {
        missingError = 'No expected concepts are defined in vault_schema.py.';
        missingState = 'warning';
      } else {
        missingError = errorMessage(mResult);
        missingState = 'error';
      }
    }

    if (isOk(fbResult)) {
      feedbackData = fbResult.data;
      feedbackState = fbResult.data.status === 'error' ? 'error' : 'ok';
      if (fbResult.data.status === 'error') {
        feedbackError = 'Feedback file has validation errors.';
      }
    } else {
      feedbackError = errorMessage(fbResult);
      feedbackState = 'error';
    }

    if (isOk(secResult)) { securityData = secResult.data; securityState = 'ok'; }
    else { securityError = errorMessage(secResult); securityState = 'error'; }
  }

  async function handleVaultChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedVault = select.value;
    await loadVaultData(selectedVault);
  }

  async function refresh() {
    if (isLoading) return;
    await loadHealth();
    if (selectedVault) {
      await loadVaultData(selectedVault);
    }
  }

  onMount(async () => {
    await loadHealth();
    await loadVaults();
    if (selectedVault) {
      await loadVaultData(selectedVault);
    }
  });
</script>

<!-- =========================================================
     Dashboard
     ========================================================= -->

<div class="space-y-6">

  <!-- ── Header: title + vault selector + refresh ── -->
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-xl font-semibold text-zinc-100">Dashboard</h1>
      <p class="text-sm text-zinc-500 mt-0.5">Live vault health from the Context Vault Engine API.</p>
    </div>
    <div class="flex items-center gap-3 flex-wrap">

      {#if vaultsState === 'loading'}
        <span class="text-sm text-zinc-500">Loading vaults…</span>
      {:else if vaultsState === 'error'}
        <span class="text-sm text-red-400">{vaultsError}</span>
      {:else if vaultList.length === 0}
        <span class="text-sm text-zinc-500">
          No vaults — <a href="/app/vault-setup" class="text-sky-400 hover:underline">set one up</a>
        </span>
      {:else if vaultList.length === 1}
        <span class="text-sm text-zinc-400">
          Vault: <span class="text-zinc-200 font-medium">{selectedVault}</span>
        </span>
      {:else}
        <div class="flex items-center gap-2">
          <label for="vault-select" class="text-sm text-zinc-400">Vault:</label>
          <select
            id="vault-select"
            value={selectedVault}
            on:change={handleVaultChange}
            class="bg-zinc-800 border border-zinc-700 text-zinc-100 text-sm rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-sky-500"
          >
            {#each vaultList as v}
              <option value={v}>{v}</option>
            {/each}
          </select>
        </div>
      {/if}

      <button
        on:click={refresh}
        disabled={isLoading}
        class="flex items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed border border-zinc-700 text-zinc-300 hover:text-zinc-100 text-sm px-3 py-1.5 rounded transition-colors"
        title="Refresh all dashboard data"
      >
        <svg
          class="w-3.5 h-3.5 {isLoading ? 'animate-spin' : ''}"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        {isLoading ? 'Loading…' : 'Refresh'}
      </button>
    </div>
  </div>

  <!-- ── Top health row: 4 status mini-cards ── -->
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">

    <!-- API health -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 flex items-center justify-between gap-2">
      <div class="min-w-0">
        <div class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">API</div>
        {#if healthState === 'loading'}
          <div class="text-sm text-zinc-400">Checking…</div>
        {:else if healthState === 'ok' && healthData}
          <div class="text-sm font-medium text-zinc-200 truncate">{formatUptime(healthData.uptime_seconds)} uptime</div>
        {:else}
          <div class="text-sm text-red-400">Unavailable</div>
        {/if}
      </div>
      <span class="shrink-0 w-2.5 h-2.5 rounded-full
        {healthState === 'loading' ? 'bg-zinc-600 animate-pulse' :
         healthState === 'ok' ? 'bg-emerald-400' : 'bg-red-400'}">
      </span>
    </div>

    <!-- Vault -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 flex items-center justify-between gap-2">
      <div class="min-w-0">
        <div class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Vault</div>
        {#if vaultsState === 'loading'}
          <div class="text-sm text-zinc-400">Loading…</div>
        {:else if selectedVault}
          <div class="text-sm font-medium text-zinc-200 truncate" title={selectedVault}>{selectedVault}</div>
        {:else}
          <div class="text-sm text-zinc-500">None</div>
        {/if}
      </div>
      {#if vaultsState === 'ok' && vaultList.length > 0}
        <span class="shrink-0 text-xs text-zinc-600 font-mono">{vaultList.length}</span>
      {/if}
    </div>

    <!-- Validation status -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 flex items-center justify-between gap-2">
      <div class="min-w-0">
        <div class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Validation</div>
        {#if validationState === 'loading'}
          <div class="text-sm text-zinc-400">Checking…</div>
        {:else if validationState === 'ok' && validationData}
          <div class="text-sm font-medium {validationData.status === 'pass' ? 'text-emerald-400' : 'text-red-400'}">
            {validationData.status === 'pass' ? 'Pass' : `${validationData.invalid_count} invalid`}
          </div>
        {:else if validationState === 'idle'}
          <div class="text-sm text-zinc-600">—</div>
        {:else}
          <div class="text-sm text-red-400">Error</div>
        {/if}
      </div>
      <span class="shrink-0 w-2.5 h-2.5 rounded-full
        {validationState === 'loading' ? 'bg-zinc-600 animate-pulse' :
         validationState === 'ok' && validationData?.status === 'pass' ? 'bg-emerald-400' :
         validationState === 'ok' ? 'bg-red-400' :
         'bg-zinc-700'}">
      </span>
    </div>

    <!-- Security status -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-3 flex items-center justify-between gap-2">
      <div class="min-w-0">
        <div class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Security</div>
        {#if securityState === 'loading'}
          <div class="text-sm text-zinc-400">Scanning…</div>
        {:else if securityState === 'ok' && securityData}
          <div class="text-sm font-medium
            {securityData.status === 'pass' ? 'text-emerald-400' :
             securityData.status === 'warning' ? 'text-amber-400' : 'text-red-400'}">
            {securityData.status === 'pass'
              ? 'Pass'
              : securityData.status === 'warning'
              ? `${securityData.summary.warning} warning${securityData.summary.warning !== 1 ? 's' : ''}`
              : `${securityData.summary.fail} failure${securityData.summary.fail !== 1 ? 's' : ''}`}
          </div>
        {:else if securityState === 'idle'}
          <div class="text-sm text-zinc-600">—</div>
        {:else}
          <div class="text-sm text-red-400">Error</div>
        {/if}
      </div>
      <span class="shrink-0 w-2.5 h-2.5 rounded-full
        {securityState === 'loading' ? 'bg-zinc-600 animate-pulse' :
         securityState === 'ok' && securityData?.status === 'pass' ? 'bg-emerald-400' :
         securityState === 'ok' && securityData?.status === 'warning' ? 'bg-amber-400' :
         securityState === 'ok' ? 'bg-red-400' :
         'bg-zinc-700'}">
      </span>
    </div>

  </div><!-- end top health row -->

  <!-- ── Main card grid ── -->
  <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">

    <!-- ── Server Health card ── -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Server</span>
        {#if healthState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>Loading
          </span>
        {:else if healthState === 'ok'}
          <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>Online
          </span>
        {:else}
          <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>Offline
          </span>
        {/if}
      </div>

      {#if healthState === 'loading'}
        <div class="space-y-2">
          <div class="h-4 bg-zinc-800 rounded animate-pulse w-3/4"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-2/3"></div>
        </div>
      {:else if healthState === 'ok' && healthData}
        <div class="space-y-1.5">
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Uptime</span>
            <span class="text-zinc-200 font-mono">{formatUptime(healthData.uptime_seconds)}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Requests served</span>
            <span class="text-zinc-200 font-mono">{healthData.requests_served}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Avg latency</span>
            <span class="text-zinc-200 font-mono">{healthData.metrics.avg_response_time_ms.toFixed(1)} ms</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Rate limit</span>
            <span class="text-zinc-200 font-mono">{healthData.rate_limit_status.max_per_second}/s</span>
          </div>
        </div>
        <details class="mt-3">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(healthData, null, 2)}</pre>
        </details>
      {:else}
        <p class="text-sm text-red-400">{healthError || 'Backend unavailable — is the server running?'}</p>
        <p class="text-xs text-zinc-600 mt-1">Start: py mcp/server/mcp_server.py</p>
      {/if}
    </div>

    <!-- ── Vault Summary card ── -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Coverage</span>
        {#if summaryState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>Loading
          </span>
        {:else if summaryState === 'ok' && summaryData}
          <span class="text-xs font-mono font-medium text-sky-400">{summaryData.coverage}%</span>
        {:else if summaryState === 'idle'}
          <span class="text-xs text-zinc-600">—</span>
        {:else}
          <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">Error</span>
        {/if}
      </div>

      {#if summaryState === 'loading'}
        <div class="space-y-2">
          <div class="h-4 bg-zinc-800 rounded animate-pulse w-3/4"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-2/3"></div>
        </div>
      {:else if summaryState === 'ok' && summaryData}
        <div class="space-y-1.5">
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Total notes</span>
            <span class="text-zinc-200 font-mono">{summaryData.total_notes}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Complete</span>
            <span class="text-emerald-400 font-mono">{summaryData.complete}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Partial</span>
            <span class="text-amber-400 font-mono">{summaryData.partial}</span>
          </div>
        </div>
        <div class="mt-3">
          <div class="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
            <div
              class="h-full bg-sky-500 rounded-full transition-all"
              style="width: {summaryData.coverage}%"
            ></div>
          </div>
        </div>
        <details class="mt-3">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(summaryData, null, 2)}</pre>
        </details>
      {:else if summaryState === 'idle'}
        <p class="text-sm text-zinc-600">Select a vault to load summary.</p>
      {:else}
        <p class="text-sm text-red-400">{summaryError}</p>
      {/if}
    </div>

    <!-- ── Validation card ── -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Validation</span>
        {#if validationState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>Loading
          </span>
        {:else if validationState === 'ok' && validationData}
          {#if validationData.status === 'pass'}
            <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>Pass
            </span>
          {:else}
            <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>Fail
            </span>
          {/if}
        {:else if validationState === 'idle'}
          <span class="text-xs text-zinc-600">—</span>
        {:else}
          <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">Error</span>
        {/if}
      </div>

      {#if validationState === 'loading'}
        <div class="space-y-2">
          <div class="h-4 bg-zinc-800 rounded animate-pulse w-3/4"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
        </div>
      {:else if validationState === 'ok' && validationData}
        <div class="space-y-1.5">
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Invalid notes</span>
            <span class="{validationData.invalid_count === 0 ? 'text-emerald-400' : 'text-red-400'} font-mono">
              {validationData.invalid_count}
            </span>
          </div>
        </div>
        {#if validationData.invalid_notes.length > 0}
          <div class="mt-2 space-y-1 max-h-32 overflow-y-auto">
            {#each validationData.invalid_notes as note}
              <div class="text-xs text-red-300 font-mono truncate bg-red-950/40 border border-red-900/40 rounded px-2 py-1" title={note}>{note}</div>
            {/each}
          </div>
          <p class="text-xs text-zinc-600 mt-2">See <a href="/app/validation" class="text-sky-600 hover:text-sky-400">Validation</a> page for details.</p>
        {/if}
        <details class="mt-3">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(validationData, null, 2)}</pre>
        </details>
      {:else if validationState === 'idle'}
        <p class="text-sm text-zinc-600">Select a vault to run validation.</p>
      {:else}
        <p class="text-sm text-red-400">{validationError}</p>
      {/if}
    </div>

    <!-- ── Tasks card (full width) ── -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4 sm:col-span-2 xl:col-span-3">
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Top Tasks</span>
          {#if tasksState === 'ok' && tasksData && tasksData.total > 5}
            <span class="text-xs text-zinc-600">showing 5 of {tasksData.total}</span>
          {/if}
        </div>
        {#if tasksState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>Loading
          </span>
        {:else if tasksState === 'ok' && tasksData}
          <span class="text-xs font-mono text-zinc-500">{tasksData.total} total</span>
        {:else if tasksState === 'idle'}
          <span class="text-xs text-zinc-600">—</span>
        {:else}
          <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">Error</span>
        {/if}
      </div>

      {#if tasksState === 'loading'}
        <div class="space-y-2">
          {#each [1, 2, 3] as _}
            <div class="h-12 bg-zinc-800 rounded animate-pulse"></div>
          {/each}
        </div>
      {:else if tasksState === 'ok' && tasksData}
        {#if tasksData.tasks.length === 0}
          <p class="text-sm text-emerald-400">No improvement tasks found. Vault is in good shape.</p>
        {:else}
          <div class="space-y-2">
            {#each tasksData.tasks as task}
              <div class="bg-zinc-950 border border-zinc-800 rounded p-3 flex flex-col sm:flex-row sm:items-start gap-3">
                <span class="shrink-0 text-xs font-mono px-1.5 py-0.5 rounded self-start {priorityColor(task.priority)}">
                  P{task.priority.toFixed(1)}
                </span>
                <div class="flex-1 min-w-0">
                  <div class="flex flex-wrap items-baseline gap-2">
                    <span class="text-sm font-medium text-zinc-200">{task.note}</span>
                    <span class="text-xs text-zinc-600 font-mono truncate" title={task.path}>{task.path}</span>
                  </div>
                  <p class="text-xs text-zinc-500 mt-0.5">{task.instruction}</p>
                  {#if task.missing.length > 0}
                    <div class="flex flex-wrap gap-1 mt-1.5">
                      {#each task.missing as section}
                        <span class="text-xs bg-zinc-800 text-zinc-400 border border-zinc-700 rounded px-1.5 py-0.5">{section}</span>
                      {/each}
                    </div>
                  {/if}
                  {#if task.feedback_weight}
                    <p class="mt-1.5 text-xs text-zinc-500">
                      Feedback:
                      <span class="{task.feedback_weight.score_delta >= 0 ? 'text-amber-400' : 'text-emerald-400'}">
                        {task.feedback_weight.score_delta >= 0 ? '+' : ''}{task.feedback_weight.score_delta.toFixed(2)}
                      </span>
                      — {task.feedback_weight.entry_summary}
                    </p>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
          {#if tasksData.feedback_status === 'error'}
            <p class="mt-2 text-xs text-amber-400">Feedback scoring unavailable — tasks are unweighted.</p>
          {/if}
          <p class="mt-3 text-xs text-zinc-600">See <a href="/app/tasks" class="text-sky-600 hover:text-sky-400">Tasks</a> page for the full list.</p>
        {/if}
        <details class="mt-3">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(tasksData, null, 2)}</pre>
        </details>
      {:else if tasksState === 'idle'}
        <p class="text-sm text-zinc-600">Select a vault to load tasks.</p>
      {:else}
        <p class="text-sm text-red-400">{tasksError}</p>
      {/if}
    </div>

    <!-- ── Missing Concepts card ── -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Missing Concepts</span>
        {#if missingState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>Loading
          </span>
        {:else if missingState === 'ok' && missingData}
          {#if missingData.total_missing === 0}
            <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>None
            </span>
          {:else}
            <span class="inline-flex items-center gap-1 text-xs bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>{missingData.total_missing} missing
            </span>
          {/if}
        {:else if missingState === 'warning'}
          <span class="text-xs text-zinc-600 border border-zinc-700 px-2 py-0.5 rounded-full">Not configured</span>
        {:else if missingState === 'idle'}
          <span class="text-xs text-zinc-600">—</span>
        {:else}
          <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">Error</span>
        {/if}
      </div>

      {#if missingState === 'loading'}
        <div class="space-y-2">
          <div class="h-4 bg-zinc-800 rounded animate-pulse w-3/4"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-2/3"></div>
        </div>
      {:else if missingState === 'warning'}
        <div class="bg-zinc-800/50 border border-zinc-700 rounded p-3">
          <p class="text-sm text-zinc-400">{missingError}</p>
          <p class="text-xs text-zinc-600 mt-1">
            Define <code class="bg-zinc-800 px-1 rounded">EXPECTED_CONCEPTS</code> in <code class="bg-zinc-800 px-1 rounded">vault_schema.py</code> to enable gap detection.
          </p>
        </div>
      {:else if missingState === 'ok' && missingData}
        <div class="grid grid-cols-2 gap-2 mb-3">
          <div class="bg-zinc-950 rounded p-2 text-center">
            <div class="text-lg font-mono font-semibold text-zinc-200">{missingData.total_expected}</div>
            <div class="text-xs text-zinc-500">Expected</div>
          </div>
          <div class="bg-zinc-950 rounded p-2 text-center">
            <div class="text-lg font-mono font-semibold {missingData.total_missing > 0 ? 'text-amber-400' : 'text-emerald-400'}">{missingData.total_missing}</div>
            <div class="text-xs text-zinc-500">Missing</div>
          </div>
        </div>
        {#if missingData.ranked.length > 0}
          <div class="space-y-1 max-h-40 overflow-y-auto">
            {#each missingData.ranked.slice(0, 5) as concept}
              <div class="flex items-center justify-between text-xs bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5">
                <div class="min-w-0 flex gap-1.5">
                  <span class="text-zinc-300 font-medium truncate">{concept.concept}</span>
                  <span class="text-zinc-600 shrink-0">{concept.subdomain}</span>
                </div>
                <span class="shrink-0 ml-2 text-zinc-500 font-mono">{concept.score.toFixed(2)}</span>
              </div>
            {/each}
          </div>
          {#if missingData.ranked.length > 5}
            <p class="text-xs text-zinc-600 mt-1">+{missingData.ranked.length - 5} more not shown</p>
          {/if}
        {:else}
          <p class="text-sm text-emerald-400">All expected concepts are present.</p>
        {/if}
        <details class="mt-3">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(missingData, null, 2)}</pre>
        </details>
      {:else if missingState === 'idle'}
        <p class="text-sm text-zinc-600">Select a vault to check concept coverage.</p>
      {:else}
        <p class="text-sm text-red-400">{missingError}</p>
      {/if}
    </div>

    <!-- ── Feedback card ── -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Feedback</span>
        {#if feedbackState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>Loading
          </span>
        {:else if feedbackState === 'ok' && feedbackData}
          {#if feedbackData.entries.length === 0}
            <span class="text-xs text-zinc-600">No entries</span>
          {:else if feedbackData.warnings.length > 0}
            <span class="inline-flex items-center gap-1 text-xs bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>{feedbackData.entries.length} entries
            </span>
          {:else}
            <span class="text-xs font-mono text-zinc-500">
              {feedbackData.entries.length} {feedbackData.entries.length === 1 ? 'entry' : 'entries'}
            </span>
          {/if}
        {:else if feedbackState === 'idle'}
          <span class="text-xs text-zinc-600">—</span>
        {:else}
          <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">Error</span>
        {/if}
      </div>

      {#if feedbackState === 'loading'}
        <div class="space-y-2">
          <div class="h-4 bg-zinc-800 rounded animate-pulse w-3/4"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-2/3"></div>
        </div>
      {:else if feedbackState === 'ok' && feedbackData}
        {#if feedbackData.entries.length === 0}
          <p class="text-sm text-zinc-500">No feedback entries found.</p>
          <p class="text-xs text-zinc-600 mt-1">
            Add entries to <code class="bg-zinc-800 px-1 rounded">Vault Files/feedback.md</code>.
          </p>
        {:else}
          <div class="grid grid-cols-3 gap-2 mb-3">
            <div class="bg-zinc-950 rounded p-2 text-center">
              <div class="text-base font-mono font-semibold text-zinc-200">{feedbackData.entries.length}</div>
              <div class="text-xs text-zinc-500">Entries</div>
            </div>
            <div class="bg-zinc-950 rounded p-2 text-center">
              <div class="text-base font-mono font-semibold {feedbackData.warnings.length > 0 ? 'text-amber-400' : 'text-zinc-200'}">{feedbackData.warnings.length}</div>
              <div class="text-xs text-zinc-500">Warnings</div>
            </div>
            <div class="bg-zinc-950 rounded p-2 text-center">
              <div class="text-base font-mono font-semibold {(feedbackData.errors as unknown[]).length > 0 ? 'text-red-400' : 'text-zinc-200'}">{(feedbackData.errors as unknown[]).length}</div>
              <div class="text-xs text-zinc-500">Errors</div>
            </div>
          </div>
          <div class="space-y-1.5 max-h-40 overflow-y-auto">
            {#each feedbackData.entries.slice(0, 4) as entry}
              <div class="text-xs bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="font-mono text-zinc-400 truncate max-w-[10rem]" title={entry.path}>{entry.path}</span>
                  <span class="shrink-0 px-1 py-0.5 rounded {severityClass(entry.severity)}">{entry.severity}</span>
                  <span class="text-zinc-600 shrink-0">{entry.signal}</span>
                </div>
                {#if entry.comment}
                  <p class="text-zinc-500 mt-0.5 truncate" title={entry.comment}>{entry.comment}</p>
                {/if}
              </div>
            {/each}
          </div>
          {#if feedbackData.entries.length > 4}
            <p class="text-xs text-zinc-600 mt-1">+{feedbackData.entries.length - 4} more not shown</p>
          {/if}
          {#if feedbackData.warnings.length > 0}
            <div class="mt-2 bg-amber-950/30 border border-amber-900/40 rounded p-2 space-y-0.5">
              {#each feedbackData.warnings as w}
                <p class="text-xs text-amber-400">{w}</p>
              {/each}
            </div>
          {/if}
        {/if}
        <details class="mt-3">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(feedbackData, null, 2)}</pre>
        </details>
      {:else if feedbackState === 'error'}
        <p class="text-sm text-red-400">{feedbackError}</p>
      {:else if feedbackState === 'idle'}
        <p class="text-sm text-zinc-600">Select a vault to load feedback.</p>
      {/if}
    </div>

    <!-- ── Index Info card (from /health, fills 3rd xl column) ── -->
    {#if healthState === 'ok' && healthData && selectedVault && healthData.vaults[selectedVault]}
      {@const vaultMeta = healthData.vaults[selectedVault]}
      <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <p class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-3">Index — {selectedVault}</p>
        <div class="space-y-1.5">
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Notes indexed</span>
            <span class="text-zinc-200 font-mono">{vaultMeta.notes}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Schema hash</span>
            <span class="text-zinc-400 font-mono text-xs ml-2 truncate max-w-[8rem]" title={vaultMeta.schema_hash}>
              {vaultMeta.schema_hash.slice(0, 12)}…
            </span>
          </div>
          {#if vaultMeta.index_size_bytes}
            <div class="flex justify-between text-sm">
              <span class="text-zinc-500">Index size</span>
              <span class="text-zinc-200 font-mono">{(vaultMeta.index_size_bytes / 1024).toFixed(1)} KB</span>
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- ── Security Scan card (full width) ── -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4 sm:col-span-2 xl:col-span-3">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Security Scan</span>
        {#if securityState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>Scanning…
          </span>
        {:else if securityState === 'ok' && securityData}
          {#if securityData.status === 'pass'}
            <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>Pass
            </span>
          {:else if securityData.status === 'warning'}
            <span class="inline-flex items-center gap-1 text-xs bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>Warning
            </span>
          {:else}
            <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>Fail
            </span>
          {/if}
        {:else if securityState === 'idle'}
          <span class="text-xs text-zinc-600">—</span>
        {:else}
          <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">Error</span>
        {/if}
      </div>

      {#if securityState === 'loading'}
        <div class="flex items-center gap-2 text-sm text-zinc-500">
          <span class="w-4 h-4 border-2 border-zinc-600 border-t-sky-500 rounded-full animate-spin"></span>
          Running deterministic security scan…
        </div>
      {:else if securityState === 'ok' && securityData}
        {#if securityData.scanned.note_count === 0}
          <div class="bg-amber-950/30 border border-amber-900/40 rounded p-3 mb-3">
            <p class="text-sm text-amber-400">No complete notes were scanned.</p>
            <p class="text-xs text-zinc-500 mt-0.5">
              The security scan uses a <code class="bg-zinc-800 px-1 rounded">status: complete</code> filter.
              Mark notes as complete to enable scanning.
            </p>
          </div>
        {/if}
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
          <div class="bg-zinc-950 rounded p-2 text-center">
            <div class="text-lg font-mono font-semibold text-zinc-200">{securityData.scanned.note_count}</div>
            <div class="text-xs text-zinc-500">Notes scanned</div>
          </div>
          <div class="bg-zinc-950 rounded p-2 text-center">
            <div class="text-lg font-mono font-semibold {securityData.summary.fail > 0 ? 'text-red-400' : 'text-zinc-200'}">{securityData.summary.fail}</div>
            <div class="text-xs text-zinc-500">Failures</div>
          </div>
          <div class="bg-zinc-950 rounded p-2 text-center">
            <div class="text-lg font-mono font-semibold {securityData.summary.warning > 0 ? 'text-amber-400' : 'text-zinc-200'}">{securityData.summary.warning}</div>
            <div class="text-xs text-zinc-500">Warnings</div>
          </div>
          <div class="bg-zinc-950 rounded p-2 text-center">
            <div class="text-lg font-mono font-semibold text-zinc-200">{securityData.summary.info}</div>
            <div class="text-xs text-zinc-500">Info</div>
          </div>
        </div>
        {#if securityData.findings.length > 0}
          <p class="text-xs text-zinc-500 mb-2">Findings:</p>
          <div class="space-y-1.5 max-h-56 overflow-y-auto">
            {#each securityData.findings as finding}
              <div class="flex items-start gap-2 text-xs bg-zinc-950 border border-zinc-800 rounded p-2">
                <span class="shrink-0 px-1.5 py-0.5 rounded font-mono {severityClass(finding.severity)}">
                  {finding.severity}
                </span>
                <div class="min-w-0">
                  <div class="font-mono text-zinc-300 truncate">{finding.path}</div>
                  <div class="text-zinc-500 mt-0.5">{finding.rule} — {finding.detail}</div>
                </div>
              </div>
            {/each}
          </div>
        {:else if securityData.scanned.note_count > 0}
          <p class="text-sm text-emerald-400">No security findings. Vault is clean.</p>
        {/if}
        <details class="mt-3">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(securityData, null, 2)}</pre>
        </details>
      {:else if securityState === 'idle'}
        <p class="text-sm text-zinc-600">Select a vault to run a security scan.</p>
      {:else}
        <p class="text-sm text-red-400">{securityError}</p>
      {/if}
    </div>

  </div><!-- end card grid -->

  <!-- ══════════════════════════════════════════════════════════
       Issue Review Section
       ══════════════════════════════════════════════════════════ -->
  <div class="border border-zinc-800 rounded-lg overflow-hidden">

    <!-- Section header -->
    <div class="bg-zinc-900 border-b border-zinc-800 px-4 py-3">
      <h2 class="text-sm font-semibold text-zinc-200">Issue Review</h2>
      <p class="text-xs text-zinc-500 mt-0.5">Inspect findings across all analysis categories.</p>
    </div>

    {#if !selectedVault}
      <div class="p-4">
        <p class="text-sm text-zinc-600">Select a vault to review issues.</p>
      </div>
    {:else}

      <!-- Cross-panel summary row -->
      <div class="bg-zinc-950 border-b border-zinc-800 px-4 py-2 flex flex-wrap gap-x-6 gap-y-1 items-center">
        <span class="text-xs text-zinc-600 uppercase tracking-wide">Summary:</span>

        <div class="flex items-center gap-1.5 text-xs">
          <span class="text-zinc-500">Validation</span>
          {#if validationState === 'ok' && validationData}
            <span class="font-mono font-medium {validationData.invalid_count > 0 ? 'text-red-400' : 'text-emerald-400'}">
              {validationData.invalid_count} issue{validationData.invalid_count !== 1 ? 's' : ''}
            </span>
          {:else if validationState === 'loading'}
            <span class="text-zinc-700">…</span>
          {:else}
            <span class="text-zinc-700">—</span>
          {/if}
        </div>

        <div class="flex items-center gap-1.5 text-xs">
          <span class="text-zinc-500">Tasks</span>
          {#if tasksState === 'ok' && tasksData}
            <span class="font-mono font-medium {tasksData.total > 0 ? 'text-amber-400' : 'text-emerald-400'}">
              {tasksData.total}
            </span>
          {:else if tasksState === 'loading'}
            <span class="text-zinc-700">…</span>
          {:else}
            <span class="text-zinc-700">—</span>
          {/if}
        </div>

        <div class="flex items-center gap-1.5 text-xs">
          <span class="text-zinc-500">Security</span>
          {#if securityState === 'ok' && securityData}
            <span class="font-mono font-medium {securityData.findings.length > 0 ? 'text-red-400' : 'text-emerald-400'}">
              {securityData.findings.length} finding{securityData.findings.length !== 1 ? 's' : ''}
            </span>
          {:else if securityState === 'loading'}
            <span class="text-zinc-700">…</span>
          {:else}
            <span class="text-zinc-700">—</span>
          {/if}
        </div>

        <div class="flex items-center gap-1.5 text-xs">
          <span class="text-zinc-500">Missing</span>
          {#if missingState === 'ok' && missingData}
            <span class="font-mono font-medium {missingData.total_missing > 0 ? 'text-amber-400' : 'text-emerald-400'}">
              {missingData.total_missing}
            </span>
          {:else if missingState === 'warning'}
            <span class="text-zinc-600">not configured</span>
          {:else if missingState === 'loading'}
            <span class="text-zinc-700">…</span>
          {:else}
            <span class="text-zinc-700">—</span>
          {/if}
        </div>

        <div class="flex items-center gap-1.5 text-xs">
          <span class="text-zinc-500">Feedback</span>
          {#if feedbackState === 'ok' && feedbackData}
            <span class="font-mono font-medium text-zinc-300">
              {feedbackData.entries.length} entr{feedbackData.entries.length !== 1 ? 'ies' : 'y'}
            </span>
          {:else if feedbackState === 'loading'}
            <span class="text-zinc-700">…</span>
          {:else}
            <span class="text-zinc-700">—</span>
          {/if}
        </div>
      </div><!-- end summary row -->

      <!-- Tab bar -->
      <div class="bg-zinc-900 border-b border-zinc-800 flex overflow-x-auto">
        <button
          on:click={() => activeIssueTab = 'validation'}
          class="px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors
            {activeIssueTab === 'validation' ? 'border-sky-500 text-zinc-100' : 'border-transparent text-zinc-500 hover:text-zinc-300'}"
        >Validation</button>
        <button
          on:click={() => activeIssueTab = 'tasks'}
          class="px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors
            {activeIssueTab === 'tasks' ? 'border-sky-500 text-zinc-100' : 'border-transparent text-zinc-500 hover:text-zinc-300'}"
        >Tasks</button>
        <button
          on:click={() => activeIssueTab = 'security'}
          class="px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors
            {activeIssueTab === 'security' ? 'border-sky-500 text-zinc-100' : 'border-transparent text-zinc-500 hover:text-zinc-300'}"
        >Security</button>
        <button
          on:click={() => activeIssueTab = 'missing'}
          class="px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors
            {activeIssueTab === 'missing' ? 'border-sky-500 text-zinc-100' : 'border-transparent text-zinc-500 hover:text-zinc-300'}"
        >Missing Concepts</button>
        <button
          on:click={() => activeIssueTab = 'feedback'}
          class="px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors
            {activeIssueTab === 'feedback' ? 'border-sky-500 text-zinc-100' : 'border-transparent text-zinc-500 hover:text-zinc-300'}"
        >Feedback</button>
      </div><!-- end tab bar -->

      <!-- Tab content -->
      <div class="p-4">

        <!-- ═══════════ Validation tab ═══════════ -->
        {#if activeIssueTab === 'validation'}
          {#if validationState === 'loading'}
            <div class="space-y-2">
              <div class="h-4 bg-zinc-800 rounded animate-pulse w-1/3"></div>
              <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
            </div>
          {:else if validationState === 'ok' && validationData}
            <div class="flex items-center gap-3 mb-4">
              {#if validationData.status === 'pass'}
                <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>Pass
                </span>
                <span class="text-sm text-zinc-400">All notes pass schema validation.</span>
              {:else}
                <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">
                  <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>Fail
                </span>
                <span class="text-sm text-zinc-300">
                  {validationData.invalid_count} note{validationData.invalid_count !== 1 ? 's' : ''} failed validation.
                </span>
              {/if}
            </div>
            {#if validationData.invalid_notes.length > 0}
              <p class="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">
                Invalid notes — {validationData.invalid_notes.length}
              </p>
              <div class="space-y-1 max-h-72 overflow-y-auto mb-3">
                {#each validationData.invalid_notes as notePath}
                  <div class="flex items-center text-xs bg-zinc-950 border border-red-900/30 rounded px-3 py-1.5">
                    <span class="font-mono text-red-300 truncate" title={notePath}>{notePath}</span>
                  </div>
                {/each}
              </div>
              <p class="text-xs text-zinc-600">
                Detailed per-field validation messages are available via
                <code class="bg-zinc-800 px-1 rounded">py run.py validate</code>.
              </p>
            {:else}
              <div class="bg-emerald-950/20 border border-emerald-900/30 rounded p-3">
                <p class="text-sm text-emerald-400">No invalid notes. Vault passes all schema checks.</p>
              </div>
            {/if}
            <details class="mt-4">
              <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
              <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(validationData, null, 2)}</pre>
            </details>
          {:else if validationState === 'idle'}
            <p class="text-sm text-zinc-600">Select a vault to run validation.</p>
          {:else}
            <p class="text-sm text-red-400">{validationError}</p>
          {/if}

        <!-- ═══════════ Tasks tab ═══════════ -->
        {:else if activeIssueTab === 'tasks'}
          {#if tasksState === 'loading'}
            <div class="space-y-2">
              {#each [1, 2, 3] as _}
                <div class="h-12 bg-zinc-800 rounded animate-pulse"></div>
              {/each}
            </div>
          {:else if tasksState === 'ok' && tasksData}
            {#if tasksData.tasks.length === 0}
              <div class="bg-emerald-950/20 border border-emerald-900/30 rounded p-3">
                <p class="text-sm text-emerald-400">No improvement tasks found. Vault is in good shape.</p>
              </div>
            {:else}
              <div class="flex items-center justify-between mb-3 gap-3 flex-wrap">
                <p class="text-xs text-zinc-500">
                  {tasksData.total > tasksData.tasks.length
                    ? `Showing top ${tasksData.tasks.length} of ${tasksData.total} tasks — click a row to expand details.`
                    : `${tasksData.tasks.length} task${tasksData.tasks.length !== 1 ? 's' : ''} — click a row to expand details.`}
                </p>
                {#if tasksData.feedback_status === 'error'}
                  <span class="text-xs text-amber-400 bg-amber-950/40 border border-amber-900/40 rounded px-2 py-0.5">
                    Feedback scoring unavailable — tasks are unweighted
                  </span>
                {/if}
              </div>
              <div class="space-y-1.5">
                {#each tasksData.tasks as task, idx}
                  {@const isExpanded = expandedTaskIds.has(idx)}
                  <div class="bg-zinc-950 border {isExpanded ? 'border-zinc-600' : 'border-zinc-800'} rounded overflow-hidden">
                    <!-- Row header — clickable -->
                    <button
                      on:click={() => toggleTask(idx)}
                      class="w-full text-left flex items-center gap-3 px-3 py-2.5 hover:bg-zinc-900/80 transition-colors"
                    >
                      <span class="shrink-0 text-xs font-mono px-1.5 py-0.5 rounded {priorityColor(task.priority)}">
                        P{task.priority.toFixed(1)}
                      </span>
                      <div class="flex-1 min-w-0">
                        <div class="flex flex-wrap items-baseline gap-x-2">
                          <span class="text-sm font-medium text-zinc-200">{task.note}</span>
                          <span class="text-xs text-zinc-600 font-mono truncate" title={task.path}>{task.path}</span>
                        </div>
                      </div>
                      <svg
                        class="shrink-0 w-3.5 h-3.5 text-zinc-500 transition-transform {isExpanded ? 'rotate-180' : ''}"
                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    <!-- Expanded body -->
                    {#if isExpanded}
                      <div class="px-3 pb-3 border-t border-zinc-800 pt-3 space-y-3">
                        <div>
                          <p class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">Instruction</p>
                          <p class="text-sm text-zinc-300">{task.instruction}</p>
                        </div>
                        {#if task.missing && task.missing.length > 0}
                          <div>
                            <p class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1.5">Missing sections</p>
                            <div class="flex flex-wrap gap-1">
                              {#each task.missing as section}
                                <span class="text-xs bg-zinc-800 text-zinc-300 border border-zinc-700 rounded px-1.5 py-0.5">{section}</span>
                              {/each}
                            </div>
                          </div>
                        {/if}
                        {#if task.constraints && task.constraints.length > 0}
                          <div>
                            <p class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1.5">Constraints</p>
                            <ul class="space-y-0.5">
                              {#each task.constraints as c}
                                <li class="text-xs text-zinc-400 flex gap-1.5">
                                  <span class="text-zinc-600 shrink-0">–</span><span>{c}</span>
                                </li>
                              {/each}
                            </ul>
                          </div>
                        {/if}
                        {#if task.feedback_weight}
                          <div>
                            <p class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1.5">Feedback weighting</p>
                            <div class="bg-zinc-900 border border-zinc-800 rounded px-3 py-2 text-xs space-y-1">
                              <div class="flex items-center gap-2">
                                <span class="text-zinc-500">Score delta:</span>
                                <span class="font-mono {task.feedback_weight.score_delta >= 0 ? 'text-amber-400' : 'text-emerald-400'}">
                                  {task.feedback_weight.score_delta >= 0 ? '+' : ''}{task.feedback_weight.score_delta.toFixed(3)}
                                </span>
                              </div>
                              <p class="text-zinc-400">{task.feedback_weight.entry_summary}</p>
                            </div>
                          </div>
                        {/if}
                        <details>
                          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw task JSON</summary>
                          <pre class="mt-1.5 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(task, null, 2)}</pre>
                        </details>
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
            <details class="mt-4">
              <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON (tasks list)</summary>
              <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(tasksData, null, 2)}</pre>
            </details>
          {:else if tasksState === 'idle'}
            <p class="text-sm text-zinc-600">Select a vault to load tasks.</p>
          {:else}
            <p class="text-sm text-red-400">{tasksError}</p>
          {/if}

        <!-- ═══════════ Security tab ═══════════ -->
        {:else if activeIssueTab === 'security'}
          {#if securityState === 'loading'}
            <div class="flex items-center gap-2 text-sm text-zinc-500">
              <span class="w-4 h-4 border-2 border-zinc-600 border-t-sky-500 rounded-full animate-spin"></span>
              Running security scan…
            </div>
          {:else if securityState === 'ok' && securityData}
            <div class="flex items-center gap-3 mb-4">
              {#if securityData.status === 'pass'}
                <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>Pass
                </span>
              {:else if securityData.status === 'warning'}
                <span class="inline-flex items-center gap-1 text-xs bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded-full">
                  <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>Warning
                </span>
              {:else}
                <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">
                  <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>Fail
                </span>
              {/if}
              <span class="text-xs text-zinc-500">
                {securityData.scanned.note_count} note{securityData.scanned.note_count !== 1 ? 's' : ''} scanned
              </span>
            </div>
            {#if securityData.scanned.note_count === 0}
              <div class="bg-amber-950/30 border border-amber-900/40 rounded p-3 mb-4">
                <p class="text-sm text-amber-400">No complete notes were scanned.</p>
                <p class="text-xs text-zinc-500 mt-0.5">
                  The security scan requires notes with
                  <code class="bg-zinc-800 px-1 rounded">status: complete</code>.
                  Mark notes as complete to enable scanning.
                </p>
              </div>
            {/if}
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
              <div class="bg-zinc-950 rounded p-2 text-center">
                <div class="text-base font-mono font-semibold text-zinc-200">{securityData.scanned.note_count}</div>
                <div class="text-xs text-zinc-500">Scanned</div>
              </div>
              <div class="bg-zinc-950 rounded p-2 text-center">
                <div class="text-base font-mono font-semibold {securityData.summary.fail > 0 ? 'text-red-400' : 'text-zinc-200'}">{securityData.summary.fail}</div>
                <div class="text-xs text-zinc-500">Failures</div>
              </div>
              <div class="bg-zinc-950 rounded p-2 text-center">
                <div class="text-base font-mono font-semibold {securityData.summary.warning > 0 ? 'text-amber-400' : 'text-zinc-200'}">{securityData.summary.warning}</div>
                <div class="text-xs text-zinc-500">Warnings</div>
              </div>
              <div class="bg-zinc-950 rounded p-2 text-center">
                <div class="text-base font-mono font-semibold text-zinc-200">{securityData.summary.info}</div>
                <div class="text-xs text-zinc-500">Info</div>
              </div>
            </div>
            {#if securityData.findings.length > 0}
              <p class="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">
                Findings — {securityData.findings.length}
              </p>
              <div class="space-y-1.5">
                {#each securityData.findings as finding}
                  <div class="bg-zinc-950 border border-zinc-800 rounded p-3">
                    <div class="flex items-start gap-2 flex-wrap mb-1.5">
                      <span class="shrink-0 text-xs font-mono px-1.5 py-0.5 rounded {severityClass(finding.severity)}">
                        {finding.severity}
                      </span>
                      <span class="text-xs font-mono text-zinc-300 truncate min-w-0" title={finding.path}>{finding.path}</span>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-x-4 gap-y-1 text-xs">
                      <div class="flex gap-1.5">
                        <span class="text-zinc-600 shrink-0">Rule:</span>
                        <span class="text-zinc-300 font-mono">{finding.rule}</span>
                      </div>
                      <div class="flex gap-1.5">
                        <span class="text-zinc-600 shrink-0">Field:</span>
                        <span class="text-zinc-300 font-mono">{finding.field}</span>
                      </div>
                      <div class="flex gap-1.5 sm:col-span-3">
                        <span class="text-zinc-600 shrink-0">Detail:</span>
                        <span class="text-zinc-400">{finding.detail}</span>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            {:else if securityData.scanned.note_count > 0}
              <div class="bg-emerald-950/20 border border-emerald-900/30 rounded p-3">
                <p class="text-sm text-emerald-400">No security findings. Vault is clean.</p>
              </div>
            {/if}
            <details class="mt-4">
              <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
              <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(securityData, null, 2)}</pre>
            </details>
          {:else if securityState === 'idle'}
            <p class="text-sm text-zinc-600">Select a vault to run a security scan.</p>
          {:else}
            <p class="text-sm text-red-400">{securityError}</p>
          {/if}

        <!-- ═══════════ Missing Concepts tab ═══════════ -->
        {:else if activeIssueTab === 'missing'}
          {#if missingState === 'loading'}
            <div class="space-y-2">
              <div class="h-4 bg-zinc-800 rounded animate-pulse w-1/3"></div>
              <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
              <div class="h-3 bg-zinc-800 rounded animate-pulse w-2/3"></div>
            </div>
          {:else if missingState === 'warning'}
            <div class="bg-zinc-800/50 border border-zinc-700 rounded p-3">
              <p class="text-sm text-zinc-400">{missingError}</p>
              <p class="text-xs text-zinc-600 mt-1.5">
                Define <code class="bg-zinc-800 px-1 rounded">EXPECTED_CONCEPTS</code> in
                <code class="bg-zinc-800 px-1 rounded">vault_schema.py</code> to enable gap detection.
              </p>
            </div>
          {:else if missingState === 'ok' && missingData}
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
              <div class="bg-zinc-950 rounded p-2 text-center">
                <div class="text-base font-mono font-semibold text-zinc-200">{missingData.total_expected}</div>
                <div class="text-xs text-zinc-500">Expected</div>
              </div>
              <div class="bg-zinc-950 rounded p-2 text-center">
                <div class="text-base font-mono font-semibold text-zinc-200">{missingData.total_actual}</div>
                <div class="text-xs text-zinc-500">Present</div>
              </div>
              <div class="bg-zinc-950 rounded p-2 text-center">
                <div class="text-base font-mono font-semibold {missingData.total_missing > 0 ? 'text-amber-400' : 'text-emerald-400'}">{missingData.total_missing}</div>
                <div class="text-xs text-zinc-500">Missing</div>
              </div>
              <div class="bg-zinc-950 rounded p-2 text-center">
                <div class="text-base font-mono font-semibold text-zinc-200">{missingData.domains_assessed}</div>
                <div class="text-xs text-zinc-500">Domains</div>
              </div>
            </div>
            {#if missingData.ranked.length > 0}
              <p class="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">
                Ranked missing concepts — {missingData.ranked.length}
              </p>
              <div class="space-y-1">
                {#each missingData.ranked as concept, i}
                  <div class="flex items-center gap-2 text-xs bg-zinc-950 border border-zinc-800 rounded px-3 py-1.5">
                    <span class="shrink-0 font-mono text-zinc-600 w-5 text-right">{i + 1}.</span>
                    <div class="flex-1 min-w-0 flex flex-wrap items-baseline gap-x-2">
                      <span class="text-zinc-200 font-medium">{concept.concept}</span>
                      <span class="text-zinc-600">{concept.subdomain}</span>
                    </div>
                    <span class="shrink-0 font-mono text-zinc-500">{concept.score.toFixed(2)}</span>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="bg-emerald-950/20 border border-emerald-900/30 rounded p-3">
                <p class="text-sm text-emerald-400">All expected concepts are present.</p>
              </div>
            {/if}
            <details class="mt-4">
              <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
              <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(missingData, null, 2)}</pre>
            </details>
          {:else if missingState === 'idle'}
            <p class="text-sm text-zinc-600">Select a vault to check concept coverage.</p>
          {:else}
            <p class="text-sm text-red-400">{missingError}</p>
          {/if}

        <!-- ═══════════ Feedback tab ═══════════ -->
        {:else if activeIssueTab === 'feedback'}
          {#if feedbackState === 'loading'}
            <div class="space-y-2">
              <div class="h-4 bg-zinc-800 rounded animate-pulse w-1/3"></div>
              <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
              <div class="h-3 bg-zinc-800 rounded animate-pulse w-2/3"></div>
            </div>
          {:else if feedbackState === 'ok' && feedbackData}
            {#if feedbackData.entries.length === 0}
              <div class="bg-zinc-900 border border-zinc-800 rounded p-3">
                <p class="text-sm text-zinc-400">No feedback entries found.</p>
                <p class="text-xs text-zinc-600 mt-1">
                  Add entries to <code class="bg-zinc-800 px-1 rounded">Vault Files/feedback.md</code>.
                </p>
              </div>
            {:else}
              <div class="grid grid-cols-3 gap-2 mb-4">
                <div class="bg-zinc-950 rounded p-2 text-center">
                  <div class="text-base font-mono font-semibold text-zinc-200">{feedbackData.entries.length}</div>
                  <div class="text-xs text-zinc-500">Entries</div>
                </div>
                <div class="bg-zinc-950 rounded p-2 text-center">
                  <div class="text-base font-mono font-semibold {feedbackData.warnings.length > 0 ? 'text-amber-400' : 'text-zinc-200'}">{feedbackData.warnings.length}</div>
                  <div class="text-xs text-zinc-500">Warnings</div>
                </div>
                <div class="bg-zinc-950 rounded p-2 text-center">
                  <div class="text-base font-mono font-semibold {(feedbackData.errors as unknown[]).length > 0 ? 'text-red-400' : 'text-zinc-200'}">{(feedbackData.errors as unknown[]).length}</div>
                  <div class="text-xs text-zinc-500">Errors</div>
                </div>
              </div>
              <p class="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">
                Feedback entries — {feedbackData.entries.length}
              </p>
              <div class="space-y-1.5">
                {#each feedbackData.entries as entry}
                  <div class="bg-zinc-950 border border-zinc-800 rounded p-3">
                    <div class="flex items-center gap-2 flex-wrap mb-1.5">
                      <span class="font-mono text-xs text-zinc-300 truncate max-w-[14rem]" title={entry.path}>{entry.path}</span>
                      <span class="shrink-0 text-xs px-1.5 py-0.5 rounded {severityClass(entry.severity)}">{entry.severity}</span>
                      <span class="shrink-0 text-xs text-zinc-500">{entry.signal}</span>
                    </div>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
                      <div class="flex gap-1.5">
                        <span class="text-zinc-600 shrink-0">Source:</span>
                        <span class="text-zinc-400">{entry.source}</span>
                      </div>
                      <div class="flex gap-1.5">
                        <span class="text-zinc-600 shrink-0">Created:</span>
                        <span class="text-zinc-400 font-mono">{entry.created_at}</span>
                      </div>
                      {#if entry.comment}
                        <div class="flex gap-1.5 sm:col-span-2 mt-0.5">
                          <span class="text-zinc-600 shrink-0">Comment:</span>
                          <span class="text-zinc-400">{entry.comment}</span>
                        </div>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
              {#if feedbackData.warnings.length > 0}
                <div class="mt-3 bg-amber-950/30 border border-amber-900/40 rounded p-2 space-y-0.5">
                  <p class="text-xs font-medium text-amber-400 mb-1">Warnings:</p>
                  {#each feedbackData.warnings as w}
                    <p class="text-xs text-amber-300">{w}</p>
                  {/each}
                </div>
              {/if}
              {#if (feedbackData.errors as unknown[]).length > 0}
                <div class="mt-2 bg-red-950/30 border border-red-900/40 rounded p-2 space-y-0.5">
                  <p class="text-xs font-medium text-red-400 mb-1">Errors:</p>
                  {#each feedbackData.errors as e}
                    <p class="text-xs text-red-300">{JSON.stringify(e)}</p>
                  {/each}
                </div>
              {/if}
            {/if}
            <details class="mt-4">
              <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">Raw JSON</summary>
              <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(feedbackData, null, 2)}</pre>
            </details>
          {:else if feedbackState === 'error'}
            <p class="text-sm text-red-400">{feedbackError}</p>
          {:else if feedbackState === 'idle'}
            <p class="text-sm text-zinc-600">Select a vault to load feedback.</p>
          {/if}

        {/if}<!-- end tab content -->
      </div><!-- end p-4 -->

    {/if}<!-- end selectedVault guard -->
  </div><!-- end Issue Review -->

</div>

