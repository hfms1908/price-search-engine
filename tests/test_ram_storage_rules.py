"""Regras de RAM e armazenamento sem rótulos explícitos."""
import unittest
from processor.extractor import extract_attributes

class CapacityInferenceTests(unittest.TestCase):
    def test_unlabeled_ram_variants(self):
        for ram in (4, 6, 8, 12):
            for unit in (f"{ram}GB", f"{ram} GB", f"{ram}/GB"):
                with self.subTest(unit=unit):
                    result = extract_attributes(f"Smartphone Samsung Galaxy A55 128GB {unit}")
                    self.assertEqual(result['ram_gb'], ram)
                    self.assertEqual(result['storage_gb'], 128)

    def test_storage_threshold(self):
        for storage in (64, 128, 256, 512):
            with self.subTest(storage=storage):
                result = extract_attributes(f"iPhone 17 {storage}GB")
                self.assertEqual(result['storage_gb'], storage)
                self.assertIsNone(result['ram_gb'])

    def test_no_guess_for_ambiguous_capacity(self):
        result = extract_attributes("Samsung Galaxy A55 32GB 16GB")
        self.assertIsNone(result['storage_gb'])
        self.assertIsNone(result['ram_gb'])

    def test_explicit_ram_takes_precedence(self):
        result = extract_attributes("Samsung Galaxy A55 128GB 8GB RAM")
        self.assertEqual(result['ram_gb'], 8)
        self.assertEqual(result['storage_gb'], 128)

    def test_unlabeled_ram_only_from_product_name(self):
        result = extract_attributes("iPhone 17 256GB", "Outro smartphone 8GB")
        self.assertIsNone(result['ram_gb'])
        self.assertEqual(result['storage_gb'], 256)
