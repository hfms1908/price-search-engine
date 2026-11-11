"""Testes de regressão com amostra REAL extraída de index.zip.

A amostra contém 21 produtos e TODAS as listas invertidas que fazem referência
àqueles doc_id. Os IDs, frequências, atributos e URLs não foram sintetizados.
Os resultados avaliam a recuperação, não a qualidade da extração original.
"""
import json
import math
import tempfile
import unittest
from pathlib import Path
from shutil import copyfile

from search.query import query_terms
from search.retriever import boolean_retrieve
from search.ranker import VectorRanker
from search.search import SearchEngine

FIXTURE = Path(__file__).parent / 'fixtures' / 'real_index_sample'


class RealIndexSampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        for name in ('inverted_index.json', 'document_map.json', 'products.json'):
            copyfile(FIXTURE / name, cls.directory / name)
        cls.engine = SearchEngine(cls.directory)
        cls.index = cls.engine.inverted_index
        cls.products = cls.engine.products
        cls.ids = set(cls.products)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_fixture_is_faithful_and_coherent(self):
        self.assertEqual(len(self.ids), 21)
        self.assertEqual(set(self.engine.document_map), self.ids)
        self.assertTrue(all(set(postings) <= self.ids for postings in self.index.values()))
        self.assertEqual(self.products['129']['attributes']['storage_gb'], 256.0)
        self.assertEqual(self.products['131']['attributes']['storage_gb'], 512.0)
        self.assertEqual(self.products['35']['attributes']['price_brl'], None)

    def test_real_postings_match_original_products(self):
        self.assertIn('129', self.index['s25'])
        self.assertIn('131', self.index['s25'])
        self.assertIn('202', self.index['s25'])
        self.assertIn('3', self.index['256gb'])
        self.assertNotIn('3', self.index['128gb'])
        self.assertTrue(all(freq > 0 for postings in self.index.values()
                            for fields in postings.values() for freq in fields.values()))

    def test_and_exact_posting_intersection(self):
        terms = query_terms('Samsung Galaxy S25 256GB')
        expected = set.intersection(*(set(self.index.get(t, {})) for t in terms))
        actual = boolean_retrieve(self.index, terms, 'AND')
        self.assertEqual(actual, expected)
        self.assertIn('129', actual)
        self.assertIn('202', actual)
        self.assertNotIn('131', actual)  # 512 GB

    def test_or_union_includes_distinct_brands(self):
        terms = query_terms('Motorola iPhone')
        expected = set.union(*(set(self.index.get(t, {})) for t in terms))
        self.assertEqual(boolean_retrieve(self.index, terms, 'OR'), expected)
        self.assertIn('56', expected)
        self.assertIn('1', expected)

    def test_not_complement_of_union(self):
        terms = query_terms('Samsung')
        excluded = set(self.index.get('samsung', {}))
        self.assertEqual(boolean_retrieve(self.index, terms, 'NOT', self.ids), self.ids - excluded)

    def test_unknown_term_and_zero_matches(self):
        self.assertEqual(self.engine.search('zzzinexistente987xyz'), [])
        self.assertEqual(self.engine.search('zzzinexistente987xyz', operator='AND'), [])
        self.assertEqual(self.engine.search('Samsung zzzinexistente987xyz', operator='AND'), [])

    def test_query_normalization_preserves_product_identifiers(self):
        self.assertEqual(query_terms('SAMSUNG Galaxy S25 256 GB'), ['samsung','galaxy','s25','256gb'])
        self.assertEqual(query_terms('Moto G35 5G'), ['moto','g35','5g'])

    def test_vector_scores_are_finite_bounded_and_sorted(self):
        results = self.engine.search('Samsung Galaxy S25 256GB', limit=21)
        self.assertTrue(results)
        self.assertTrue(all(math.isfinite(r['score']) and 0 < r['score'] <= 1 for r in results))
        self.assertEqual([r['score'] for r in results], sorted((r['score'] for r in results), reverse=True))

    def test_and_vector_has_same_candidates_as_boolean(self):
        query = 'Samsung Galaxy S25 256GB'
        boolean = self.engine.search(query, operator='AND', ranking='boolean', limit=21)
        vector = self.engine.search(query, operator='AND', ranking='vector', limit=21)
        self.assertEqual({r['doc_id'] for r in boolean}, {r['doc_id'] for r in vector})

    def test_repeated_terms_and_idf_smoothing(self):
        ranker = VectorRanker(self.index, self.ids)
        term = 's25'
        df = len(self.index[term])
        self.assertAlmostEqual(ranker.idf[term], math.log2((len(self.ids)+1)/(df+1))+1)
        single = ranker.rank(['s25'], self.ids)
        repeated = ranker.rank(['s25', 's25'], self.ids)
        self.assertEqual([x[0] for x in single], [x[0] for x in repeated])
        self.assertTrue(all(abs(a[1]-b[1]) < 1e-12 for a,b in zip(single,repeated)))

    def test_result_preserves_real_metadata(self):
        result = next(r for r in self.engine.search('iPhone 16 Plus 256GB',limit=21)
                      if r['doc_id'] == '3')
        self.assertEqual(result['product_id'], self.engine.document_map['3']['product_id'])
        self.assertEqual(result['source_file'], self.engine.document_map['3']['source_file'])
        self.assertEqual(result['name'], self.products['3']['name'])
        self.assertEqual(result['url'], self.products['3']['url'])
        self.assertEqual(result['attributes']['price_brl'], 7299.1)

    def test_missing_attributes_are_preserved(self):
        result = next(r for r in self.engine.search('Tcl Tab 11', limit=21)
                      if r['doc_id'] == '35')
        self.assertIsNone(result['attributes']['model'])
        self.assertIsNone(result['attributes']['price_brl'])
        self.assertEqual(result['category'], 'tablet')

    def test_no_implicit_category_filter_or_data_repair(self):
        # O índice original contém um carregador: a busca não deve inventar uma
        # categoria ou reclassificar a oferta durante a recuperação.
        results = self.engine.search('Carregador Moto G54',limit=21)
        match = next(r for r in results if r['doc_id'] == '1295')
        self.assertEqual(match['name'], self.products['1295']['name'])
        self.assertEqual(match['category'], self.products['1295']['category'])
        self.assertIsNone(match['attributes']['brand'])

    def test_limit_and_boolean_order(self):
        all_results = self.engine.search('Galaxy', ranking='boolean', limit=21)
        self.assertEqual([r['doc_id'] for r in all_results],
                         sorted((r['doc_id'] for r in all_results), key=int))
        self.assertEqual(self.engine.search('Galaxy', ranking='boolean', limit=2), all_results[:2])
        self.assertTrue(all(r['score'] is None for r in all_results))

    def test_mismatched_index_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            for name in ('inverted_index.json', 'document_map.json', 'products.json'):
                copyfile(FIXTURE/name,target/name)
            path=target/'inverted_index.json'
            broken=json.loads(path.read_text(encoding='utf-8'))
            broken['s25']['99999999']={'name':1}
            path.write_text(json.dumps(broken),encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'desconhecido'):
                SearchEngine(target)


if __name__ == '__main__':
    unittest.main()
