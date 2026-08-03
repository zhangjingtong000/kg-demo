import unittest

from pdf_parser import chunk_document, is_usable_table_data, table_to_text


class PdfTableChunkingTests(unittest.TestCase):
    def test_table_serialization_preserves_headers_and_rows(self):
        table = {
            "page": 1,
            "table_idx": 1,
            "rows": 2,
            "data": [["Model", "BLEU"], ["Transformer", "28.4"]],
        }

        self.assertEqual(
            table_to_text(table),
            "Table 1\nModel | BLEU\nTransformer | 28.4",
        )

    def test_chunk_document_emits_a_separate_table_chunk(self):
        parsed = {
            "file": "sample.pdf",
            "total_pages": 1,
            "pages": [{"num": 1, "text": "A short introduction.", "images": []}],
            "tables": [{
                "page": 1,
                "table_idx": 1,
                "rows": 2,
                "data": [["Model", "BLEU"], ["Transformer", "28.4"]],
            }],
        }

        chunked = chunk_document(parsed, max_chars=500)
        table_chunks = [chunk for chunk in chunked["chunks"] if chunk["kind"] == "table"]

        self.assertEqual(len(table_chunks), 1)
        self.assertEqual(table_chunks[0]["page"], 1)
        self.assertIn("Transformer | 28.4", table_chunks[0]["text"])

    def test_layout_noise_with_too_many_columns_is_not_a_usable_table(self):
        noisy_rows = [["x"] * 20, ["y"] * 20]

        self.assertFalse(is_usable_table_data(noisy_rows))
        self.assertTrue(is_usable_table_data([["Model", "BLEU"], ["Transformer", "28.4"]]))


if __name__ == "__main__":
    unittest.main()
