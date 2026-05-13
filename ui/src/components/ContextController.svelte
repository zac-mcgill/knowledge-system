<script lang="ts">
  // Phase 30E2 - Controller as a command-centre planning page.
  //
  // Two-column layout at xl+:
  //   - left/main: readiness state, blockers, warnings, service summary
  //   - right/secondary: ranked recommendations and next-best action
  //
  // Readiness polarity is corrected via readinessPolarity() so negative
  // flags (has_tasks, has_missing_concepts, has_feedback_warnings) never
  // render as positive/green just because the field is true.
  //
  // Recommendations deep-link to authoritative /app/* routes via
  // recommendationRoute(); the backend usually populates rec.links.ui
  // already, but we still expose recommendationRoute() so the link
  // contract is deterministic.
  //
  // Raw controller responses are demoted to cve-details--inspector with
  // a Developer deep-link to /app/raw (shared Phase 30D deep-link
  // contract from buildRawDeepLink).

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
  import {
    buildRawDeepLink,
    readinessPolarity,
    readinessLabel,
    readinessStatusText,
    recommendationRoute,
    sortRecommendations,
    severityRank,
  } from '../lib/phase30e2.ts';
  import { getStoredVault, setStoredVault } from '../lib/vaultState.ts';

  // ---------------------------------------------------------------------------
  // Vault state
  // ---------------------------------------------------------------------------

  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';

  let selectedVault = '';

  type Intent = 'review' | 'export' | 'agent-context' | 'quality' | 'security';
  const INTENTS: { value: Intent; label: string; description: string }[] = [
    { value: 'review',        label: 'Review',        description: 'General vault health' },
    { value: 'export',        label: 'Export',        description: 'Readiness for export' },
    { value: 'agent-context', label: 'Agent Context', description: 'Readiness for agent use' },
    { value: 'quality',       label: 'Quality',       description: 'Coverage and quality gaps' },
    { value: 'security',      label: 'Security',      description: 'Security findings' },
  ];
  let selectedIntent: Intent = 'review';

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';
  let stateLoadState: LoadState = 'idle';
  let planLoadState: LoadState = 'idle';

  let stateData: ContextStateData | null = null;
  let planData: ContextPlanData | null = null;

  let stateError = '';
  let planError = '';

  $: sortedRecs = planData ? sortRecommendations(planData.recommendations) : [];

  $: statePillLabel = (() => {
    if (vaultsLoading) return 'Loading';
    if (vaultsError) return 'Error';
    if (!selectedVault) return 'Idle';
    if (stateLoadState === 'loading' || planLoadState === 'loading') return 'Loading';
    if (stateLoadState === 'error' || planLoadState === 'error') return 'Error';
    if (stateLoadState !== 'ok' || planLoadState !== 'ok') return 'Idle';
    if (!stateData || !planData) return 'Idle';
    if (stateData.blockers.length > 0) return 'Blocked';
    if (!stateData.readiness.valid) return 'Blocked';
    if (planData.recommendations.length > 0) return 'Action needed';
    return 'Ready';
  })();

  $: statePillClass = (() => {
    switch (statePillLabel) {
      case 'Ready': return 'cve-p30e2-pill cve-p30e2-pill--ready';
      case 'Blocked': return 'cve-p30e2-pill cve-p30e2-pill--blocked';
      case 'Action needed': return 'cve-p30e2-pill cve-p30e2-pill--action';
      case 'Error': return 'cve-p30e2-pill cve-p30e2-pill--blocked';
      default: return 'cve-p30e2-pill';
    }
  })();

  $: headlineBanner = (() => {
    if (!selectedVault) return null;
    if (stateLoadState === 'error') {
      return { kind: 'danger', title: 'Could not load context state', body: stateError } as const;
    }
    if (planLoadState === 'error') {
      return { kind: 'danger', title: 'Could not build plan', body: planError } as const;
    }
    if (!stateData || !planData) return null;
    if (stateData.blockers.length > 0) {
      return {
        kind: 'danger',
        title: 'Blocked',
        body: `${stateData.blockers.length} blocker${stateData.blockers.length === 1 ? '' : 's'} must be resolved before this vault is ready.`,
      } as const;
    }
    if (!stateData.readiness.valid) {
      return {
        kind: 'danger',
        title: 'Validation failing',
        body: 'Validation is currently failing for this vault. Fix validation errors first.',
      } as const;
    }
    if (planData.recommendations.length > 0) {
      const top = planData.next_best_action;
      return {
        kind: 'warning',
        title: 'Action recommended',
        body: top ? top.title : `${planData.recommendations.length} recommendation${planData.recommendations.length === 1 ? '' : 's'} pending for intent "${planData.intent}".`,
      } as const;
    }
    if (stateData.warnings.length > 0) {
      return {
        kind: 'warning',
        title: 'Warnings present',
        body: `${stateData.warnings.length} warning${stateData.warnings.length === 1 ? '' : 's'} reported but no actions required for this intent.`,
      } as const;
    }
    return {
      kind: 'success',
      title: 'Ready',
      body: 'No blockers, no outstanding actions for this intent.',
    } as const;
  })();

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

  function recommendationHref(rec: ContextRecommendation): string {
    const route = recommendationRoute(rec);
    if (selectedVault) {
      const sep = route.includes('?') ? '&' : '?';
      return `${route}${sep}vault=${encodeURIComponent(selectedVault)}`;
    }
    return route;
  }

  function severityClass(sev: string): string {
    const r = severityRank(sev);
    if (r <= 1) return 'cve-p30e2-sev cve-p30e2-sev--high';
    if (r === 2) return 'cve-p30e2-sev cve-p30e2-sev--medium';
    if (r === 3) return 'cve-p30e2-sev cve-p30e2-sev--low';
    return 'cve-p30e2-sev cve-p30e2-sev--info';
  }

  $: rawStateDeepLink = buildRawDeepLink('context-state', selectedVault, 'controller');
  $: rawPlanDeepLink = buildRawDeepLink('context-plan', selectedVault, 'controller');
</script>

<!-- ============================================================
     Toolbar
     ============================================================ -->
<div class="cve-page cve-p30e2-page">

  <header class="cve-toolbar" data-testid="controller-toolbar">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Controller</h1>
      <span
        class="{statePillClass} cve-toolbar__status"
        data-testid="controller-state-pill"
        aria-live="polite"
      >
        {statePillLabel}
      </span>

      <div class="cve-toolbar__meta">
        <label class="cve-p30e2-inline-label" for="controller-vault-select">Vault</label>
        <select
          id="controller-vault-select"
          bind:value={selectedVault}
          on:change={handleVaultChange}
          class="cve-p30e2-inline-select cve-toolbar__select"
          disabled={vaultsLoading || !!vaultsError || vaultList.length === 0}
          aria-label="Active vault"
        >
          {#if vaultList.length === 0}
            <option value="">No vaults available</option>
          {/if}
          {#each vaultList as v}
            <option value={v}>{v}</option>
          {/each}
        </select>

        <label class="cve-p30e2-inline-label" for="controller-intent-select">Intent</label>
        <select
          id="controller-intent-select"
          bind:value={selectedIntent}
          on:change={handleIntentChange}
          class="cve-p30e2-inline-select cve-toolbar__select"
          disabled={!selectedVault}
          aria-label="Controller intent"
        >
          {#each INTENTS as intent}
            <option value={intent.value}>{intent.label}</option>
          {/each}
        </select>
      </div>

      <div class="cve-toolbar__actions">
        <button
          type="button"
          on:click={loadAll}
          disabled={!selectedVault || stateLoadState === 'loading' || planLoadState === 'loading'}
          class="cve-btn cve-btn-secondary"
          data-testid="controller-refresh"
          aria-label="Refresh controller"
        >
          {stateLoadState === 'loading' || planLoadState === 'loading' ? 'Loading...' : 'Refresh'}
        </button>
      </div>
    </div>
  </header>

  <!-- Headline banner -->
  {#if vaultsError}
    <section
      class="cve-banner cve-banner--danger"
      data-testid="controller-headline-banner"
      role="status"
    >
      <div>
        <p class="cve-banner__title">Could not load vaults</p>
        <p class="cve-banner__body">{vaultsError}</p>
      </div>
    </section>
  {:else if vaultsLoading}
    <section class="cve-banner cve-banner--info" data-testid="controller-headline-banner">
      <div>
        <p class="cve-banner__title">Loading vaults</p>
        <p class="cve-banner__body">Reading registered vaults from config.</p>
      </div>
    </section>
  {:else if vaultList.length === 0}
    <section class="cve-banner cve-banner--warning" data-testid="controller-headline-banner">
      <div>
        <p class="cve-banner__title">No vaults registered</p>
        <p class="cve-banner__body">
          Use <a href="/app/vault-setup" class="cve-link">Vault Setup</a>
          to create or connect a vault.
        </p>
      </div>
    </section>
  {:else if headlineBanner}
    <section
      class={`cve-banner cve-banner--${headlineBanner.kind}`}
      data-testid="controller-headline-banner"
      role="status"
    >
      <div>
        <p class="cve-banner__title">{headlineBanner.title}</p>
        <p class="cve-banner__body">{headlineBanner.body}</p>
      </div>
    </section>
  {/if}

  <!-- Status strip -->
  {#if stateData}
    <section class="cve-status-strip" data-testid="controller-status-strip" aria-label="Vault summary">
      {#each Object.entries(stateData.readiness) as [key, val]}
        {@const polarity = readinessPolarity(key, val)}
        <div
          class={`cve-status-tile cve-status-tile--${polarity === 'good' ? 'success' : 'danger'}`}
          data-testid={`controller-readiness-${key}`}
          data-polarity={polarity}
        >
          <span class="cve-status-tile__label">{readinessLabel(key)}</span>
          <span class="cve-status-tile__value">{readinessStatusText(key, val)}</span>
        </div>
      {/each}

      <div class="cve-status-tile cve-status-tile--neutral" data-testid="controller-tile-tasks">
        <span class="cve-status-tile__label">Tasks</span>
        <span class="cve-status-tile__value">{stateData.state.summary.total_tasks}</span>
      </div>
      <div class="cve-status-tile cve-status-tile--neutral" data-testid="controller-tile-missing">
        <span class="cve-status-tile__label">Missing concepts</span>
        <span class="cve-status-tile__value">{stateData.state.summary.total_missing}</span>
      </div>
      <div class="cve-status-tile cve-status-tile--neutral" data-testid="controller-tile-feedback">
        <span class="cve-status-tile__label">Feedback</span>
        <span class="cve-status-tile__value">{stateData.state.summary.feedback_entry_count}</span>
      </div>
      <div class="cve-status-tile cve-status-tile--neutral" data-testid="controller-tile-graph">
        <span class="cve-status-tile__label">Graph nodes</span>
        <span class="cve-status-tile__value">{stateData.state.summary.graph_node_count}</span>
      </div>
    </section>
  {/if}

  <!-- Command-centre grid -->
  <section class="cve-p30e2-controller-grid" data-testid="controller-command-grid">

    <!-- ── Left: state, blockers, warnings ── -->
    <div class="cve-p30e2-main" data-testid="controller-state-column">

      <article class="cve-p30e2-panel" data-testid="controller-state-panel">
        <h2 class="cve-p30e2-panel__title">Vault state</h2>

        {#if stateLoadState === 'idle'}
          <p class="cve-p30e2-empty">Select a vault to load the state snapshot.</p>
        {:else if stateLoadState === 'loading'}
          <p class="cve-p30e2-empty">Loading state...</p>
        {:else if stateLoadState === 'error'}
          <p class="cve-p30e2-empty">Could not load state.</p>
        {:else if stateData}

          <div class="cve-p30e2-kv-list">
            <div class="cve-kv-row">
              <span class="cve-kv-row__key">Validation</span>
              <span class="cve-kv-row__value" data-testid="controller-kv-validation">
                {stateData.state.summary.validation_status}
              </span>
            </div>
            <div class="cve-kv-row">
              <span class="cve-kv-row__key">Security</span>
              <span class="cve-kv-row__value" data-testid="controller-kv-security">
                {stateData.state.summary.security_status}
              </span>
            </div>
            <div class="cve-kv-row">
              <span class="cve-kv-row__key">Pending tasks</span>
              <span class="cve-kv-row__value">{stateData.state.summary.total_tasks}</span>
            </div>
            <div class="cve-kv-row">
              <span class="cve-kv-row__key">Missing concepts</span>
              <span class="cve-kv-row__value">{stateData.state.summary.total_missing}</span>
            </div>
            <div class="cve-kv-row">
              <span class="cve-kv-row__key">Feedback entries</span>
              <span class="cve-kv-row__value">{stateData.state.summary.feedback_entry_count}</span>
            </div>
            <div class="cve-kv-row">
              <span class="cve-kv-row__key">Graph nodes</span>
              <span class="cve-kv-row__value">{stateData.state.summary.graph_node_count}</span>
            </div>
          </div>
        {/if}
      </article>

      {#if stateData && stateData.blockers.length > 0}
        <article class="cve-p30e2-panel cve-p30e2-panel--danger" data-testid="controller-blockers-panel">
          <h2 class="cve-p30e2-panel__title">Blockers</h2>
          <ul class="cve-p30e2-issue-list">
            {#each stateData.blockers as b}
              <li class="cve-p30e2-issue cve-p30e2-issue--blocker">
                <span class="cve-p30e2-issue__label">Blocker</span>
                <span class="cve-p30e2-issue__text">{b}</span>
              </li>
            {/each}
          </ul>
        </article>
      {/if}

      {#if stateData && stateData.warnings.length > 0}
        <article class="cve-p30e2-panel cve-p30e2-panel--warning" data-testid="controller-warnings-panel">
          <h2 class="cve-p30e2-panel__title">Warnings</h2>
          <ul class="cve-p30e2-issue-list">
            {#each stateData.warnings as w}
              <li class="cve-p30e2-issue cve-p30e2-issue--warning">
                <span class="cve-p30e2-issue__label">Warning</span>
                <span class="cve-p30e2-issue__text">{w}</span>
              </li>
            {/each}
          </ul>
        </article>
      {/if}

    </div>

    <!-- ── Right: recommendations + next best action ── -->
    <aside class="cve-p30e2-aside" data-testid="controller-recommendation-column">

      <article class="cve-p30e2-panel" data-testid="controller-next-action-panel">
        <h2 class="cve-p30e2-panel__title">Next best action</h2>
        {#if planLoadState === 'idle'}
          <p class="cve-p30e2-empty">Select a vault to generate a plan.</p>
        {:else if planLoadState === 'loading'}
          <p class="cve-p30e2-empty">Building plan...</p>
        {:else if planLoadState === 'error'}
          <p class="cve-p30e2-empty">Could not build plan.</p>
        {:else if planData && planData.next_best_action}
          <p class="cve-p30e2-next-title">{planData.next_best_action.title}</p>
          {#if sortedRecs.length > 0}
            <a
              href={recommendationHref(sortedRecs[0])}
              class="cve-p30e2-next-cta"
              data-testid="controller-next-action-link"
            >
              Open in {recommendationRoute(sortedRecs[0]).replace('/app/', '')}
            </a>
          {/if}
        {:else if planData}
          <p class="cve-p30e2-empty">No actions required for intent "{planData.intent}".</p>
        {/if}
      </article>

      <article class="cve-p30e2-panel" data-testid="controller-recommendations-panel">
        <h2 class="cve-p30e2-panel__title">Recommendations</h2>

        {#if planLoadState !== 'ok' || !planData}
          <p class="cve-p30e2-empty">Recommendations will appear after the plan loads.</p>
        {:else if sortedRecs.length === 0}
          <p class="cve-p30e2-empty">No recommendations for intent "{planData.intent}".</p>
        {:else}
          <ol class="cve-p30e2-rec-list" data-testid="controller-recommendation-list">
            {#each sortedRecs as rec}
              <li class="cve-p30e2-rec" data-testid={`controller-rec-${rec.action}`}>
                <div class="cve-p30e2-rec__head">
                  <span class="cve-p30e2-rec__rank">#{rec.rank}</span>
                  <span class={severityClass(rec.severity)}>{rec.severity}</span>
                  <span class="cve-p30e2-rec__title">{rec.title}</span>
                </div>
                <p class="cve-p30e2-rec__reason">{rec.reason}</p>
                <a
                  href={recommendationHref(rec)}
                  class="cve-p30e2-rec__link"
                  data-testid={`controller-rec-link-${rec.action}`}
                >
                  Open {recommendationRoute(rec)}
                </a>
              </li>
            {/each}
          </ol>
        {/if}
      </article>
    </aside>
  </section>

  <!-- Developer / raw JSON behind cve-details--inspector -->
  <details class="cve-details cve-details--inspector" data-testid="controller-developer-details">
    <summary class="cve-details__summary">Developer details</summary>
    <div class="cve-details__body">
      <p class="cve-p30e2-helper-text">
        Raw controller responses are exposed via the deterministic Developer route.
        Use these deep-links to inspect the underlying JSON without leaving the
        Controller workflow.
      </p>
      <div class="cve-p30e2-developer-row">
        <a
          href={rawStateDeepLink}
          class="cve-details__developer-link"
          data-testid="controller-developer-state-link"
        >
          Open context state in Developer
        </a>
        <a
          href={rawPlanDeepLink}
          class="cve-details__developer-link"
          data-testid="controller-developer-plan-link"
        >
          Open context plan in Developer
        </a>
      </div>
    </div>
  </details>
</div>
