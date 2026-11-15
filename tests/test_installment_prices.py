"""Regressões: parcelas não são preços finais de smartphones."""
import unittest
from bs4 import BeautifulSoup
from processor.products import _node_price, extract_products

BASE = 'https://www.oficinadosbits.com.br/categoria/celulares-e-comunicacao-smartphone/'


def card(pricing):
    return ("<article class='product-item'><h2><a href='/produto/samsung-galaxy-s25/'>"
            "Smartphone Samsung Galaxy S25 256GB 8GB RAM</a></h2>"
            + pricing + "</article>")


class InstallmentPriceTests(unittest.TestCase):
    def test_cash_price_preferred_over_installments(self):
        html = card('<div class="price-group"><span class="price months">'
                    '<b>12x </b><strong>R$119,44</strong></span>'
                    '<span class="price cash">ou <b>R$1.289,99</b> no PIX</span></div>')
        products = extract_products(html, BASE)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]['attributes']['price_brl'], 1289.99)

    def test_installment_variants_are_not_prices(self):
        for value in ('12x R$119,44', '12 x R$ 119,44', '10x R$ 250,00'):
            with self.subTest(value=value):
                html = card(f'<span class="price">{value}</span>')
                products = extract_products(html, BASE)
                self.assertEqual(len(products), 1)
                self.assertIsNone(products[0]['attributes']['price_brl'])

    def test_only_installment_class_is_not_price(self):
        html = card('<span class="price months"><b>12x</b><strong>R$119,44</strong></span>')
        self.assertIsNone(extract_products(html, BASE)[0]['attributes']['price_brl'])

    def test_normal_price_remains_supported(self):
        html = card('<span class="price">R$ 2.599,90</span>')
        self.assertEqual(extract_products(html, BASE)[0]['attributes']['price_brl'], 2599.9)

    def test_cash_price_is_selected_even_if_months_first(self):
        node = BeautifulSoup('<div class="price-group">'
            '<span class="price months">12x R$119,44</span>'
            '<span class="price cash">R$1.289,99</span></div>', 'html.parser').div
        self.assertEqual(_node_price(node), 1289.99)

    def test_prices_do_not_leak_between_cards(self):
        html = card('<span class="price months">12x R$119,44</span>') + (
            '<article class="product-item"><h2><a href="/produto/motorola-moto-g84/">'
            'Smartphone Motorola Moto G84 256GB</a></h2>'
            '<span class="price cash">R$1.999,00</span></article>')
        products = extract_products(html, BASE)
        self.assertEqual(len(products), 2)
        self.assertIsNone(products[0]['attributes']['price_brl'])
        self.assertEqual(products[1]['attributes']['price_brl'], 1999.0)


if __name__ == '__main__':
    unittest.main()
