<script lang="ts">
  /*
    Phase 30D1 - Validation Review.
    Real implementation backed by the existing /validation API helper
    (fetchValidation). Uses Phase 30B primitives only: cve-toolbar,
    cve-banner, cve-status-strip, cve-status-tile, cve-table, and the
    cve-details--inspector + cve-details__developer-link deep-link
    contract to the Developer route at /app/raw. No new dependency, no
    icon library, no raw Tailwind dark palette literals.

    The /validation API surface is intentionally compact: it returns
    invalid_count and the sorted list of invalid_notes. This page does
    not invent extra metadata; it surfaces only what the API exposes
    and links out to /app/notes for per-note inspection.
  */

  import { onMount } from 'svelte';
  import {
    fetchVaults,
    fetchValidation,
    isOk,
    errorMessage,
    type ValidationData,
  } from '../lib/api.ts';
  import {
    getStoredVault,
    setStoredVault,
    getVaultFromUrl,
    chooseInitialVault,
  } from '../lib/vaultState.ts';

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

  const CHECKED_LABEL = 'Checked this session';
  const NOT_CHECKED_LABEL = 'Not yet checked';

  let vaultsState: LoadState = 'loading';
  let vaultList: string[] = [];
  let vaultsError = '';
  let selectedVault = '';

  let validationState: LoadState = 'idle';
  let validationData: ValidationData | null = null;
  let validationError = '';

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

  async function loadValidation(vault: string) {
    if (!vault) return;
    validationState = 'loading';
    validationData = null;
    validationError = '';
    const result = await fetchValidation(vault);
    if (isOk(result)) {
      validationData = result.data;
      validationState = 'ok';
    } else {
      validationError = errorMessage(result);
      validationState = 'error';
    }
  }

  async function handleVaultChange(event: Event) {
    const select = event.target as HTMLSelectElement;
    selectedVault = select.value;
    setStoredVault(selectedVault);
    await loadValidation(selectedVault);
  }

  async function refresh() {
    if (validationState === 'loading') return;
    if (selectedVault) await loadValidation(selectedVault);
  }

  // Derived banner state.
  type BannerSeverity = 'success' | 'warning' | 'danger' | 'info';
  $: banner = ((): { severity: BannerSeverity; title: string; body: string } => {
    if (!selectedVault) {
      return {
        severity: 'info',
        title: 'No vault selected',
        body: 'Pick a vault to run schema validation.',
      };
    }
    if (validationState === 'loading') {
      return {
        severity: 'info',
        title: 'Validating vault',
        body: 'Running deterministic schema checks for ' + selectedVault + '.',
      };
    }
    if (validationState === 'error') {
      return {
        severity: 'danger',
        title: 'Validation request failed',
        body: validationError || 'Unable to reach the backend validation route.',
      };
    }
    if (validationState === 'ok' && validationData) {
      if (validationData.invalid_count === 0) {
        return {
          severity: 'success',
          title: 'Validation pass',
          body: 'All notes in ' + selectedVault + ' match the active schema.',
        };
      }
      return {
        severity: 'danger',
        title: 'Validation fail',
        body:
          validationData.invalid_count +
          ' note(s) in ' +
          selectedVault +
          ' failed schema checks.',
      };
    }
    return {
      severity: 'info',
      title: 'Validation idle',
      body: 'No validation run yet.',
    };
  })();

  $: invalidNotes = (() => {
    if (validationState !== 'ok' || !validationData) return [];
    return [...validationData.invalid_notes].sort((a, b) =>
      a.toLowerCase().localeCompare(b.toLowerCase()),
    );
  })();

  $: invalidCount = validationData?.invalid_count ?? 0;
  $: validStatus = validationData?.status ?? '-';

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
    const base = '/app/raw?endpoint=validation';
    if (selectedVault) {
      return base + '&vault=' + encodeURIComponent(selectedVault) + '&source=validation';
    }
    return base + '&source=validation';
  })();

  onMount(async () => {
    await loadVaults();
    if (selectedVault) await loadValidation(selectedVault);
  });
</script>

<div class="cve-page cve-stack">

  <header class="cve-toolbar" aria-label="Validation header">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Validation</h1>
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
          <label class="cve-label" for="validation-vault-select">Vault</label>
          <select
            id="validation-vault-select"
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
          disabled={validationState === 'loading' || !selectedVault}
          aria-label="Re-run validation"
        >
          {validationState === 'loading' ? 'Validating' : 'Re-run'}
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

  <section aria-label="Validation summary">
    <div class="cve-status-strip">
      <div class="cve-status-tile cve-status-tile--{validationState === 'ok' && validationData ? (validationData.invalid_count === 0 ? 'success' : 'danger') : 'neutral'}">
        <span class="cve-status-tile__label">Status</span>
        <span class="cve-status-tile__value">
          {validationState === 'loading'
            ? 'Checking'
            : validationState === 'error'
              ? 'Error'
              : (validStatus === 'pass' ? 'Pass' : validStatus === 'fail' ? 'Fail' : '-')}
        </span>
        <span class="cve-status-tile__hint">
          {validationState === 'error' ? validationError : 'Schema status reported by /validation.'}
        </span>
        <span class="cve-status-tile__meta">{lastChecked(validationState)}</span>
      </div>

      <div class="cve-status-tile cve-status-tile--{invalidCount === 0 && validationState === 'ok' ? 'success' : invalidCount > 0 ? 'danger' : 'neutral'}">
        <span class="cve-status-tile__label">Invalid notes</span>
        <span class="cve-status-tile__value">
          {validationState === 'ok' && validationData ? invalidCount : '-'}
        </span>
        <span class="cve-status-tile__hint">
          {validationState === 'ok' && validationData
            ? (invalidCount === 0
                ? 'No notes failed schema checks.'
                : invalidCount + ' note(s) failed.')
            : 'Awaiting validation run.'}
        </span>
        <span class="cve-status-tile__meta">{lastChecked(validationState)}</span>
      </div>

      <div class="cve-status-tile cve-status-tile--info">
        <span class="cve-status-tile__label">Vault</span>
        <span class="cve-status-tile__value">{selectedVault || '-'}</span>
        <span class="cve-status-tile__hint">Active vault for validation.</span>
        <span class="cve-status-tile__meta">{lastChecked(validationState)}</span>
      </div>
    </div>
  </section>

  <section aria-labelledby="invalid-notes-title">
    <div class="cve-section">
      <h2 id="invalid-notes-title" class="cve-section-title">Invalid notes</h2>

      {#if validationState === 'loading'}
        <p class="cve-loading">Running validation...</p>
      {:else if validationState === 'error'}
        <p class="cve-error">{validationError}</p>
      {:else if !validationData}
        <p class="cve-empty">No validation result yet. Select a vault to run a check.</p>
      {:else if invalidNotes.length === 0}
        <p class="cve-success">
          All notes pass schema checks. Run
          <code>py run.py validate</code>
          on the CLI for the same result.
        </p>
      {:else}
        <div class="cve-table-wrap cve-p30d1-table">
          <table class="cve-table" aria-label="Invalid notes">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Note path</th>
                <th scope="col">Reason</th>
                <th scope="col">Open</th>
              </tr>
            </thead>
            <tbody>
              {#each invalidNotes as path, index}
                <tr>
                  <td class="cve-mono">{index + 1}</td>
                  <td class="cve-mono">{path}</td>
                  <td>
                    <span class="cve-badge cve-badge-danger">Schema fail</span>
                    <span class="cve-meta" style="margin-left: 0.5rem;">
                      Reported by /validation. Per-field detail not exposed by the API.
                    </span>
                  </td>
                  <td>
                    <a class="cve-link" href={noteHref(path)} aria-label="Open {path} in Notes">
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
        Raw /validation JSON is intentionally not rendered inline on this
        page. The Developer route hosts the full payload, request history,
        and copy-ready output.
      </p>
      <p style="margin-top: 0.5rem;">
        <a
          class="cve-details__developer-link"
          href={rawHref}
          aria-label="Open Developer route for raw validation payload"
        >
          Open in Developer
        </a>
      </p>
    </div>
  </details>

</div>
