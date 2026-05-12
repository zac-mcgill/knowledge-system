# Context Bundle Specification

A context bundle is a deterministic package of selected vault notes, assembled for use in external workflows, LLM pipelines, or agent systems. Bundles carry their own validation status, budget metadata, and graph relationships.

Bundles are **JSON responses** returned by `POST /context/bundle` or `py run.py bundle`. They are not written to disk at the bundle layer. To write a bundle to disk as a portable package, use `POST /context/export` or `py run.py export` (see [Phase 4 Export](ROADMAP.md#phase-4--export-and-packaging)).

---

## Bundle Request

`POST /context/bundle` accepts a JSON body. All fields except `vault` are optional.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vault` | string | **required** | Registered vault name |
| `filters` | object | `{}` | Equality filters on frontmatter fields. Only fields in `ALL_KNOWN_FIELDS` are accepted. |
| `include_sections` | array of strings | `["Key Principles", "How It Works", "Trade-offs"]` | Section names to extract (without `## ` prefix). |
| `include_related` | boolean | `false` | Include graph relationship IDs for each note. |
| `include_body` | boolean | `true` | Include full note body text. |
| `max_notes` | integer | `10` | Maximum notes to include. Range: 1–100. |
| `max_chars` | integer | `20000` | Character budget. Range: 100–500000. |
| `allow_partial` | boolean | `false` | Include notes with `status=partial`. By default only `status=complete` notes are eligible. |

**Filter validation:** Only fields listed in `vault_schema.py` `ALL_KNOWN_FIELDS` are accepted. Unknown fields return HTTP 400 `INVALID_FILTER`. Supported operators: equality (`field: value`), list (`field__in: [...]`), substring (`field__contains: "..."`).

**CLI:** `py run.py bundle` uses hardcoded defaults: `filters={"status": "complete"}` (falls back to `allow_partial=True` with a warning if no complete notes exist), `include_sections=["Key Principles", "How It Works", "Trade-offs"]`, `include_body=True`, `max_notes=10`, `max_chars=20000`.

---

## Bundle Response

```json
{
  "status": "ok",
  "bundle_id": "c240ffb1e9250194",
  "vault": "demo-vault",
  "filters": {"status": "complete"},
  "created_at": "2026-05-04T12:00:00+00:00",
  "validation_status": "pass",
  "schema_version": "3.0.0",
  "notes": [...],
  "graph": {"related": {}},
  "budget": {
    "max_chars": 20000,
    "used_chars": 18500,
    "note_count": 8,
    "truncated": false
  },
  "warnings": [],
  "manifest": {
    "source_paths": ["Fundamentals/Algorithms.md", "..."],
    "schema_version": "3.0.0"
  },
  "feedback": {
    "entries": [...],
    "warnings": []
  }
}
```

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Always `"ok"` on success. |
| `bundle_id` | string | 16-character hex ID. Deterministic (SHA-256 of request params, excluding timestamp). |
| `vault` | string | Vault name used. |
| `filters` | object | Filters applied to select notes. |
| `created_at` | string | ISO-8601 UTC timestamp. **Non-deterministic** - changes on each request. |
| `validation_status` | string | `"pass"` if no selected note appears in the invalid list; `"fail"` otherwise. |
| `schema_version` | string \| null | Value of `SCHEMA_VERSION` in `vault_schema.py` if defined; `null` if the schema does not expose this constant. The demo vault exposes `"3.0.0"`. |
| `notes` | array | Selected note objects (see below). |
| `graph` | object | Graph data for selected notes. `{"related": {}}` when `include_related=false`. |
| `budget` | object | Budget accounting (see below). |
| `warnings` | array of strings | Human-readable warnings (e.g. budget truncation, fallback to partial notes). |
| `manifest` | object | Source paths and schema version. |
| `feedback` | object | Feedback entries and warnings from `feedback.md`. |

---

## Note Object

Each entry in the `notes` array:

```json
{
  "path": "Fundamentals/Algorithms.md",
  "fields": {
    "title": "Algorithms",
    "domain": "fundamentals",
    "status": "complete",
    "difficulty": "intermediate"
  },
  "sections": {
    "Key Principles": "...",
    "How It Works": "...",
    "Trade-offs": "..."
  },
  "body": "...",
  "related": [],
  "trust_metadata": {
    "trust_level": "verified",
    "source_type": "authored",
    "last_reviewed": "2025-06-01",
    "review_after": "2026-06-01",
    "confidence": "high",
    "trust_score": 90,
    "stale": false
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Vault-relative POSIX path (forward slashes). |
| `fields` | object | All parsed frontmatter fields for this note. |
| `sections` | object | Extracted section content, keyed by section name. Empty string if section not found. Only sections listed in `include_sections` are present. |
| `body` | string \| null | Full note body text (everything after frontmatter). Present when `include_body=true`; absent (key not present) when `include_body=false`. |
| `related` | array | Graph relationship IDs for this note. Empty when `include_related=false`. |
| `trust_metadata` | object | Trust/confidence metadata computed from frontmatter trust fields. Always present (Phase 25+). Confidence reflects note maintenance status, **not factual correctness**. |

**`trust_metadata` fields:**

| Field | Type | Description |
|-------|------|-------------|
| `trust_level` | string \| null | User-set trust level: `verified`, `working`, `draft`, `external`, `deprecated`. |
| `source_type` | string \| null | User-set source type: `authored`, `imported`, `generated`, `agent_suggested`. |
| `last_reviewed` | string \| null | ISO date of last review. |
| `review_after` | string \| null | ISO date after which the note is considered stale. |
| `confidence` | string | Computed confidence: `high`, `medium`, `low`, `deprecated`, `unknown`. |
| `trust_score` | integer | Numeric trust score (higher is better). Deprecated notes score negative. |
| `stale` | boolean | `true` if `review_after` is before today's UTC date. |

---

## Sections Behaviour

- Sections are extracted by scanning for headings matching `## <name>` (case-insensitive match).
- Content runs until the next `##`-level heading or end of file.
- If a section is not found, the value is an empty string `""`.
- Sections are extracted from the note body after frontmatter.
- Only sections listed in `include_sections` are included in the output.

---

## Body Behaviour

- When `include_body=true`, the full note text after the frontmatter delimiter is included as `body`.
- When `include_body=false`, the `body` key is absent from the note object.
- Body and section text may overlap: a section extract is a substring of the body. Both can be included simultaneously; the character budget counts both.

---

## Budget Behaviour

The character budget tracks how many characters of note content (body + section text) have been included.

- `max_notes` caps the candidate pool first. If `max_notes=10`, at most 10 notes are considered, even if more match the filters.
- `max_chars` then stops adding notes once the character budget would be exceeded by adding the next candidate.
- `budget.truncated` is `true` only when notes were excluded because of the character budget (not because of the `max_notes` cap).
- When `truncated=true`, a warning entry names the first note that was excluded by budget.
- Notes are added in deterministic order (case-insensitive alphabetical by path) until the budget is exhausted.

**Example:** With `max_notes=10` and 11 complete notes, the candidate pool is capped at 10. If the 8th note would push the total over `max_chars=20000`, then `note_count=8`, `truncated=true`, and a warning names note 9.

---

## Validation Status Behaviour

- `validation_status` is `"pass"` if none of the selected notes appear in the vault's invalid note list.
- `validation_status` is `"fail"` if any selected note is in the invalid list.
- Schema-invalid notes are **always excluded** from the selected pool regardless of filters.
- Notes with `status=partial` are excluded by default (`allow_partial=false`). Set `allow_partial=true` to include them.

---

## Feedback Inclusion

The bundle always includes a `feedback` block:

```json
"feedback": {
  "entries": [
    {
      "path": "Fundamentals/Algorithms.md",
      "source": "human",
      "signal": "unclear",
      "severity": "medium",
      "comment": "The How It Works section needs a clearer description.",
      "created_at": "2026-05-04T12:00:00Z"
    }
  ],
  "warnings": []
}
```

- Only entries linked to notes in the selected bundle are included.
- Missing `feedback.md` results in `entries: []` and no error.
- Entries with unknown note paths produce a warning but are kept.
- Feedback **does not affect note selection** in the bundle. It is informational only.
- To adjust task priorities by feedback, use `GET /tasks?include_feedback=true`.

---

## Determinism Guarantees

| Property | Deterministic? | Notes |
|----------|---------------|-------|
| `bundle_id` | Yes | SHA-256 of request params (vault, filters, sections, flags, bounds) |
| Note selection | Yes | Filtered by schema, sorted by path |
| Note ordering | Yes | Case-insensitive alphabetical by path |
| Section extraction | Yes | Heading scan is deterministic |
| `created_at` | **No** | Wall-clock UTC timestamp at request time |
| `validation_status` | Yes | Derived from vault state at request time |
| `graph.related` | Yes | Deterministic graph traversal |

---

## Limitations

- **`created_at` is non-deterministic.** Two identical requests at different times will have different `created_at` values but the same `bundle_id`.
- **Budget may be conservative when both body and sections are included.** The budget counts characters from both `body` and `sections` content, which can overlap. A note whose body is 3000 chars but whose 3 requested sections total 2000 chars will count ~3000 chars (body dominates, sections may be substrings of body).
- **Bundles are JSON responses, not files.** The bundle response is returned by the API or printed to stdout by the CLI. To write a bundle to disk with hashes and a manifest, use Phase 4 export.
- **No bundle history.** There is no bundle registry or versioning. Each request generates a new bundle from the current vault state.
- **No streaming.** The entire bundle is assembled in memory before returning.
