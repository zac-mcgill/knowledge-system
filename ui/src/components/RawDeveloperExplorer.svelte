<script lang="ts">
  /*
    Phase 30D1 - Raw Developer endpoint explorer.
    A diagnostics surface for inspecting raw API payloads. Uses only
    the existing safe read helpers exported from ui/src/lib/api.ts -
    no backend routes are added, no mutation endpoints are exposed.
    Renders inside the Phase 30B developer layout shell and reuses the
    cve-toolbar, cve-banner, cve-status-strip, and a bounded raw JSON
    viewer (cve-raw with internal scroll). No syntax highlighting
    dependency. No icon library.

    Endpoints surfaced here are read-only diagnostic GETs from the
    existing helper layer. The /context/security helper is intentionally
    excluded because it triggers a full vault scan; users should run it
    from the Security page instead. Destructive operations (delete,
    accept/reject, write, import-write, overwrite) are explicitly never
    exposed.

    Query-parameter contract:
      ?vault=<name>       - preselect the active vault.
      ?endpoint=<key>     - preselect the catalogue entry by key.
      ?source=<route>     - free-form provenance label, recorded only.
      ?focus=<value>      - free-form focus hint, recorded only.
    Unknown parameters are tolerated.
  */

  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchHealth,
    fetchSummary,
    fetchValidation,
    fetchTasks,
    fetchMissing,
    fetchFeedback,
    fetchNotes,
    fetchGraph,
    fetchGraphMissing,
    fetchContextProfiles,
    fetchTrustSummary,
    fetchStaleSummary,
    isOk,
    errorMessage,
    type ApiResult,
  } from '../lib/api.ts';
  import {
    getStoredVault,
    setStoredVault,
    chooseInitialVault,
  } from '../lib/vaultState.ts';

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

  interface EndpointEntry {
    key: string;
    label: string;
    method: 'GET';
    description: string;
    /** True if the endpoint requires an active vault. */
    requiresVault: boolean;
    /** Resolve the documented HTTP path for display purposes. */
    httpPath: (vault: string) => string;
    /** Authoritative UI route to hand off to. */
    uiRoute: string;
    /** Invoke the typed helper. */
    run: (vault: string) => Promise<ApiResult<unknown>>;
  }

  // Catalogue is intentionally tight: only safe, read-only diagnostic
  // GETs. Security scan and bundle generation are *not* listed because
  // they have side-effects (long scans, large response bodies, file
  // writes when paired with /context/export). Mutation routes (PUT,
  // POST that writes, DELETE) are deliberately omitted.
  const CATALOGUE: EndpointEntry[] = [
    {
      key: 'health',
      label: 'GET /health',
      method: 'GET',
      description: 'Server health, uptime, request counters, per-vault index metadata.',
      requiresVault: false,
      httpPath: () => '/health',
      uiRoute: '/app/',
      run: () => fetchHealth(),
    },
    {
      key: 'vaults',
      label: 'GET /vaults',
      method: 'GET',
      description: 'List registered vault names.',
      requiresVault: false,
      httpPath: () => '/vaults',
      uiRoute: '/app/vault-setup',
      run: () => fetchVaults(),
    },
    {
      key: 'summary',
      label: 'GET /summary',
      method: 'GET',
      description: 'Vault completion summary (total / complete / partial / coverage).',
      requiresVault: true,
      httpPath: (v) => '/summary?vault=' + encodeURIComponent(v),
      uiRoute: '/app/',
      run: (v) => fetchSummary(v),
    },
    {
      key: 'validation',
      label: 'GET /validation',
      method: 'GET',
      description: 'Schema validation status and invalid-note list.',
      requiresVault: true,
      httpPath: (v) => '/validation?vault=' + encodeURIComponent(v),
      uiRoute: '/app/validation',
      run: (v) => fetchValidation(v),
    },
    {
      key: 'tasks',
      label: 'GET /tasks',
      method: 'GET',
      description: 'Prioritised improvement tasks (feedback weighting enabled).',
      requiresVault: true,
      httpPath: (v) => '/tasks?vault=' + encodeURIComponent(v) + '&include_feedback=true',
      uiRoute: '/app/tasks',
      run: (v) => fetchTasks(v, { include_feedback: true }),
    },
    {
      key: 'missing',
      label: 'GET /missing',
      method: 'GET',
      description: 'Missing expected concepts. Returns MISSING_CONCEPTS_EMPTY when none configured.',
      requiresVault: true,
      httpPath: (v) => '/missing?vault=' + encodeURIComponent(v),
      uiRoute: '/app/graph',
      run: (v) => fetchMissing(v),
    },
    {
      key: 'feedback',
      label: 'GET /feedback',
      method: 'GET',
      description: 'Feedback entries from Vault Files/feedback.md.',
      requiresVault: true,
      httpPath: (v) => '/feedback?vault=' + encodeURIComponent(v),
      uiRoute: '/app/feedback',
      run: (v) => fetchFeedback(v),
    },
    {
      key: 'notes',
      label: 'GET /notes',
      method: 'GET',
      description: 'List notes with status / difficulty / missing / trust metadata.',
      requiresVault: true,
      httpPath: (v) => '/notes?vault=' + encodeURIComponent(v),
      uiRoute: '/app/notes',
      run: (v) => fetchNotes(v),
    },
    {
      key: 'graph',
      label: 'GET /graph',
      method: 'GET',
      description: 'Deterministic vault graph (nodes and edges).',
      requiresVault: true,
      httpPath: (v) => '/graph?vault=' + encodeURIComponent(v),
      uiRoute: '/app/graph',
      run: (v) => fetchGraph(v),
    },
    {
      key: 'graph-missing',
      label: 'GET /graph/missing',
      method: 'GET',
      description: 'Missing-concept rollup keyed by graph node.',
      requiresVault: true,
      httpPath: (v) => '/graph/missing?vault=' + encodeURIComponent(v),
      uiRoute: '/app/graph',
      run: (v) => fetchGraphMissing(v),
    },
    {
      key: 'context-profiles',
      label: 'GET /context/profiles',
      method: 'GET',
      description: 'Built-in context modes and device profiles.',
      requiresVault: false,
      httpPath: () => '/context/profiles',
      uiRoute: '/app/bundles',
      run: () => fetchContextProfiles(),
    },
    {
      key: 'trust',
      label: 'GET /trust',
      method: 'GET',
      description: 'Trust and review-state summary across the vault.',
      requiresVault: true,
      httpPath: (v) => '/trust?vault=' + encodeURIComponent(v),
      uiRoute: '/app/trust',
      run: (v) => fetchTrustSummary(v),
    },
    {
      key: 'stale',
      label: 'GET /stale',
      method: 'GET',
      description: 'Stale-note summary (last_reviewed / review_after windows).',
      requiresVault: true,
      httpPath: (v) => '/stale?vault=' + encodeURIComponent(v),
      uiRoute: '/app/trust',
      run: (v) => fetchStaleSummary(v),
    },
  ];

  const CATALOGUE_BY_KEY: Record<string, EndpointEntry> = (() => {
    const map: Record<string, EndpointEntry> = {};
    for (const e of CATALOGUE) map[e.key] = e;
    return map;
  })();

  // Endpoint operations explicitly excluded from this Developer surface.
  // Listed for the user so it is clear what raw inspection does *not*
  // give them. Phase 30D1 hard rule: no destructive / write actions.
  const EXCLUDED_ACTIONS = [
    'PUT /note (write)',
    'DELETE /vault/{vault_name}',
    'POST /import/markdown-folder (write)',
    'POST /import/obsidian-vault (write)',
    'POST /context/export (writes package to disk)',
    'POST /memory/* (accept / reject / draft writes)',
    'POST /feedback, PUT /feedback/{id}, DELETE /feedback/{id}',
    'POST /context/security (full vault scan with side effects)',
  ];

  let vaultsState: LoadState = 'loading';
  let vaultList: string[] = [];
  let vaultsError = '';
  let selectedVault = '';

  let endpointKey: string = 'health';
  let endpoint: EndpointEntry = CATALOGUE_BY_KEY.health;

  let requestState: LoadState = 'idle';
  let responseEnvelope: unknown = null;
  let responseError = '';
  let responseText = '';
  let lastEndpointKey = '';
  let lastVault = '';
  let downloadHref = '';
  let downloadName = '';
  let copyState: 'idle' | 'copied' | 'error' = 'idle';

  // Recorded deep-link provenance, tolerated and displayed only.
  let querySource = '';
  let queryFocus = '';

  function readQueryParam(name: string): string | null {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get(name);
    } catch {
      return null;
    }
  }

  async function loadVaults() {
    vaultsState = 'loading';
    const result = await fetchVaults();
    if (isOk(result)) {
      vaultList = result.data.vaults;
      if (vaultList.length > 0 && !selectedVault) {
        const urlVault = readQueryParam('vault');
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

  function selectEndpoint(key: string) {
    if (!(key in CATALOGUE_BY_KEY)) return;
    endpointKey = key;
    endpoint = CATALOGUE_BY_KEY[key];
  }

  function handleEndpointChange(event: Event) {
    const sel = event.target as HTMLSelectElement;
    selectEndpoint(sel.value);
  }

  function handleVaultChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedVault = select.value;
    setStoredVault(selectedVault);
  }

  function revokeDownload() {
    if (downloadHref) {
      try {
        URL.revokeObjectURL(downloadHref);
      } catch {
        // Ignore.
      }
      downloadHref = '';
      downloadName = '';
    }
  }

  async function runRequest() {
    if (endpoint.requiresVault && !selectedVault) {
      responseError = 'This endpoint requires an active vault.';
      requestState = 'error';
      responseEnvelope = null;
      responseText = '';
      revokeDownload();
      return;
    }
    requestState = 'loading';
    responseError = '';
    responseEnvelope = null;
    responseText = '';
    copyState = 'idle';
    revokeDownload();
    try {
      const result = await endpoint.run(selectedVault);
      responseEnvelope = result;
      responseText = JSON.stringify(result, null, 2);
      lastEndpointKey = endpoint.key;
      lastVault = selectedVault;
      if (isOk(result)) {
        requestState = 'ok';
      } else {
        requestState = 'error';
        responseError = errorMessage(result);
      }
      // Prepare a Blob URL for download.
      try {
        const blob = new Blob([responseText], { type: 'application/json' });
        downloadHref = URL.createObjectURL(blob);
        downloadName = 'cve-' + endpoint.key + (selectedVault ? '-' + selectedVault : '') + '.json';
      } catch {
        downloadHref = '';
        downloadName = '';
      }
    } catch (err) {
      requestState = 'error';
      responseError = err instanceof Error ? err.message : 'Unexpected error running request.';
    }
  }

  async function copyResponse() {
    if (!responseText) return;
    try {
      await navigator.clipboard.writeText(responseText);
      copyState = 'copied';
    } catch {
      copyState = 'error';
    }
  }

  type BannerSeverity = 'success' | 'warning' | 'danger' | 'info';
  $: banner = ((): { severity: BannerSeverity; title: string; body: string } => {
    return {
      severity: 'warning',
      title: 'Developer diagnostics surface',
      body:
        'This route exposes raw API payloads for debugging only. Only safe, read-only GET endpoints are listed. Destructive and write actions are deliberately not callable from here.',
    };
  })();

  onMount(async () => {
    // Tolerate the deep-link query contract.
    const ep = readQueryParam('endpoint');
    if (ep && ep in CATALOGUE_BY_KEY) {
      selectEndpoint(ep);
    }
    querySource = readQueryParam('source') || '';
    queryFocus = readQueryParam('focus') || '';
    await loadVaults();
  });
</script>

<div class="cve-page cve-stack">

  <header class="cve-toolbar" aria-label="Raw developer header">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">API / Raw Output</h1>
      <div class="cve-toolbar__meta">
        <span class="cve-badge cve-badge-info" aria-label="Developer surface">Developer</span>
        {#if vaultsState === 'loading'}
          <span>Loading vaults...</span>
        {:else if vaultsState === 'error'}
          <span class="cve-badge cve-badge-danger" role="status">
            Vaults: {vaultsError}
          </span>
        {:else if vaultList.length === 0}
          <span>
            No vaults configured.
            <a class="cve-link" href="/app/vault-setup">Set one up</a>.
          </span>
        {:else}
          <label class="cve-label" for="raw-vault-select">Vault</label>
          <select
            id="raw-vault-select"
            class="cve-select cve-toolbar__select"
            value={selectedVault}
            on:change={handleVaultChange}
            aria-label="Active vault"
          >
            {#each vaultList as v}
              <option value={v}>{v}</option>
            {/each}
          </select>
        {/if}
      </div>
      <div class="cve-toolbar__actions">
        <button
          type="button"
          class="cve-btn cve-btn-primary"
          on:click={runRequest}
          disabled={requestState === 'loading' || (endpoint.requiresVault && !selectedVault)}
          aria-label="Run selected endpoint"
        >
          {requestState === 'loading' ? 'Running' : 'Run request'}
        </button>
      </div>
    </div>
  </header>

  <section
    class="cve-banner cve-banner--{banner.severity}"
    role="status"
    aria-live="polite"
  >
    <div>
      <div class="cve-banner__title">{banner.title}</div>
      <div class="cve-banner__body">{banner.body}</div>
    </div>
  </section>

  <section class="cve-p30d1-raw-controls" aria-label="Endpoint selection">
    <div class="cve-field">
      <label class="cve-label" for="raw-endpoint-select">Endpoint</label>
      <select
        id="raw-endpoint-select"
        class="cve-select"
        value={endpointKey}
        on:change={handleEndpointChange}
        aria-label="API endpoint"
      >
        {#each CATALOGUE as entry}
          <option value={entry.key}>{entry.label}</option>
        {/each}
      </select>
      <p class="cve-helper">{endpoint.description}</p>
      <p class="cve-meta">
        Path: <code class="cve-mono">{endpoint.httpPath(selectedVault || '<vault>')}</code>
      </p>
      <p class="cve-meta">
        Authoritative UI:
        <a class="cve-link" href={endpoint.uiRoute}>{endpoint.uiRoute}</a>
      </p>
      {#if endpoint.requiresVault && !selectedVault}
        <p class="cve-meta">This endpoint requires an active vault.</p>
      {/if}
    </div>

    {#if querySource || queryFocus}
      <div class="cve-p30d1-provenance" aria-label="Deep-link provenance">
        {#if querySource}
          <span class="cve-badge cve-badge-neutral">source: {querySource}</span>
        {/if}
        {#if queryFocus}
          <span class="cve-badge cve-badge-neutral">focus: {queryFocus}</span>
        {/if}
      </div>
    {/if}
  </section>

  <section aria-labelledby="raw-response-title" class="cve-section">
    <h2 id="raw-response-title" class="cve-section-title">Response</h2>

    {#if requestState === 'idle'}
      <p class="cve-empty">No request issued yet. Pick an endpoint and click Run.</p>
    {:else if requestState === 'loading'}
      <p class="cve-loading">Requesting {endpoint.label}...</p>
    {:else}
      <div class="cve-status-strip" aria-label="Response metadata">
        <div class="cve-status-tile cve-status-tile--{requestState === 'ok' ? 'success' : 'danger'}">
          <span class="cve-status-tile__label">Status</span>
          <span class="cve-status-tile__value">{requestState === 'ok' ? 'ok' : 'error'}</span>
          <span class="cve-status-tile__hint">
            {requestState === 'ok' ? 'Envelope: status=ok' : (responseError || 'Envelope: status=error')}
          </span>
        </div>
        <div class="cve-status-tile cve-status-tile--info">
          <span class="cve-status-tile__label">Endpoint</span>
          <span class="cve-status-tile__value cve-mono">{lastEndpointKey || '-'}</span>
          <span class="cve-status-tile__hint">Last invoked entry.</span>
        </div>
        <div class="cve-status-tile cve-status-tile--neutral">
          <span class="cve-status-tile__label">Vault</span>
          <span class="cve-status-tile__value">{lastVault || '(n/a)'}</span>
          <span class="cve-status-tile__hint">Vault scope of the last run.</span>
        </div>
        <div class="cve-status-tile cve-status-tile--neutral">
          <span class="cve-status-tile__label">Size</span>
          <span class="cve-status-tile__value">{responseText.length.toLocaleString()} chars</span>
          <span class="cve-status-tile__hint">Formatted JSON length.</span>
        </div>
      </div>

      <div class="cve-p30d1-raw-actions">
        <button
          type="button"
          class="cve-btn cve-btn-secondary"
          on:click={copyResponse}
          disabled={!responseText}
          aria-label="Copy raw JSON to clipboard"
        >
          {copyState === 'copied' ? 'Copied' : copyState === 'error' ? 'Copy failed' : 'Copy JSON'}
        </button>
        {#if downloadHref}
          <a
            class="cve-btn cve-btn-secondary"
            href={downloadHref}
            download={downloadName}
            aria-label="Download raw JSON file"
          >
            Download JSON
          </a>
        {/if}
        <a class="cve-link" href={endpoint.uiRoute}>Back to {endpoint.uiRoute}</a>
      </div>

      <div class="cve-details cve-details--inspector cve-p30d1-raw-viewer" aria-label="Raw JSON viewer">
        <div class="cve-details__body">
          <pre class="cve-raw cve-p30d1-raw-pre" tabindex="0" aria-label="Raw JSON output">{responseText}</pre>
        </div>
      </div>
    {/if}
  </section>

  <section class="cve-section" aria-labelledby="raw-excluded-title">
    <h2 id="raw-excluded-title" class="cve-section-title">Not callable from this surface</h2>
    <p class="cve-meta">
      The Raw / Developer route is a read-only diagnostic surface. The
      following operations are intentionally <strong>not</strong> exposed
      here. Use the authoritative UI route or the CLI for any action
      with side effects.
    </p>
    <ul class="cve-list">
      {#each EXCLUDED_ACTIONS as item}
        <li class="cve-badge cve-badge-neutral" style="display: inline-flex; margin-right: 0.5rem;">
          {item}
        </li>
      {/each}
    </ul>
  </section>

</div>
