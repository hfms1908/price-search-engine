"""Regressões: URL complementa HTML sem alterar atributos já identificados."""
import unittest
from processor.extractor import extract_attributes, fill_missing_from_url
from processor.products import extract_products

URL = ('http://www.oficinadosbits.com.br/produto/'
       'smartphone-samsung-galaxy-a17-tela-6-7-fhd-128gb-4gb-ram-dual-chip-'
       'camera-tripla-50mp-selfie-13mp-octa-core-preto-sm-a175f-ds/')

class URLFallbackTests(unittest.TestCase):
    def test_example_product_json_ld(self):
        html = '''<script type="application/ld+json">{"@context":"https://schema.org",
        "@type":"Product","name":"Smartphone Samsung Galaxy A17 - Tela 6.7 Super AMOLED FHD+, 128gb, Dual Chip, 4G, Câmera Tripla 50MP, Octa Core - Preto - SM-A175F",
        "offers":{"@type":"Offer","price":"939.99","priceCurrency":"BRL"}}</script>'''
        products = extract_products(html, URL)
        self.assertEqual(len(products), 1)
        attrs = products[0]['attributes']
        self.assertEqual((attrs['brand'],attrs['model'],attrs['ram_gb'],attrs['storage_gb'],attrs['price_brl']),
                         ('Samsung','Galaxy A17',4,128,939.99))

    def test_html_has_priority(self):
        original = extract_attributes('Samsung Galaxy A17 256GB 8GB RAM')
        filled = fill_missing_from_url(original, URL)
        self.assertEqual(filled['ram_gb'],8)
        self.assertEqual(filled['storage_gb'],256)

    def test_query_does_not_supply_ram(self):
        attrs = extract_attributes('iPhone 17 256GB')
        result = fill_missing_from_url(attrs,'https://site.com/celular/iphone-17-256gb?other=12gb-ram')
        self.assertIsNone(result['ram_gb'])

    def test_url_without_trailing_slash(self):
        attrs = extract_attributes('Samsung Galaxy A17 128GB')
        self.assertEqual(fill_missing_from_url(attrs,URL.rstrip('/'))['ram_gb'],4)

    def test_missing_price_never_inferred_from_url(self):
        attrs = extract_attributes('Samsung Galaxy A17 128GB')
        result = fill_missing_from_url(attrs,URL+'?price=939.99')
        self.assertIsNone(result['price_brl'])

if __name__ == '__main__': unittest.main()
