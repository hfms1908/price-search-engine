import unittest
from processor.config import BRANDS, MODEL_PATTERNS
from processor.classifier import BRAND, MODEL, classify_document
from processor.extractor import extract_attributes

class SharedVocabularyTests(unittest.TestCase):
    def test_all_brands_recognized(self):
        for key, name in BRANDS.items():
            with self.subTest(brand=key):
                self.assertIsNotNone(BRAND.search(key))
                self.assertEqual(extract_attributes(f"Smartphone {name}", "")["brand"], name)

    def test_shared_models(self):
        for title in ("Samsung Galaxy S25 Ultra", "Apple iPhone 16 Pro", "Xiaomi Redmi Note 14"):
            self.assertIsNotNone(MODEL.search(title))
            self.assertIsNotNone(extract_attributes(title, "")["model"])

if __name__ == "__main__":
    unittest.main()
