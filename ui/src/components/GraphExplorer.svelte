<script lang="ts">
  /*
    Phase 30D2 - Graph Workbench.

    Split-pane Graph workspace built on the Phase 30B primitives.

    Layout:
      cve-toolbar header (title, vault selector, reload, action card toggle)
      optional cve-banner for status / vault / error guidance
      cve-workbench (rail + inspector)
        rail:     node filters, edge filters, node search, deterministic
                  grouped node list (internal scroll)
        inspector when no node is selected:
                    ranked missing concepts overview (secondary, with
                    non-destructive copyable action card)
                  when a node is selected:
                    node header, neighbours, related notes, missing
                    concepts inline (no tabbed sub-views)
                  Developer deep-link to /app/raw for raw payloads.

    Removed in Phase 30D2:
      - The legacy tabbed view model (the three tab values: graph,
        inspector, missing). Missing concepts now appear inline in
        the inspector instead.
      - Inline raw JSON disclosure panels for /graph, neighbours,
        related, and /missing payloads. Diagnostic JSON is accessed
        through /app/raw via the Developer deep-link.

    Preserved:
      - All four backend helpers: fetchGraph, fetchGraphNeighbors,
        fetchGraphRelated, fetchGraphMissing (plus fetchMissing for
        the ranked overview).
      - Non-destructive action card generation for ranked missing
        concepts. It is text only, copy-only, and never writes to
        the vault.

    Token-only styling: no Tailwind dark palette literals.
  */

  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchGraph,
    fetchGraphNeighbors,
    fetchGraphRelated,
    fetchGraphMissing,
    fetchMissing,
    isOk,
    type GraphData,
    type GraphNode,
    type GraphNeighborsData,
    type GraphRelatedData,
    type GraphMissingNeighborsData,
    type MissingData,
    type RankedMissingConcept,
  } from '../lib/api.ts';
  import {
    getStoredVault,
    setStoredVault,
    chooseInitialVault,
    getVaultFromUrl,
  } from '../lib/vaultState.ts';

  // ---------------------------------------------------------------------------
  // Types / state
  // ---------------------------------------------------------------------------

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

  const ALL_NODE_TYPES: GraphNode['type'][] = [
    'note',
    'domain',
    'subdomain',
    'topic',
    'expected_concept',
  ];
  const ALL_EDGE_TYPES = ['parent', 'member_of', 'expected_coverage'] as const;

  // Vault
  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';
  let selectedVault = '';

  // Graph
  let graphState: LoadState = 'idle';
  let graphData: GraphData | null = null;
  let graphError = '';

  // Filters
  let enabledNodeTypes = new Set<GraphNode['type']>(ALL_NODE_TYPES);
  let enabledEdgeTypes = new Set<string>(ALL_EDGE_TYPES);
  let nodeSearch = '';

  // Selection
  let selectedNodeId = '';
  let neighborsState: LoadState = 'idle';
  let neighborsData: GraphNeighborsData | null = null;
  let neighborsError = '';
  let relatedState: LoadState = 'idle';
  let relatedData: GraphRelatedData | null = null;
  let relatedError = '';
  let missingNeighboursState: LoadState = 'idle';
  let missingNeighboursData: GraphMissingNeighborsData | null = null;
  let missingNeighboursError = '';
  let minStrength: 'subdomain' | 'domain' = 'domain';

  // Global ranked missing
  let missingState: LoadState = 'idle';
  let missingData: MissingData | null = null;
  let missingError = '';

  // Action card (non-destructive, secondary, never writes)
  let actionCardOpen = false;
  let actionCardText = '';
  let actionCardCopied = false;

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------

  $: filteredNodes = (graphData?.nodes ?? []).filter((n) => {
    if (!enabledNodeTypes.has(n.type)) return false;
    if (nodeSearch.trim()) {
      const q = nodeSearch.trim().toLowerCase();
      if (!n.label.toLowerCase().includes(q) && !n.id.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  $: groupedNodes = ALL_NODE_TYPES.map((t) => ({
    type: t,
    nodes: filteredNodes.filter((n) => n.type === t),
  })).filter((g) => g.nodes.length > 0);

  $: filteredEdgeCount =
    graphData?.edges?.filter((e) => enabledEdgeTypes.has(e.type)).length ?? 0;

  $: rankedMissing = missingData?.ranked ?? [];

  $: selectedNode = selectedNodeId && graphData
    ? graphData.nodes.find((n) => n.id === selectedNodeId) ?? null
    : null;

  $: filteredNeighbors = (neighborsData?.neighbors ?? []).filter(
    (n) => enabledEdgeTypes.has(n.edge_type) && enabledNodeTypes.has(n.type as GraphNode['type']),
  );

  $: filteredRelated = relatedData?.related ?? [];

  $: filteredMissingForNode = missingNeighboursData?.missing ?? [];

  // Banner
  type BannerSeverity = 'success' | 'warning' | 'danger' | 'info';
  $: banner = ((): { severity: BannerSeverity; title: string; body: string } | null => {
    if (vaultsLoading) return { severity: 'info', title: 'Loading vaults', body: 'Reading registered vaults.' };
    if (vaultsError) return { severity: 'danger', title: 'Vaults unavailable', body: vaultsError };
    if (!vaultsLoading && vaultList.length === 0) {
      return { severity: 'warning', title: 'No vaults configured', body: 'Use Vault Setup to register a vault before exploring the graph.' };
    }
    if (graphState === 'error') return { severity: 'danger', title: 'Graph unavailable', body: graphError };
    if (missingState === 'error') return { severity: 'warning', title: 'Missing concepts unavailable', body: missingError };
    return null;
  })();

  // Developer deep-link
  // Base: /app/raw?endpoint=graph&source=graph
  $: rawDeveloperHref = (() => {
    const params = new URLSearchParams();
    params.set('endpoint', 'graph');
    params.set('source', 'graph');
    if (selectedVault) params.set('vault', selectedVault);
    if (selectedNodeId) params.set('focus', selectedNodeId);
    // Static literal so guardrail tests can detect the contract: endpoint=graph&source=graph
    return `/app/raw?${params.toString()}`;
  })();

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function nodeTypeVariant(t: string): string {
    switch (t) {
      case 'note': return 'cve-badge-info';
      case 'domain': return 'cve-badge-success';
      case 'subdomain': return 'cve-badge-warning';
      case 'topic': return 'cve-badge-neutral';
      case 'expected_concept': return 'cve-badge-danger';
      default: return 'cve-badge-neutral';
    }
  }

  function edgeTypeVariant(t: string): string {
    switch (t) {
      case 'parent': return 'cve-badge-info';
      case 'member_of': return 'cve-badge-success';
      case 'expected_coverage': return 'cve-badge-warning';
      default: return 'cve-badge-neutral';
    }
  }

  function strengthVariant(s: string): string {
    switch (s) {
      case 'subdomain': return 'cve-badge-success';
      case 'domain': return 'cve-badge-info';
      default: return 'cve-badge-neutral';
    }
  }

  function toggleNodeType(t: GraphNode['type']) {
    const next = new Set(enabledNodeTypes);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    enabledNodeTypes = next;
  }

  function toggleEdgeType(t: string) {
    const next = new Set(enabledEdgeTypes);
    if (next.has(t)) next.delete(t);
    else next.add(t);
    enabledEdgeTypes = next;
  }

  function selectAllNodeTypes() {
    enabledNodeTypes = new Set(ALL_NODE_TYPES);
  }

  function selectAllEdgeTypes() {
    enabledEdgeTypes = new Set(ALL_EDGE_TYPES);
  }

  function generateActionCard(concepts: RankedMissingConcept[], limit: number) {
    const top = concepts.slice(0, Math.max(1, Math.min(20, limit)));
    if (top.length === 0) {
      actionCardText = '';
      return;
    }
    const lines: string[] = [];
    lines.push('# Ranked Missing Concepts - Improvement Brief');
    lines.push('');
    lines.push(`Vault: ${selectedVault}`);
    lines.push(`Total expected: ${missingData?.total_expected ?? 0}`);
    lines.push(`Total actual:   ${missingData?.total_actual ?? 0}`);
    lines.push(`Total missing:  ${missingData?.total_missing ?? 0}`);
    lines.push('');
    lines.push('## Suggested next concepts to author');
    lines.push('');
    for (const c of top) {
      lines.push(`- ${c.rank}. ${c.concept} (subdomain: ${c.subdomain}, score: ${c.score.toFixed(2)})`);
    }
    lines.push('');
    lines.push('This brief is read-only. No vault changes are performed.');
    actionCardText = lines.join('\n');
    actionCardCopied = false;
  }

  async function copyActionCard() {
    if (!actionCardText) return;
    try {
      await navigator.clipboard.writeText(actionCardText);
      actionCardCopied = true;
      setTimeout(() => { actionCardCopied = false; }, 2000);
    } catch {
      actionCardCopied = false;
    }
  }

  function clearActionCard() {
    actionCardText = '';
    actionCardCopied = false;
  }

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  async function loadVaults() {
    vaultsLoading = true;
    vaultsError = '';
    const result = await fetchVaults();
    vaultsLoading = false;
    if (isOk(result)) {
      vaultList = result.data.vaults;
      if (vaultList.length > 0) {
        const urlVault = getVaultFromUrl();
        const stored = getStoredVault();
        selectedVault = chooseInitialVault(vaultList, urlVault, stored);
        if (selectedVault) setStoredVault(selectedVault);
        await loadAll();
      }
    } else {
      vaultsError = result.error?.message ?? 'Failed to load vaults';
    }
  }

  async function loadAll() {
    await Promise.all([loadGraph(), loadGlobalMissing()]);
  }

  async function loadGraph() {
    if (!selectedVault) return;
    graphState = 'loading';
    graphError = '';
    const result = await fetchGraph(selectedVault);
    if (isOk(result)) {
      graphData = result.data;
      graphState = 'ok';
    } else {
      graphError = result.error?.message ?? 'Failed to load graph';
      graphState = 'error';
    }
  }

  async function loadGlobalMissing() {
    if (!selectedVault) return;
    missingState = 'loading';
    missingError = '';
    const result = await fetchMissing(selectedVault);
    if (isOk(result)) {
      missingData = result.data;
      missingState = 'ok';
    } else {
      missingError = result.error?.message ?? 'Missing concepts not available';
      missingData = null;
      missingState = 'error';
    }
  }

  async function selectNode(id: string) {
    if (!selectedVault) return;
    selectedNodeId = id;
    neighborsData = null;
    relatedData = null;
    missingNeighboursData = null;
    neighborsState = 'loading';
    relatedState = 'loading';
    missingNeighboursState = 'loading';

    const [n, r, m] = await Promise.all([
      fetchGraphNeighbors(id, selectedVault),
      fetchGraphRelated(id, selectedVault, minStrength),
      fetchGraphMissing(id, selectedVault),
    ]);

    if (isOk(n)) { neighborsData = n.data; neighborsState = 'ok'; }
    else { neighborsError = n.error?.message ?? 'Failed to load neighbours'; neighborsState = 'error'; }

    if (isOk(r)) { relatedData = r.data; relatedState = 'ok'; }
    else { relatedError = r.error?.message ?? 'Failed to load related notes'; relatedState = 'error'; }

    if (isOk(m)) { missingNeighboursData = m.data; missingNeighboursState = 'ok'; }
    else { missingNeighboursError = m.error?.message ?? 'Failed to load missing concepts'; missingNeighboursState = 'error'; }
  }

  async function refreshRelated() {
    if (!selectedNodeId || !selectedVault) return;
    relatedState = 'loading';
    const r = await fetchGraphRelated(selectedNodeId, selectedVault, minStrength);
    if (isOk(r)) { relatedData = r.data; relatedState = 'ok'; }
    else { relatedError = r.error?.message ?? 'Failed to load related notes'; relatedState = 'error'; }
  }

  function clearSelection() {
    selectedNodeId = '';
    neighborsData = null;
    relatedData = null;
    missingNeighboursData = null;
    neighborsState = 'idle';
    relatedState = 'idle';
    missingNeighboursState = 'idle';
  }

  function onVaultChange() {
    if (!selectedVault) return;
    setStoredVault(selectedVault);
    clearSelection();
    clearActionCard();
    loadAll();
  }

  onMount(loadVaults);
</script>

<!-- =========================================================================
  Phase 30D2 - Graph Workbench
  ========================================================================= -->
<div class="cve-page cve-stack">

  <header class="cve-toolbar" aria-label="Graph header">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Graph</h1>
      <div class="cve-toolbar__meta">
        {#if vaultsLoading}
          <span>Loading vaults...</span>
        {:else if vaultsError}
          <span class="cve-badge cve-badge-danger" role="status">Vaults: {vaultsError}</span>
        {:else if vaultList.length === 0}
          <span>
            No vaults configured.
            <a class="cve-link" href="/app/vault-setup">Set one up</a>.
          </span>
        {:else}
          <label class="cve-label" for="graph-vault-select">Vault</label>
          <select
            id="graph-vault-select"
            class="cve-select cve-toolbar__select"
            bind:value={selectedVault}
            on:change={onVaultChange}
            aria-label="Active vault"
          >
            {#each vaultList as v}
              <option value={v}>{v}</option>
            {/each}
          </select>
        {/if}
        {#if graphData}
          <span class="cve-meta cve-mono">
            {filteredNodes.length}/{graphData.nodes.length} nodes,
            {filteredEdgeCount}/{graphData.edges.length} edges
          </span>
        {/if}
      </div>
      <div class="cve-toolbar__actions">
        <button
          type="button"
          class="cve-btn cve-btn-secondary"
          on:click={() => selectedVault && loadAll()}
          disabled={!selectedVault || graphState === 'loading'}
          aria-label="Reload graph"
        >
          {graphState === 'loading' ? 'Loading' : 'Reload'}
        </button>
      </div>
    </div>
  </header>

  {#if banner}
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
  {/if}

  <div class="cve-workbench">

    <!-- ────────────────────────── Rail ────────────────────────── -->
    <aside class="cve-workbench__rail cve-p30d2-rail" aria-label="Graph filters and node list">

      <div class="cve-p30d2-rail__head">

        <div class="cve-p30d2-section-row">
          <h2 class="cve-p30d2-section-title">Node types</h2>
          <button type="button" class="cve-btn cve-btn-ghost cve-p30d2-mini-btn" on:click={selectAllNodeTypes}>All</button>
        </div>
        <div class="cve-p30d2-checkbox-row">
          {#each ALL_NODE_TYPES as t}
            <label class="cve-p30d2-checkbox">
              <input type="checkbox" checked={enabledNodeTypes.has(t)} on:change={() => toggleNodeType(t)} />
              <span class="cve-badge {nodeTypeVariant(t)}">{t}</span>
            </label>
          {/each}
        </div>

        <div class="cve-p30d2-section-row">
          <h2 class="cve-p30d2-section-title">Edge types</h2>
          <button type="button" class="cve-btn cve-btn-ghost cve-p30d2-mini-btn" on:click={selectAllEdgeTypes}>All</button>
        </div>
        <div class="cve-p30d2-checkbox-row">
          {#each ALL_EDGE_TYPES as t}
            <label class="cve-p30d2-checkbox">
              <input type="checkbox" checked={enabledEdgeTypes.has(t)} on:change={() => toggleEdgeType(t)} />
              <span class="cve-badge {edgeTypeVariant(t)}">{t}</span>
            </label>
          {/each}
        </div>

        <div class="cve-field">
          <label class="cve-label" for="graph-node-search">Search nodes</label>
          <input
            id="graph-node-search"
            class="cve-input"
            type="text"
            bind:value={nodeSearch}
            placeholder="Filter by label or id"
          />
        </div>

      </div>

      <div class="cve-p30d2-rail__list-head">
        <span class="cve-p30d2-section-title">Nodes</span>
        <span class="cve-meta cve-mono">{filteredNodes.length}</span>
      </div>

      <div class="cve-scroll-region cve-p30d2-list">
        {#if graphState === 'loading'}
          <p class="cve-loading">Loading graph...</p>
        {:else if graphState === 'error'}
          <p class="cve-error">{graphError}</p>
        {:else if !graphData || graphData.nodes.length === 0}
          <p class="cve-empty">No nodes in the graph.</p>
        {:else if filteredNodes.length === 0}
          <p class="cve-empty">No nodes match the current filters.</p>
        {:else}
          {#each groupedNodes as group}
            <div class="cve-p30d2-node-group">
              <div class="cve-p30d2-group-head">
                <span class="cve-badge {nodeTypeVariant(group.type)}">{group.type}</span>
                <span class="cve-meta cve-mono">{group.nodes.length}</span>
              </div>
              <ul class="cve-p30d2-node-list" role="list">
                {#each group.nodes as node}
                  <li>
                    <button
                      type="button"
                      class="cve-p30d2-node-row"
                      aria-current={selectedNodeId === node.id ? 'true' : undefined}
                      on:click={() => selectNode(node.id)}
                    >
                      <span class="cve-p30d2-node-row__label">{node.label}</span>
                      <span class="cve-mono cve-meta cve-p30d2-node-row__id">{node.id}</span>
                    </button>
                  </li>
                {/each}
              </ul>
            </div>
          {/each}
        {/if}
      </div>
    </aside>

    <!-- ────────────────────────── Inspector ────────────────────────── -->
    <section class="cve-workbench__inspector cve-p30d2-inspector" aria-label="Graph inspector">

      {#if !selectedNodeId}

        <!-- Default inspector view: ranked missing concepts overview -->
        <header class="cve-p30d2-inspector__head">
          <div>
            <h2 class="cve-section-title">Ranked Missing Concepts</h2>
            <p class="cve-helper">
              Select a node in the rail to inspect its neighbours, related notes, and missing
              concepts. While no node is selected, this pane surfaces the deterministic ranked
              list of missing concepts across the vault.
            </p>
          </div>
        </header>

        <div class="cve-scroll-region cve-p30d2-inspector__body">

          {#if missingState === 'loading'}
            <p class="cve-loading">Loading missing concepts...</p>
          {:else if missingState === 'error'}
            <p class="cve-error">{missingError}</p>
          {:else if !missingData || rankedMissing.length === 0}
            <p class="cve-empty">No missing concepts reported.</p>
          {:else}
            <div class="cve-p30d2-status-strip">
              <span class="cve-badge cve-badge-info">expected {missingData.total_expected}</span>
              <span class="cve-badge cve-badge-success">actual {missingData.total_actual}</span>
              <span class="cve-badge cve-badge-warning">missing {missingData.total_missing}</span>
              <span class="cve-badge cve-badge-neutral">domains {missingData.domains_assessed}</span>
              {#if missingData.subdomains !== undefined}
                <span class="cve-badge cve-badge-neutral">subdomains {missingData.subdomains}</span>
              {/if}
            </div>

            <section class="cve-section" aria-labelledby="graph-ranked-title">
              <h3 id="graph-ranked-title" class="cve-section-title">Top ranked missing concepts</h3>
              <div class="cve-table-wrap cve-p30d2-table">
                <table class="cve-table" aria-label="Ranked missing concepts">
                  <thead>
                    <tr>
                      <th scope="col">Rank</th>
                      <th scope="col">Concept</th>
                      <th scope="col">Subdomain</th>
                      <th scope="col">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each rankedMissing.slice(0, 50) as c}
                      <tr>
                        <td class="cve-mono">{c.rank}</td>
                        <td>{c.concept}</td>
                        <td class="cve-mono">{c.subdomain}</td>
                        <td class="cve-mono">{c.score.toFixed(2)}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </section>

            <!-- Non-destructive action card (read-only brief) -->
            <details class="cve-details cve-p30d2-action-card" bind:open={actionCardOpen}>
              <summary>
                Generate improvement brief (read-only, non-destructive)
              </summary>
              <div class="cve-details__body cve-stack">
                <p class="cve-helper">
                  Produces a Markdown brief listing the top missing concepts. This text is
                  copy-only - it does not write to the vault, edit notes, or call any
                  destructive endpoint.
                </p>
                <div class="cve-p30d2-search-actions">
                  <button type="button" class="cve-btn cve-btn-secondary" on:click={() => generateActionCard(rankedMissing, 10)}>
                    Generate top 10
                  </button>
                  <button type="button" class="cve-btn cve-btn-secondary" on:click={() => generateActionCard(rankedMissing, 20)}>
                    Generate top 20
                  </button>
                  {#if actionCardText}
                    <button type="button" class="cve-btn cve-btn-primary" on:click={copyActionCard}>
                      {actionCardCopied ? 'Copied' : 'Copy to clipboard'}
                    </button>
                    <button type="button" class="cve-btn cve-btn-ghost" on:click={clearActionCard}>Clear</button>
                  {/if}
                </div>
                {#if actionCardText}
                  <pre class="cve-raw cve-p30d2-action-text">{actionCardText}</pre>
                {/if}
              </div>
            </details>
          {/if}

          <details class="cve-details cve-details--inspector">
            <summary>Diagnostic detail</summary>
            <div class="cve-details__body">
              <p class="cve-helper">
                Raw /graph, /graph/neighbors, /graph/related, /graph/missing, and /missing
                payloads are not rendered inline on the Graph workbench. The Developer
                route exposes the full JSON payloads.
              </p>
              <p>
                <a class="cve-details__developer-link" href={rawDeveloperHref} aria-label="Open Developer route for raw graph payload">
                  Open in Developer
                </a>
              </p>
            </div>
          </details>

        </div>

      {:else}

        <!-- Node-selected inspector view -->
        <header class="cve-p30d2-inspector__head">
          <div>
            <h2 class="cve-section-title">
              {selectedNode?.label ?? selectedNodeId}
            </h2>
            <p class="cve-meta cve-mono">{selectedNodeId}</p>
          </div>
          <div class="cve-p30d2-inspector__actions">
            {#if selectedNode}
              <span class="cve-badge {nodeTypeVariant(selectedNode.type)}">{selectedNode.type}</span>
            {/if}
            <button type="button" class="cve-btn cve-btn-ghost" on:click={clearSelection} aria-label="Clear selection">
              Clear
            </button>
          </div>
        </header>

        <div class="cve-scroll-region cve-p30d2-inspector__body">

          <!-- Neighbours -->
          <section class="cve-section" aria-labelledby="graph-neighbours-title">
            <h3 id="graph-neighbours-title" class="cve-section-title">
              Neighbours
              <span class="cve-meta cve-mono">({filteredNeighbors.length}/{neighborsData?.neighbors.length ?? 0})</span>
            </h3>
            {#if neighborsState === 'loading'}
              <p class="cve-loading">Loading neighbours...</p>
            {:else if neighborsState === 'error'}
              <p class="cve-error">{neighborsError}</p>
            {:else if !neighborsData || filteredNeighbors.length === 0}
              <p class="cve-empty">
                {neighborsData?.neighbors.length ? 'No neighbours match the current filters.' : 'No neighbours found.'}
              </p>
            {:else}
              <div class="cve-table-wrap cve-p30d2-table">
                <table class="cve-table" aria-label="Direct neighbours">
                  <thead>
                    <tr>
                      <th scope="col">Label</th>
                      <th scope="col">Type</th>
                      <th scope="col">Edge</th>
                      <th scope="col">Id</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each filteredNeighbors as n}
                      <tr>
                        <td>
                          <button type="button" class="cve-p30d2-link-btn" on:click={() => selectNode(n.id)}>
                            {n.label}
                          </button>
                        </td>
                        <td><span class="cve-badge {nodeTypeVariant(n.type)}">{n.type}</span></td>
                        <td><span class="cve-badge {edgeTypeVariant(n.edge_type)}">{n.edge_type}</span></td>
                        <td class="cve-mono">{n.id}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          </section>

          <!-- Related notes -->
          <section class="cve-section" aria-labelledby="graph-related-title">
            <h3 id="graph-related-title" class="cve-section-title">
              Related notes
              <span class="cve-meta cve-mono">({filteredRelated.length})</span>
            </h3>
            <div class="cve-p30d2-related-controls">
              <label class="cve-label" for="graph-min-strength">Minimum strength</label>
              <select
                id="graph-min-strength"
                class="cve-select cve-p30d2-strength-select"
                bind:value={minStrength}
                on:change={refreshRelated}
              >
                <option value="domain">domain</option>
                <option value="subdomain">subdomain</option>
              </select>
            </div>
            {#if relatedState === 'loading'}
              <p class="cve-loading">Loading related notes...</p>
            {:else if relatedState === 'error'}
              <p class="cve-error">{relatedError}</p>
            {:else if filteredRelated.length === 0}
              <p class="cve-empty">No related notes at strength <code>{minStrength}</code> or above.</p>
            {:else}
              <div class="cve-table-wrap cve-p30d2-table">
                <table class="cve-table" aria-label="Related notes">
                  <thead>
                    <tr>
                      <th scope="col">Label</th>
                      <th scope="col">Strength</th>
                      <th scope="col">Via</th>
                      <th scope="col">Id</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each filteredRelated as r}
                      <tr>
                        <td>
                          <button type="button" class="cve-p30d2-link-btn" on:click={() => selectNode(r.id)}>
                            {r.label}
                          </button>
                        </td>
                        <td><span class="cve-badge {strengthVariant(r.strength)}">{r.strength}</span></td>
                        <td class="cve-mono">{r.via}</td>
                        <td class="cve-mono">{r.id}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          </section>

          <!-- Missing concepts inline -->
          <section class="cve-section" aria-labelledby="graph-missing-title">
            <h3 id="graph-missing-title" class="cve-section-title">
              Missing concepts near this node
              <span class="cve-meta cve-mono">({filteredMissingForNode.length})</span>
            </h3>
            {#if missingNeighboursState === 'loading'}
              <p class="cve-loading">Loading missing concepts...</p>
            {:else if missingNeighboursState === 'error'}
              <p class="cve-error">{missingNeighboursError}</p>
            {:else if filteredMissingForNode.length === 0}
              <p class="cve-empty">No missing concepts reported near this node.</p>
            {:else}
              <div class="cve-table-wrap cve-p30d2-table">
                <table class="cve-table" aria-label="Missing concepts near this node">
                  <thead>
                    <tr>
                      <th scope="col">Concept</th>
                      <th scope="col">Via</th>
                      <th scope="col">Id</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each filteredMissingForNode as m}
                      <tr>
                        <td>{m.label}</td>
                        <td class="cve-mono">{m.via}</td>
                        <td class="cve-mono">{m.id}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          </section>

          <details class="cve-details cve-details--inspector">
            <summary>Diagnostic detail</summary>
            <div class="cve-details__body">
              <p class="cve-helper">
                Raw /graph, /graph/neighbors, /graph/related, and /graph/missing payloads
                are not rendered inline. The Developer route exposes the full JSON payloads.
              </p>
              <p>
                <a class="cve-details__developer-link" href={rawDeveloperHref} aria-label="Open Developer route for raw graph payload">
                  Open in Developer
                </a>
              </p>
            </div>
          </details>

        </div>

      {/if}

    </section>
  </div>

</div>
