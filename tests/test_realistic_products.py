import unittest
from processor.products import extract_products

class RealisticProductsTests(unittest.TestCase):
    def test_jsonld_multiple_products(self):
        html='''<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Product","name":"Samsung Galaxy S25 256 GB","url":"/a","offers":{"price":"3499.90","priceCurrency":"BRL"}},{"@type":"Product","name":"Apple iPhone 16 128 GB","url":"/b","offers":{"price":"4299.90","priceCurrency":"BRL"}}]}</script>'''
        p=extract_products(html,'https://loja.com/smartphones')
        self.assertEqual(len(p),2)
        self.assertEqual(p[0]['attributes']['price_brl'],3499.9)
    def test_irrelevant_category(self):
        self.assertEqual(extract_products('<h1>Geladeiras</h1>','https://loja.com/geladeiras'),[])

if __name__=='__main__': unittest.main()
