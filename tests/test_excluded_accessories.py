import json
import unittest
from processor.products import extract_products, is_excluded_product_name


class ExcludedAccessoriesTests(unittest.TestCase):
    def test_prefixes(self):
        for prefix in ('Capa', 'Capinha', 'Carcasa', 'Case', 'Fone', 'Película', 'Suporte'):
            with self.subTest(prefix=prefix):
                self.assertTrue(is_excluded_product_name(f'{prefix} Samsung Galaxy S25'))

    def test_terms_anywhere(self):
        for term in ('Cabo', 'CCabo', 'Carregador', 'Rugged Case', 'Card Case',
                     'Card Slot Case', 'Silicone Case', 'Magnet Case'):
            with self.subTest(term=term):
                self.assertTrue(is_excluded_product_name(f'Samsung Galaxy S25 {term}'))

    def test_case_insensitive_and_word_boundaries(self):
        self.assertTrue(is_excluded_product_name('  CAPINHA para iPhone 16'))
        self.assertTrue(is_excluded_product_name('Smartphone Samsung com CABO USB'))
        self.assertFalse(is_excluded_product_name('Smartphone Motorola Moto G 256 GB'))
        self.assertFalse(is_excluded_product_name('Smartphone Caseiro 128 GB'))

    def test_jsonld_filters_before_brand_is_prepended(self):
        items = [
            {'@type': 'Product', 'name': 'Capa Galaxy S25', 'brand': {'name': 'Samsung'}},
            {'@type': 'Product', 'name': 'Smartphone Samsung Galaxy S25 256 GB'},
            {'@type': 'Product', 'name': 'iPhone 16 Rugged Case'},
        ]
        html = '<script type="application/ld+json">' + json.dumps(items) + '</script>'
        products = extract_products(html, 'https://example.com/loja')
        self.assertEqual(len(products), 1)
        self.assertIn('Smartphone Samsung', products[0]['name'])

    def test_html_cards_filtered(self):
        html = '''<article class="product-card"><h2>Capa Samsung Galaxy S25</h2>
            <a href="/produto/capa">Ver</a></article>
            <article class="product-card"><h2>Smartphone Samsung Galaxy S25 256 GB</h2>
            <a href="/produto/s25">Ver</a></article>'''
        products = extract_products(html, 'https://example.com/loja')
        self.assertEqual(len(products), 1)
        self.assertIn('Smartphone', products[0]['name'])


if __name__ == '__main__':
    unittest.main()
