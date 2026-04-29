"""
Graph builder — deterministic relationship graph over vault notes.

Derives relationships ONLY from:
    - schema-defined hierarchy (domain / subdomain / topic)
    - note frontmatter fields
    - EXPECTED_CONCEPTS table

No LLMs, no embeddings, no natural-language parsing.
All outputs are deterministically sorted; identical input → identical output.

Hub model (O(n) edges):
    Notes connect to their group nodes (domain / subdomain / topic) via
    member_of edges.  Structural similarity is implicit through the shared
    hub node — no pairwise note↔note edges are emitted.

Node types:
    note             — a vault note
    domain           — schema-defined domain
    subdomain        — schema-defined subdomain
    topic            — schema-defined topic
    expected_concept — concept listed in EXPECTED_CONCEPTS but absent from vault

Edge types:
    parent           — schema hierarchy: child points to its parent
                       (subdomain → domain, topic → subdomain)
    member_of        — note belongs to a domain / subdomain / topic hub
                       (note → domain, note → subdomain, note → topic)
    expected_coverage — note satisfies an EXPECTED_CONCEPTS slot (note → group),
                        or group → missing expected_concept node
"""

from __future__ import annotations

from mcp.core.vault_registry import list_vaults, get_schema
from mcp.core.note_index import get_index


def build_graph(vault_name: str | None = None) -> dict:
    """Build a deterministic relationship graph for a vault.

    Args:
        vault_name: Registered vault name. Defaults to the first registered vault.

    Returns:
        {
            "nodes": list[dict],  # sorted ascending by id
            "edges": list[dict],  # sorted ascending by (from, to, type)
        }

    Node shape:  {"id": str, "type": str, "label": str}
    Edge shape:  {"from": str, "to": str, "type": str}
    """
    if vault_name is None:
        vaults = list_vaults()
        if not vaults:
            return {"nodes": [], "edges": []}
        vault_name = vaults[0]

    schema = get_schema(vault_name)
    index = get_index(vault_name)

    # id → node dict (deduplicated)
    nodes: dict[str, dict] = {}
    # (from_id, to_id, edge_type) tuples (deduplicated via set)
    edges_set: set[tuple[str, str, str]] = set()

    # ------------------------------------------------------------------
    # 1. Hierarchy nodes from the schema definition
    # ------------------------------------------------------------------

    # Domain nodes
    for _folder, domain_slug in schema.DOMAIN_MAP.items():
        node_id = f"domain::{domain_slug}"
        nodes[node_id] = {"id": node_id, "type": "domain", "label": domain_slug}

    # Subdomain nodes + subdomain→domain parent edges (child points to parent)
    subdomain_map = getattr(schema, "SUBDOMAIN_MAP", {})
    for _folder, (subdomain_slug, parent_domain) in subdomain_map.items():
        node_id = f"subdomain::{subdomain_slug}"
        nodes[node_id] = {"id": node_id, "type": "subdomain", "label": subdomain_slug}
        parent_id = f"domain::{parent_domain}"
        edges_set.add((node_id, parent_id, "parent"))

    # Topic nodes + topic→subdomain parent edges (child points to parent)
    topic_map = getattr(schema, "TOPIC_MAP", {})
    for _folder, (topic_slug, parent_subdomain) in topic_map.items():
        node_id = f"topic::{topic_slug}"
        nodes[node_id] = {"id": node_id, "type": "topic", "label": topic_slug}
        parent_id = f"subdomain::{parent_subdomain}"
        edges_set.add((node_id, parent_id, "parent"))

    # ------------------------------------------------------------------
    # 2. Note nodes + member_of edges to hub nodes
    # ------------------------------------------------------------------

    for note in index:
        path = note["path"]
        fields = note["fields"]

        # Derive label from filename stem
        filename = path.rsplit("/", 1)[-1]
        label = filename[:-3] if filename.endswith(".md") else filename

        nodes[path] = {"id": path, "type": "note", "label": label}

        domain = (fields.get("domain") or "").strip()
        subdomain = (fields.get("subdomain") or "").strip()
        topic = (fields.get("topic") or "").strip()

        # Hub edges: note → domain/subdomain/topic group node
        if domain:
            domain_node_id = f"domain::{domain}"
            if domain_node_id not in nodes:
                # Note references a domain not in DOMAIN_MAP — create it defensively
                nodes[domain_node_id] = {
                    "id": domain_node_id,
                    "type": "domain",
                    "label": domain,
                }
            edges_set.add((path, domain_node_id, "member_of"))

        if subdomain:
            subdomain_node_id = f"subdomain::{subdomain}"
            if subdomain_node_id not in nodes:
                nodes[subdomain_node_id] = {
                    "id": subdomain_node_id,
                    "type": "subdomain",
                    "label": subdomain,
                }
            edges_set.add((path, subdomain_node_id, "member_of"))

        if topic:
            topic_node_id = f"topic::{topic}"
            if topic_node_id not in nodes:
                nodes[topic_node_id] = {
                    "id": topic_node_id,
                    "type": "topic",
                    "label": topic,
                }
            edges_set.add((path, topic_node_id, "member_of"))

    # ------------------------------------------------------------------
    # 3. EXPECTED_CONCEPTS coverage edges
    # ------------------------------------------------------------------

    expected_concepts: dict = getattr(schema, "EXPECTED_CONCEPTS", {})
    if expected_concepts:
        # Map lowercase stem → actual path for fast lookup
        stem_to_path: dict[str, str] = {
            (note["path"].rsplit("/", 1)[-1][:-3]
             if note["path"].endswith(".md")
             else note["path"].rsplit("/", 1)[-1]).lower(): note["path"]
            for note in index
        }

        for group_key, concept_names in sorted(expected_concepts.items()):
            # Prefer domain node, fall back to subdomain node
            group_node_id = (
                f"domain::{group_key}"
                if f"domain::{group_key}" in nodes
                else f"subdomain::{group_key}"
            )

            for concept_name in sorted(concept_names):
                concept_lower = concept_name.lower()
                if concept_lower in stem_to_path:
                    # Existing note satisfies this expected concept slot
                    note_path = stem_to_path[concept_lower]
                    edges_set.add((note_path, group_node_id, "expected_coverage"))
                else:
                    # Missing concept: materialise a placeholder node
                    missing_id = f"expected_concept::{concept_name}"
                    if missing_id not in nodes:
                        nodes[missing_id] = {
                            "id": missing_id,
                            "type": "expected_concept",
                            "label": concept_name,
                        }
                    edges_set.add((group_node_id, missing_id, "expected_coverage"))

    # ------------------------------------------------------------------
    # 4. Deterministic final sort
    # ------------------------------------------------------------------

    sorted_nodes = sorted(nodes.values(), key=lambda n: n["id"])
    sorted_edges = sorted(
        [{"from": f, "to": t, "type": tp} for f, t, tp in edges_set],
        key=lambda e: (e["from"], e["to"], e["type"]),
    )

    return {"nodes": sorted_nodes, "edges": sorted_edges}
