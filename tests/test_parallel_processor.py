"""Verifica equivalência entre processamento sequencial e paralelo."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from processor.processor import process_documents, worker_count


class ParallelProcessorTests(unittest.TestCase):
    def test_default_workers(self):
        with patch('processor.processor.physical_cores', return_value=4):
            with patch('processor.processor.MAX_WORKERS', None):
                self.assertEqual(worker_count(), 3)
        with patch('processor.processor.physical_cores', return_value=1):
            with patch('processor.processor.MAX_WORKERS', None):
                self.assertEqual(worker_count(), 1)

    def test_invalid_workers(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                worker_count(value)

    def test_parallel_equals_sequential(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / 'raw'
            raw.mkdir()
            for i in range(3):
                document_id = f'doc{i}'
                html_file = f'{document_id}.html'
                (raw / html_file).write_text('''<html><head><title>Smartphone Samsung Galaxy S25 8GB 256GB</title></head><body><script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"Smartphone Samsung Galaxy S25 8GB 256GB","offers":{"@type":"Offer","price":"2999.90","priceCurrency":"BRL"}}</script></body></html>''', encoding='utf-8')
                (raw / f'{document_id}.json').write_text(json.dumps({'document_id': document_id, 'html_file': html_file, 'url': f'https://example.com/produto/{i}', 'collected_at': '2026-10-17'}), encoding='utf-8')
            single = root / 'single'
            parallel = root / 'parallel'
            a = process_documents(raw, single, workers=1)
            b = process_documents(raw, parallel, workers=2)
            for key in ('read', 'processed', 'products', 'skipped', 'irrelevant', 'errors'):
                self.assertEqual(a[key], b[key], key)
            self.assertEqual(sorted(p.name for p in single.glob('*.json')), sorted(p.name for p in parallel.glob('*.json')))
            for path in single.glob('*.json'):
                self.assertEqual(json.loads(path.read_text()), json.loads((parallel / path.name).read_text()))


if __name__ == '__main__':
    unittest.main()
