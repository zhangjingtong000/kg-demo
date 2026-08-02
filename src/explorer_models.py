"""Pure view-model helpers for multiscale knowledge-graph exploration."""


def score_node(node: dict) -> tuple[float, float, float, str]:
    """Rank the recommended detailed view deterministically."""
    return (
        -float(node.get("importance", 0)),
        -float(node.get("bridge_score", 0)),
        -float(node.get("relevance", 0)),
        str(node["id"]),
    )


def build_detail_window(nodes: list[dict], limit: int = 80) -> dict:
    """Return a bounded, explainable reading window without discarding totals."""
    ranked = sorted(nodes, key=score_node)
    return {
        "nodes": ranked[:limit],
        "visible_count": min(len(ranked), limit),
        "total_count": len(ranked),
    }


def build_source_summary(source_id: str, source_name: str, nodes: list[dict]) -> dict:
    """Build the compact source summary used by the source exploration view."""
    pages = {
        reference["page"]
        for node in nodes
        for reference in node.get("evidence", [])
        if reference.get("page") is not None
    }
    representatives = sorted(
        nodes,
        key=lambda node: (-float(node.get("importance", 0)), node["name"]),
    )[:3]
    return {
        "source_id": source_id,
        "source_name": source_name,
        "entity_count": len(nodes),
        "page_count": len(pages),
        "representatives": representatives,
    }
