"""
Graph query — deterministic traversal functions over the vault graph.

All functions accept a pre-built graph dict (from build_graph) and a
node_id string.  Results are always sorted; identical input → identical
output.

No LLMs, no embeddings, no natural-language parsing.

Functions
---------
get_neighbors(graph, node_id)
    Directly connected nodes (both directions), deduplicated and sorted.

get_related_nodes(graph, node_id)
    Notes that share a group hub (domain / subdomain / topic) with the
    given note.  Traversal: note → group → all other notes in that group.

get_missing_neighbors(graph, node_id)
    expected_concept nodes reachable from the group nodes the given note
    belongs to.  These represent concepts expected near this note but not
    yet present in the vault.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_adjacency(graph: dict) -> dict[str, set[str]]:
    """Build a bidirectional adjacency map: node_id → {neighbour_ids}.

    Both edge directions are indexed so that traversal does not depend on
    edge orientation.
    """
    adj: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        src, dst = edge["from"], edge["to"]
        adj.setdefault(src, set()).add(dst)
        adj.setdefault(dst, set()).add(src)
    return adj


def _node_map(graph: dict) -> dict[str, dict]:
    """Return id → node dict for O(1) lookups."""
    return {n["id"]: n for n in graph["nodes"]}


def _edges_from(graph: dict, node_id: str) -> list[dict]:
    """Return all edges where node_id is the source."""
    return [e for e in graph["edges"] if e["from"] == node_id]


def _edges_to(graph: dict, node_id: str) -> list[dict]:
    """Return all edges where node_id is the target."""
    return [e for e in graph["edges"] if e["to"] == node_id]


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------

def get_neighbors(graph: dict, node_id: str) -> dict:
    """Return all directly connected nodes (both edge directions).

    Args:
        graph: Output of build_graph().
        node_id: The id of the node to query.

    Returns:
        {
            "node_id": str,
            "found": bool,
            "neighbors": list[dict],  # sorted by id
        }

    Each neighbor: {"id": str, "type": str, "label": str, "edge_type": str}
    """
    nmap = _node_map(graph)
    if node_id not in nmap:
        return {"node_id": node_id, "found": False, "neighbors": []}

    seen: dict[str, str] = {}  # neighbour_id → edge_type (first encountered)

    for edge in _edges_from(graph, node_id):
        nbr = edge["to"]
        if nbr not in seen:
            seen[nbr] = edge["type"]

    for edge in _edges_to(graph, node_id):
        nbr = edge["from"]
        if nbr not in seen:
            seen[nbr] = edge["type"]

    neighbours = []
    for nbr_id, etype in seen.items():
        nbr_node = nmap.get(nbr_id)
        if nbr_node:
            neighbours.append({
                "id": nbr_id,
                "type": nbr_node["type"],
                "label": nbr_node["label"],
                "edge_type": etype,
            })

    neighbours.sort(key=lambda n: n["id"])
    return {"node_id": node_id, "found": True, "neighbors": neighbours}


def get_related_nodes(graph: dict, node_id: str) -> dict:
    """Return notes that share a group hub with the given node.

    Traversal (two hops):
        1. Follow all edges from node_id to group nodes
           (member_of edges outbound, or inbound parent edges for group nodes).
        2. From each group node, collect all notes connected via member_of.
        3. Exclude node_id itself.

    Args:
        graph: Output of build_graph().
        node_id: The id of the node to query.

    Returns:
        {
            "node_id": str,
            "found": bool,
            "related": list[dict],  # sorted by id
        }

    Each related entry: {"id": str, "type": str, "label": str, "via": str}
    where "via" is the group node id through which the relationship was found.
    """
    nmap = _node_map(graph)
    if node_id not in nmap:
        return {"node_id": node_id, "found": False, "related": []}

    _GROUP_TYPES = frozenset({"domain", "subdomain", "topic"})

    # Step 1: find group nodes this node connects to via member_of (outbound)
    group_node_ids: list[str] = []
    for edge in _edges_from(graph, node_id):
        if edge["type"] == "member_of":
            target = edge["to"]
            if nmap.get(target, {}).get("type") in _GROUP_TYPES:
                group_node_ids.append(target)

    # Step 2: for each group node, collect all member notes (inbound member_of)
    # id → via group id (keep earliest-sorted group if multiple paths)
    related: dict[str, str] = {}
    for group_id in sorted(group_node_ids):
        for edge in _edges_to(graph, group_id):
            if edge["type"] == "member_of":
                peer_id = edge["from"]
                if peer_id != node_id and peer_id not in related:
                    related[peer_id] = group_id

    result = []
    for peer_id, via in related.items():
        peer_node = nmap.get(peer_id)
        if peer_node:
            result.append({
                "id": peer_id,
                "type": peer_node["type"],
                "label": peer_node["label"],
                "via": via,
            })

    result.sort(key=lambda n: n["id"])
    return {"node_id": node_id, "found": True, "related": result}


def get_missing_neighbors(graph: dict, node_id: str) -> dict:
    """Return expected_concept nodes reachable from this note's group hubs.

    These are concepts that the schema expects to exist near this note's
    domain/subdomain/topic cluster but are not yet present in the vault.

    Traversal:
        1. Follow member_of edges from node_id to group nodes.
        2. From each group node, follow expected_coverage edges to
           expected_concept nodes.

    Args:
        graph: Output of build_graph().
        node_id: The id of the note to query.

    Returns:
        {
            "node_id": str,
            "found": bool,
            "missing": list[dict],  # sorted by id
        }

    Each missing entry:
        {"id": str, "label": str, "via": str}
    where "via" is the group node that declared the expected concept.
    """
    nmap = _node_map(graph)
    if node_id not in nmap:
        return {"node_id": node_id, "found": False, "missing": []}

    _GROUP_TYPES = frozenset({"domain", "subdomain", "topic"})

    # Step 1: group nodes this note belongs to
    group_node_ids: list[str] = []
    for edge in _edges_from(graph, node_id):
        if edge["type"] == "member_of":
            target = edge["to"]
            if nmap.get(target, {}).get("type") in _GROUP_TYPES:
                group_node_ids.append(target)

    # Step 2: expected_concept nodes reachable from those groups
    # id → via group id
    missing: dict[str, str] = {}
    for group_id in sorted(group_node_ids):
        for edge in _edges_from(graph, group_id):
            if edge["type"] == "expected_coverage":
                target = edge["to"]
                if nmap.get(target, {}).get("type") == "expected_concept":
                    if target not in missing:
                        missing[target] = group_id

    result = []
    for concept_id, via in missing.items():
        concept_node = nmap.get(concept_id)
        if concept_node:
            result.append({
                "id": concept_id,
                "label": concept_node["label"],
                "via": via,
            })

    result.sort(key=lambda n: n["id"])
    return {"node_id": node_id, "found": True, "missing": result}
