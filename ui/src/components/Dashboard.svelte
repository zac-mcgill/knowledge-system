<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchHealth,
    fetchVaults,
    fetchSummary,
    fetchValidation,
    fetchSecurity,
    isOk,
    errorMessage,
    type HealthData,
    type SummaryData,
    type ValidationData,
    type SecurityData,
  } from '../lib/api.ts';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

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

  // Security
  let securityState: LoadState = 'idle';
  let securityData: SecurityData | null = null;
  let securityError = '';

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

    // Summary
    summaryState = 'loading';
    summaryData = null;
    summaryError = '';
    const sResult = await fetchSummary(vault);
    if (isOk(sResult)) {
      summaryData = sResult.data;
      summaryState = 'ok';
    } else {
      summaryError = errorMessage(sResult);
      summaryState = 'error';
    }

    // Validation
    validationState = 'loading';
    validationData = null;
    validationError = '';
    const vResult = await fetchValidation(vault);
    if (isOk(vResult)) {
      validationData = vResult.data;
      validationState = 'ok';
    } else {
      validationError = errorMessage(vResult);
      validationState = 'error';
    }

    // Security
    securityState = 'loading';
    securityData = null;
    securityError = '';
    const secResult = await fetchSecurity(vault);
    if (isOk(secResult)) {
      securityData = secResult.data;
      securityState = 'ok';
    } else {
      securityError = errorMessage(secResult);
      securityState = 'error';
    }
  }

  async function handleVaultChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedVault = select.value;
    await loadVaultData(selectedVault);
  }

  async function refresh() {
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

  <!-- Header row: title + refresh + vault selector -->
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-xl font-semibold text-zinc-100">Dashboard</h1>
      <p class="text-sm text-zinc-500 mt-0.5">Live status from the Context Vault Engine API.</p>
    </div>
    <div class="flex items-center gap-3">
      {#if vaultList.length > 1}
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
      {:else if vaultsState === 'ok' && vaultList.length === 1}
        <span class="text-sm text-zinc-400">
          Vault: <span class="text-zinc-200 font-medium">{selectedVault}</span>
        </span>
      {/if}
      <button
        on:click={refresh}
        class="flex items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-zinc-300 hover:text-zinc-100 text-sm px-3 py-1.5 rounded transition-colors"
        title="Refresh all data"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh
      </button>
    </div>
  </div>

  <!-- Status card grid -->
  <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">

    <!-- Server Health card -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Server</span>
        {#if healthState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>
            Loading
          </span>
        {:else if healthState === 'ok'}
          <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            Online
          </span>
        {:else}
          <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
            Offline
          </span>
        {/if}
      </div>

      {#if healthState === 'loading'}
        <div class="space-y-2">
          <div class="h-4 bg-zinc-800 rounded animate-pulse w-3/4"></div>
          <div class="h-3 bg-zinc-800 rounded animate-pulse w-1/2"></div>
        </div>
      {:else if healthState === 'ok' && healthData}
        <div class="space-y-1.5">
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Uptime</span>
            <span class="text-zinc-200 font-mono">{formatUptime(healthData.uptime_seconds)}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Requests</span>
            <span class="text-zinc-200 font-mono">{healthData.requests_served}</span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-zinc-500">Avg latency</span>
            <span class="text-zinc-200 font-mono">{healthData.metrics.avg_response_time_ms.toFixed(1)} ms</span>
          </div>
        </div>
        <!-- Raw JSON expander -->
        <details class="mt-3">
          <summary class="text-xs text-zinc-600 hover:text-zinc-400 cursor-pointer select-none">
            Raw JSON
          </summary>
          <pre class="mt-2 text-xs text-zinc-400 bg-zinc-950 border border-zinc-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(healthData, null, 2)}</pre>
        </details>
      {:else}
        <p class="text-sm text-red-400">{healthError || 'Backend unavailable — is the server running?'}</p>
        <p class="text-xs text-zinc-600 mt-1">py mcp/server/mcp_server.py</p>
      {/if}
    </div>

    <!-- Vault Summary card -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Coverage</span>
        {#if summaryState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>
            Loading
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
        <!-- Coverage bar -->
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

    <!-- Validation card -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Validation</span>
        {#if validationState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>
            Loading
          </span>
        {:else if validationState === 'ok' && validationData}
          {#if validationData.status === 'pass'}
            <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Pass
            </span>
          {:else}
            <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
              Fail
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
            <span class="{validationData.invalid_count === 0 ? 'text-emerald-400' : 'text-red-400'} font-mono">{validationData.invalid_count}</span>
          </div>
        </div>
        {#if validationData.invalid_notes.length > 0}
          <ul class="mt-2 space-y-1">
            {#each validationData.invalid_notes as note}
              <li class="text-xs text-red-300 font-mono truncate" title={note}>{note}</li>
            {/each}
          </ul>
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

    <!-- Security Scan card -->
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4 sm:col-span-2 xl:col-span-3">
      <div class="flex items-center justify-between mb-3">
        <span class="text-xs font-medium text-zinc-500 uppercase tracking-wide">Security Scan</span>
        {#if securityState === 'loading'}
          <span class="inline-flex items-center gap-1 text-xs bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full">
            <span class="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse"></span>
            Scanning…
          </span>
        {:else if securityState === 'ok' && securityData}
          {#if securityData.status === 'pass'}
            <span class="inline-flex items-center gap-1 text-xs bg-emerald-950 text-emerald-400 border border-emerald-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Pass
            </span>
          {:else if securityData.status === 'warning'}
            <span class="inline-flex items-center gap-1 text-xs bg-amber-950 text-amber-400 border border-amber-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
              Warning
            </span>
          {:else}
            <span class="inline-flex items-center gap-1 text-xs bg-red-950 text-red-400 border border-red-800 px-2 py-0.5 rounded-full">
              <span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>
              Fail
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
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
          <div class="bg-zinc-950 rounded p-2 text-center">
            <div class="text-lg font-mono font-semibold text-zinc-200">{securityData.scanned.note_count}</div>
            <div class="text-xs text-zinc-500">Notes scanned</div>
          </div>
          <div class="bg-zinc-950 rounded p-2 text-center">
            <div class="text-lg font-mono font-semibold {securityData.summary.fail > 0 ? 'text-red-400' : 'text-zinc-200'}">{securityData.summary.fail}</div>
            <div class="text-xs text-zinc-500">Fail findings</div>
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
          <div class="mt-2">
            <p class="text-xs text-zinc-500 mb-2">Findings:</p>
            <div class="space-y-1 max-h-48 overflow-y-auto">
              {#each securityData.findings as finding}
                <div class="flex items-start gap-2 text-xs bg-zinc-950 border border-zinc-800 rounded p-2">
                  <span class="shrink-0 px-1.5 py-0.5 rounded font-mono
                    {finding.severity === 'high' || finding.severity === 'critical' ? 'bg-red-950 text-red-400 border border-red-800' :
                     finding.severity === 'medium' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                     'bg-zinc-800 text-zinc-400 border border-zinc-700'}">
                    {finding.severity}
                  </span>
                  <div class="min-w-0">
                    <div class="font-mono text-zinc-300 truncate">{finding.path}</div>
                    <div class="text-zinc-500">{finding.rule} — {finding.detail}</div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {:else}
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

  <!-- Vault index info (from health) -->
  {#if healthState === 'ok' && healthData && selectedVault && healthData.vaults[selectedVault]}
    {@const vaultMeta = healthData.vaults[selectedVault]}
    <div class="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
      <p class="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-3">Index — {selectedVault}</p>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div>
          <div class="text-sm text-zinc-500">Notes indexed</div>
          <div class="text-zinc-200 font-mono font-medium mt-0.5">{vaultMeta.notes}</div>
        </div>
        <div>
          <div class="text-sm text-zinc-500">Schema hash</div>
          <div class="text-zinc-400 font-mono text-xs mt-0.5 truncate" title={vaultMeta.schema_hash}>
            {vaultMeta.schema_hash.slice(0, 16)}…
          </div>
        </div>
        {#if vaultMeta.index_size_bytes}
          <div>
            <div class="text-sm text-zinc-500">Index size</div>
            <div class="text-zinc-200 font-mono font-medium mt-0.5">
              {(vaultMeta.index_size_bytes / 1024).toFixed(1)} KB
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}

</div>
