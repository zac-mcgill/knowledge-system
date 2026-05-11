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
  details?: unknown;
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

export interface SecurityScanned {
  note_count: number;
  source_paths: string[];
  total_notes?: number;
  coverage?: number;
  truncated?: boolean;
}

export interface SecurityData {
  status: 'pass' | 'warning' | 'fail';
  findings: SecurityFinding[];
  summary: SecuritySummary;
  scanned: SecurityScanned;
}

// Alias so SecurityScan.svelte can import a distinct name
export type ContextSecurityResponse = SecurityData;

export interface ContextSecurityRequest {
  vault: string;
  filters?: Record<string, string | string[]>;
  include_sections?: string[];
  include_body?: boolean;
  max_notes?: number;
  max_chars?: number;
  allow_partial?: boolean;
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
 * POST /context/security — vault-level security scan covering all content notes.
 * Partial notes are included by default because they can still contain secrets
 * or injection phrases. Generated/system files under Vault Files/ are excluded
 * by the vault index and are never scanned.
 */
export function fetchSecurity(vault: string): Promise<ApiResult<SecurityData>> {
  return post<SecurityData>('/context/security', {
    vault,
    include_body: true,
    allow_partial: true,
    max_notes: 200,
  });
}

/**
 * POST /context/security — full configurable security scan.
 * Used by the Security Scan UI for user-configured requests.
 */
export function scanContextSecurity(
  request: ContextSecurityRequest,
): Promise<ApiResult<ContextSecurityResponse>> {
  return post<ContextSecurityResponse>('/context/security', request);
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
  subdomains?: number;
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
// Feedback — GET /feedback + write operations
// ---------------------------------------------------------------------------

export type FeedbackSource = 'human' | 'agent' | 'system';
export type FeedbackSignal =
  | 'unclear'
  | 'incomplete'
  | 'outdated'
  | 'incorrect'
  | 'agent_failed'
  | 'needs_example'
  | 'needs_constraints'
  | 'useful'
  | 'agent_succeeded';
export type FeedbackSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface FeedbackEntry {
  id?: string;
  path: string;
  source: FeedbackSource | string;
  signal: FeedbackSignal | string;
  severity: FeedbackSeverity | string;
  comment: string;
  created_at: string;
  updated_at?: string;
}

export interface FeedbackData {
  status: 'ok' | 'error';
  vault: string;
  entries: FeedbackEntry[];
  warnings: string[];
  errors: unknown[];
}

/** Shape returned by POST /feedback and PUT /feedback/{id} */
export interface FeedbackResponse {
  entry: FeedbackEntry;
  feedback: FeedbackData;
}

/** Shape returned by DELETE /feedback/{id} */
export interface FeedbackDeleteResponse {
  deleted: string;
  feedback: FeedbackData;
}

/** Shape returned by POST /feedback/normalise */
export interface FeedbackNormaliseResponse {
  normalised: number;
  feedback: FeedbackData;
}

export interface FeedbackCreateRequest {
  vault: string;
  path: string;
  source: FeedbackSource;
  signal: FeedbackSignal;
  severity: FeedbackSeverity;
  comment: string;
}

export interface FeedbackUpdateRequest {
  vault: string;
  path: string;
  source: FeedbackSource;
  signal: FeedbackSignal;
  severity: FeedbackSeverity;
  comment: string;
}

/** Perform a PUT request with a JSON body and return the typed result. */
async function put<T>(path: string, body: unknown): Promise<ApiResult<T>> {
  try {
    const resp = await fetch(`${API_BASE}${path}`, {
      method: 'PUT',
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

/** Perform a DELETE request and return the typed result. */
async function del<T>(path: string): Promise<ApiResult<T>> {
  try {
    const resp = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
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

/** GET /feedback — vault feedback entries from Vault Files/feedback.md. */
export function fetchFeedback(vault?: string): Promise<ApiResult<FeedbackData>> {
  const qs = vault ? `?vault=${encodeURIComponent(vault)}` : '';
  return get<FeedbackData>(`/feedback${qs}`);
}

/** POST /feedback — add a new feedback entry. */
export function createFeedback(
  request: FeedbackCreateRequest,
): Promise<ApiResult<FeedbackResponse>> {
  return post<FeedbackResponse>('/feedback', request);
}

/** PUT /feedback/{feedback_id} — update an existing feedback entry. */
export function updateFeedback(
  feedbackId: string,
  request: FeedbackUpdateRequest,
): Promise<ApiResult<FeedbackResponse>> {
  return put<FeedbackResponse>(`/feedback/${encodeURIComponent(feedbackId)}`, request);
}

/** DELETE /feedback/{feedback_id}?vault=<vault> — delete a feedback entry. */
export function deleteFeedback(
  feedbackId: string,
  vault: string,
): Promise<ApiResult<FeedbackDeleteResponse>> {
  return del<FeedbackDeleteResponse>(
    `/feedback/${encodeURIComponent(feedbackId)}?vault=${encodeURIComponent(vault)}`,
  );
}

/** POST /feedback/normalise?vault=<vault> — assign IDs to id-less entries. */
export function normaliseFeedback(vault: string): Promise<ApiResult<FeedbackNormaliseResponse>> {
  return post<FeedbackNormaliseResponse>(
    `/feedback/normalise?vault=${encodeURIComponent(vault)}`,
    {},
  );
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
  expected_concepts?: { requested: number; written: number };
}

/** POST /vault/bootstrap — create a new vault from structured inputs. */
export function bootstrapVault(
  request: VaultBootstrapRequest,
): Promise<ApiResult<VaultBootstrapResponse>> {
  return post<VaultBootstrapResponse>('/vault/bootstrap', request);
}
// ---------------------------------------------------------------------------
// Context Export — POST /context/export
// ---------------------------------------------------------------------------

export interface ExportFileInfo {
  sha256: string;
  bytes: number;
}

export interface ContextExportRequest extends ContextBundleRequest {
  overwrite: boolean;
  require_security_pass: boolean;
}

export interface ContextExportResponse {
  status: string;
  bundle_id: string;
  package_dir: string;
  files: Record<string, ExportFileInfo>;
  warnings: string[];
}

/**
 * POST /context/export — generate a context bundle and write it to disk as a
 * portable package. Returns file manifest with SHA-256 hashes.
 */
export function exportContextPackage(
  request: ContextExportRequest,
): Promise<ApiResult<ContextExportResponse>> {
  return post<ContextExportResponse>('/context/export', request);
}
// ---------------------------------------------------------------------------
// Note Browser — GET /notes, GET /note, POST /query
// ---------------------------------------------------------------------------

/** Item returned by GET /notes. */
export interface NoteListItem {
  name: string;
  status: string;
  difficulty: string;
  missing: string[];
  path: string;
}

export interface NotesData {
  notes: NoteListItem[];
}

/** Frontmatter fields from a single note (all values are unknown from YAML). */
export interface NoteFields {
  title?: string;
  status?: string;
  domain?: string;
  type?: string;
  difficulty?: string;
  [key: string]: unknown;
}

/** Full note detail returned by GET /note. Includes path, fields, and body. */
export interface NoteDetail {
  path: string;
  fields: NoteFields;
  body?: string;
}

/** Request body for POST /query. */
export interface NoteQueryRequest {
  vault: string;
  filters?: Record<string, string | string[]>;
  limit?: number;
  offset?: number;
  strict?: boolean;
  q?: string;
  q_fields?: string[];
}

/** Single result item from POST /query. */
export interface QueryResultItem {
  path: string;
  fields: NoteFields;
  score?: number;
}

/** Response data from POST /query. */
export interface NoteQueryResponse {
  count: number;
  returned: number;
  offset: number;
  limit: number;
  results: QueryResultItem[];
}

/** GET /notes — list all notes with metadata. */
export function fetchNotes(vault?: string): Promise<ApiResult<NotesData>> {
  const qs = vault ? `?vault=${encodeURIComponent(vault)}` : '';
  return get<NotesData>(`/notes${qs}`);
}

/** GET /note — retrieve a single note by vault and path. Includes body. */
export function fetchNote(vault: string, path: string): Promise<ApiResult<NoteDetail>> {
  return get<NoteDetail>(
    `/note?vault=${encodeURIComponent(vault)}&path=${encodeURIComponent(path)}`,
  );
}

/** POST /query — query notes with optional filters and free-text search. */
export function queryNotes(request: NoteQueryRequest): Promise<ApiResult<NoteQueryResponse>> {
  return post<NoteQueryResponse>('/query', request);
}

// ---------------------------------------------------------------------------
// Note Update — PUT /note
// ---------------------------------------------------------------------------

/** Request body for PUT /note. */
export interface NoteUpdateRequest {
  vault: string;
  path: string;
  fields: Record<string, unknown>;
  body: string;
}

/** Validation result returned inside a successful PUT /note response. */
export interface NoteUpdateValidation {
  status: string;
  errors: string[];
}

/** Data returned by PUT /note on success. */
export interface NoteUpdateResponse {
  path: string;
  fields: Record<string, unknown>;
  body: string;
  validation: NoteUpdateValidation;
  warnings: string[];
}

/** PUT /note — atomically update an existing note's fields and body. */
export function updateNote(
  request: NoteUpdateRequest,
): Promise<ApiResult<NoteUpdateResponse>> {
  return put<NoteUpdateResponse>('/note', request);
}

// ---------------------------------------------------------------------------
// Graph — GET /graph, GET /graph/neighbors, GET /graph/related, GET /graph/missing
// ---------------------------------------------------------------------------

export interface GraphNode {
  id: string;
  type: 'note' | 'domain' | 'subdomain' | 'topic' | 'expected_concept';
  label: string;
}

export interface GraphEdge {
  from: string;
  to: string;
  type: 'parent' | 'member_of' | 'expected_coverage';
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNeighborEntry {
  id: string;
  type: string;
  label: string;
  edge_type: string;
}

export interface GraphNeighborsData {
  node_id: string;
  found: boolean;
  neighbors: GraphNeighborEntry[];
}

export interface GraphRelatedEntry {
  id: string;
  type: string;
  label: string;
  via: string;
  strength: string;
}

export interface GraphRelatedData {
  node_id: string;
  found: boolean;
  related: GraphRelatedEntry[];
}

export interface GraphMissingEntry {
  id: string;
  label: string;
  via: string;
}

export interface GraphMissingNeighborsData {
  node_id: string;
  found: boolean;
  missing: GraphMissingEntry[];
}

export interface RankedMissingConcept {
  rank: number;
  score: number;
  subdomain: string;
  concept: string;
}

/** GET /graph — deterministic vault relationship graph. */
export function fetchGraph(vault?: string): Promise<ApiResult<GraphData>> {
  const qs = vault ? `?vault=${encodeURIComponent(vault)}` : '';
  return get<GraphData>(`/graph${qs}`);
}

/** GET /graph/neighbors — directly connected nodes (both directions). */
export function fetchGraphNeighbors(
  nodeId: string,
  vault?: string,
): Promise<ApiResult<GraphNeighborsData>> {
  const params = new URLSearchParams({ node: nodeId });
  if (vault) params.set('vault', vault);
  return get<GraphNeighborsData>(`/graph/neighbors?${params.toString()}`);
}

/** GET /graph/related — notes that share a group hub with the given node. */
export function fetchGraphRelated(
  nodeId: string,
  vault?: string,
  minStrength = 'domain',
): Promise<ApiResult<GraphRelatedData>> {
  const params = new URLSearchParams({ node: nodeId, min_strength: minStrength });
  if (vault) params.set('vault', vault);
  return get<GraphRelatedData>(`/graph/related?${params.toString()}`);
}

/** GET /graph/missing — expected concepts missing near a node's group hubs. */
export function fetchGraphMissing(
  nodeId: string,
  vault?: string,
): Promise<ApiResult<GraphMissingNeighborsData>> {
  const params = new URLSearchParams({ node: nodeId });
  if (vault) params.set('vault', vault);
  return get<GraphMissingNeighborsData>(`/graph/missing?${params.toString()}`);
}

// ---------------------------------------------------------------------------
// Vault Deletion — DELETE /vault/{name}
// ---------------------------------------------------------------------------

export interface VaultDeleteRequest {
  /** Must be exactly "DELETE <vault-name>". */
  confirm: string;
}

export interface VaultDeleteResponse {
  deleted: string;
  remaining_vaults: string[];
  active_vault: string;
}

/**
 * DELETE /vault/{vaultName} — permanently delete a non-demo vault.
 *
 * Requires an exact confirmation phrase: "DELETE <vault-name>".
 * demo-vault is always rejected. The last remaining vault is protected.
 */
export function deleteVault(
  vaultName: string,
  confirm: string,
): Promise<ApiResult<VaultDeleteResponse>> {
  try {
    return fetch(`${API_BASE}/vault/${encodeURIComponent(vaultName)}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm }),
    })
      .then((resp) => resp.json())
      .then((json) => json as ApiResult<VaultDeleteResponse>)
      .catch((err: unknown) => ({
        status: 'error' as const,
        error: {
          code: 'NETWORK_ERROR',
          message: err instanceof Error ? err.message : 'Network request failed',
        },
      }));
  } catch (err) {
    return Promise.resolve({
      status: 'error',
      error: {
        code: 'NETWORK_ERROR',
        message: err instanceof Error ? err.message : 'Network request failed',
      },
    });
  }
}