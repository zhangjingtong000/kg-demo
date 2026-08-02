from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from graph_store import NetworkXStore
from kg_extractor import deduplicate_entities


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
