"""Regressão opcional com os 100 HTMLs reais do usuário.

Executar: RAW_TEST_ZIP=/caminho/raw.zip python -m unittest discover -s tests -v
Sem a variável, os testes de lote são ignorados (não incluir HTMLs pessoais no código).
"""
import json
import os
import unittest
import zipfile
from pathlib import PurePosixPath
from processor.products import extract_products
from processor.extractor import extract_attributes

class RealBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zip_path = os.environ.get('RAW_TEST_ZIP')
        if not cls.zip_path or not os.path.isfile(cls.zip_path):
            raise unittest.SkipTest('Defina RAW_TEST_ZIP para testar os 100 HTMLs reais')

    def test_all_100_files_and_known_examples(self):
        total=0
        results={}
        with zipfile.ZipFile(self.zip_path) as z:
            metas=sorted(n for n in z.namelist() if n.endswith('.json'))
            self.assertEqual(len(metas),100)
            for path in metas:
                meta=json.loads(z.read(path))
                html_path=str(PurePosixPath(path).parent / meta['html_file'])
                html=z.read(html_path).decode('utf-8',errors='replace')
                products=extract_products(html,meta['url'])
                results[PurePosixPath(path).stem[:8]]=products
                total+=len(products)
                for product in products:
                    attrs=product['attributes']
                    self.assertTrue(attrs['brand'] or attrs['model'])
                    self.assertTrue(product['name'])
                    for k in ('ram_gb','storage_gb','price_brl'):
                        self.assertTrue(attrs[k] is None or attrs[k]>0,(path,product,k))
            self.assertGreater(total,40)
            self.assertEqual(results['00aecb67'],[]) # geladeiras
            self.assertEqual(results['0e13d308'],[]) # memória RAM para PC
            iphone=next(p for p in results['0cbb1d93'] if p['name'].lower().startswith('iphone 17 256'))
            self.assertEqual(iphone['attributes']['brand'],'Apple')
            self.assertEqual(iphone['attributes']['storage_gb'],256)
            self.assertIsNotNone(iphone['attributes']['price_brl'])
            a=results['0c8b24f7'][0]['attributes']
            self.assertEqual((a['brand'],a['model'],a['ram_gb'],a['storage_gb']),('Samsung','Galaxy S25 FE',8,256))
            self.assertEqual(results['0d3ec8ab'],[]) # página de categoria não é produto
            self.assertEqual(results['0ababd91'],[]) # página de categoria não é produto

    def test_explicit_title_cases(self):
        cases=[
            ('iPhone 17 256gb',('Apple','iPhone 17',None,256)),
            ('PRIMETEK Smartphone Samsung A07 4g 128gb 4gb 50mp',('Samsung','Samsung A07',4,128)),
            ('Smartphone Motorola Edge 70 5G 512GB 12GB RAM',('Motorola','Motorola Edge 70',12,512)),
            ('Smartphone Realme C73 4G 128GB 4GB RAM',('Realme','Realme C73',4,128)),
            ('Infinix Note 50X 5G 8GB RAM 256GB',('Infinix','Infinix Note 50X',8,256)),
        ]
        for name,expected in cases:
            with self.subTest(name=name):
                a=extract_attributes(name)
                self.assertEqual((a['brand'],a['model'],a['ram_gb'],a['storage_gb']),expected)
