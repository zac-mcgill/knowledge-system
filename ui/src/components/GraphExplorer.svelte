<script lang="ts">
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
    type GraphNeighborEntry,
    type GraphRelatedEntry,
    type GraphMissingEntry,
    type GraphNeighborsData,
    type GraphRelatedData,
    type GraphMissingNeighborsData,
    type MissingData,
    type RankedMissingConcept,
  } from '../lib/api.ts';

  // ---------------------------------------------------------------------------
  // Vault state
  // ---------------------------------------------------------------------------

  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';
  let selectedVault = '';

  // ---------------------------------------------------------------------------
  // Graph state
  // ---------------------------------------------------------------------------

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

  let graphState: LoadState = 'idle';
  let graphData: GraphData | null = null;
  let graphError = '';
  let graphRaw: unknown = null;

  // ---------------------------------------------------------------------------
  // Filters
  // ---------------------------------------------------------------------------

  const ALL_NODE_TYPES = ['note', 'domain', 'subdomain', 'topic', 'expected_concept'] as const;
  type NodeType = typeof ALL_NODE_TYPES[number];

  const ALL_EDGE_TYPES = ['parent', 'member_of', 'expected_coverage'] as const;
  type EdgeType = typeof ALL_EDGE_TYPES[number];

  let enabledNodeTypes: Set<string> = new Set(ALL_NODE_TYPES);
  let enabledEdgeTypes: Set<string> = new Set(ALL_EDGE_TYPES);

  // ---------------------------------------------------------------------------
  // Node search
  // ---------------------------------------------------------------------------

  let nodeSearch = '';

  // ---------------------------------------------------------------------------
  // Inspector state
  // ---------------------------------------------------------------------------

  let selectedNodeId: string | null = null;
  let selectedNode: GraphNode | null = null;
  let inspectorState: LoadState = 'idle';
  let inspectorError = '';
  let neighborData: GraphNeighborsData | null = null;
  let relatedData: GraphRelatedData | null = null;
  let missingNeighborData: GraphMissingNeighborsData | null = null;
  let inspectorRaw: unknown = null;

  // ---------------------------------------------------------------------------
  // Missing concepts state
  // ---------------------------------------------------------------------------

  let missingState: LoadState = 'idle';
  let missingData: MissingData | null = null;
  let missingError = '';
  let missingErrorCode = '';
  let missingRaw: unknown = null;

  // ---------------------------------------------------------------------------
  // Action card state
  // ---------------------------------------------------------------------------

  interface ActionCard {
    proposedTitle: string;
    proposedPath: string;
    domain: string;
    subdomain: string;
    suggestedSections: string[];
    copyableInstruction: string;
    sourceConcept: RankedMissingConcept;
  }

  let actionCard: ActionCard | null = null;
  let actionCopied = false;

  // ---------------------------------------------------------------------------
  // Tab state
  // ---------------------------------------------------------------------------

  type Tab = 'graph' | 'inspector' | 'missing';
  let activeTab: Tab = 'graph';

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------

  onMount(async () => {
    const res = await fetchVaults();
    vaultsLoading = false;
    if (isOk(res)) {
      vaultList = res.data.vaults;
      if (vaultList.length > 0) {
        selectedVault = vaultList[0];
        await Promise.all([loadGraph(), loadMissing()]);
      }
    } else {
      vaultsError = res.error?.message ?? 'Failed to load vaults';
    }
  });

  // ---------------------------------------------------------------------------
  // Load graph
  // ---------------------------------------------------------------------------

  async function loadGraph(): Promise<void> {
    if (!selectedVault) return;
    graphState = 'loading';
    graphData = null;
    graphError = '';
    graphRaw = null;
    selectedNodeId = null;
    selectedNode = null;
    neighborData = null;
    relatedData = null;
    missingNeighborData = null;
    inspectorState = 'idle';
    const res = await fetchGraph(selectedVault);
    if (isOk(res)) {
      graphData = res.data;
      graphRaw = res;
      graphState = 'ok';
    } else {
      graphError = res.error?.message ?? 'Failed to load graph';
      graphState = 'error';
    }
  }

  // ---------------------------------------------------------------------------
  // Load missing concepts
  // ---------------------------------------------------------------------------

  async function loadMissing(): Promise<void> {
    if (!selectedVault) return;
    missingState = 'loading';
    missingData = null;
    missingError = '';
    missingErrorCode = '';
    missingRaw = null;
    actionCard = null;
    const res = await fetchMissing(selectedVault);
    if (isOk(res)) {
      missingData = res.data;
      missingRaw = res;
      missingState = 'ok';
    } else {
      missingError = res.error?.message ?? 'Failed to load missing concepts';
      missingErrorCode = res.error?.code ?? '';
      missingState = 'error';
    }
  }

  // ---------------------------------------------------------------------------
  // Vault change
  // ---------------------------------------------------------------------------

  async function onVaultChange(): Promise<void> {
    selectedNodeId = null;
    selectedNode = null;
    actionCard = null;
    await Promise.all([loadGraph(), loadMissing()]);
  }

  // ---------------------------------------------------------------------------
  // Reload all
  // ---------------------------------------------------------------------------

  async function reloadAll(): Promise<void> {
    selectedNodeId = null;
    selectedNode = null;
    actionCard = null;
    await Promise.all([loadGraph(), loadMissing()]);
  }

  // ---------------------------------------------------------------------------
  // Node selection
  // ---------------------------------------------------------------------------

  async function selectNode(nodeId: string): Promise<void> {
    if (!graphData) return;
    const node = graphData.nodes.find(n => n.id === nodeId) ?? null;
    selectedNodeId = nodeId;
    selectedNode = node;
    activeTab = 'inspector';
    inspectorState = 'loading';
    inspectorError = '';
    neighborData = null;
    relatedData = null;
    missingNeighborData = null;
    inspectorRaw = null;

    const isNote = node?.type === 'note';

    try {
      const nbRes = await fetchGraphNeighbors(nodeId, selectedVault);
      const relRes = isNote ? await fetchGraphRelated(nodeId, selectedVault) : null;
      const misRes = isNote ? await fetchGraphMissing(nodeId, selectedVault) : null;

      if (isOk(nbRes)) {
        neighborData = nbRes.data;
      } else {
        inspectorError = nbRes.error?.message ?? 'Failed to load neighbours';
      }

      if (relRes && isOk(relRes)) {
        relatedData = relRes.data;
      }

      if (misRes && isOk(misRes)) {
        missingNeighborData = misRes.data;
      }

      inspectorRaw = { neighbors: nbRes, related: relRes, missing: misRes };
      inspectorState = inspectorError ? 'error' : 'ok';
    } catch (err) {
      inspectorError = err instanceof Error ? err.message : 'Inspector request failed';
      inspectorState = 'error';
    }
  }

  // ---------------------------------------------------------------------------
  // Filter toggles
  // ---------------------------------------------------------------------------

  function toggleNodeType(type: string): void {
    if (enabledNodeTypes.has(type)) {
      enabledNodeTypes = new Set([...enabledNodeTypes].filter(t => t !== type));
    } else {
      enabledNodeTypes = new Set([...enabledNodeTypes, type]);
    }
  }

  function toggleEdgeType(type: string): void {
    if (enabledEdgeTypes.has(type)) {
      enabledEdgeTypes = new Set([...enabledEdgeTypes].filter(t => t !== type));
    } else {
      enabledEdgeTypes = new Set([...enabledEdgeTypes, type]);
    }
  }

  // ---------------------------------------------------------------------------
  // Action card
  // ---------------------------------------------------------------------------

  function getDomainForSubdomain(subdomain: string): string {
    if (!graphData) return '';
    const subId = `subdomain::${subdomain}`;
    const parentEdge = graphData.edges.find(e => e.from === subId && e.type === 'parent');
    if (parentEdge) {
      const domainNode = graphData.nodes.find(n => n.id === parentEdge.to);
      return domainNode?.label ?? parentEdge.to.replace('domain::', '');
    }
    return '';
  }

  function generateActionCard(concept: RankedMissingConcept): void {
    const domain = getDomainForSubdomain(concept.subdomain);
    const proposedTitle = concept.concept;
    const proposedPath = `Fundamentals/${proposedTitle}.md`;
    const suggestedSections = ['Key Principles', 'How It Works', 'Trade-offs', 'Examples', 'Common Mistakes'];

    const lines = [
      `# Draft: Create missing concept note`,
      ``,
      `Title:         ${proposedTitle}`,
      `Proposed path: ${proposedPath}`,
      `Domain:        ${domain || '(see vault schema)'}`,
      `Subdomain:     ${concept.subdomain}`,
      `Missing rank:  ${concept.rank}   Score: ${concept.score.toFixed(2)}`,
      ``,
      `Suggested frontmatter:`,
      `  title: "${proposedTitle}"`,
      `  domain: "${domain || concept.subdomain}"`,
      `  subdomain: "${concept.subdomain}"`,
      `  status: partial`,
      `  type: concept`,
      ``,
      `Suggested sections:`,
      ...suggestedSections.map(s => `  - ${s}`),
      ``,
      `Instructions:`,
      `  Review the vault schema (vault_schema.py) and confirm the correct path,`,
      `  domain, and subdomain before creating this note.`,
      ``,
      `  Draft action only — no file has been created by the UI.`,
    ];

    actionCard = {
      proposedTitle,
      proposedPath,
      domain: domain || '',
      subdomain: concept.subdomain,
      suggestedSections,
      copyableInstruction: lines.join('\n'),
      sourceConcept: concept,
    };
    actionCopied = false;
    // Scroll action card into view via tick is not needed — it renders in the panel
  }

  async function copyActionCard(): Promise<void> {
    if (!actionCard) return;
    try {
      await navigator.clipboard.writeText(actionCard.copyableInstruction);
      actionCopied = true;
      setTimeout(() => { actionCopied = false; }, 2500);
    } catch {
      // clipboard access denied — user can select text manually
    }
  }

  function clearActionCard(): void {
    actionCard = null;
    actionCopied = false;
  }

  // ---------------------------------------------------------------------------
  // Derived / reactive
  // ---------------------------------------------------------------------------

  $: filteredNodes = graphData
    ? graphData.nodes.filter(n => {
        if (!enabledNodeTypes.has(n.type)) return false;
        if (!nodeSearch) return true;
        const q = nodeSearch.toLowerCase();
        return n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q);
      })
    : [];

  $: nodesByType = (() => {
    const groups: Record<string, GraphNode[]> = {};
    for (const n of filteredNodes) {
      (groups[n.type] = groups[n.type] ?? []).push(n);
    }
    return groups;
  })();

  $: nodeCounts = (() => {
    if (!graphData) return {} as Record<string, number>;
    const counts: Record<string, number> = {};
    for (const n of graphData.nodes) {
      counts[n.type] = (counts[n.type] ?? 0) + 1;
    }
    return counts;
  })();

  $: edgeCounts = (() => {
    if (!graphData) return {} as Record<string, number>;
    const counts: Record<string, number> = {};
    for (const e of graphData.edges) {
      counts[e.type] = (counts[e.type] ?? 0) + 1;
    }
    return counts;
  })();

  $: filteredNeighbors = neighborData
    ? neighborData.neighbors.filter(
        n => enabledNodeTypes.has(n.type) && enabledEdgeTypes.has(n.edge_type),
      )
    : [];

  $: rankedMissing = missingData
    ? (missingData.ranked as unknown as RankedMissingConcept[])
    : [];

  // ---------------------------------------------------------------------------
  // Style helpers (deterministic, no dynamic class generation)
  // ---------------------------------------------------------------------------

  const NODE_TYPE_DOT: Record<string, string> = {
    note: 'bg-sky-500',
    domain: 'bg-violet-500',
    subdomain: 'bg-indigo-500',
    topic: 'bg-teal-500',
    expected_concept: 'bg-amber-500',
  };

  const NODE_TYPE_BADGE: Record<string, string> = {
    note: 'bg-sky-900 text-sky-300 border border-sky-700',
    domain: 'bg-violet-900 text-violet-300 border border-violet-700',
    subdomain: 'bg-indigo-900 text-indigo-300 border border-indigo-700',
    topic: 'bg-teal-900 text-teal-300 border border-teal-700',
    expected_concept: 'bg-amber-900 text-amber-300 border border-amber-700',
  };

  const NODE_TYPE_ROW: Record<string, string> = {
    note: 'hover:bg-sky-950/40 border-l-sky-700',
    domain: 'hover:bg-violet-950/40 border-l-violet-700',
    subdomain: 'hover:bg-indigo-950/40 border-l-indigo-700',
    topic: 'hover:bg-teal-950/40 border-l-teal-700',
    expected_concept: 'hover:bg-amber-950/40 border-l-amber-700',
  };

  const EDGE_TYPE_BADGE: Record<string, string> = {
    parent: 'bg-violet-900/60 text-violet-300 border border-violet-700',
    member_of: 'bg-sky-900/60 text-sky-300 border border-sky-700',
    expected_coverage: 'bg-amber-900/60 text-amber-300 border border-amber-700',
  };

  const STRENGTH_BADGE: Record<string, string> = {
    topic: 'bg-teal-900/60 text-teal-300 border border-teal-700',
    subdomain: 'bg-indigo-900/60 text-indigo-300 border border-indigo-700',
    domain: 'bg-violet-900/60 text-violet-300 border border-violet-700',
  };

  function nodeTypeBadge(type: string): string {
    return NODE_TYPE_BADGE[type] ?? 'bg-zinc-800 text-zinc-400 border border-zinc-700';
  }

  function nodeTypeRow(type: string): string {
    return NODE_TYPE_ROW[type] ?? 'hover:bg-zinc-800/40 border-l-zinc-600';
  }

  function edgeTypeBadge(type: string): string {
    return EDGE_TYPE_BADGE[type] ?? 'bg-zinc-800 text-zinc-400 border border-zinc-700';
  }

  function strengthBadge(strength: string): string {
    return STRENGTH_BADGE[strength] ?? 'bg-zinc-800 text-zinc-400 border border-zinc-700';
  }

  function nodeDot(type: string): string {
    return NODE_TYPE_DOT[type] ?? 'bg-zinc-500';
  }

  // Display label for node type
  const NODE_TYPE_LABELS: Record<string, string> = {
    note: 'Notes',
    domain: 'Domains',
    subdomain: 'Subdomains',
    topic: 'Topics',
    expected_concept: 'Expected Concepts',
  };
</script>

<!-- =========================================================================
     Graph Explorer
     Schema-derived deterministic relationships only.
     ========================================================================= -->

<div class="space-y-5">

  <!-- Header ---------------------------------------------------------------- -->
  <div class="flex flex-col gap-1">
    <div class="flex items-center gap-3">
      <h1 class="text-xl font-semibold text-zinc-100">Graph Explorer</h1>
      {#if selectedVault}
        <span class="px-2 py-0.5 rounded text-xs font-mono bg-zinc-800 text-zinc-400 border border-zinc-700">
          {selectedVault}
        </span>
      {/if}
    </div>
    <p class="text-xs text-amber-400 font-medium">
      Schema-derived deterministic relationships, not semantic or AI-inferred links.
    </p>
    <p class="text-xs text-zinc-500">
      Graph edges are built from schema hierarchy (domain → subdomain → topic) and note
      frontmatter fields only. No embeddings, no LLMs, no natural-language parsing.
    </p>
  </div>

  <!-- Controls -------------------------------------------------------------- -->
  <div class="flex flex-wrap items-center gap-3 p-3 rounded-lg bg-zinc-900 border border-zinc-800">

    <!-- Vault selector -->
    {#if vaultsLoading}
      <span class="text-xs text-zinc-500">Loading vaults…</span>
    {:else if vaultsError}
      <span class="text-xs text-red-400">{vaultsError}</span>
    {:else}
      <div class="flex items-center gap-2">
        <label for="graph-vault-select" class="text-xs text-zinc-400 shrink-0">Vault</label>
        <select
          id="graph-vault-select"
          bind:value={selectedVault}
          on:change={onVaultChange}
          class="text-xs bg-zinc-800 border border-zinc-700 text-zinc-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-sky-600"
        >
          {#each vaultList as v}
            <option value={v}>{v}</option>
          {/each}
        </select>
      </div>
    {/if}

    <!-- Reload button -->
    <button
      on:click={reloadAll}
      disabled={graphState === 'loading' || missingState === 'loading'}
      class="text-xs px-3 py-1.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-300 hover:bg-zinc-700 disabled:opacity-40 transition-colors"
    >
      {#if graphState === 'loading' || missingState === 'loading'}
        Loading…
      {:else}
        Reload
      {/if}
    </button>
  </div>

  <!-- Filter rows ----------------------------------------------------------- -->
  {#if graphState === 'ok' && graphData}
    <div class="flex flex-col gap-2 p-3 rounded-lg bg-zinc-900 border border-zinc-800">

      <!-- Node type filters -->
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs text-zinc-500 w-20 shrink-0">Node types</span>
        {#each ALL_NODE_TYPES as nt}
          <button
            on:click={() => toggleNodeType(nt)}
            class="flex items-center gap-1.5 text-xs px-2 py-1 rounded border transition-colors {enabledNodeTypes.has(nt)
              ? nodeTypeBadge(nt)
              : 'bg-zinc-900 text-zinc-600 border-zinc-800 opacity-50'}"
          >
            <span class="w-1.5 h-1.5 rounded-full {nodeDot(nt)}"></span>
            {nt.replace('_', ' ')}
            <span class="font-mono text-[10px] opacity-60">({nodeCounts[nt] ?? 0})</span>
          </button>
        {/each}
      </div>

      <!-- Edge type filters -->
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs text-zinc-500 w-20 shrink-0">Edge types</span>
        {#each ALL_EDGE_TYPES as et}
          <button
            on:click={() => toggleEdgeType(et)}
            class="text-xs px-2 py-1 rounded border transition-colors {enabledEdgeTypes.has(et)
              ? edgeTypeBadge(et)
              : 'bg-zinc-900 text-zinc-600 border-zinc-800 opacity-50'}"
          >
            {et.replace('_', ' ')}
            <span class="font-mono text-[10px] opacity-60">({edgeCounts[et] ?? 0})</span>
          </button>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Graph metrics --------------------------------------------------------- -->
  {#if graphState === 'ok' && graphData}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
      <div class="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-center">
        <div class="text-lg font-mono font-semibold text-zinc-100">{graphData.nodes.length}</div>
        <div class="text-xs text-zinc-500 mt-0.5">Total nodes</div>
      </div>
      <div class="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-center">
        <div class="text-lg font-mono font-semibold text-zinc-100">{graphData.edges.length}</div>
        <div class="text-xs text-zinc-500 mt-0.5">Total edges</div>
      </div>
      {#each ALL_NODE_TYPES as nt}
        {#if (nodeCounts[nt] ?? 0) > 0}
          <div class="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-center">
            <div class="text-lg font-mono font-semibold {nt === 'expected_concept' ? 'text-amber-400' : 'text-zinc-100'}">
              {nodeCounts[nt] ?? 0}
            </div>
            <div class="text-xs text-zinc-500 mt-0.5">{nt.replace('_', ' ')}</div>
          </div>
        {/if}
      {/each}
    </div>
  {/if}

  <!-- Tab bar --------------------------------------------------------------- -->
  <div class="flex gap-1 border-b border-zinc-800">
    {#each [['graph', 'Graph'], ['inspector', 'Inspector'], ['missing', 'Missing Concepts']] as [tab, label]}
      <button
        on:click={() => activeTab = tab as Tab}
        class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px {activeTab === tab
          ? 'border-sky-500 text-sky-400'
          : 'border-transparent text-zinc-500 hover:text-zinc-300'}"
      >
        {label}
        {#if tab === 'inspector' && selectedNode}
          <span class="ml-1.5 text-xs font-mono px-1 py-0.5 rounded {nodeTypeBadge(selectedNode.type)}">
            {selectedNode.type}
          </span>
        {/if}
        {#if tab === 'missing' && missingData && missingData.total_missing > 0}
          <span class="ml-1.5 text-xs font-mono px-1.5 py-0.5 rounded bg-amber-900 text-amber-300 border border-amber-700">
            {missingData.total_missing}
          </span>
        {/if}
      </button>
    {/each}
  </div>

  <!-- ========== TAB: GRAPH ================================================= -->
  {#if activeTab === 'graph'}
    <div class="space-y-4">

      {#if graphState === 'idle'}
        <p class="text-sm text-zinc-500">Select a vault to load the graph.</p>

      {:else if graphState === 'loading'}
        <div class="flex items-center gap-2 text-sm text-zinc-400">
          <span class="animate-pulse">Building graph…</span>
        </div>

      {:else if graphState === 'error'}
        <div class="p-4 rounded-lg bg-red-950 border border-red-800 text-red-300 text-sm">
          <span class="font-medium">Graph unavailable:</span> {graphError}
        </div>

      {:else if graphState === 'ok' && graphData}

        {#if graphData.nodes.length === 0}
          <div class="p-4 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-500 text-sm">
            Graph is empty. No nodes found for this vault.
          </div>
        {:else}

          <!-- Node search -->
          <div class="flex items-center gap-2">
            <input
              type="text"
              bind:value={nodeSearch}
              placeholder="Filter nodes by label or id…"
              class="flex-1 max-w-sm text-xs bg-zinc-900 border border-zinc-700 text-zinc-200 rounded px-3 py-1.5 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-sky-600"
            />
            {#if nodeSearch}
              <button
                on:click={() => nodeSearch = ''}
                class="text-xs text-zinc-500 hover:text-zinc-300"
              >Clear</button>
            {/if}
            <span class="text-xs text-zinc-600 font-mono">{filteredNodes.length} / {graphData.nodes.length}</span>
          </div>

          <!-- Node groups -->
          {#if filteredNodes.length === 0}
            <p class="text-sm text-zinc-500">No nodes match the current filters.</p>
          {:else}
            {#each ALL_NODE_TYPES as nt}
              {#if nodesByType[nt] && nodesByType[nt].length > 0}
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full {nodeDot(nt)}"></span>
                    <span class="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
                      {NODE_TYPE_LABELS[nt] ?? nt}
                    </span>
                    <span class="text-xs font-mono text-zinc-600">({nodesByType[nt].length})</span>
                  </div>

                  <div class="space-y-0.5 ml-4">
                    {#each nodesByType[nt] as node (node.id)}
                      <button
                        on:click={() => selectNode(node.id)}
                        class="w-full text-left flex items-center gap-2 px-3 py-2 rounded border-l-2 text-sm transition-colors {nodeTypeRow(node.type)} {selectedNodeId === node.id ? 'bg-zinc-800 border-l-sky-500' : 'border-l-transparent'}"
                      >
                        <span class="flex-1 text-zinc-200 truncate">{node.label}</span>
                        <span class="shrink-0 text-[10px] font-mono text-zinc-600 truncate max-w-[180px] hidden sm:block">
                          {node.id}
                        </span>
                      </button>
                    {/each}
                  </div>
                </div>
              {/if}
            {/each}
          {/if}

          <!-- Raw graph JSON -->
          <details class="mt-2">
            <summary class="cursor-pointer text-xs text-zinc-600 hover:text-zinc-400 select-none py-1">
              Raw graph JSON
            </summary>
            <pre class="mt-2 p-3 rounded bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-400 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap break-all">{JSON.stringify(graphRaw, null, 2)}</pre>
          </details>

        {/if}
      {/if}
    </div>
  {/if}

  <!-- ========== TAB: INSPECTOR ============================================= -->
  {#if activeTab === 'inspector'}
    <div class="space-y-4">

      {#if !selectedNodeId || !selectedNode}
        <div class="p-4 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-500 text-sm">
          No node selected. Click a node in the Graph tab to inspect it.
        </div>

      {:else}

        <!-- Node header card -->
        <div class="p-4 rounded-lg bg-zinc-900 border border-zinc-800 space-y-2">
          <div class="flex items-start gap-3">
            <span class="shrink-0 mt-0.5 px-2 py-0.5 rounded text-xs font-medium {nodeTypeBadge(selectedNode.type)}">
              {selectedNode.type}
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-base font-semibold text-zinc-100 break-all">{selectedNode.label}</div>
              <div class="text-xs font-mono text-zinc-500 mt-1 break-all">{selectedNode.id}</div>
            </div>
          </div>
        </div>

        {#if inspectorState === 'loading'}
          <div class="text-sm text-zinc-400 animate-pulse">Loading neighbours…</div>

        {:else if inspectorState === 'error' && inspectorError}
          <div class="p-3 rounded-lg bg-red-950 border border-red-800 text-red-300 text-sm">
            {inspectorError}
          </div>

        {:else if inspectorState === 'ok'}

          <!-- Direct neighbours -->
          <div class="space-y-2">
            <h3 class="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
              Direct Neighbours
              {#if neighborData?.neighbors}
                <span class="font-mono normal-case text-zinc-600">({neighborData.neighbors.length} total, {filteredNeighbors.length} shown)</span>
              {/if}
            </h3>

            {#if !neighborData || !neighborData.found}
              <p class="text-sm text-zinc-500">Node not found in graph.</p>
            {:else if filteredNeighbors.length === 0}
              <p class="text-sm text-zinc-500">
                {neighborData.neighbors.length === 0 ? 'No direct neighbours.' : 'All neighbours hidden by current filters.'}
              </p>
            {:else}
              <div class="space-y-0.5">
                {#each filteredNeighbors as nb (nb.id)}
                  <div class="flex items-center gap-2 px-3 py-2 rounded bg-zinc-900 border border-zinc-800 text-sm">
                    <span class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium {nodeTypeBadge(nb.type)}">
                      {nb.type}
                    </span>
                    <span class="flex-1 text-zinc-200 truncate">{nb.label}</span>
                    <span class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium {edgeTypeBadge(nb.edge_type)}">
                      {nb.edge_type}
                    </span>
                    <button
                      on:click={() => selectNode(nb.id)}
                      class="shrink-0 text-[10px] text-zinc-600 hover:text-sky-400 transition-colors"
                      title="Inspect this node"
                    >inspect →</button>
                  </div>
                {/each}
              </div>
            {/if}
          </div>

          <!-- Related notes (notes only) -->
          {#if selectedNode.type === 'note'}
            <div class="space-y-2">
              <h3 class="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
                Related Notes
                {#if relatedData?.related}
                  <span class="font-mono normal-case text-zinc-600">({relatedData.related.length})</span>
                {/if}
              </h3>

              {#if !relatedData || !relatedData.found}
                <p class="text-sm text-zinc-500">Not found.</p>
              {:else if relatedData.related.length === 0}
                <p class="text-sm text-zinc-500">No related notes in the same domain/subdomain/topic.</p>
              {:else}
                <div class="space-y-0.5">
                  {#each relatedData.related as rel (rel.id)}
                    <div class="flex items-center gap-2 px-3 py-2 rounded bg-zinc-900 border border-zinc-800 text-sm">
                      <span class="flex-1 text-zinc-200 truncate">{rel.label}</span>
                      <span class="shrink-0 px-1.5 py-0.5 rounded text-[10px] {strengthBadge(rel.strength)}">
                        via {rel.strength}
                      </span>
                      <button
                        on:click={() => selectNode(rel.id)}
                        class="shrink-0 text-[10px] text-zinc-600 hover:text-sky-400 transition-colors"
                        title="Inspect this node"
                      >inspect →</button>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          <!-- Missing concepts near this node (notes only) -->
          {#if selectedNode.type === 'note'}
            <div class="space-y-2">
              <h3 class="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
                Missing Expected Concepts Near This Note
                {#if missingNeighborData?.missing}
                  <span class="font-mono normal-case text-zinc-600">({missingNeighborData.missing.length})</span>
                {/if}
              </h3>

              {#if !missingNeighborData || !missingNeighborData.found}
                <p class="text-sm text-zinc-500">Not found.</p>
              {:else if missingNeighborData.missing.length === 0}
                <p class="text-sm text-zinc-500">No missing expected concepts near this note.</p>
              {:else}
                <div class="space-y-0.5">
                  {#each missingNeighborData.missing as mc (mc.id)}
                    <div class="flex items-center gap-2 px-3 py-2 rounded bg-amber-950/30 border border-amber-800/40 text-sm">
                      <span class="shrink-0 px-1.5 py-0.5 rounded text-[10px] bg-amber-900 text-amber-300 border border-amber-700 font-medium">
                        missing
                      </span>
                      <span class="flex-1 text-amber-200 truncate">{mc.label}</span>
                      <span class="shrink-0 text-[10px] font-mono text-zinc-600 truncate hidden sm:block">
                        via {mc.via}
                      </span>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

        {/if}

        <!-- Raw inspector JSON -->
        <details>
          <summary class="cursor-pointer text-xs text-zinc-600 hover:text-zinc-400 select-none py-1">
            Raw inspector JSON
          </summary>
          <pre class="mt-2 p-3 rounded bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-400 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap break-all">{JSON.stringify(inspectorRaw, null, 2)}</pre>
        </details>

      {/if}
    </div>
  {/if}

  <!-- ========== TAB: MISSING CONCEPTS ====================================== -->
  {#if activeTab === 'missing'}
    <div class="space-y-4">

      {#if missingState === 'loading'}
        <div class="text-sm text-zinc-400 animate-pulse">Loading missing concepts…</div>

      {:else if missingState === 'error'}
        <div class="p-4 rounded-lg bg-zinc-900 border border-zinc-800 space-y-2">
          <p class="text-sm text-amber-400 font-medium">Missing concepts unavailable</p>
          {#if missingErrorCode === 'MISSING_CONCEPTS_EMPTY'}
            <p class="text-sm text-zinc-400">
              <code class="text-xs font-mono bg-zinc-800 px-1 rounded">EXPECTED_CONCEPTS</code>
              is not defined or empty in <code class="text-xs font-mono bg-zinc-800 px-1 rounded">vault_schema.py</code>.
              Define expected concepts to enable gap detection.
            </p>
          {:else}
            <p class="text-sm text-zinc-400">{missingError}</p>
            <p class="text-xs font-mono text-zinc-600">{missingErrorCode}</p>
          {/if}
        </div>

      {:else if missingState === 'ok' && missingData}

        <!-- Summary cards -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-center">
            <div class="text-lg font-mono font-semibold text-zinc-100">{missingData.total_expected}</div>
            <div class="text-xs text-zinc-500 mt-0.5">Expected concepts</div>
          </div>
          <div class="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-center">
            <div class="text-lg font-mono font-semibold text-emerald-400">{missingData.total_actual}</div>
            <div class="text-xs text-zinc-500 mt-0.5">Present in vault</div>
          </div>
          <div class="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-center">
            <div class="text-lg font-mono font-semibold {missingData.total_missing > 0 ? 'text-amber-400' : 'text-emerald-400'}">{missingData.total_missing}</div>
            <div class="text-xs text-zinc-500 mt-0.5">Missing</div>
          </div>
          <div class="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-center">
            <div class="text-lg font-mono font-semibold text-zinc-100">{missingData.domains_assessed}</div>
            <div class="text-xs text-zinc-500 mt-0.5">Domains assessed</div>
          </div>
          {#if missingData.subdomains !== undefined}
            <div class="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-center">
              <div class="text-lg font-mono font-semibold text-zinc-100">{missingData.subdomains}</div>
              <div class="text-xs text-zinc-500 mt-0.5">Subdomains</div>
            </div>
          {/if}
        </div>

        {#if missingData.total_missing === 0}
          <div class="p-4 rounded-lg bg-emerald-950 border border-emerald-800 text-emerald-300 text-sm">
            No missing concepts. All expected concepts are present in the vault.
          </div>

        {:else}

          <!-- Ranked missing concepts -->
          <div class="space-y-2">
            <h3 class="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
              Ranked Missing Concepts
              <span class="font-mono normal-case text-zinc-600">({rankedMissing.length})</span>
            </h3>

            {#if rankedMissing.length === 0}
              <p class="text-sm text-zinc-500">No ranked data available.</p>
            {:else}
              <div class="overflow-x-auto rounded-lg border border-zinc-800">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-zinc-800 bg-zinc-900/80">
                      <th class="text-left px-3 py-2 text-xs font-medium text-zinc-500 w-10">#</th>
                      <th class="text-left px-3 py-2 text-xs font-medium text-zinc-500">Concept</th>
                      <th class="text-left px-3 py-2 text-xs font-medium text-zinc-500">Subdomain</th>
                      <th class="text-right px-3 py-2 text-xs font-medium text-zinc-500 w-16">Score</th>
                      <th class="px-3 py-2 w-28"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each rankedMissing as rc, i (rc.concept + rc.subdomain)}
                      <tr class="border-b border-zinc-800/60 hover:bg-zinc-900/60 transition-colors {actionCard?.sourceConcept === rc ? 'bg-amber-950/20' : ''}">
                        <td class="px-3 py-2 text-xs font-mono text-zinc-600">{rc.rank ?? i + 1}</td>
                        <td class="px-3 py-2 text-zinc-200 font-medium">{rc.concept}</td>
                        <td class="px-3 py-2">
                          <span class="text-xs px-1.5 py-0.5 rounded {nodeTypeBadge('subdomain')}">{rc.subdomain}</span>
                        </td>
                        <td class="px-3 py-2 text-right text-xs font-mono text-zinc-400">{rc.score.toFixed(2)}</td>
                        <td class="px-3 py-2 text-right">
                          <button
                            on:click={() => generateActionCard(rc)}
                            class="text-[10px] px-2 py-1 rounded bg-amber-900/60 text-amber-300 border border-amber-700 hover:bg-amber-800/60 transition-colors"
                          >
                            Draft action
                          </button>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          </div>

          <!-- Action card -->
          {#if actionCard}
            <div class="mt-4 p-4 rounded-lg bg-amber-950/20 border border-amber-700/50 space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-amber-400 uppercase tracking-wide">
                  Draft action only — no file has been created
                </span>
                <button
                  on:click={clearActionCard}
                  class="text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
                >dismiss</button>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div>
                  <div class="text-xs text-zinc-500 mb-0.5">Proposed title</div>
                  <div class="font-semibold text-zinc-100">{actionCard.proposedTitle}</div>
                </div>
                <div>
                  <div class="text-xs text-zinc-500 mb-0.5">Proposed path</div>
                  <div class="font-mono text-xs text-zinc-300">{actionCard.proposedPath}</div>
                </div>
                {#if actionCard.domain}
                  <div>
                    <div class="text-xs text-zinc-500 mb-0.5">Domain</div>
                    <div class="text-zinc-300">{actionCard.domain}</div>
                  </div>
                {/if}
                <div>
                  <div class="text-xs text-zinc-500 mb-0.5">Subdomain</div>
                  <div class="text-zinc-300">{actionCard.subdomain}</div>
                </div>
              </div>

              <div>
                <div class="text-xs text-zinc-500 mb-1">Suggested sections</div>
                <div class="flex flex-wrap gap-1">
                  {#each actionCard.suggestedSections as sec}
                    <span class="text-xs px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700">{sec}</span>
                  {/each}
                </div>
              </div>

              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs text-zinc-500">Copyable instruction</span>
                  <button
                    on:click={copyActionCard}
                    class="text-xs px-2.5 py-1 rounded {actionCopied ? 'bg-emerald-900 text-emerald-300 border border-emerald-700' : 'bg-zinc-800 text-zinc-300 border border-zinc-700 hover:bg-zinc-700'} transition-colors"
                  >
                    {actionCopied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <pre class="p-3 rounded bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-300 overflow-x-auto whitespace-pre-wrap break-all max-h-48 overflow-y-auto">{actionCard.copyableInstruction}</pre>
              </div>

              <details>
                <summary class="cursor-pointer text-xs text-zinc-600 hover:text-zinc-400 select-none py-1">
                  Source concept object (raw JSON)
                </summary>
                <pre class="mt-2 p-3 rounded bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-400 overflow-x-auto whitespace-pre-wrap break-all">{JSON.stringify(actionCard.sourceConcept, null, 2)}</pre>
              </details>
            </div>
          {/if}

        {/if}

        <!-- Raw missing JSON -->
        <details>
          <summary class="cursor-pointer text-xs text-zinc-600 hover:text-zinc-400 select-none py-1">
            Raw missing concepts JSON
          </summary>
          <pre class="mt-2 p-3 rounded bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-400 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap break-all">{JSON.stringify(missingRaw, null, 2)}</pre>
        </details>

      {:else if missingState === 'idle'}
        <p class="text-sm text-zinc-500">Select a vault to load missing concepts.</p>
      {/if}

    </div>
  {/if}

</div>
