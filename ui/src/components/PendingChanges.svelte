<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchVaults,
    listPendingChanges,
    getPendingChange,
    acceptPendingChange,
    rejectPendingChange,
    isOk,
    type PendingChange,
  } from '../lib/api.ts';
  import { getStoredVault } from '../lib/vaultState.ts';
  import {
    buildRawDeepLink,
    PENDING_ACCEPT_PHRASE,
    PENDING_REJECT_PHRASE,
    isConfirmed,
  } from '../lib/phase30e1.ts';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

  let vaultList: string[] = [];
  let vaultsLoading = true;
  let vaultsError = '';
  let selectedVault = '';

  let listState: LoadState = 'idle';
  let changes: PendingChange[] = [];
  let listError = '';
  let filterStatus = 'pending';
  let filterLimit = 50;
  let filterText = '';

  let selectedChange: PendingChange | null = null;
  let detailState: LoadState = 'idle';
  let detailError = '';

  type ActionState = 'idle' | 'loading' | 'ok' | 'error';
  let actionState: ActionState = 'idle';
  let actionError = '';
  let actionErrorCode = '';
  let reviewerInput = '';
  let auditNoteInput = '';
  let acceptConfirmInput = '';
  let rejectConfirmInput = '';
  let activeAction: 'accept' | 'reject' | null = null;

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------

  $: rawDeepLink = buildRawDeepLink('pending', selectedVault, 'pending');

  $: counts = (() => {
    const c = { pending: 0, accepted: 0, rejected: 0, invalid: 0, total: 0 };
    for (const ch of changes) {
      c.total += 1;
      if (ch.status === 'pending') c.pending += 1;
      else if (ch.status === 'accepted') c.accepted += 1;
      else if (ch.status === 'rejected') c.rejected += 1;
      else if (ch.status === 'invalid') c.invalid += 1;
    }
    return c;
  })();

  $: filteredChanges = (() => {
    const q = filterText.trim().toLowerCase();
    if (!q) return changes;
    return changes.filter((ch) => {
      return (
        ch.path.toLowerCase().includes(q) ||
        (ch.section ?? '').toLowerCase().includes(q) ||
        ch.id.toLowerCase().includes(q)
      );
    });
  })();

  $: banner = (() => {
    if (listState === 'error') {
      return { severity: 'danger' as const, title: 'Could not load pending changes', body: listError };
    }
    if (detailState === 'error') {
      return { severity: 'danger' as const, title: 'Could not load change detail', body: detailError };
    }
    if (actionState === 'error') {
      return {
        severity: 'danger' as const,
        title: actionErrorCode ? `Action failed (${actionErrorCode})` : 'Action failed',
        body: actionError,
      };
    }
    if (selectedChange && selectedChange.validation_status === 'fail') {
      return {
        severity: 'warning' as const,
        title: 'Selected change has validation errors',
        body: 'Accepting is disabled until the proposal is re-validated upstream.',
      };
    }
    if (listState === 'ok' && changes.length === 0) {
      return {
        severity: 'info' as const,
        title: 'No pending changes',
        body: 'No proposed memory writes match the current filters.',
      };
    }
    return null;
  })();

  $: acceptReady =
    !!selectedChange &&
    selectedChange.status === 'pending' &&
    selectedChange.validation_status !== 'fail' &&
    isConfirmed(acceptConfirmInput, PENDING_ACCEPT_PHRASE) &&
    actionState !== 'loading';

  $: rejectReady =
    !!selectedChange &&
    selectedChange.status === 'pending' &&
    isConfirmed(rejectConfirmInput, PENDING_REJECT_PHRASE) &&
    actionState !== 'loading';

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
    if (selectedVault) await loadChanges();
  });

  // ---------------------------------------------------------------------------
  // Loaders
  // ---------------------------------------------------------------------------

  async function loadChanges() {
    if (!selectedVault) return;
    listState = 'loading';
    listError = '';
    changes = [];
    selectedChange = null;
    detailState = 'idle';
    const statusArg = filterStatus === 'all' ? undefined : filterStatus;
    const resp = await listPendingChanges(selectedVault, statusArg, filterLimit);
    if (!isOk(resp)) {
      listState = 'error';
      listError = resp.error?.message ?? 'Failed to load pending changes';
      return;
    }
    changes = resp.data.changes;
    listState = 'ok';
  }

  async function selectChange(change: PendingChange) {
    selectedChange = change;
    actionState = 'idle';
    actionError = '';
    actionErrorCode = '';
    activeAction = null;
    reviewerInput = '';
    auditNoteInput = '';
    acceptConfirmInput = '';
    rejectConfirmInput = '';

    detailState = 'loading';
    const resp = await getPendingChange(selectedVault, change.id);
    if (!isOk(resp)) {
      detailState = 'error';
      detailError = resp.error?.message ?? 'Failed to load change detail';
      return;
    }
    selectedChange = resp.data.change;
    detailState = 'ok';
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  async function submitAccept() {
    if (!selectedChange || !acceptReady) return;
    actionState = 'loading';
    actionError = '';
    actionErrorCode = '';
    const resp = await acceptPendingChange(
      selectedVault,
      selectedChange.id,
      reviewerInput || undefined,
      auditNoteInput || undefined,
    );
    if (!isOk(resp)) {
      actionState = 'error';
      actionError = resp.error?.message ?? 'Failed to accept change';
      actionErrorCode = resp.error?.code ?? '';
      return;
    }
    actionState = 'ok';
    selectedChange = resp.data.change;
    activeAction = null;
    acceptConfirmInput = '';
    await loadChanges();
  }

  async function submitReject() {
    if (!selectedChange || !rejectReady) return;
    actionState = 'loading';
    actionError = '';
    actionErrorCode = '';
    const resp = await rejectPendingChange(
      selectedVault,
      selectedChange.id,
      reviewerInput || undefined,
      auditNoteInput || undefined,
    );
    if (!isOk(resp)) {
      actionState = 'error';
      actionError = resp.error?.message ?? 'Failed to reject change';
      actionErrorCode = resp.error?.code ?? '';
      return;
    }
    actionState = 'ok';
    selectedChange = resp.data.change;
    activeAction = null;
    rejectConfirmInput = '';
    await loadChanges();
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function diffLineClass(line: string): string {
    if (line.startsWith('@@')) return 'cve-diff__line cve-diff__line--hunk';
    if (line.startsWith('+') && !line.startsWith('+++')) return 'cve-diff__line cve-diff__line--add';
    if (line.startsWith('-') && !line.startsWith('---')) return 'cve-diff__line cve-diff__line--remove';
    return 'cve-diff__line';
  }

  function statusTag(status: string): string {
    if (status === 'pending') return 'cve-p30e1-tag cve-p30e1-tag--pending';
    if (status === 'accepted') return 'cve-p30e1-tag cve-p30e1-tag--accepted';
    if (status === 'rejected') return 'cve-p30e1-tag cve-p30e1-tag--rejected';
    if (status === 'invalid') return 'cve-p30e1-tag cve-p30e1-tag--invalid';
    return 'cve-p30e1-tag';
  }

  function typeLabel(type: string): string {
    if (type === 'create_note_draft') return 'CREATE';
    if (type === 'suggest_note_update') return 'UPDATE';
    if (type === 'update_note_section_draft') return 'SECTION';
    return type.toUpperCase();
  }

  function fmtDate(iso: string | null): string {
    if (!iso) return '-';
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }
</script>

<div class="cve-page cve-p30e1-page">

  <!-- Toolbar -->
  <header class="cve-toolbar">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Pending Changes</h1>
      <div class="cve-toolbar__meta">
        <span
          class="cve-p30e1-pill"
          class:cve-p30e1-pill--pending={counts.pending > 0}
          data-testid="pending-state-pill"
        >{counts.pending} pending</span>
        {#if selectedVault}
          <span>Vault: <code class="cve-p30e1-mono">{selectedVault}</code></span>
        {/if}
        <span>Status filter: {filterStatus}</span>
      </div>
      <div class="cve-toolbar__actions">
        {#if vaultList.length > 1}
          <label class="cve-label cve-p30e1-inline-label" for="pending-vault-select">Vault</label>
          <select
            id="pending-vault-select"
            class="cve-select cve-p30e1-inline-select"
            bind:value={selectedVault}
            on:change={loadChanges}
            aria-label="Active vault"
          >
            {#each vaultList as v}
              <option value={v}>{v}</option>
            {/each}
          </select>
        {/if}
        <button
          type="button"
          class="cve-btn cve-btn-secondary"
          on:click={loadChanges}
          disabled={!selectedVault || listState === 'loading'}
          aria-label="Refresh pending changes"
        >
          {listState === 'loading' ? 'Refreshing' : 'Refresh'}
        </button>
        <a class="cve-details__developer-link" href={rawDeepLink}>Open in Developer</a>
      </div>
    </div>
  </header>

  <!-- Vault load states -->
  {#if vaultsLoading}
    <div class="cve-banner cve-banner--info"><div class="cve-banner__body">Loading vaults...</div></div>
  {:else if vaultsError}
    <div class="cve-banner cve-banner--danger">
      <div>
        <div class="cve-banner__title">Could not load vaults</div>
        <div class="cve-banner__body">{vaultsError}</div>
      </div>
    </div>
  {:else if vaultList.length === 0}
    <div class="cve-banner cve-banner--info">
      <div>
        <div class="cve-banner__title">No vaults registered</div>
        <div class="cve-banner__body">
          Use <a class="cve-link" href="/app/vault-setup">Vault Setup</a> to create one.
        </div>
      </div>
    </div>
  {:else}

    <!-- State banner -->
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

    <!-- Status strip -->
    <div class="cve-status-strip" aria-label="Pending queue summary">
      <div class="cve-status-tile" data-zero={counts.total === 0}>
        <span class="cve-status-tile__label">Total</span>
        <span class="cve-status-tile__value">{counts.total}</span>
      </div>
      <div class="cve-status-tile" data-zero={counts.pending === 0}>
        <span class="cve-status-tile__label">Pending</span>
        <span class="cve-status-tile__value">{counts.pending}</span>
      </div>
      <div class="cve-status-tile" data-zero={counts.accepted === 0}>
        <span class="cve-status-tile__label">Accepted</span>
        <span class="cve-status-tile__value">{counts.accepted}</span>
      </div>
      <div class="cve-status-tile" data-zero={counts.rejected === 0}>
        <span class="cve-status-tile__label">Rejected</span>
        <span class="cve-status-tile__value">{counts.rejected}</span>
      </div>
      <div class="cve-status-tile" data-zero={counts.invalid === 0}>
        <span class="cve-status-tile__label">Invalid</span>
        <span class="cve-status-tile__value">{counts.invalid}</span>
      </div>
    </div>

    <!-- Workbench: rail + inspector -->
    <div class="cve-workbench">

      <!-- Queue rail -->
      <aside class="cve-workbench__rail cve-p30e1-rail" aria-label="Pending change queue">
        <div class="cve-p30e1-rail__head">
          <div class="cve-field">
            <label class="cve-label" for="pending-filter-text">Search queue</label>
            <input
              id="pending-filter-text"
              class="cve-input"
              type="search"
              bind:value={filterText}
              placeholder="path, section, or id"
            />
          </div>
          <div class="cve-p30e1-filter-row">
            <div class="cve-field">
              <label class="cve-label" for="pending-filter-status">Status</label>
              <select
                id="pending-filter-status"
                class="cve-select"
                bind:value={filterStatus}
                on:change={loadChanges}
              >
                <option value="pending">Pending</option>
                <option value="accepted">Accepted</option>
                <option value="rejected">Rejected</option>
                <option value="invalid">Invalid</option>
                <option value="all">All</option>
              </select>
            </div>
            <div class="cve-field">
              <label class="cve-label" for="pending-filter-limit">Limit</label>
              <select
                id="pending-filter-limit"
                class="cve-select"
                bind:value={filterLimit}
                on:change={loadChanges}
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
              </select>
            </div>
          </div>
        </div>

        <div class="cve-p30e1-rail__body" data-testid="pending-queue-scroll">
          {#if listState === 'loading'}
            <div class="cve-loading">Loading pending changes...</div>
          {:else if listState === 'error'}
            <div class="cve-error">{listError}</div>
          {:else if filteredChanges.length === 0}
            <div class="cve-empty">No changes match the current filters.</div>
          {:else}
            <ul class="cve-p30e1-queue-list" role="list">
              {#each filteredChanges as ch (ch.id)}
                <li>
                  <button
                    type="button"
                    class="cve-p30e1-queue-item"
                    class:cve-p30e1-queue-item--active={selectedChange?.id === ch.id}
                    on:click={() => selectChange(ch)}
                    aria-label={`Inspect change ${ch.id} for ${ch.path}`}
                  >
                    <span class="cve-p30e1-queue-item__row">
                      <span class="cve-p30e1-queue-item__type">{typeLabel(ch.type)}</span>
                      <span class={statusTag(ch.status)}>{ch.status}</span>
                      {#if ch.validation_status === 'fail'}
                        <span class="cve-p30e1-tag cve-p30e1-tag--invalid">validation fail</span>
                      {/if}
                    </span>
                    <span class="cve-p30e1-queue-item__path">{ch.path}</span>
                    {#if ch.section}
                      <span class="cve-p30e1-queue-item__section">section: {ch.section}</span>
                    {/if}
                    <span class="cve-p30e1-queue-item__meta">{fmtDate(ch.created_at)}</span>
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      </aside>

      <!-- Inspector -->
      <section class="cve-workbench__inspector cve-p30e1-inspector" aria-label="Selected change inspector">

        {#if !selectedChange && detailState !== 'loading'}
          <div class="cve-p30e1-inspector__empty">
            <p>Select a change from the queue to review provenance, diff, and accept or reject it.</p>
          </div>
        {:else if detailState === 'loading'}
          <div class="cve-loading">Loading change detail...</div>
        {:else if detailState === 'error'}
          <div class="cve-error">{detailError}</div>
        {:else if selectedChange}
          {@const ch = selectedChange}

          <header class="cve-p30e1-inspector__head">
            <div class="cve-p30e1-inspector__title-row">
              <span class="cve-p30e1-queue-item__type">{typeLabel(ch.type)}</span>
              <span class={statusTag(ch.status)}>{ch.status}</span>
              <span class="cve-p30e1-validation cve-p30e1-validation--{ch.validation_status}">
                validation: {ch.validation_status}
              </span>
            </div>
            <h2 class="cve-p30e1-inspector__path" data-testid="pending-inspector-path">{ch.path}</h2>
            {#if ch.section}
              <p class="cve-p30e1-inspector__section">Section: {ch.section}</p>
            {/if}
            <p class="cve-p30e1-inspector__id">id: <code class="cve-p30e1-mono">{ch.id}</code></p>
          </header>

          <div class="cve-p30e1-inspector__body" data-testid="pending-inspector-scroll">

            <!-- Provenance / target / trust impact -->
            <section class="cve-p30e1-section" aria-labelledby="pending-provenance-head">
              <h3 id="pending-provenance-head" class="cve-p30e1-section__title">Provenance and target</h3>
              <dl class="cve-p30e1-kv" data-testid="pending-provenance">
                <div><dt>Source</dt><dd><code class="cve-p30e1-mono">{ch.source}</code></dd></div>
                <div><dt>Target note</dt><dd><code class="cve-p30e1-mono">{ch.path}</code></dd></div>
                {#if ch.section}
                  <div><dt>Target section</dt><dd>{ch.section}</dd></div>
                {/if}
                <div><dt>Created</dt><dd>{fmtDate(ch.created_at)}</dd></div>
                {#if ch.session_id}
                  <div><dt>Session</dt><dd><code class="cve-p30e1-mono">{ch.session_id}</code></dd></div>
                {/if}
                {#if ch.project}
                  <div><dt>Project</dt><dd>{ch.project}</dd></div>
                {/if}
                {#if ch.reviewer}
                  <div><dt>Reviewer</dt><dd>{ch.reviewer}</dd></div>
                {/if}
                {#if ch.applied_at}
                  <div><dt>Applied</dt><dd>{fmtDate(ch.applied_at)}</dd></div>
                {/if}
                {#if ch.rejected_at}
                  <div><dt>Rejected</dt><dd>{fmtDate(ch.rejected_at)}</dd></div>
                {/if}
              </dl>
              <!-- Trust impact: the backend pending API does not expose a
                   trust-impact field. The note below is the deterministic
                   fallback so reviewers always see the trust effect of
                   accepting. -->
              <p class="cve-p30e1-trust-impact" data-testid="pending-trust-impact">
                <strong>Trust impact.</strong> Accepting writes proposed content to
                the vault as a deterministic note edit. Trust metadata
                (trust_level, last_reviewed, review_after) is not modified by
                this action and must be reviewed separately on
                <a class="cve-link" href="/app/trust">Trust</a>.
              </p>
              {#if ch.original_content_hash}
                <p class="cve-p30e1-stale" data-testid="pending-hash-warning">
                  <strong>Original hash recorded.</strong> The backend re-checks
                  this hash on accept. If the target note has changed on disk
                  since the proposal was created, the accept will be rejected
                  as stale.
                </p>
              {/if}
            </section>

            <!-- Reason -->
            {#if ch.reason}
              <section class="cve-p30e1-section" aria-labelledby="pending-reason-head">
                <h3 id="pending-reason-head" class="cve-p30e1-section__title">Reason</h3>
                <p>{ch.reason}</p>
              </section>
            {/if}

            <!-- Audit note -->
            {#if ch.audit_note}
              <section class="cve-p30e1-section" aria-labelledby="pending-audit-head">
                <h3 id="pending-audit-head" class="cve-p30e1-section__title">Audit note</h3>
                <p>{ch.audit_note}</p>
              </section>
            {/if}

            <!-- Validation errors -->
            {#if ch.validation_errors.length > 0}
              <section class="cve-p30e1-section" aria-labelledby="pending-validation-head">
                <h3 id="pending-validation-head" class="cve-p30e1-section__title">Validation errors</h3>
                <ul class="cve-p30e1-validation-list">
                  {#each ch.validation_errors as err}
                    <li><code class="cve-p30e1-mono">{err}</code></li>
                  {/each}
                </ul>
              </section>
            {/if}

            <!-- Diff -->
            <section class="cve-p30e1-section" aria-labelledby="pending-diff-head">
              <h3 id="pending-diff-head" class="cve-p30e1-section__title">Proposed diff</h3>
              {#if ch.diff.length === 0}
                <p class="cve-helper">No diff. This is a new note proposal.</p>
              {:else}
                <pre class="cve-diff cve-p30e1-diff" data-testid="pending-diff"><code>{#each ch.diff as line}<span class={diffLineClass(line)}>{line}
</span>{/each}</code></pre>
              {/if}
            </section>

            <!-- Action result -->
            {#if actionState === 'ok'}
              <div class="cve-banner cve-banner--success" role="status">
                <div>
                  <div class="cve-banner__title">Action applied</div>
                  <div class="cve-banner__body">Change status is now <strong>{ch.status}</strong>.</div>
                </div>
              </div>
            {/if}

            <!-- Accept / reject confirmation panel -->
            {#if ch.status === 'pending'}
              <section class="cve-p30e1-section cve-p30e1-section--actions" aria-labelledby="pending-actions-head">
                <h3 id="pending-actions-head" class="cve-p30e1-section__title">Review decision</h3>

                <div class="cve-p30e1-action-row">
                  <div class="cve-field">
                    <label class="cve-label" for="pending-reviewer">Reviewer (optional)</label>
                    <input
                      id="pending-reviewer"
                      class="cve-input"
                      type="text"
                      bind:value={reviewerInput}
                      placeholder="Your name or handle"
                    />
                  </div>
                  <div class="cve-field">
                    <label class="cve-label" for="pending-audit-note">Audit note (optional)</label>
                    <input
                      id="pending-audit-note"
                      class="cve-input"
                      type="text"
                      bind:value={auditNoteInput}
                      placeholder="Reason for decision"
                    />
                  </div>
                </div>

                {#if ch.validation_status === 'fail'}
                  <div class="cve-banner cve-banner--danger" role="alert">
                    <div>
                      <div class="cve-banner__title">Cannot accept</div>
                      <div class="cve-banner__body">
                        This change has validation errors. Accepting is disabled
                        until the proposal is re-validated upstream.
                      </div>
                    </div>
                  </div>
                {/if}

                <div class="cve-p30e1-decision">

                  <!-- Accept -->
                  <div class="cve-p30e1-decision__pane cve-p30e1-decision__pane--accept">
                    <h4 class="cve-p30e1-decision__title">Accept and apply</h4>
                    <p class="cve-helper">
                      Writes the proposed content to <code class="cve-p30e1-mono">{ch.path}</code>.
                      This action is recorded in the vault audit log.
                    </p>
                    <div class="cve-field">
                      <label class="cve-label" for="pending-accept-confirm">
                        Type <code class="cve-p30e1-mono">{PENDING_ACCEPT_PHRASE}</code> to confirm
                      </label>
                      <input
                        id="pending-accept-confirm"
                        class="cve-input"
                        type="text"
                        autocomplete="off"
                        bind:value={acceptConfirmInput}
                        on:focus={() => { activeAction = 'accept'; }}
                        disabled={ch.validation_status === 'fail'}
                        aria-describedby="pending-accept-help"
                      />
                      <p id="pending-accept-help" class="cve-helper">
                        Accept is disabled until the confirmation phrase matches exactly.
                      </p>
                    </div>
                    <button
                      type="button"
                      class="cve-btn cve-btn-primary"
                      data-testid="pending-accept-submit"
                      on:click={submitAccept}
                      disabled={!acceptReady}
                    >
                      {actionState === 'loading' && activeAction === 'accept' ? 'Applying...' : 'Accept and apply'}
                    </button>
                  </div>

                  <!-- Reject -->
                  <div class="cve-p30e1-decision__pane cve-p30e1-decision__pane--reject">
                    <h4 class="cve-p30e1-decision__title">Reject and archive</h4>
                    <p class="cve-helper">
                      Marks this proposal as rejected. The vault is not modified.
                    </p>
                    <div class="cve-field">
                      <label class="cve-label" for="pending-reject-confirm">
                        Type <code class="cve-p30e1-mono">{PENDING_REJECT_PHRASE}</code> to confirm
                      </label>
                      <input
                        id="pending-reject-confirm"
                        class="cve-input"
                        type="text"
                        autocomplete="off"
                        bind:value={rejectConfirmInput}
                        on:focus={() => { activeAction = 'reject'; }}
                        aria-describedby="pending-reject-help"
                      />
                      <p id="pending-reject-help" class="cve-helper">
                        Reject is disabled until the confirmation phrase matches exactly.
                      </p>
                    </div>
                    <button
                      type="button"
                      class="cve-btn cve-btn-danger"
                      data-testid="pending-reject-submit"
                      on:click={submitReject}
                      disabled={!rejectReady}
                    >
                      {actionState === 'loading' && activeAction === 'reject' ? 'Rejecting...' : 'Reject and archive'}
                    </button>
                  </div>

                </div>
              </section>
            {/if}

            <!-- Raw JSON: deferred to Developer route -->
            <details class="cve-details cve-details--inspector">
              <summary>Raw pending response</summary>
              <div class="cve-details__body">
                <p class="cve-helper">
                  The raw pending JSON is intentionally not shown inline here.
                  Open the full payload in the Developer route:
                </p>
                <a class="cve-details__developer-link" href={rawDeepLink}
                  >Open this vault in /app/raw</a>
              </div>
            </details>

          </div>
        {/if}

      </section>
    </div>

  {/if}

</div>
