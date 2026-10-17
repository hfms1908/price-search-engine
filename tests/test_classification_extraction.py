import unittest
from processor.classifier import classify_document
from processor.extractor import extract_attributes

class ProductTests(unittest.TestCase):
    def test_relevant_smartphone(self):
        self.assertEqual(classify_document('Smartphone Samsung Galaxy S25 Ultra', '', '')['category'], 'smartphone')
    def test_relevant_tablet(self):
        self.assertEqual(classify_document('Tablet Apple iPad Air', '', '')['category'], 'tablet')
    def test_unrelated_page(self):
        self.assertFalse(classify_document('Geladeira Samsung 400L', 'smartphones ofertas', '')['relevant'])
    def test_attributes(self):
        a = extract_attributes('Smartphone Samsung Galaxy S25 Ultra 8 GB RAM / 256 GB', '')
        self.assertEqual(a['brand'], 'Samsung')
        self.assertEqual(a['model'], 'Galaxy S25 Ultra')
        self.assertEqual(a['ram_gb'], 8)
        self.assertEqual(a['storage_gb'], 256)
    def test_no_guessed_price(self):
        self.assertIsNone(extract_attributes('Tablet Apple iPad Air', 'Oferta de outro produto R$ 2.499,90')['price_brl'])

if __name__ == '__main__':
    unittest.main()
