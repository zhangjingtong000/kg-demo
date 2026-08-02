import unittest

from kg_extractor import (
    build_entity_response_schema,
    build_relation_response_schema,
    build_local_json_payload,
    parse_structured_entities,
    parse_structured_relations,
)


class LocalStructuredExtractionTests(unittest.TestCase):
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

    def test_structured_entities_keep_only_valid_domain_types(self):
        raw = {
            "entities": [
                {"name": "Encoder", "type": "Concept", "description": "The encoder stack."},
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
