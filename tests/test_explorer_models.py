from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from explorer_models import build_detail_window, build_source_summary


def test_detail_window_keeps_core_then_bridge_then_relevance():
    nodes = [
        {"id": "core", "importance": 9, "bridge_score": 0, "relevance": 0},
        {"id": "bridge", "importance": 1, "bridge_score": 8, "relevance": 0},
        {"id": "search", "importance": 1, "bridge_score": 0, "relevance": 7},
    ] + [
        {"id": f"n{index}", "importance": 0, "bridge_score": 0, "relevance": 0}
        for index in range(100)
    ]

    window = build_detail_window(nodes, limit=80)

    assert window["visible_count"] == 80
    assert [node["id"] for node in window["nodes"][:3]] == ["core", "bridge", "search"]
    assert window["total_count"] == 103


def test_source_summary_counts_unique_pages_and_representatives():
    summary = build_source_summary(
        "paper-1",
        "paper.pdf",
        [
            {"name": "A", "importance": 6, "evidence": [{"page": 1}]},
            {"name": "B", "importance": 5, "evidence": [{"page": 1}, {"page": 2}]},
        ],
    )

    assert summary["source_id"] == "paper-1"
    assert summary["entity_count"] == 2
    assert summary["page_count"] == 2
    assert [item["name"] for item in summary["representatives"]] == ["A", "B"]
