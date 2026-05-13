// ---------------------------------------------------------------------------
// Phase 30E2 - shared helpers for Controller and Vault Setup polish
// ---------------------------------------------------------------------------
// Tiny deterministic helpers used by the Controller command-centre and the
// Vault Setup grouped form / vault management surface. No new runtime deps;
// no backend contract changes; pure functions only.

import type { ContextReadiness, ContextRecommendation } from './api.ts';
export { buildRawDeepLink } from './phase30e1.ts';

/**
 * Readiness polarity contract.
 *
 * The Controller surfaces a mix of positive and negative readiness flags.
 * A naive renderer that paints every true flag green would mark
 * `has_tasks: true` (= work outstanding) as "healthy", which is wrong.
 * Positive flags are healthy when true; negative flags are healthy when
 * false. `readinessPolarity` returns 'good' or 'bad' so the UI never
 * has to guess the sign.
 */
const POSITIVE_FLAGS: ReadonlyArray<keyof ContextReadiness> = [
  'valid',
  'security_passed',
  'ready_to_export',
  'ready_for_agent_context',
];

const NEGATIVE_FLAGS: ReadonlyArray<keyof ContextReadiness> = [
  'has_tasks',
  'has_missing_concepts',
  'has_feedback_warnings',
];

export function isPositiveReadinessFlag(key: string): boolean {
  return (POSITIVE_FLAGS as readonly string[]).includes(key);
}

export function isNegativeReadinessFlag(key: string): boolean {
  return (NEGATIVE_FLAGS as readonly string[]).includes(key);
}

export type Polarity = 'good' | 'bad';

export function readinessPolarity(key: string, value: boolean): Polarity {
  if (isNegativeReadinessFlag(key)) {
    return value ? 'bad' : 'good';
  }
  // Positive or unknown flag - true is good.
  return value ? 'good' : 'bad';
}

/**
 * Human-readable label for a readiness key. The backend supplies snake_case
 * so we render it lowercase, hyphen-friendly, with a clear positive-tense
 * label so the polarity is visible without colour cues.
 */
const READINESS_LABEL: Record<string, string> = {
  valid: 'Validation',
  security_passed: 'Security',
  has_tasks: 'Outstanding tasks',
  has_missing_concepts: 'Missing concepts',
  has_feedback_warnings: 'Feedback warnings',
  ready_to_export: 'Ready to export',
  ready_for_agent_context: 'Ready for agent context',
};

export function readinessLabel(key: string): string {
  return READINESS_LABEL[key] ?? key.replace(/_/g, ' ');
}

/**
 * Status text paired with the polarity dot. Status text is required so the
 * colour dot is never the only signal (a11y rule: colour must not be the
 * sole information channel).
 */
export function readinessStatusText(key: string, value: boolean): string {
  const polarity = readinessPolarity(key, value);
  if (isNegativeReadinessFlag(key)) {
    return polarity === 'good' ? 'None' : 'Present';
  }
  return polarity === 'good' ? 'Pass' : 'Fail';
}

/**
 * Recommendation -> authoritative /app/* route fallback.
 *
 * The backend usually populates `rec.links.ui` already; this helper exists
 * so the Controller can still produce a deterministic deep-link if the
 * backend response is sparse, and so tests can verify the routing
 * contract directly.
 */
const ACTION_ROUTE: Record<string, string> = {
  fix_validation_errors: '/app/validation',
  resolve_security_findings: '/app/security',
  resolve_security_warnings: '/app/security',
  complete_tasks: '/app/tasks',
  fill_missing_concepts: '/app/graph',
  review_notes: '/app/notes',
  review_feedback: '/app/feedback',
  review_pending: '/app/pending',
  review_trust: '/app/trust',
  prepare_export: '/app/exports',
};

const SOURCE_ROUTE: Record<string, string> = {
  validation: '/app/validation',
  security: '/app/security',
  tasks: '/app/tasks',
  missing: '/app/graph',
  graph: '/app/graph',
  notes: '/app/notes',
  feedback: '/app/feedback',
  pending: '/app/pending',
  trust: '/app/trust',
};

export function recommendationRoute(rec: ContextRecommendation): string {
  const fromAction = ACTION_ROUTE[rec.action];
  if (fromAction) return fromAction;
  const fromSource = SOURCE_ROUTE[rec.source];
  if (fromSource) return fromSource;
  return '/app/raw';
}

/**
 * Deterministic recommendation sort: rank ascending if present, then
 * severity weight, then stable title/action.
 */
const SEVERITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

export function severityRank(sev: string): number {
  const w = SEVERITY_RANK[sev];
  return typeof w === 'number' ? w : 99;
}

export function sortRecommendations(
  recs: ReadonlyArray<ContextRecommendation>,
): ContextRecommendation[] {
  return [...recs].sort((a, b) => {
    if (a.rank !== b.rank) return a.rank - b.rank;
    const sa = severityRank(a.severity);
    const sb = severityRank(b.severity);
    if (sa !== sb) return sa - sb;
    if (a.title !== b.title) return a.title < b.title ? -1 : 1;
    return a.action < b.action ? -1 : 1;
  });
}

/**
 * Vault delete typed-confirmation contract. The backend requires the
 * exact phrase "DELETE <vault>" (see mcp/core/vault_delete.py); we
 * compute the expected phrase here so the UI and the tests agree.
 */
export function deleteConfirmPhrase(vault: string): string {
  return vault ? `DELETE ${vault}` : '';
}

export function isDeleteConfirmed(vault: string, input: string): boolean {
  const expected = deleteConfirmPhrase(vault);
  return expected !== '' && input.trim() === expected;
}

export const VAULT_DELETE_PROTECTED = 'demo-vault';

/**
 * Backend deletion semantics, rendered verbatim into the destructive
 * confirmation panel. The current backend (mcp/core/vault_delete.py)
 * deletes the vault directory from disk with shutil.rmtree and rewrites
 * config.yaml atomically; the action is not reversible by the app.
 */
export const VAULT_DELETE_SEMANTICS = {
  files_deleted: true,
  reversible: false,
} as const;
