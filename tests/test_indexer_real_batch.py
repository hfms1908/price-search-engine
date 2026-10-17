"""Regressão do índice com o lote real de JSONs processados (arquivo fornecido)."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from indexer.indexer import build_index
from indexer.tokenizer import tokenize

FIXTURE = Path(__file__).parent / 'fixtures' / 'processed_batch.zip'


class RealProcessedBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.processed = cls.root / 'processed'
        cls.processed.mkdir()
        with zipfile.ZipFile(FIXTURE) as archive:
            for member in archive.infolist():
                if member.filename.endswith('.json') and not member.is_dir():
                    # Extrair apenas o nome do arquivo, sem confiar em caminhos do ZIP.
                    target = cls.processed / Path(member.filename).name
                    if target.exists():
                        raise ValueError('Nome de arquivo duplicado no lote')
                    target.write_bytes(archive.read(member))
        cls.index_dir = cls.root / 'index'
        cls.stats = build_index(cls.processed, cls.index_dir)
        cls.index = json.loads((cls.index_dir / 'inverted_index.json').read_text(encoding='utf-8'))
        cls.products = json.loads((cls.index_dir / 'products.json').read_text(encoding='utf-8'))
        cls.document_map = json.loads((cls.index_dir / 'document_map.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_total_real_files_and_products(self):
        self.assertEqual(self.stats['documents_read'], 71)
        self.assertEqual(self.stats['products_indexed'], 344)
        self.assertEqual(len(self.products), 344)
        self.assertEqual(len(self.document_map), 344)
        self.assertEqual(set(self.products), set(self.document_map))
        self.assertEqual(len({v['product_id'] for v in self.document_map.values()}), 344)
        self.assertTrue(all(v['source_file'].endswith('.json') for v in self.document_map.values()))

    def test_all_postings_reference_existing_products(self):
        for term, posting in self.index.items():
            self.assertTrue(posting, term)
            for product_id, fields in posting.items():
                self.assertIn(product_id, self.products)
                self.assertTrue(fields)
                self.assertTrue(all(isinstance(v, int) and v > 0 for v in fields.values()))

    def test_attribute_completeness_matches_real_batch(self):
        self.assertEqual(self.stats['missing_attributes'], {
            'brand': 0, 'model': 52, 'ram_gb': 129,
            'storage_gb': 45, 'price_brl': 62,
        })
        self.assertEqual(self.stats['products_by_extraction_source'], {
            'html_card': 153, 'json_ld': 191,
        })

    def test_capacities_are_indexed_from_structured_attributes(self):
        for pid, product in self.products.items():
            attrs = product['attributes']
            for field in ('ram_gb', 'storage_gb'):
                value = attrs.get(field)
                if value is not None and float(value) > 0:
                    term = f'{float(value):g}gb'
                    self.assertEqual(self.index[term][pid][field], 1)

    def test_real_product_name_model_and_price(self):
        matches = [(pid, p) for pid, p in self.products.items()
                   if p.get('name', '').startswith('Celular Samsung Galaxy A57 5G 256gb 8gb Ram')]
        self.assertTrue(matches)
        pid, product = matches[0]
        self.assertEqual(product['attributes']['brand'], 'Samsung')
        self.assertEqual(product['attributes']['model'], 'Galaxy A57')
        self.assertEqual(product['attributes']['price_brl'], 2299.9)
        for term in ('samsung', 'a57', '8gb', '256gb'):
            self.assertIn(pid, self.index[term])

    def test_output_statistics_persisted(self):
        persisted = json.loads((self.index_dir / 'statistics.json').read_text(encoding='utf-8'))
        self.assertEqual(persisted, self.stats)
        self.assertGreater(persisted['index_file_bytes'], 0)

    def test_rebuild_is_deterministic(self):
        other = self.root / 'index2'
        stats2 = build_index(self.processed, other)
        self.assertEqual(stats2['products_indexed'], self.stats['products_indexed'])
        for filename in ('inverted_index.json', 'products.json', 'document_map.json'):
            self.assertEqual((self.index_dir / filename).read_bytes(), (other / filename).read_bytes())


if __name__ == '__main__':
    unittest.main()
