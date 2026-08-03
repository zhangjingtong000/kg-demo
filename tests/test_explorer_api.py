from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from graph_store import NetworkXStore, separate_structural_twins
from kg_extractor import deduplicate_entities
from fastapi.testclient import TestClient
from app import app, graphs


client = TestClient(app)


def test_structural_twins_get_a_symmetric_minimum_separation():
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_edges_from([
        ("Source", "Twin A"), ("Source", "Twin B"),
        ("Twin A", "Target"), ("Twin B", "Target"),
    ])
    positions = {node: [0.0, 0.0, 0.0] for node in graph.nodes}

    separate_structural_twins(graph, positions)

    assert positions["Twin A"] != positions["Twin B"]
    distance_squared = sum(
        (positions["Twin A"][axis] - positions["Twin B"][axis]) ** 2
        for axis in range(3)
    )
    assert distance_squared >= 0.32 ** 2


def test_import_data_merges_node_and_edge_evidence():
    store = NetworkXStore()
    evidence = {"source_id": "g1", "page": 3, "chunk_idx": 2}
    store.import_data(
        [{"name": "Squat", "evidence": [evidence]}, {"name": "Quadriceps"}],
        [
            {
                "source": "Squat",
                "target": "Quadriceps",
                "type": "TRAINS",
                "evidence": [evidence],
            }
        ],
    )

    node = next(item for item in store.query_nodes() if item["name"] == "Squat")
    edge = store.query_edges()[0]

    assert node["evidence"] == [evidence]
    assert edge["evidence"] == [evidence]


def test_entity_deduplication_keeps_every_chunk_reference():
    entities = deduplicate_entities(
        [
            {"name": "Squat", "type": "Exercise", "description": "A", "evidence": [{"page": 1}]},
            {"name": "squat", "type": "Exercise", "description": "Longer", "evidence": [{"page": 2}]},
        ]
    )

    assert len(entities) == 1
    assert entities[0]["description"] == "Longer"
    assert entities[0]["evidence"] == [{"page": 1}, {"page": 2}]


def test_explorer_endpoint_exposes_source_summary_and_80_node_window():
    graph_id = "explorer-test"
    graphs[graph_id] = {
        "id": graph_id,
        "source": {"id": graph_id, "name": "fixture.pdf", "kind": "pdf"},
        "nodes": [
            {"name": f"Entity {index}", "evidence": [{"page": 1}]}
            for index in range(81)
        ],
        "edges": [
            {"source": "Entity 0", "target": f"Entity {index}"}
            for index in range(1, 81)
        ],
    }

    response = client.get(f"/graph/{graph_id}/explorer?limit=80")

    assert response.status_code == 200
    body = response.json()
    assert body["detail_window"]["visible_count"] == 80
    assert body["detail_window"]["total_count"] == 81
    assert body["sources"][0]["source_id"] == graph_id
