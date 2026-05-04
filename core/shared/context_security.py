"""Context Security Scanner — Phase 5

Deterministic, local, rule-based security checks for context bundles.

Scans note body text and section content for:
- Secret-like strings (private keys, API keys, tokens, password assignments)
- Prompt injection patterns
- Tool misuse instructions
- External links
- Suspicious HTML/script blocks
- Executable code fenced blocks
- Overly broad agent instructions

Design rules:
- No LLM required.  All rules are regex/keyword based.
- No network calls.  Entirely local and deterministic.
- Placeholder values (example, changeme, your_api_key, etc.) are not flagged
  for credential patterns to reduce false positives.
- Tests must use only fake, synthetic secrets — never real credentials.

Status levels returned:
  pass    No findings.
  warning Findings exist but none meet the fail threshold.
  fail    One or more findings with severity high/critical for a blocking rule
          (private-key, api-key-aws, api-key-github, api-key-slack,
          bearer-token, password-pattern).

Severity levels used:
  critical  Private key blocks.
  high      API keys and bearer tokens.
  medium    Prompt injection, script/HTML, tool misuse, broad agent instructions.
  low       External links, executable code blocks.
  info      Informational only (reserved for future use).

Findings are ordered deterministically:
  path asc, severity desc, rule asc, field asc, detail asc.

This is not a full DLP or malware scanner.  It provides a first-pass
signal to alert content authors before context is served to agents.
"""

from __future__ import annotations

import re

from core.shared.context_bundle import generate_bundle


# ---------------------------------------------------------------------------
# Severity ranking
# ---------------------------------------------------------------------------

_SEVERITY_RANK: dict[str, int] = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# ---------------------------------------------------------------------------
# Rules that can cause status=fail when severity is high or critical
# ---------------------------------------------------------------------------

_BLOCKING_RULES: frozenset[str] = frozenset(
    {
        "private-key",
        "api-key-aws",
        "api-key-github",
        "api-key-slack",
        "bearer-token",
        "password-pattern",
    }
)

# ---------------------------------------------------------------------------
# Placeholder substrings — suppress credential-pattern findings when present
# in the matched value.
# ---------------------------------------------------------------------------

_PLACEHOLDER_SUBSTRINGS: tuple[str, ...] = (
    "example",
    "placeholder",
    "your_api_key",
    "<token>",
    "<api_key>",
    "changeme",
    "redacted",
    "dummy",
    "test",
)


def _is_placeholder(value: str) -> bool:
    """Return True if value looks like a non-secret placeholder."""
    lower = value.lower().strip()
    # Angle-bracket or double-brace templates (<...> / {{...}})
    if lower.startswith("<") or lower.startswith("{{"):
        return True
    for substr in _PLACEHOLDER_SUBSTRINGS:
        if substr in lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Rule definitions: (pattern_string, severity, rule_id, detail_message)
#
# Compiled lazily via _get_compiled_rules().
# ---------------------------------------------------------------------------

_RAW_RULES: list[tuple[str, str, str, str]] = [
    # ------------------------------------------------------------------
    # Private keys  (critical)
    # ------------------------------------------------------------------
    (
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "critical",
        "private-key",
        "Private key block detected.",
    ),
    # ------------------------------------------------------------------
    # AWS access key  (high)
    # ------------------------------------------------------------------
    (
        r"\bAKIA[0-9A-Z]{16}\b",
        "high",
        "api-key-aws",
        "AWS access key pattern (AKIA...) detected.",
    ),
    # ------------------------------------------------------------------
    # GitHub tokens  (high)
    # ------------------------------------------------------------------
    (
        r"\bghp_[A-Za-z0-9_]{36,}\b",
        "high",
        "api-key-github",
        "GitHub personal access token (ghp_...) detected.",
    ),
    (
        r"\bgithub_pat_[A-Za-z0-9_]{22,}\b",
        "high",
        "api-key-github",
        "GitHub fine-grained PAT (github_pat_...) detected.",
    ),
    # ------------------------------------------------------------------
    # Slack tokens  (high)
    # ------------------------------------------------------------------
    (
        r"\bxoxb-[A-Za-z0-9\-]{20,}\b",
        "high",
        "api-key-slack",
        "Slack bot token (xoxb-) detected.",
    ),
    (
        r"\bxoxp-[A-Za-z0-9\-]{20,}\b",
        "high",
        "api-key-slack",
        "Slack user token (xoxp-) detected.",
    ),
    (
        r"\bxoxa-[A-Za-z0-9\-]{20,}\b",
        "high",
        "api-key-slack",
        "Slack app token (xoxa-) detected.",
    ),
    # ------------------------------------------------------------------
    # Bearer token in header  (high)
    # ------------------------------------------------------------------
    (
        r"Authorization:\s*Bearer\s+[A-Za-z0-9._\-+=\/]{20,}",
        "high",
        "bearer-token",
        "Authorization Bearer token detected.",
    ),
    # ------------------------------------------------------------------
    # Prompt injection patterns  (medium)
    # ------------------------------------------------------------------
    (
        r"(?i)ignore\s+(?:all\s+)?previous\s+instructions",
        "medium",
        "prompt-injection-pattern",
        "Potential instruction override phrase detected: 'ignore previous instructions'.",
    ),
    (
        r"(?i)disregard\s+previous\s+instructions",
        "medium",
        "prompt-injection-pattern",
        "Potential instruction override phrase detected: 'disregard previous instructions'.",
    ),
    (
        r"(?i)reveal\s+(?:the\s+)?system\s+prompt",
        "medium",
        "prompt-injection-pattern",
        "Potential instruction override phrase detected: 'reveal system prompt'.",
    ),
    (
        r"(?i)print\s+hidden\s+instructions",
        "medium",
        "prompt-injection-pattern",
        "Potential instruction override phrase detected: 'print hidden instructions'.",
    ),
    (
        r"(?i)override\s+(?:the\s+)?system\s+message",
        "medium",
        "prompt-injection-pattern",
        "Potential instruction override phrase detected: 'override system message'.",
    ),
    (
        r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
        "medium",
        "prompt-injection-pattern",
        "Potential instruction override phrase detected: 'you are now in developer mode'.",
    ),
    (
        r"(?i)disable\s+safety",
        "medium",
        "prompt-injection-pattern",
        "Potential instruction override phrase detected: 'disable safety'.",
    ),
    (
        r"(?i)do\s+not\s+follow\s+(?:the\s+)?system\s+message",
        "medium",
        "prompt-injection-pattern",
        "Potential instruction override phrase detected: 'do not follow the system message'.",
    ),
    # ------------------------------------------------------------------
    # Tool misuse instructions  (medium)
    # ------------------------------------------------------------------
    (
        r"(?i)run\s+shell\s+command\s+to\s+delete",
        "medium",
        "tool-misuse",
        "Potential tool misuse instruction detected: 'run shell command to delete'.",
    ),
    (
        r"(?i)\bexfiltrate\b",
        "medium",
        "tool-misuse",
        "Potential tool misuse instruction detected: 'exfiltrate'.",
    ),
    (
        r"(?i)\bsteal\s+credentials\b",
        "medium",
        "tool-misuse",
        "Potential tool misuse instruction detected: 'steal credentials'.",
    ),
    (
        r"(?i)\bsend\s+secrets\b",
        "medium",
        "tool-misuse",
        "Potential tool misuse instruction detected: 'send secrets'.",
    ),
    (
        r"(?i)\bbypass\s+authentication\b",
        "medium",
        "tool-misuse",
        "Potential tool misuse instruction detected: 'bypass authentication'.",
    ),
    (
        r"(?i)\bdisable\s+logging\b",
        "medium",
        "tool-misuse",
        "Potential tool misuse instruction detected: 'disable logging'.",
    ),
    # ------------------------------------------------------------------
    # External links  (low)
    # ------------------------------------------------------------------
    (
        r"https?://\S+",
        "low",
        "external-link",
        "External URL detected.",
    ),
    # ------------------------------------------------------------------
    # Suspicious HTML / script  (medium)
    # ------------------------------------------------------------------
    (
        r"<script[\s>]",
        "medium",
        "script-html",
        "HTML <script> tag detected.",
    ),
    (
        r"javascript:",
        "medium",
        "script-html",
        "javascript: URI scheme detected.",
    ),
    (
        r"onerror\s*=",
        "medium",
        "script-html",
        "onerror event handler attribute detected.",
    ),
    (
        r"onclick\s*=",
        "medium",
        "script-html",
        "onclick event handler attribute detected.",
    ),
    # ------------------------------------------------------------------
    # Executable code fenced blocks  (low)
    # ------------------------------------------------------------------
    (
        r"```(?:bash|sh|powershell|ps1|cmd|bat|python)\b",
        "low",
        "executable-code-block",
        "Executable code block detected.",
    ),
    # ------------------------------------------------------------------
    # Overly broad agent instructions  (medium)
    # ------------------------------------------------------------------
    (
        r"(?i)always\s+obey\s+this\s+document",
        "medium",
        "broad-agent-instruction",
        "Overly broad agent instruction phrase: 'always obey this document'.",
    ),
    (
        r"(?i)this\s+document\s+overrides\s+all\s+other\s+instructions",
        "medium",
        "broad-agent-instruction",
        "Overly broad agent instruction phrase: 'this document overrides all other instructions'.",
    ),
    (
        r"(?i)you\s+must\s+follow\s+these\s+instructions\s+over\s+system\s+instructions",
        "medium",
        "broad-agent-instruction",
        "Overly broad agent instruction phrase: 'you must follow these instructions over system instructions'.",
    ),
]

# Password/credential assignment patterns are handled separately
# so placeholder detection can be applied to the matched value.
_CREDENTIAL_PATTERN = re.compile(
    r"(?i)(?P<key>password|passwd|secret|api_key|token)\s*[=:]\s*(?P<value>[^\s,\n\"\']{4,})",
)

# Compiled rule list (lazy init, module-level cache)
_COMPILED_RULES: list[tuple[re.Pattern, str, str, str]] | None = None


def _get_compiled_rules() -> list[tuple[re.Pattern, str, str, str]]:
    """Return compiled rule list (compiled once per process)."""
    global _COMPILED_RULES
    if _COMPILED_RULES is None:
        _COMPILED_RULES = [
            (re.compile(pattern), severity, rule_id, detail)
            for pattern, severity, rule_id, detail in _RAW_RULES
        ]
    return _COMPILED_RULES


# ---------------------------------------------------------------------------
# Core public functions
# ---------------------------------------------------------------------------


def scan_text(
    text: str,
    path: str | None = None,
    field: str | None = None,
) -> list[dict]:
    """Scan a single text string for security findings.

    Each rule is applied at most once per text+field combination to avoid
    duplicate findings for repeated pattern occurrences.

    Args:
        text:  The text to scan (note body, section content, etc.).
        path:  Vault-relative POSIX path to the source note (for reporting).
        field: Name of the field being scanned (e.g. ``"body"``,
               ``"section:Key Principles"``).

    Returns:
        List of finding dicts, each with ``path``, ``severity``, ``rule``,
        ``field``, and ``detail`` keys.  Empty list if no findings.
        Findings are NOT sorted here; sorting happens at the bundle level.
    """
    if not text:
        return []

    findings: list[dict] = []
    reported_rules: set[str] = set()  # deduplicate per rule within this text

    norm_path = path or ""
    norm_field = field or ""

    for pattern, severity, rule_id, detail in _get_compiled_rules():
        if rule_id not in reported_rules and pattern.search(text):
            reported_rules.add(rule_id)
            findings.append(
                {
                    "path": norm_path,
                    "severity": severity,
                    "rule": rule_id,
                    "field": norm_field,
                    "detail": detail,
                }
            )

    # ------------------------------------------------------------------
    # Credential assignment patterns (with placeholder suppression)
    # ------------------------------------------------------------------
    if "password-pattern" not in reported_rules:
        for match in _CREDENTIAL_PATTERN.finditer(text):
            value = match.group("value")
            key = match.group("key").lower()
            if _is_placeholder(value):
                continue
            findings.append(
                {
                    "path": norm_path,
                    "severity": "high",
                    "rule": "password-pattern",
                    "field": norm_field,
                    "detail": (
                        f"Credential assignment pattern detected: "
                        f"'{key}' with a non-placeholder value."
                    ),
                }
            )
            reported_rules.add("password-pattern")
            break  # one finding per text for this rule

    return findings


def scan_context_bundle(bundle: dict) -> dict:
    """Scan a context bundle for security issues.

    Scans note body text and section content for all registered rules.
    Does not modify the bundle.

    Args:
        bundle: Bundle dict as returned by ``generate_bundle()``.
                If the bundle has ``status="error"``, returns a structured
                error immediately without scanning.

    Returns:
        Security scan result dict::

            {
                "status": "pass" | "warning" | "fail",
                "findings": [...],
                "summary": {"fail": N, "warning": N, "info": N},
                "scanned": {
                    "note_count": N,
                    "source_paths": [...]
                }
            }

        On error::

            {"status": "error", "error": {"code": ..., "message": ...}}
    """
    if bundle.get("status") == "error":
        return {
            "status": "error",
            "error": bundle.get(
                "error",
                {"code": "BUNDLE_ERROR", "message": "Bundle has error status"},
            ),
        }

    notes = bundle.get("notes", [])
    all_findings: list[dict] = []

    for note in notes:
        note_path = note.get("path", "")

        # Scan full body
        body = note.get("body", "")
        if body:
            all_findings.extend(scan_text(body, path=note_path, field="body"))

        # Scan extracted sections
        sections = note.get("sections", {})
        for sec_name, sec_text in sections.items():
            if sec_text:
                all_findings.extend(
                    scan_text(sec_text, path=note_path, field=f"section:{sec_name}")
                )

    # ------------------------------------------------------------------
    # Deduplicate: same (path, rule, field, detail) → one finding
    # ------------------------------------------------------------------
    seen: set[tuple] = set()
    unique: list[dict] = []
    for f in all_findings:
        key = (f["path"], f["rule"], f["field"], f["detail"])
        if key not in seen:
            seen.add(key)
            unique.append(f)

    # ------------------------------------------------------------------
    # Deterministic sort: path asc, severity desc, rule, field, detail
    # ------------------------------------------------------------------
    unique.sort(
        key=lambda f: (
            f["path"],
            -_SEVERITY_RANK[f["severity"]],
            f["rule"],
            f["field"],
            f["detail"],
        )
    )

    source_paths = [n.get("path", "") for n in notes]

    return {
        "status": _derive_status(unique),
        "findings": unique,
        "summary": _derive_summary(unique),
        "scanned": {
            "note_count": len(notes),
            "source_paths": source_paths,
        },
    }


def scan_vault_context(
    vault_name: str,
    filters: dict | None = None,
    include_sections: list[str] | None = None,
    include_body: bool = True,
    max_notes: int = 10,
    max_chars: int = 20000,
    allow_partial: bool = False,
) -> dict:
    """Generate a context bundle and scan it for security issues.

    Uses the same note selection logic as ``generate_bundle()``.
    Does not write files or modify the vault.

    Args:
        vault_name:       Registered vault name.
        filters:          Equality filters on frontmatter fields.
        include_sections: Section heading names to scan (without ``## `` prefix).
                          Defaults to ``["Key Principles", "How It Works",
                          "Trade-offs"]`` when ``None``.
        include_body:     If ``True``, scan full note body text.
        max_notes:        Maximum number of notes to include in scan scope.
        max_chars:        Character budget for the underlying bundle.
        allow_partial:    If ``True``, include notes with ``status=partial``.

    Returns:
        Security scan result dict (same shape as ``scan_context_bundle``),
        or a structured error dict if vault lookup fails.
    """
    if include_sections is None:
        include_sections = ["Key Principles", "How It Works", "Trade-offs"]

    bundle = generate_bundle(
        vault_name=vault_name,
        filters=filters or {},
        include_sections=include_sections,
        include_related=False,
        include_body=include_body,
        max_notes=max_notes,
        max_chars=max_chars,
        allow_partial=allow_partial,
    )

    if bundle.get("status") == "error":
        return bundle

    return scan_context_bundle(bundle)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_status(findings: list[dict]) -> str:
    """Compute overall scan status from a findings list.

    ``fail``    — any finding with severity high/critical AND a blocking rule.
    ``warning`` — findings exist but no fail condition.
    ``pass``    — no findings.
    """
    if not findings:
        return "pass"
    for f in findings:
        if f["severity"] in ("high", "critical") and f["rule"] in _BLOCKING_RULES:
            return "fail"
    return "warning"


def _derive_summary(findings: list[dict]) -> dict:
    """Return counts grouped by fail / warning / info buckets.

    ``fail``    — severity high or critical.
    ``warning`` — severity medium or low.
    ``info``    — severity info.
    """
    return {
        "fail": sum(1 for f in findings if f["severity"] in ("high", "critical")),
        "warning": sum(1 for f in findings if f["severity"] in ("medium", "low")),
        "info": sum(1 for f in findings if f["severity"] == "info"),
    }
