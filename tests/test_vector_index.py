"""Testes do pré-cálculo vetorial com log2 e integração ao indexador."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from indexer.indexer import build_index
from indexer.vector import build_vector_index, tf_weight
from search.ranker import VectorRanker
from search.search import SearchEngine


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

    def test_precomputed_rank_matches_runtime_calculation(self):
        index = {
            'samsung': {'1': {'name': 2}, '2': {'text': 1}},
            'galaxy': {'1': {'model': 1}, '2': {'name': 1}},
            'outro': {'3': {'text': 1}},
        }
        
        ids = ['1', '2', '3', '4']
        vector = build_vector_index(index, ids)
        cached = VectorRanker(index, ids, vector_index=vector)
        calculated = VectorRanker(index, ids)
        self.assertEqual(cached.idf, calculated.idf)
        
        for doc_id in ids:
            self.assertAlmostEqual(cached.norms_squared[doc_id], calculated.norms_squared[doc_id])
        
        for query in (['samsung'], ['samsung', 'galaxy'], ['galaxy', 'galaxy']):
            actual = cached.rank(query, ids)
            expected = calculated.rank(query, ids)
            self.assertEqual([doc for doc, _ in actual], [doc for doc, _ in expected])
            
            for (_, score_a), (_, score_b) in zip(actual, expected):
                self.assertAlmostEqual(score_a, score_b)

    def test_precomputed_skips_runtime_recalculation(self):
        from unittest.mock import patch
        
        index = {'s25': {'1': {'model': 1}}}
        vector = build_vector_index(index, ['1'])
        
        with patch.object(VectorRanker, '_calculate_vectors', side_effect=AssertionError('recalculou')):
            ranker = VectorRanker(index, ['1'], vector_index=vector)
        
        self.assertEqual(ranker.rank(['s25'], ['1'])[0][0], '1')

    def test_rejects_incompatible_precomputed_index(self):
        index = {'s25': {'1': {'model': 1}}}
        vector = build_vector_index(index, ['1'])
        for key, value in (
            ('format_version', 999),
            ('field_weights', {'name': 1}),
            ('document_count', 2),
            ('idf', {'other': 1.0}),
            ('document_norms', {'2': 1.0}),
        ):
            invalid = {**vector, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                VectorRanker(index, ['1'], vector_index=invalid)

    def test_search_engine_loads_precomputed_and_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'processed'
            source.mkdir()
            (source / 'sample.json').write_text(json.dumps({'products': [
                {'product_id': 'p1', 'name': 'Samsung Galaxy S25', 'attributes': {'brand': 'Samsung'}},
                {'product_id': 'p2', 'name': 'Apple iPhone', 'attributes': {'brand': 'Apple'}},
            ]}), encoding='utf-8')
            
            dest = root / 'index'
            build_index(source, dest)
            
            with self.subTest(mode='precomputed'):
                from unittest.mock import patch
                
                with patch.object(VectorRanker, '_calculate_vectors', side_effect=AssertionError('recalculou')):
                    engine = SearchEngine(dest)
                
                expected = engine.search('Samsung Galaxy')
            
            (dest / 'vector_index.json').unlink()
            
            with self.subTest(mode='legacy'):
                engine = SearchEngine(dest)
                self.assertEqual(engine.search('Samsung Galaxy'), expected)

    def test_rejects_invalid_weights(self):
        with self.assertRaises(ValueError):
            build_vector_index({}, [], {'name': -1})


if __name__ == '__main__':
    unittest.main()
