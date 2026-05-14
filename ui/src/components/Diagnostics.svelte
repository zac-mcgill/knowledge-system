<script lang="ts">
  /*
    Diagnostics.svelte - Phase 37

    Local diagnostics and support report UI.  Loads the safe, redacted
    report from GET /diagnostics and renders it in clearly labelled
    sections.  The page never displays note bodies, prompt contents,
    pending-change proposed content, or the value of CVE_AUTH_TOKEN.

    All styling uses existing cve-* primitives so the page inherits
    light/dark theme support and the Phase 30B overflow guards.  No
    new dependency, no icon library, no animation library.
  */

  import { onMount } from 'svelte';
  import {
    fetchDiagnostics,
    isOk,
    type DiagnosticsReport,
  } from '../lib/api.ts';

  type LoadState = 'idle' | 'loading' | 'ok' | 'error';

  let state: LoadState = 'idle';
  let report: DiagnosticsReport | null = null;
  let errorMessage = '';
  let copyState: 'idle' | 'copied' | 'failed' = 'idle';

  async function load(): Promise<void> {
    state = 'loading';
    errorMessage = '';
    const result = await fetchDiagnostics();
    if (isOk(result)) {
      report = result.data;
      state = 'ok';
    } else {
      report = null;
      errorMessage = result.error?.message ?? 'Failed to load diagnostics';
      state = 'error';
    }
  }

  async function copyJson(): Promise<void> {
    if (!report) return;
    const text = JSON.stringify(report, null, 2);
    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        copyState = 'copied';
        setTimeout(() => (copyState = 'idle'), 1500);
        return;
      }
    } catch {
      // fall through to manual fallback
    }
    copyState = 'failed';
    setTimeout(() => (copyState = 'idle'), 1500);
  }

  function yesNo(value: boolean | null | undefined): string {
    if (value === null || value === undefined) return 'unknown';
    return value ? 'yes' : 'no';
  }

  $: rawJson = report ? JSON.stringify(report, null, 2) : '';

  $: commandRows = report
    ? Object.entries(report.commands).map(([name, info]) => ({
        name,
        available: info.available,
      }))
    : [];

  $: envRows = report
    ? Object.entries(report.environment).map(([name, info]) => ({
        name,
        set: info.set,
        value: typeof info.value === 'string' ? info.value : null,
      }))
    : [];

  onMount(() => {
    load();
  });
</script>

<div class="cve-page">
  <header class="cve-toolbar">
    <div class="cve-toolbar__main">
      <h1 class="cve-toolbar__title">Diagnostics</h1>
      <div class="cve-toolbar__meta">
        <span data-testid="diagnostics-state-pill">
          {#if state === 'loading'}Loading{:else if state === 'ok'}Loaded{:else if state === 'error'}Error{:else}Idle{/if}
        </span>
        <span>Local-only</span>
        <span>Redacted</span>
      </div>
      <div class="cve-toolbar__actions">
        <button type="button" class="cve-btn cve-btn-secondary" on:click={load} disabled={state === 'loading'}>
          Refresh
        </button>
      </div>
    </div>
  </header>

  <div class="cve-banner cve-banner--info">
    <div class="cve-banner__body">
      This report is generated locally on this machine and is intended for
      debugging and support. It is redacted before display: note bodies,
      auth tokens, API keys, passwords, and other secret environment values
      are never shown. No report is uploaded anywhere.
    </div>
  </div>

  {#if state === 'loading'}
    <div class="cve-banner cve-banner--info">
      <div class="cve-banner__body">Loading diagnostics report...</div>
    </div>
  {:else if state === 'error'}
    <div class="cve-banner cve-banner--danger">
      <div>
        <div class="cve-banner__title">Could not load diagnostics</div>
        <div class="cve-banner__body">{errorMessage}</div>
      </div>
    </div>
  {:else if report}
    <section class="cve-section" aria-label="Runtime">
      <h2 class="cve-section-title">Runtime</h2>
      <div class="cve-table-wrap">
        <table class="cve-table">
          <tbody>
            <tr><th scope="row">App</th><td>{report.app.name} (version {report.app.version})</td></tr>
            <tr><th scope="row">Python version</th><td>{report.runtime.python_version}</td></tr>
            <tr><th scope="row">Platform</th><td>{report.runtime.platform}</td></tr>
            <tr><th scope="row">OS</th><td>{report.runtime.os}</td></tr>
            <tr>
              <th scope="row">Repository root (local path)</th>
              <td>
                <code class="cve-mono">{report.app.repository_root.local_path}</code>
                <span class="cve-meta"> (present: {yesNo(report.app.repository_root.present)})</span>
              </td>
            </tr>
            <tr>
              <th scope="row">Working directory (local path)</th>
              <td><code class="cve-mono">{report.runtime.cwd.local_path}</code></td>
            </tr>
            <tr>
              <th scope="row">Python executable (local path)</th>
              <td><code class="cve-mono">{report.runtime.executable.local_path}</code></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="cve-section" aria-label="UI build">
      <h2 class="cve-section-title">UI build</h2>
      <div class="cve-table-wrap">
        <table class="cve-table">
          <tbody>
            <tr><th scope="row">ui/ directory present</th><td>{yesNo(report.ui.ui_dir_present)}</td></tr>
            <tr><th scope="row">package.json present</th><td>{yesNo(report.ui.package_json_present)}</td></tr>
            <tr><th scope="row">dist/ present</th><td>{yesNo(report.ui.dist_present)}</td></tr>
            <tr><th scope="row">dist/index.html present</th><td>{yesNo(report.ui.index_present)}</td></tr>
            <tr><th scope="row">Build hint</th><td>{report.ui.build_hint}</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="cve-section" aria-label="Vault and configuration">
      <h2 class="cve-section-title">Vault and configuration</h2>
      <div class="cve-table-wrap">
        <table class="cve-table">
          <thead>
            <tr><th>Vault</th><th>Path</th><th>Schema</th><th>State dir</th><th>Notes</th></tr>
          </thead>
          <tbody>
            {#if report.config.vaults.length === 0}
              <tr><td colspan="5">No vaults registered.</td></tr>
            {:else}
              {#each report.config.vaults as v (v.name)}
                <tr>
                  <td><code class="cve-mono">{v.name}</code></td>
                  <td>{yesNo(v.path_present)}</td>
                  <td>{yesNo(v.schema_present)}</td>
                  <td>{yesNo(v.state_dir_present)}</td>
                  <td>{v.note_count === null ? 'unknown' : v.note_count}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
      <p class="cve-meta">config.yaml present: {yesNo(report.config.config_present)}</p>
    </section>

    <section class="cve-section" aria-label="Commands">
      <h2 class="cve-section-title">Commands</h2>
      <div class="cve-table-wrap">
        <table class="cve-table">
          <thead><tr><th>Command</th><th>Available</th></tr></thead>
          <tbody>
            {#each commandRows as row (row.name)}
              <tr><td><code class="cve-mono">{row.name}</code></td><td>{yesNo(row.available)}</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="cve-section" aria-label="Private cloud">
      <h2 class="cve-section-title">Private cloud</h2>
      <div class="cve-table-wrap">
        <table class="cve-table">
          <tbody>
            <tr><th scope="row">Enabled</th><td>{yesNo(report.private_cloud.enabled)}</td></tr>
            <tr><th scope="row">Deployment mode</th><td><code class="cve-mono">{report.private_cloud.deployment_mode}</code></td></tr>
            <tr><th scope="row">Authentication required</th><td>{yesNo(report.private_cloud.require_auth)}</td></tr>
            <tr><th scope="row">Token configured</th><td>{yesNo(report.private_cloud.token_configured)}</td></tr>
            <tr><th scope="row">Remote read-only</th><td>{yesNo(report.private_cloud.remote_read_only)}</td></tr>
            <tr>
              <th scope="row">Public base URL configured</th>
              <td>{report.private_cloud.public_base_url ? 'yes' : 'no'}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="cve-meta">
        The auth token value is never displayed. Only the "Token configured" boolean is shown.
      </p>
    </section>

    <section class="cve-section" aria-label="CVE environment variables">
      <h2 class="cve-section-title">Environment (CVE_*)</h2>
      <div class="cve-table-wrap">
        <table class="cve-table">
          <thead><tr><th>Variable</th><th>Set</th><th>Display value</th></tr></thead>
          <tbody>
            {#each envRows as row (row.name)}
              <tr>
                <td><code class="cve-mono">{row.name}</code></td>
                <td>{yesNo(row.set)}</td>
                <td>
                  {#if row.name === 'CVE_AUTH_TOKEN'}
                    <span class="cve-meta">(never displayed)</span>
                  {:else if row.value}
                    <code class="cve-mono">{row.value}</code>
                  {:else}
                    <span class="cve-meta">(none)</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="cve-section" aria-label="Redaction and safety">
      <h2 class="cve-section-title">Redaction and safety</h2>
      <ul class="cve-list">
        <li>Note bodies included: <strong>{yesNo(report.redaction.note_bodies_included)}</strong></li>
        <li>Secret values included: <strong>{yesNo(report.redaction.secret_values_included)}</strong></li>
        <li>Content included: <strong>{yesNo(report.redaction.content_included)}</strong></li>
        <li>Redaction marker: <code class="cve-mono">{report.redaction.redaction_marker}</code></li>
      </ul>
      <details class="cve-details">
        <summary>Redaction rules</summary>
        <div class="cve-details__body">
          <ul class="cve-list">
            {#each report.redaction.rules as rule (rule)}
              <li>{rule}</li>
            {/each}
          </ul>
        </div>
      </details>
    </section>

    <section class="cve-section" aria-label="Warnings">
      <h2 class="cve-section-title">Warnings</h2>
      {#if report.warnings.length === 0}
        <p class="cve-meta">No warnings.</p>
      {:else}
        <ul class="cve-list">
          {#each report.warnings as w (w)}
            <li>{w}</li>
          {/each}
        </ul>
      {/if}
    </section>

    <details class="cve-details cve-details--inspector" data-testid="diagnostics-raw">
      <summary>Raw JSON</summary>
      <div class="cve-details__body">
        <div class="cve-toolbar__actions" style="margin-bottom: 0.5rem;">
          <button type="button" class="cve-btn cve-btn-secondary" on:click={copyJson}>
            {#if copyState === 'copied'}Copied{:else if copyState === 'failed'}Copy failed{:else}Copy JSON{/if}
          </button>
        </div>
        <pre class="cve-raw"><code>{rawJson}</code></pre>
      </div>
    </details>
  {/if}
</div>
