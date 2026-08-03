import unittest

from kg_extractor import (
    ENTITY_TYPES,
    LOCAL_ENTITY_PROMPT,
    LOCAL_RELATION_PROMPT,
    RELATION_TYPES,
    build_entity_response_schema,
    build_relation_response_schema,
    build_local_json_payload,
    decode_local_json_response,
    parse_structured_entities,
    parse_structured_relations,
    deduplicate_entities,
    retain_relations_with_known_endpoints,
)


class LocalStructuredExtractionTests(unittest.TestCase):
    def test_default_ontology_is_domain_neutral(self):
        self.assertIn("Concept", ENTITY_TYPES)
        self.assertIn("Method", ENTITY_TYPES)
        self.assertIn("Document", ENTITY_TYPES)
        self.assertNotIn("Exercise", ENTITY_TYPES)
        self.assertNotIn("Muscle", ENTITY_TYPES)
        self.assertIn("CITES", RELATION_TYPES)
        self.assertIn("EVALUATES", RELATION_TYPES)

    def test_local_entity_payload_requires_json_schema_and_bounded_output(self):
        payload = build_local_json_payload(
            model="qwen3.5:9b",
            prompt="Extract entities from this text.",
            schema=build_entity_response_schema(),
        )

        self.assertEqual(payload["model"], "qwen3.5:9b")
        self.assertEqual(payload["format"]["type"], "object")
        self.assertEqual(payload["options"]["temperature"], 0)
        self.assertLessEqual(payload["options"]["num_predict"], 512)
        self.assertFalse(payload["think"])

    def test_local_payload_can_omit_schema_for_compatible_json_mode(self):
        payload = build_local_json_payload(
            model="qwen3.5:9b", prompt="Return JSON.", schema=None,
        )

        self.assertNotIn("format", payload)

    def test_decoder_accepts_json_wrapped_in_a_markdown_fence(self):
        raw = '```json\n{"entities": [{"name": "Encoder"}]}\n```'

        self.assertEqual(
            decode_local_json_response(raw),
            {"entities": [{"name": "Encoder"}]},
        )

    def test_local_prompts_format_without_interpreting_json_examples(self):
        self.assertIn(
            '"entities"',
            LOCAL_ENTITY_PROMPT.format(entity_types="Concept", text="Encoder"),
        )

    def test_deduplication_keeps_distinct_technical_terms(self):
        entities = [
            {"name": "Encoder", "type": "Component", "description": ""},
            {"name": "Decoder", "type": "Component", "description": ""},
            {"name": "Sequential", "type": "Component", "description": ""},
            {"name": "Convolutional", "type": "Component", "description": ""},
        ]

        self.assertEqual(
            [entity["name"] for entity in deduplicate_entities(entities)],
            ["Encoder", "Decoder", "Sequential", "Convolutional"],
        )

    def test_relation_pruner_drops_edges_with_unknown_or_combined_endpoints(self):
        relations = [
            {"source": "Encoder", "target": "Attention", "type": "USES", "description": ""},
            {"source": "Encoder", "target": "Feed Forward", "type": "USES", "description": ""},
            {"source": "Transformer", "target": "Dataset A, Dataset B", "type": "APPLIES_TO", "description": ""},
        ]

        self.assertEqual(
            retain_relations_with_known_endpoints(relations, ["Encoder", "Feed Forward", "Transformer"]),
            [{"source": "Encoder", "target": "Feed Forward", "type": "USES", "description": ""}],
        )
        self.assertIn(
            '"relations"',
            LOCAL_RELATION_PROMPT.format(
                entity_list="- Encoder", relation_types="PART_OF", text="Encoder stack",
            ),
        )

    def test_structured_entities_keep_only_valid_domain_types(self):
        raw = {
            "entities": [
                {"name": "Encoder", "type": "Concept", "description": "The encoder stack."},
                {"name": "Figure 2", "type": "Document", "description": "A visual reference."},
                {"name": "Prompt rule", "type": "EntityName", "description": "Not a domain entity."},
            ]
        }

        self.assertEqual(
            parse_structured_entities(raw),
            [{"name": "Encoder", "type": "Concept", "description": "The encoder stack."}],
        )

    def test_structured_relations_keep_only_valid_domain_types(self):
        raw = {
            "relations": [
                {
                    "source": "Encoder",
                    "target": "Decoder",
                    "type": "RELATED_TO",
                    "description": "They form the architecture.",
                },
                {
                    "source": "Prompt rule",
                    "target": "EntityName",
                    "type": "TargetEntity",
                    "description": "A leaked prompt fragment.",
                },
            ]
        }

        self.assertEqual(build_relation_response_schema()["type"], "object")
        self.assertEqual(
            parse_structured_relations(raw),
            [{
                "source": "Encoder",
                "target": "Decoder",
                "type": "RELATED_TO",
                "description": "They form the architecture.",
            }],
        )


if __name__ == "__main__":
    unittest.main()
