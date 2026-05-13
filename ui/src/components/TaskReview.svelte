<script lang="ts">
  /*
    Phase 30D1 - Task Review.
    Real implementation backed by the existing /tasks API helper
    (fetchTasks). Uses Phase 30B primitives only: cve-toolbar,
    cve-banner, cve-status-strip, cve-status-tile, cve-table, plus the
    cve-details--inspector + cve-details__developer-link deep-link
    contract to the Developer route. No new dependency, no icon
    library, no raw Tailwind dark palette literals.

    The /tasks API exposes priority, type, target, note, path, missing,
    instruction, constraints, and an optional feedback_weight. The
    page surfaces those fields directly with deterministic sorting
    (priority desc, path asc as tiebreaker) and low-risk filters by
    task type.
  */

  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchTasks,
    isOk,
    errorMessage,
    type Task,
    type TasksData,
  } from '../lib/api.ts';
  import {
    getStoredVault,
    setStoredVault,
    getVaultFromUrl,
    chooseInitialVault,
  } from '../lib/vaultState.ts';

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';
  type SortKey = 'priority' | 'path' | 'type';

  const CHECKED_LABEL = 'Checked this session';
  const NOT_CHECKED_LABEL = 'Not yet checked';

  let vaultsState: LoadState = 'loading';
  let vaultList: string[] = [];
  let vaultsError = '';
  let selectedVault = '';

  let tasksState: LoadState = 'idle';
  let tasksData: TasksData | null = null;
  let tasksError = '';

  let typeFilter = 'all';
  let sortKey: SortKey = 'priority';

  function lastChecked(state: LoadState): string {
    if (state === 'ok' || state === 'error') return CHECKED_LABEL;
    return NOT_CHECKED_LABEL;
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

  async function loadTasks(vault: string) {
    if (!vault) return;
    tasksState = 'loading';
    tasksData = null;
    tasksError = '';
    const result = await fetchTasks(vault, { include_feedback: true });
    if (isOk(result)) {
      tasksData = result.data;
      tasksState = 'ok';
    } else {
      tasksError = errorMessage(result);
      tasksState = 'error';
    }
  }

  async function handleVaultChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedVault = select.value;
    setStoredVault(selectedVault);
    await loadTasks(selectedVault);
  }

  async function refresh() {
    if (tasksState === 'loading') return;
    if (selectedVault) await loadTasks(selectedVault);
  }

  // Derived task type catalogue (sorted, deterministic).
  $: taskTypes = (() => {
    if (!tasksData) return [] as string[];
    const set = new Set<string>();
    for (const t of tasksData.tasks) set.add(t.type);
    return Array.from(set).sort();
  })();

  // Filter + sort.
  function sortTasks(tasks: Task[], key: SortKey): Task[] {
    const copy = [...tasks];
    copy.sort((a, b) => {
      if (key === 'priority') {
        if (b.priority !== a.priority) return b.priority - a.priority;
        return a.path.toLowerCase().localeCompare(b.path.toLowerCase());
      }
      if (key === 'type') {
        const t = a.type.localeCompare(b.type);
        if (t !== 0) return t;
        return a.path.toLowerCase().localeCompare(b.path.toLowerCase());
      }
      return a.path.toLowerCase().localeCompare(b.path.toLowerCase());
    });
    return copy;
  }

  $: visibleTasks = (() => {
    if (!tasksData) return [] as Task[];
    const filtered =
      typeFilter === 'all'
        ? tasksData.tasks
        : tasksData.tasks.filter((t) => t.type === typeFilter);
    return sortTasks(filtered, sortKey);
  })();

  $: totalTasks = tasksData?.total ?? 0;
  $: highPriority = tasksData
    ? tasksData.tasks.filter((t) => t.priority >= 7).length
    : 0;
  $: mediumPriority = tasksData
    ? tasksData.tasks.filter((t) => t.priority >= 4 && t.priority < 7).length
    : 0;
  $: lowPriority = tasksData
    ? tasksData.tasks.filter((t) => t.priority < 4).length
    : 0;

  // Banner.
  type BannerSeverity = 'success' | 'warning' | 'danger' | 'info';
  $: banner = ((): { severity: BannerSeverity; title: string; body: string } => {
    if (!selectedVault) {
      return {
        severity: 'info',
        title: 'No vault selected',
        body: 'Pick a vault to view prioritised improvement tasks.',
      };
    }
    if (tasksState === 'loading') {
      return {
        severity: 'info',
        title: 'Loading tasks',
        body: 'Computing prioritised task queue for ' + selectedVault + '.',
      };
    }
    if (tasksState === 'error') {
      return {
        severity: 'danger',
        title: 'Tasks request failed',
        body: tasksError || 'Unable to reach the backend tasks route.',
      };
    }
    if (tasksState === 'ok' && tasksData) {
      if (tasksData.total === 0) {
        return {
          severity: 'success',
          title: 'No improvement tasks',
          body: selectedVault + ' has no outstanding improvement tasks.',
        };
      }
      if (tasksData.feedback_status === 'error') {
        return {
          severity: 'warning',
          title: tasksData.total + ' task(s) - feedback scoring unavailable',
          body: 'Tasks are ranked by base priority only because the feedback file has validation errors.',
        };
      }
      return {
        severity: 'info',
        title: tasksData.total + ' improvement task(s)',
        body: 'Tasks are ranked by priority for ' + selectedVault + '. Use the filters below to narrow the queue.',
      };
    }
    return {
      severity: 'info',
      title: 'Tasks idle',
      body: 'No task run yet.',
    };
  })();

  function noteHref(path: string): string {
    if (!selectedVault) return '/app/notes';
    return (
      '/app/notes?vault=' +
      encodeURIComponent(selectedVault) +
      '&path=' +
      encodeURIComponent(path)
    );
  }

  $: rawHref = (() => {
    const base = '/app/raw?endpoint=tasks';
    if (selectedVault) {
      return base + '&vault=' + encodeURIComponent(selectedVault) + '&source=tasks';
    }
    return base + '&source=tasks';
  })();

  function priorityBadge(p: number): string {
    if (p >= 7) return 'cve-badge cve-badge-danger';
    if (p >= 4) return 'cve-badge cve-badge-warning';
    return 'cve-badge cve-badge-info';
  }

  onMount(async () => {
    await loadVaults();
    if (selectedVault) await loadTasks(selectedVault);
  });
</script>

<div class="cve-page cve-stack">

  <header class="cve-toolbar" aria-label="Tasks header">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Tasks</h1>
      <div class="cve-toolbar__meta">
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
          <label class="cve-label" for="tasks-vault-select">Vault</label>
          <select
            id="tasks-vault-select"
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
          class="cve-btn cve-btn-secondary"
          on:click={refresh}
          disabled={tasksState === 'loading' || !selectedVault}
          aria-label="Refresh tasks"
        >
          {tasksState === 'loading' ? 'Loading' : 'Refresh'}
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

  <section aria-label="Task metrics">
    <div class="cve-status-strip">
      <div class="cve-status-tile cve-status-tile--info">
        <span class="cve-status-tile__label">Total</span>
        <span class="cve-status-tile__value">{tasksState === 'ok' ? totalTasks : '-'}</span>
        <span class="cve-status-tile__hint">Improvement tasks in queue.</span>
        <span class="cve-status-tile__meta">{lastChecked(tasksState)}</span>
      </div>
      <div class="cve-status-tile cve-status-tile--danger">
        <span class="cve-status-tile__label">High (>=7)</span>
        <span class="cve-status-tile__value">{tasksState === 'ok' ? highPriority : '-'}</span>
        <span class="cve-status-tile__hint">Highest-priority items.</span>
        <span class="cve-status-tile__meta">{lastChecked(tasksState)}</span>
      </div>
      <div class="cve-status-tile cve-status-tile--warning">
        <span class="cve-status-tile__label">Medium (4-6)</span>
        <span class="cve-status-tile__value">{tasksState === 'ok' ? mediumPriority : '-'}</span>
        <span class="cve-status-tile__hint">Mid-priority items.</span>
        <span class="cve-status-tile__meta">{lastChecked(tasksState)}</span>
      </div>
      <div class="cve-status-tile cve-status-tile--neutral">
        <span class="cve-status-tile__label">Low (&lt;4)</span>
        <span class="cve-status-tile__value">{tasksState === 'ok' ? lowPriority : '-'}</span>
        <span class="cve-status-tile__hint">Lowest-priority items.</span>
        <span class="cve-status-tile__meta">{lastChecked(tasksState)}</span>
      </div>
    </div>
  </section>

  <section class="cve-p30d1-filters" aria-label="Task filters">
    <div class="cve-field">
      <label class="cve-label" for="task-type-filter">Filter by type</label>
      <select
        id="task-type-filter"
        class="cve-select"
        bind:value={typeFilter}
        disabled={!tasksData || tasksData.tasks.length === 0}
        aria-label="Filter tasks by type"
      >
        <option value="all">All types</option>
        {#each taskTypes as t}
          <option value={t}>{t}</option>
        {/each}
      </select>
    </div>
    <div class="cve-field">
      <label class="cve-label" for="task-sort-key">Sort by</label>
      <select
        id="task-sort-key"
        class="cve-select"
        bind:value={sortKey}
        disabled={!tasksData || tasksData.tasks.length === 0}
        aria-label="Sort tasks"
      >
        <option value="priority">Priority (high to low)</option>
        <option value="type">Type, then path</option>
        <option value="path">Note path</option>
      </select>
    </div>
  </section>

  <section aria-labelledby="task-list-title">
    <div class="cve-section">
      <h2 id="task-list-title" class="cve-section-title">Task queue</h2>

      {#if tasksState === 'loading'}
        <p class="cve-loading">Computing prioritised task queue...</p>
      {:else if tasksState === 'error'}
        <p class="cve-error">{tasksError}</p>
      {:else if !tasksData}
        <p class="cve-empty">No task result yet. Select a vault to load tasks.</p>
      {:else if visibleTasks.length === 0}
        {#if tasksData.total === 0}
          <p class="cve-success">No improvement tasks for this vault.</p>
        {:else}
          <p class="cve-empty">No tasks match the active filter.</p>
        {/if}
      {:else}
        <div class="cve-table-wrap cve-p30d1-table">
          <table class="cve-table" aria-label="Improvement tasks">
            <thead>
              <tr>
                <th scope="col">Priority</th>
                <th scope="col">Type</th>
                <th scope="col">Note</th>
                <th scope="col">Action</th>
                <th scope="col">Source</th>
                <th scope="col">Open</th>
              </tr>
            </thead>
            <tbody>
              {#each visibleTasks as task}
                <tr>
                  <td>
                    <span class={priorityBadge(task.priority)} aria-label="Priority {task.priority.toFixed(1)}">
                      P{task.priority.toFixed(1)}
                    </span>
                  </td>
                  <td class="cve-mono">{task.type}</td>
                  <td>
                    <div>{task.note}</div>
                    <div class="cve-meta cve-mono">{task.path}</div>
                  </td>
                  <td>
                    <div>{task.instruction}</div>
                    {#if task.missing && task.missing.length > 0}
                      <div class="cve-meta">
                        Missing: {task.missing.join(', ')}
                      </div>
                    {/if}
                  </td>
                  <td>
                    {#if task.feedback_weight}
                      <span class="cve-badge cve-badge-info" title={task.feedback_weight.entry_summary}>
                        feedback {task.feedback_weight.score_delta >= 0 ? '+' : ''}{task.feedback_weight.score_delta.toFixed(1)}
                      </span>
                    {:else}
                      <span class="cve-meta">schema</span>
                    {/if}
                  </td>
                  <td>
                    <a class="cve-link" href={noteHref(task.path)} aria-label="Open {task.path} in Notes">
                      Open in Notes
                    </a>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  </section>

  <details class="cve-details cve-details--inspector">
    <summary>Diagnostic detail</summary>
    <div class="cve-details__body">
      <p class="cve-meta">
        Raw /tasks JSON is intentionally not rendered inline on this
        page. The Developer route hosts the full payload and copy-ready
        output.
      </p>
      <p style="margin-top: 0.5rem;">
        <a
          class="cve-details__developer-link"
          href={rawHref}
          aria-label="Open Developer route for raw tasks payload"
        >
          Open in Developer
        </a>
      </p>
    </div>
  </details>

</div>
