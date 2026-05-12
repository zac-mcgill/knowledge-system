<script lang="ts">
  /*
    Phase 30C - Dashboard redesign.
    The Dashboard is the command-centre entry point for the local UI.
    It summarises vault readiness across validation, security, coverage,
    missing concepts, and feedback, surfaces a compact next-actions list
    sourced from /tasks, and exposes a Developer deep link for raw
    inspection without rendering large JSON blocks inline.

    All visuals route through Phase 30B primitives (cve-toolbar,
    cve-status-strip, cve-status-tile, cve-banner, cve-card,
    cve-details--inspector, cve-details__developer-link) and tokenised
    Phase 30C helpers (cve-link, cve-status-tile__cta, cve-kv-row,
    cve-next-action, cve-dashboard-grid). The readiness banner can
    render any of cve-banner--success, cve-banner--warning,
    cve-banner--danger, or cve-banner--info depending on derived
    severity. Raw Tailwind dark palette
    literals are deliberately avoided so the Phase 30F light-mode
    toggle can flip themes without touching this component.
  */

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
  import {
    getStoredVault,
    setStoredVault,
    getVaultFromUrl,
    chooseInitialVault,
  } from '../lib/vaultState.ts';

  type LoadState = 'idle' | 'loading' | 'ok' | 'error' | 'warning';
  type Severity = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

  // Deterministic last-checked label. The backend API does not expose a
  // per-call timestamp, so the Dashboard uses a fixed deterministic
  // string once a request completes. This keeps the UI text stable for
  // snapshot/grep tests and avoids client-only time-of-render values.
  const CHECKED_LABEL = 'Checked this session';
  const NOT_CHECKED_LABEL = 'Not yet checked';
  const NO_TIMESTAMP_LABEL = 'No timestamp exposed by API';

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

  $: isLoading =
    healthState === 'loading' ||
    summaryState === 'loading' ||
    validationState === 'loading' ||
    tasksState === 'loading' ||
    missingState === 'loading' ||
    feedbackState === 'loading' ||
    securityState === 'loading';

  function formatUptime(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  }

  function tileSeverity(state: LoadState, severity: Severity): string {
    if (state === 'loading' || state === 'idle') return 'cve-status-tile--neutral';
    if (state === 'error') return 'cve-status-tile--danger';
    return `cve-status-tile--${severity}`;
  }

  function lastCheckedLabel(state: LoadState): string {
    if (state === 'ok' || state === 'warning' || state === 'error') {
      return CHECKED_LABEL;
    }
    return NOT_CHECKED_LABEL;
  }

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
        const urlVault = getVaultFromUrl();
        const storedVault = getStoredVault();
        selectedVault = chooseInitialVault(vaultList, urlVault, storedVault);
        setStoredVault(selectedVault);
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

    try {
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
      } else if (mResult.error?.code === 'MISSING_CONCEPTS_EMPTY') {
        missingError = 'No expected concepts defined in vault_schema.py.';
        missingState = 'warning';
      } else {
        missingError = errorMessage(mResult);
        missingState = 'error';
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
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unexpected error loading vault data';
      if (summaryState    === 'loading') { summaryError    = msg; summaryState    = 'error'; }
      if (validationState === 'loading') { validationError = msg; validationState = 'error'; }
      if (tasksState      === 'loading') { tasksError      = msg; tasksState      = 'error'; }
      if (missingState    === 'loading') { missingError    = msg; missingState    = 'error'; }
      if (feedbackState   === 'loading') { feedbackError   = msg; feedbackState   = 'error'; }
      if (securityState   === 'loading') { securityError   = msg; securityState   = 'error'; }
    }
  }

  async function handleVaultChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedVault = select.value;
    setStoredVault(selectedVault);
    await loadVaultData(selectedVault);
  }

  async function refresh() {
    if (isLoading) return;
    await loadHealth();
    if (selectedVault) {
      await loadVaultData(selectedVault);
    }
  }

  // Derived: validation tile
  $: validationSeverity = ((): Severity => {
    if (validationState !== 'ok' || !validationData) return 'neutral';
    return validationData.invalid_count === 0 ? 'success' : 'danger';
  })();
  $: validationValue = (() => {
    if (validationState === 'loading') return 'Checking';
    if (validationState !== 'ok' || !validationData) return '-';
    return validationData.invalid_count === 0 ? 'Pass' : `${validationData.invalid_count} invalid`;
  })();
  $: validationHint = (() => {
    if (validationState !== 'ok' || !validationData) return '';
    return validationData.invalid_count === 0
      ? 'All notes match the schema.'
      : `${validationData.invalid_count} note(s) failed schema checks.`;
  })();

  // Derived: security tile
  $: securitySeverity = ((): Severity => {
    if (securityState !== 'ok' || !securityData) return 'neutral';
    if (securityData.status === 'pass') return 'success';
    if (securityData.status === 'warning') return 'warning';
    return 'danger';
  })();
  $: securityValue = (() => {
    if (securityState === 'loading') return 'Scanning';
    if (securityState !== 'ok' || !securityData) return '-';
    if (securityData.status === 'pass') return 'Pass';
    if (securityData.status === 'warning') {
      const w = securityData.summary.warning;
      return `${w} warning${w !== 1 ? 's' : ''}`;
    }
    const f = securityData.summary.fail;
    return `${f} failure${f !== 1 ? 's' : ''}`;
  })();
  $: securityHint = (() => {
    if (securityState !== 'ok' || !securityData) return '';
    const n = securityData.scanned.note_count;
    return `${n} note${n !== 1 ? 's' : ''} scanned.`;
  })();

  // Derived: coverage tile
  $: coverageSeverity = ((): Severity => {
    if (summaryState !== 'ok' || !summaryData) return 'neutral';
    if (summaryData.coverage >= 80) return 'success';
    if (summaryData.coverage >= 50) return 'warning';
    return 'danger';
  })();
  $: coverageValue = (() => {
    if (summaryState === 'loading') return 'Loading';
    if (summaryState !== 'ok' || !summaryData) return '-';
    return `${summaryData.coverage}%`;
  })();
  $: coverageHint = (() => {
    if (summaryState !== 'ok' || !summaryData) return '';
    return `${summaryData.complete} of ${summaryData.total_notes} notes complete.`;
  })();

  // Derived: missing tile
  $: missingSeverity = ((): Severity => {
    if (missingState === 'warning') return 'neutral';
    if (missingState !== 'ok' || !missingData) return 'neutral';
    return missingData.total_missing === 0 ? 'success' : 'warning';
  })();
  $: missingValue = (() => {
    if (missingState === 'loading') return 'Checking';
    if (missingState === 'warning') return 'Not configured';
    if (missingState !== 'ok' || !missingData) return '-';
    return `${missingData.total_missing}`;
  })();
  $: missingHint = (() => {
    if (missingState === 'warning') return 'Define EXPECTED_CONCEPTS in vault_schema.py.';
    if (missingState !== 'ok' || !missingData) return '';
    return missingData.total_missing === 0
      ? 'All expected concepts present.'
      : `${missingData.total_missing} of ${missingData.total_expected} expected concepts missing.`;
  })();

  // Derived: feedback tile
  $: feedbackSeverity = ((): Severity => {
    if (feedbackState === 'error') return 'danger';
    if (feedbackState !== 'ok' || !feedbackData) return 'neutral';
    if (feedbackData.warnings.length > 0) return 'warning';
    return feedbackData.entries.length > 0 ? 'info' : 'neutral';
  })();
  $: feedbackValue = (() => {
    if (feedbackState === 'loading') return 'Loading';
    if (feedbackState === 'error') return 'Invalid';
    if (feedbackState !== 'ok' || !feedbackData) return '-';
    const n = feedbackData.entries.length;
    return `${n} ${n === 1 ? 'entry' : 'entries'}`;
  })();
  $: feedbackHint = (() => {
    if (feedbackState === 'error') return feedbackError || 'Feedback file has validation errors.';
    if (feedbackState !== 'ok' || !feedbackData) return '';
    if (feedbackData.warnings.length > 0) {
      return `${feedbackData.warnings.length} warning(s) flagged.`;
    }
    return feedbackData.entries.length === 0
      ? 'No feedback entries recorded yet.'
      : 'Feedback file is well-formed.';
  })();

  // Aggregate readiness banner
  type Readiness = {
    severity: 'success' | 'warning' | 'danger' | 'info';
    title: string;
    body: string;
  };
  $: readiness = ((): Readiness => {
    if (!selectedVault) {
      return {
        severity: 'info',
        title: 'No vault selected',
        body: 'Pick a vault to load its readiness summary.',
      };
    }
    if (isLoading) {
      return {
        severity: 'info',
        title: 'Loading vault status',
        body: 'Fetching validation, security, coverage, missing concepts, and feedback for ' + selectedVault + '.',
      };
    }
    const blockers: string[] = [];
    const warnings: string[] = [];
    if (validationState === 'ok' && validationData && validationData.invalid_count > 0) {
      blockers.push(`${validationData.invalid_count} validation failure(s)`);
    }
    if (securityState === 'ok' && securityData && securityData.status === 'fail') {
      blockers.push(`${securityData.summary.fail} security failure(s)`);
    }
    if (securityState === 'ok' && securityData && securityData.status === 'warning') {
      warnings.push(`${securityData.summary.warning} security warning(s)`);
    }
    if (feedbackState === 'error') {
      blockers.push('feedback file invalid');
    } else if (feedbackState === 'ok' && feedbackData && feedbackData.warnings.length > 0) {
      warnings.push(`${feedbackData.warnings.length} feedback warning(s)`);
    }
    if (missingState === 'ok' && missingData && missingData.total_missing > 0) {
      warnings.push(`${missingData.total_missing} missing concept(s)`);
    }
    if (blockers.length > 0) {
      return {
        severity: 'danger',
        title: 'Vault has unresolved blockers',
        body: 'Action needed: ' + blockers.join(', ') + '.',
      };
    }
    if (warnings.length > 0) {
      return {
        severity: 'warning',
        title: 'Vault is healthy with open items',
        body: 'Review: ' + warnings.join(', ') + '.',
      };
    }
    return {
      severity: 'success',
      title: 'Vault is release-ready',
      body: 'Validation, security, coverage, missing concepts, and feedback all pass for ' + selectedVault + '.',
    };
  })();

  // Top 3 weighted next actions, sourced from /tasks.
  $: nextActions = ((): Array<{ priority: number; note: string; path: string; instruction: string }> => {
    if (tasksState !== 'ok' || !tasksData) return [];
    return tasksData.tasks.slice(0, 3).map((t) => ({
      priority: t.priority,
      note: t.note,
      path: t.path,
      instruction: t.instruction,
    }));
  })();

  onMount(async () => {
    await loadHealth();
    await loadVaults();
    if (selectedVault) {
      await loadVaultData(selectedVault);
    }
  });
</script>

<div class="cve-page cve-stack">

  <!-- ============================================================
       Toolbar: title, vault selector, refresh
       ============================================================ -->
  <header class="cve-toolbar" aria-label="Dashboard header">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Dashboard</h1>
      <div class="cve-toolbar__meta">
        {#if vaultsState === 'loading'}
          <span>Loading vaults...</span>
        {:else if vaultsState === 'error'}
          <span class="cve-badge cve-badge-danger" role="status">Vaults: {vaultsError}</span>
        {:else if vaultList.length === 0}
          <span>
            No vaults configured.
            <a class="cve-link" href="/app/vault-setup">Set one up</a>.
          </span>
        {:else}
          <label class="cve-label" for="vault-select">Vault</label>
          <select
            id="vault-select"
            class="cve-select"
            value={selectedVault}
            on:change={handleVaultChange}
            aria-label="Active vault"
          >
            {#each vaultList as v}
              <option value={v}>{v}</option>
            {/each}
          </select>
          <span class="cve-badge cve-badge-neutral" aria-label="Active vault status">
            {selectedVault || 'none'}
          </span>
        {/if}
      </div>
      <div class="cve-toolbar__actions">
        <button
          type="button"
          class="cve-btn cve-btn-secondary"
          on:click={refresh}
          disabled={isLoading}
          aria-label="Refresh dashboard data"
        >
          {isLoading ? 'Loading' : 'Refresh'}
        </button>
      </div>
    </div>
  </header>

  <!-- ============================================================
       Readiness banner: single canonical headline
       ============================================================ -->
  <section
    class="cve-banner cve-banner--{readiness.severity}"
    role="status"
    aria-live="polite"
  >
    <div>
      <div class="cve-banner__title">{readiness.title}</div>
      <div class="cve-banner__body">{readiness.body}</div>
    </div>
  </section>

  <!-- ============================================================
       Canonical status strip: 5 tiles
       Each tile: label, value, status text, last-checked, single CTA
       ============================================================ -->
  <section aria-label="Vault status">
    <div class="cve-status-strip">

      <!-- Validation -->
      <div class="cve-status-tile {tileSeverity(validationState, validationSeverity)}">
        <span class="cve-status-tile__label">Validation</span>
        <span class="cve-status-tile__value">{validationValue}</span>
        <span class="cve-status-tile__hint">
          {validationState === 'error' ? validationError : validationHint || '-'}
        </span>
        <a class="cve-status-tile__cta cve-link" href="/app/validation">
          Open Validation
        </a>
        <span class="cve-status-tile__meta">{lastCheckedLabel(validationState)}</span>
      </div>

      <!-- Security -->
      <div class="cve-status-tile {tileSeverity(securityState, securitySeverity)}">
        <span class="cve-status-tile__label">Security</span>
        <span class="cve-status-tile__value">{securityValue}</span>
        <span class="cve-status-tile__hint">
          {securityState === 'error' ? securityError : securityHint || '-'}
        </span>
        <a class="cve-status-tile__cta cve-link" href="/app/security">
          Open Security
        </a>
        <span class="cve-status-tile__meta">{lastCheckedLabel(securityState)}</span>
      </div>

      <!-- Coverage -->
      <div class="cve-status-tile {tileSeverity(summaryState, coverageSeverity)}">
        <span class="cve-status-tile__label">Coverage</span>
        <span class="cve-status-tile__value">{coverageValue}</span>
        <span class="cve-status-tile__hint">
          {summaryState === 'error' ? summaryError : coverageHint || '-'}
        </span>
        <a class="cve-status-tile__cta cve-link" href="/app/notes">
          Open Notes
        </a>
        <span class="cve-status-tile__meta">{lastCheckedLabel(summaryState)}</span>
      </div>

      <!-- Missing concepts / gaps -->
      <div class="cve-status-tile {tileSeverity(missingState, missingSeverity)}">
        <span class="cve-status-tile__label">Missing concepts</span>
        <span class="cve-status-tile__value">{missingValue}</span>
        <span class="cve-status-tile__hint">
          {missingState === 'error' ? missingError : missingHint || '-'}
        </span>
        <a class="cve-status-tile__cta cve-link" href="/app/graph">
          Open Graph
        </a>
        <span class="cve-status-tile__meta">{lastCheckedLabel(missingState)}</span>
      </div>

      <!-- Feedback -->
      <div class="cve-status-tile {tileSeverity(feedbackState, feedbackSeverity)}">
        <span class="cve-status-tile__label">Feedback</span>
        <span class="cve-status-tile__value">{feedbackValue}</span>
        <span class="cve-status-tile__hint">
          {feedbackHint || '-'}
        </span>
        <a class="cve-status-tile__cta cve-link" href="/app/feedback">
          Open Feedback
        </a>
        <span class="cve-status-tile__meta">{lastCheckedLabel(feedbackState)}</span>
      </div>

    </div>
  </section>

  <!-- ============================================================
       Main grid: next actions + vault health
       ============================================================ -->
  <section class="cve-dashboard-grid">

    <!-- Next actions card -->
    <article class="cve-card" aria-labelledby="next-actions-title">
      <div class="cve-card__header">
        <h2 id="next-actions-title" class="cve-card-title">Next best actions</h2>
        {#if tasksState === 'ok' && tasksData}
          <span class="cve-badge cve-badge-neutral">
            {tasksData.total} task{tasksData.total === 1 ? '' : 's'}
          </span>
        {/if}
      </div>

      {#if !selectedVault}
        <p class="cve-meta">Select a vault to surface the highest-priority improvement tasks.</p>
      {:else if tasksState === 'loading'}
        <p class="cve-meta">Computing prioritised task queue...</p>
      {:else if tasksState === 'error'}
        <p class="cve-meta">{tasksError}</p>
      {:else if tasksState === 'ok' && tasksData}
        {#if nextActions.length === 0}
          <p class="cve-meta">No improvement tasks. The vault is in good shape.</p>
        {:else}
          <ol class="cve-next-actions" aria-label="Top tasks">
            {#each nextActions as action}
              <li class="cve-next-action">
                <span class="cve-next-action__priority" aria-label="Priority {action.priority.toFixed(1)}">
                  P{action.priority.toFixed(1)}
                </span>
                <div class="cve-next-action__body">
                  <div class="cve-next-action__title">{action.note}</div>
                  <div class="cve-next-action__hint">{action.instruction}</div>
                </div>
              </li>
            {/each}
          </ol>
          {#if tasksData.feedback_status === 'error'}
            <p class="cve-meta">Feedback scoring unavailable; ranks are unweighted.</p>
          {/if}
        {/if}
        <p class="cve-meta" style="margin-top: 0.75rem;">
          Full queue:
          <a class="cve-link" href="/app/tasks">Open Tasks</a>
        </p>
      {/if}
    </article>

    <!-- Vault health card -->
    <article class="cve-card" aria-labelledby="vault-health-title">
      <div class="cve-card__header">
        <h2 id="vault-health-title" class="cve-card-title">Vault health</h2>
        {#if healthState === 'ok'}
          <span class="cve-badge cve-badge-success">Online</span>
        {:else if healthState === 'loading'}
          <span class="cve-badge cve-badge-neutral">Checking</span>
        {:else}
          <span class="cve-badge cve-badge-danger">Offline</span>
        {/if}
      </div>

      {#if healthState === 'ok' && healthData}
        <div class="cve-stack-tight">
          <div class="cve-kv-row">
            <span class="cve-kv-row__key">Uptime</span>
            <span class="cve-kv-row__value">{formatUptime(healthData.uptime_seconds)}</span>
          </div>
          <div class="cve-kv-row">
            <span class="cve-kv-row__key">Requests served</span>
            <span class="cve-kv-row__value">{healthData.requests_served}</span>
          </div>
          <div class="cve-kv-row">
            <span class="cve-kv-row__key">Avg latency</span>
            <span class="cve-kv-row__value">{healthData.metrics.avg_response_time_ms.toFixed(1)} ms</span>
          </div>
          <div class="cve-kv-row">
            <span class="cve-kv-row__key">Rate limit</span>
            <span class="cve-kv-row__value">{healthData.rate_limit_status.max_per_second}/s</span>
          </div>
          {#if selectedVault && healthData.vaults[selectedVault]}
            {@const meta = healthData.vaults[selectedVault]}
            <div class="cve-kv-row">
              <span class="cve-kv-row__key">Notes indexed</span>
              <span class="cve-kv-row__value">{meta.notes}</span>
            </div>
            <div class="cve-kv-row">
              <span class="cve-kv-row__key">Schema hash</span>
              <span class="cve-kv-row__value" title={meta.schema_hash}>
                {meta.schema_hash.slice(0, 12)}
              </span>
            </div>
            {#if meta.index_size_bytes}
              <div class="cve-kv-row">
                <span class="cve-kv-row__key">Index size</span>
                <span class="cve-kv-row__value">{(meta.index_size_bytes / 1024).toFixed(1)} KB</span>
              </div>
            {/if}
          {/if}
        </div>
      {:else if healthState === 'loading'}
        <p class="cve-meta">Contacting backend...</p>
      {:else}
        <p class="cve-meta">{healthError || 'Backend unavailable.'}</p>
      {/if}
    </article>
  </section>

  <!-- ============================================================
       Developer deep-link inspector
       Raw JSON is intentionally not rendered inline. The Developer
       route (/app/raw) hosts the full endpoint explorer in Phase 30D.
       ============================================================ -->
  <details class="cve-details cve-details--inspector">
    <summary>Diagnostic detail</summary>
    <div class="cve-details__body">
      <p class="cve-meta">
        Raw JSON inspection has moved off the Dashboard. Use the
        Developer route to view full API payloads, request history, and
        copy-ready output. {NO_TIMESTAMP_LABEL}.
      </p>
      <p style="margin-top: 0.5rem;">
        <a
          class="cve-details__developer-link"
          href={selectedVault ? `/app/raw?vault=${encodeURIComponent(selectedVault)}` : '/app/raw'}
          aria-label="Open Developer route for raw payload inspection"
        >
          Open in Developer
        </a>
      </p>
    </div>
  </details>

</div>
