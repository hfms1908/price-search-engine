"""Testes de indexação textual e por oferta."""
import json
import tempfile
import unittest
from pathlib import Path
from indexer.tokenizer import tokenize
from indexer.indexer import build_index

class TokenizerTests(unittest.TestCase):
    def test_identificadores_e_capacidades(self):
        tokens = tokenize('Samsung Galaxy S25 8/GB 256 GB 5G SM-G781B/DS')
        for term in ('samsung', 's25', '8gb', '256gb', '5g', 'sm-g781b'):
            self.assertIn(term, tokens)
    def test_fractional_capacity_remains_one_token(self):
        self.assertIn('0.062gb', tokenize('0.062gb'))
        self.assertIn('1.5gb', tokenize('1,5 GB'))

    def test_stopwords_and_accents(self):
        self.assertEqual(tokenize('Câmera de smartphone com 128 GB'), ['camera', 'smartphone', '128gb'])

class IndexTests(unittest.TestCase):
    def test_two_products_one_document(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source=root/'processed'; dest=root/'index'; source.mkdir()
            data={'document_id':'doc1','url':'https://loja.test', 'products':[
                {'product_id':'p1','name':'Samsung Galaxy S25 8 GB 256GB', 'category':'smartphone', 'text':'Samsung Galaxy S25', 'attributes':{'brand':'Samsung','model':'Galaxy S25','ram_gb':8,'storage_gb':256,'price_brl':3500}},
                {'product_id':'p2','name':'Apple iPhone 17 256GB', 'category':'smartphone','text':'Apple iPhone 17','attributes':{'brand':'Apple','model':'iPhone 17','ram_gb':None,'storage_gb':256,'price_brl':5000}},
            ]}
            (source/'doc1.json').write_text(json.dumps(data),encoding='utf-8')
            stats=build_index(source,dest)
            idx=json.loads((dest/'inverted_index.json').read_text())
            products=json.loads((dest/'products.json').read_text())
            self.assertEqual(stats['products_indexed'],2)
            self.assertEqual(stats['documents_read'],1)
            docmap=json.loads((dest/'document_map.json').read_text())
            self.assertEqual(docmap, {'1': {'product_id':'p1','source_file':'doc1.json'}, '2': {'product_id':'p2','source_file':'doc1.json'}})
            self.assertEqual(set(idx['256gb']),{'1','2'})
            self.assertEqual(idx['samsung']['1']['brand'],1)
            self.assertEqual(idx['8gb']['1']['ram_gb'],1)
            self.assertNotIn('2',idx['8gb'])
            self.assertEqual(products['2']['attributes']['price_brl'],5000)
            self.assertEqual(products['1']['document_id'],'doc1')
            self.assertTrue((dest/'statistics.json').exists())
    def test_natural_order_for_numeric_document_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'processed'
            source.mkdir()
            data = {'products': [
                {'product_id': f'p{i}', 'name': 'Samsung Galaxy S25'}
                for i in range(1, 13)
            ]}
            (source / 'batch.json').write_text(json.dumps(data), encoding='utf-8')
            dest = root / 'index'
            build_index(source, dest)
            expected = [str(i) for i in range(1, 13)]
            for filename in ('document_map.json', 'products.json'):
                content = json.loads((dest / filename).read_text(encoding='utf-8'))
                self.assertEqual(list(content), expected)
            inverted = json.loads((dest / 'inverted_index.json').read_text(encoding='utf-8'))
            self.assertEqual(list(inverted['samsung']), expected)

    def test_duplicate_product_id_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/'processed'; source.mkdir()
            for name in ('a','b'):
                (source/f'{name}.json').write_text(json.dumps({'products':[{'product_id':'p1'}]}))
            with self.assertRaisesRegex(ValueError,'duplicado'):
                build_index(source,root/'index')

if __name__ == '__main__': unittest.main()
