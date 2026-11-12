"""Testes do pré-cálculo vetorial com log2 e integração ao indexador."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from indexer.indexer import build_index
from indexer.vector import build_vector_index, tf_weight
from search.ranker import VectorRanker


class VectorIndexTests(unittest.TestCase):
    def test_tf_uses_log2(self):
        self.assertEqual(tf_weight(0), 0)
        self.assertEqual(tf_weight(1), 1)
        self.assertEqual(tf_weight(4), 3)

    def test_idf_uses_log2_and_smoothing(self):
        index = {'alpha': {'1': {'name': 1}}, 'beta': {'1': {'text': 1}, '2': {'text': 1}}}
        result = build_vector_index(index, ['1', '2'])
        self.assertAlmostEqual(result['idf']['alpha'], 1 + math.log2(3 / 2))
        self.assertEqual(result['idf']['beta'], 1.0)
        self.assertEqual(result['document_count'], 2)

    def test_norms_match_existing_ranker(self):
        index = {
            'samsung': {'1': {'name': 2, 'brand': 1}, '2': {'text': 1}},
            's25': {'1': {'model': 1}},
            '256gb': {'1': {'storage_gb': 1}, '2': {'name': 1}},
        }
        
        vector = build_vector_index(index, ['1', '2', '3'])
        ranker = VectorRanker(index, ['1', '2', '3'])
        
        for doc_id, norm in vector['document_norms'].items():
            self.assertAlmostEqual(norm, math.sqrt(ranker.norms_squared[doc_id]))
        
        self.assertEqual(vector['document_norms']['3'], 0.0)
        self.assertEqual(vector['field_weights'], ranker.weights)

    def test_indexer_generates_vector_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'processed'
            source.mkdir()
            
            (source / 'sample.json').write_text(json.dumps({'products': [
                {'product_id': 'p1', 'name': 'Samsung S25 256GB', 'attributes': {'brand': 'Samsung'}},
                {'product_id': 'p2', 'name': 'Apple iPhone 256GB', 'attributes': {'brand': 'Apple'}},
            ]}), encoding='utf-8')

            dest = root / 'index'
            stats = build_index(source, dest)
            vector = json.loads((dest / 'vector_index.json').read_text(encoding='utf-8'))
            self.assertEqual(vector['document_count'], 2)
            self.assertEqual(set(vector['document_norms']), {'1', '2'})
            self.assertIn('samsung', vector['idf'])
            self.assertGreater(stats['vector_index_file_bytes'], 0)
            self.assertEqual(
                json.loads((dest / 'statistics.json').read_text())['vector_index_file_bytes'],
                stats['vector_index_file_bytes']
            )

    def test_rejects_invalid_weights(self):
        with self.assertRaises(ValueError):
            build_vector_index({}, [], {'name': -1})


if __name__ == '__main__':
    unittest.main()
