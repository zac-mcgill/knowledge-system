/**
 * api.ts — Typed API client for Context Vault Engine.
 *
 * All requests go to the FastAPI backend (default: http://127.0.0.1:8000).
 * Set PUBLIC_API_BASE_URL in the environment to override.
 *
 * Response envelope:
 *   Success: { status: "ok", data: ... }
 *   Error:   { status: "error", error: { code: string, message: string } }
 */

// ---------------------------------------------------------------------------
// Base URL
// ---------------------------------------------------------------------------

export const API_BASE: string =
  (typeof import.meta !== 'undefined' && import.meta.env?.PUBLIC_API_BASE_URL) ||
  'http://127.0.0.1:8000';

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface ApiError {
  code: string;
  message: string;
}

export interface ApiOk<T> {
  status: 'ok';
  data: T;
}

export interface ApiErrorEnvelope {
  status: 'error';
  error: ApiError;
}

export type ApiResult<T> = ApiOk<T> | ApiErrorEnvelope;

// -- /health --

export interface VaultHealth {
  notes: number;
  schema_hash: string;
  last_index_time: number;
  index_size_bytes?: number;
}

export interface HealthData {
  vaults: Record<string, VaultHealth>;
  uptime_seconds: number;
  requests_served: number;
  rate_limit_status: {
    max_per_second: number;
    current_window: number;
    total_rejected: number;
  };
  metrics: {
    per_endpoint: Record<string, number>;
    avg_response_time_ms: number;
  };
}

// -- /vaults --

export interface VaultsData {
  vaults: string[];
}

// -- /summary --

export interface SummaryData {
  total_notes: number;
  complete: number;
  partial: number;
  coverage: number;
}

// -- /validation --

export interface ValidationData {
  status: 'pass' | 'fail';
  invalid_count: number;
  invalid_notes: string[];
}

// -- /context/security --

export interface SecurityFinding {
  path: string;
  severity: string;
  rule: string;
  field: string;
  detail: string;
}

export interface SecuritySummary {
  fail: number;
  warning: number;
  info: number;
}

export interface SecurityData {
  status: 'pass' | 'warning' | 'fail';
  findings: SecurityFinding[];
  summary: SecuritySummary;
  scanned: {
    note_count: number;
    source_paths: string[];
  };
}

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

/** Perform a GET request and return the typed result. */
async function get<T>(path: string): Promise<ApiResult<T>> {
  try {
    const resp = await fetch(`${API_BASE}${path}`);
    const json = await resp.json();
    return json as ApiResult<T>;
  } catch (err) {
    return {
      status: 'error',
      error: {
        code: 'NETWORK_ERROR',
        message: err instanceof Error ? err.message : 'Network request failed',
      },
    };
  }
}

/** Perform a POST request with a JSON body and return the typed result. */
async function post<T>(path: string, body: unknown): Promise<ApiResult<T>> {
  try {
    const resp = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const json = await resp.json();
    return json as ApiResult<T>;
  } catch (err) {
    return {
      status: 'error',
      error: {
        code: 'NETWORK_ERROR',
        message: err instanceof Error ? err.message : 'Network request failed',
      },
    };
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** GET /health — server health and vault metrics. */
export function fetchHealth(): Promise<ApiResult<HealthData>> {
  return get<HealthData>('/health');
}

/** GET /vaults — list registered vault names. */
export function fetchVaults(): Promise<ApiResult<VaultsData>> {
  return get<VaultsData>('/vaults');
}

/** GET /summary?vault=<vault> — vault completion summary. */
export function fetchSummary(vault: string): Promise<ApiResult<SummaryData>> {
  return get<SummaryData>(`/summary?vault=${encodeURIComponent(vault)}`);
}

/** GET /validation?vault=<vault> — validation pass/fail status. */
export function fetchValidation(vault: string): Promise<ApiResult<ValidationData>> {
  return get<ValidationData>(`/validation?vault=${encodeURIComponent(vault)}`);
}

/**
 * POST /context/security — scan vault notes for credential leaks and
 * injection patterns. Uses status=complete filter with max 10 notes.
 */
export function fetchSecurity(vault: string): Promise<ApiResult<SecurityData>> {
  return post<SecurityData>('/context/security', {
    vault,
    filters: { status: 'complete' },
    max_notes: 10,
    include_body: true,
    allow_partial: false,
  });
}

// ---------------------------------------------------------------------------
// Tasks — GET /tasks
// ---------------------------------------------------------------------------

export interface FeedbackWeight {
  score_delta: number;
  entry_summary: string;
}

export interface Task {
  note: string;
  path: string;
  priority: number;
  type: string;
  target: string;
  missing: string[];
  instruction: string;
  constraints: string[];
  feedback_weight?: FeedbackWeight;
}

export interface TasksData {
  total: number;
  tasks: Task[];
  feedback_status?: 'ok' | 'error';
  feedback_errors?: unknown[];
}

/** GET /tasks — prioritised improvement tasks. */
export function fetchTasks(
  vault?: string,
  options?: { limit?: number; include_feedback?: boolean; min_priority?: number },
): Promise<ApiResult<TasksData>> {
  const params = new URLSearchParams();
  if (vault) params.set('vault', vault);
  if (options?.limit !== undefined) params.set('limit', String(options.limit));
  if (options?.include_feedback !== undefined)
    params.set('include_feedback', String(options.include_feedback));
  if (options?.min_priority !== undefined)
    params.set('min_priority', String(options.min_priority));
  const qs = params.toString();
  return get<TasksData>(`/tasks${qs ? `?${qs}` : ''}`);
}

// ---------------------------------------------------------------------------
// Missing Concepts — GET /missing
// ---------------------------------------------------------------------------

export interface MissingConcept {
  concept: string;
  subdomain: string;
  score: number;
}

export interface MissingData {
  total_expected: number;
  total_actual: number;
  total_missing: number;
  domains_assessed: number;
  gaps: Record<string, MissingConcept[]>;
  ranked: MissingConcept[];
}

/**
 * GET /missing — detect missing concepts.
 * Returns MISSING_CONCEPTS_EMPTY (HTTP 422) when no expected concepts
 * are defined in vault_schema.py.
 */
export function fetchMissing(vault?: string): Promise<ApiResult<MissingData>> {
  const qs = vault ? `?vault=${encodeURIComponent(vault)}` : '';
  return get<MissingData>(`/missing${qs}`);
}

// ---------------------------------------------------------------------------
// Feedback — GET /feedback
// ---------------------------------------------------------------------------

export interface FeedbackEntry {
  path: string;
  source: string;
  signal: string;
  severity: string;
  comment: string;
  created_at: string;
}

export interface FeedbackData {
  status: 'ok' | 'error';
  vault: string;
  entries: FeedbackEntry[];
  warnings: string[];
  errors: unknown[];
}

/** GET /feedback — vault feedback entries from Vault Files/feedback.md. */
export function fetchFeedback(vault?: string): Promise<ApiResult<FeedbackData>> {
  const qs = vault ? `?vault=${encodeURIComponent(vault)}` : '';
  return get<FeedbackData>(`/feedback${qs}`);
}

// ---------------------------------------------------------------------------
// Context Bundle — POST /context/bundle
// ---------------------------------------------------------------------------

export interface ContextBundleRequest {
  vault: string;
  filters?: Record<string, string | string[]>;
  include_sections?: string[];
  include_related?: boolean;
  include_body?: boolean;
  max_notes?: number;
  max_chars?: number;
  allow_partial?: boolean;
}

export interface BundleNoteFields {
  title?: string;
  status?: string;
  domain?: string;
  difficulty?: string;
  [key: string]: string | undefined;
}

export interface BundleNote {
  path: string;
  fields: BundleNoteFields;
  sections: Record<string, string>;
  body?: string;
  related?: string[];
}

export interface BundleBudget {
  max_chars: number;
  used_chars: number;
  note_count: number;
  truncated: boolean;
}

export interface BundleManifest {
  source_paths: string[];
  schema_version: string | null;
}

export interface BundleFeedbackEntry {
  path: string;
  source: string;
  signal: string;
  severity: string;
  comment: string;
  created_at: string;
}

export interface BundleFeedback {
  entries: BundleFeedbackEntry[];
  warnings: string[];
}

export interface BundleGraph {
  related: Record<string, string[]>;
}

export interface ContextBundleResponse {
  status: string;
  bundle_id: string;
  vault: string;
  filters: Record<string, string | string[]>;
  created_at: string;
  validation_status: 'pass' | 'fail';
  schema_version: string | null;
  notes: BundleNote[];
  graph: BundleGraph;
  budget: BundleBudget;
  warnings: string[];
  manifest: BundleManifest;
  feedback: BundleFeedback;
}

/**
 * POST /context/bundle — generate a deterministic context bundle.
 * Returns a full bundle JSON including notes, budget, graph, feedback, and manifest.
 */
export function generateContextBundle(
  request: ContextBundleRequest,
): Promise<ApiResult<ContextBundleResponse>> {
  return post<ContextBundleResponse>('/context/bundle', request);
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

/** Return true if the result is a success envelope. */
export function isOk<T>(result: ApiResult<T>): result is ApiOk<T> {
  return result.status === 'ok';
}

/** Return the error message from any error result, or a fallback. */
export function errorMessage(result: ApiErrorEnvelope): string {
  return result.error?.message ?? 'Unknown error';
}

// ---------------------------------------------------------------------------
// Vault Bootstrap — POST /vault/bootstrap
// ---------------------------------------------------------------------------

export interface VaultBootstrapRequest {
  vault_name: string;
  domain: string;
  note_type: string;
  sections: string[];
  expected_concepts: string[];
}

export interface VaultBootstrapResponse {
  vault: string;
  created: string[];
  warnings: string[];
}

/** POST /vault/bootstrap — create a new vault from structured inputs. */
export function bootstrapVault(
  request: VaultBootstrapRequest,
): Promise<ApiResult<VaultBootstrapResponse>> {
  return post<VaultBootstrapResponse>('/vault/bootstrap', request);
}
