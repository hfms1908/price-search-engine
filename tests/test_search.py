"""Testes unitários da recuperação e integração com o indexador real."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from indexer.indexer import build_index
from search.query import query_terms
from search.retriever import boolean_retrieve
from search.ranker import VectorRanker
from search.search import SearchEngine


class BooleanTests(unittest.TestCase):
    def setUp(self):
        self.index = {'samsung': {'1': {'name': 1}, '2': {'text': 1}},
                      's25': {'1': {'model': 1}},
                      'iphone': {'3': {'name': 1}}}

    def test_and(self):
        self.assertEqual(boolean_retrieve(self.index, ['samsung', 's25']), {'1'})

    def test_or(self):
        self.assertEqual(boolean_retrieve(self.index, ['s25', 'iphone'], 'OR'), {'1', '3'})

    def test_not(self):
        self.assertEqual(boolean_retrieve(self.index, ['samsung'], 'NOT', {'1', '2', '3'}), {'3'})

    def test_unknown_and_empty(self):
        self.assertEqual(boolean_retrieve(self.index, ['unknown'], 'OR'), set())
        self.assertEqual(boolean_retrieve(self.index, [], 'NOT', {'1'}), set())

    def test_invalid_operator_and_not_without_universe(self):
        with self.assertRaises(ValueError):
            boolean_retrieve(self.index, ['s25'], 'XOR')
        with self.assertRaises(ValueError):
            boolean_retrieve(self.index, ['s25'], 'NOT')


class VectorTests(unittest.TestCase):
    def test_weighted_tf(self):
        ranker = VectorRanker({}, [], field_weights={
            'model': 5, 'name': 4, 'storage_gb': 3,
            'ram_gb': 3, 'brand': 2, 'text': 1,
        })
        fields = {'name': 2, 'brand': 1, 'text': 3}
        expected = 4 * (1 + math.log2(2)) + 2 + (1 + math.log2(3))
        self.assertAlmostEqual(ranker._weighted_tf(fields), expected)
        self.assertEqual(ranker._weighted_tf({}), 0.0)
        self.assertEqual(ranker._weighted_tf({'name': 0, 'text': -1}), 0.0)
    
    def test_weights_prioritize_model(self):
        index = {'s25': {'1': {'model': 1}, '2': {'text': 1}},
                 'galaxy': {'1': {'model': 1}, '2': {'text': 1}},
                 'outro': {'2': {'text': 1}}}
        ranker = VectorRanker(index, {'1', '2'})
        result = ranker.rank(['s25', 'galaxy'], {'1', '2'})
        self.assertEqual(result[0][0], '1')
        self.assertTrue(all(0 < score <= 1 for _, score in result))

    def test_idf_smoothing_and_query_frequency(self):
        ranker = VectorRanker({'s25': {'1': {'name': 1}},
                               'galaxy': {'1': {'name': 1}, '2': {'name': 1}}}, {'1', '2'})
        self.assertAlmostEqual(ranker.idf['s25'], math.log2(3 / 2) + 1)
        self.assertEqual(ranker.rank(['missing'], {'1', '2'}), [])
        self.assertTrue(ranker.rank(['s25', 's25'], {'1'}))

    def test_weight_configuration(self):
        with self.assertRaises(ValueError):
            VectorRanker({}, [], {'name': -1})


class SearchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        source = root / 'processed'
        source.mkdir()
        self.index_dir = root / 'index'
        data = {'document_id': 'documento', 'collected_at': '2026-11-11', 'products': [
            {'product_id': 'p1', 'name': 'Samsung Galaxy S25 256GB', 'category': 'smartphone',
             'url': 'https://loja.test/s25', 'text': 'Galaxy S25',
             'attributes': {'brand': 'Samsung', 'model': 'Galaxy S25', 'ram_gb': 8,
                            'storage_gb': 256, 'price_brl': 3500}},
            {'product_id': 'p2', 'name': 'Samsung Galaxy A55 128GB', 'category': 'smartphone',
             'url': 'https://loja.test/a55', 'text': 'Samsung Galaxy A55',
             'attributes': {'brand': 'Samsung', 'model': 'Galaxy A55', 'storage_gb': 128}},
            {'product_id': 'p3', 'name': 'Apple iPhone 16 256GB', 'category': 'smartphone',
             'url': 'https://loja.test/iphone', 'text': 'Apple iPhone 16',
             'attributes': {'brand': 'Apple', 'model': 'iPhone 16', 'storage_gb': 256}},
        ]}
        (source / 'documento.json').write_text(json.dumps(data), encoding='utf-8')
        build_index(source, self.index_dir)
        self.engine = SearchEngine(self.index_dir)

    def test_query_uses_same_tokenizer(self):
        self.assertEqual(query_terms('Samsung Galaxy S25 256 GB'),
                         ['samsung', 'galaxy', 's25', '256gb'])

    def test_and_and_metadata(self):
        results = self.engine.search('Samsung S25 256GB', operator='AND')
        self.assertEqual([r['product_id'] for r in results], ['p1'])
        self.assertEqual(results[0]['source_file'], 'documento.json')
        self.assertEqual(results[0]['attributes']['price_brl'], 3500)

    def test_or_vector(self):
        results = self.engine.search('Samsung Galaxy S25 256GB')
        self.assertEqual(results[0]['product_id'], 'p1')
        self.assertTrue(all(results[i]['score'] >= results[i + 1]['score']
                            for i in range(len(results) - 1)))

    def test_boolean_not(self):
        results = self.engine.search('Samsung', operator='NOT', ranking='boolean')
        self.assertEqual([r['product_id'] for r in results], ['p3'])
        self.assertIsNone(results[0]['score'])

    def test_limit_and_missing(self):
        self.assertEqual(len(self.engine.search('galaxy', limit=1)), 1)
        self.assertEqual(self.engine.search('produto_inexistente'), [])
        self.assertEqual(self.engine.search('galaxy', limit=0), [])

    def test_invalid_combinations(self):
        with self.assertRaises(ValueError):
            self.engine.search('samsung', operator='NOT')
        with self.assertRaises(ValueError):
            self.engine.search('samsung', limit=-1)

    def test_mismatched_files(self):
        (self.index_dir / 'document_map.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'não correspondem'):
            SearchEngine(self.index_dir)


if __name__ == '__main__':
    unittest.main()
