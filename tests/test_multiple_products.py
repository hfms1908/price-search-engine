import json
import tempfile
import unittest
from pathlib import Path
from processor.products import extract_products
from processor.processor import process_documents

class MultiProductTests(unittest.TestCase):
    def test_two_jsonld_products(self):
        data = {'@context':'https://schema.org','@type':'ItemList','itemListElement':[
            {'@type':'Product','name':'Smartphone Samsung Galaxy S25 8 GB RAM / 256 GB','url':'/produto/s25','offers':{'@type':'Offer','price':'3499.90','priceCurrency':'BRL'}},
            {'@type':'Product','name':'Tablet Apple iPad Air 128 GB','url':'/produto/ipad','offers':{'@type':'Offer','price':'2999,90','priceCurrency':'BRL'}}]}
        html = '<html><head><title>Celulares</title><script type="application/ld+json">'+json.dumps(data)+'</script></head><body><main>Promoções</main></body></html>'
        products = extract_products(html, 'https://example.com/celulares')
        self.assertEqual(len(products), 2)
        self.assertEqual(products[0]['attributes']['price_brl'], 3499.9)
        self.assertEqual(products[1]['attributes']['price_brl'], 2999.9)

    def test_document_generates_multiple_products(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)/'raw'; processed = Path(tmp)/'processed'; raw.mkdir()
            data = [{'@type':'Product','name':'Smartphone Samsung Galaxy S25','url':'/p/s25'}, {'@type':'Product','name':'Tablet Apple iPad Air','url':'/p/ipad'}]
            html = '<html><title>Ofertas</title><script type="application/ld+json">'+json.dumps(data)+'</script><body>Newsletter</body></html>'
            (raw/'abc.html').write_text(html, encoding='utf-8')
            (raw/'abc.json').write_text(json.dumps({'document_id':'abc','html_file':'abc.html','url':'https://example.com/'}), encoding='utf-8')
            stats = process_documents(raw, processed)
            result = json.loads((processed/'abc.json').read_text())
            self.assertEqual(stats['products'], 2)
            self.assertEqual(len(result['products']), 2)
            self.assertIn('Galaxy S25', result['text'])

    def test_promotional_text_only_not_product(self):
        html = '<html><title>Smartphone Samsung Galaxy S20 FE</title><body>Promoções exclusivas</body></html>'
        self.assertEqual(extract_products(html,'https://example.com/'), [])

if __name__ == '__main__':
    unittest.main()
