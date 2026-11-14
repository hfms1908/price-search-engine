"""Regressões de extração de RAM e armazenamento da versão conservadora."""
import unittest
from processor.extractor import extract_attributes


class RamStorageAdjustmentsTests(unittest.TestCase):
    def assert_memory(self, title, storage, ram, description=''):
        attrs = extract_attributes(title, description)
        self.assertEqual(attrs['storage_gb'], storage, title)
        self.assertEqual(attrs['ram_gb'], ram, title)

    def test_card_memory_capacity_is_excluded_before_extraction(self):
        self.assert_memory(
            'Smartphone A17 256GB', 256, 8,
            'Cartão de Memória: Até 2TB Memória RAM: 8GB'
        )

    def test_card_memory_with_adjacent_labels(self):
        self.assert_memory(
            'Smartphone A17 256GB', 256, 8,
            'Suporte a Cartão de Memória: Sim Tipo Cartão de Memória Suportado: MicroSD '
            'Capacidade do Cartão de Memória: Até 2TB Memória RAM: 8GB'
        )

    def test_storage_labels_with_colon(self):
        for label in ('Memória Interna:', 'Armazenamento Interno:', 'Armazenamento:'):
            with self.subTest(label=label):
                self.assert_memory(f'Smartphone {label} 256GB RAM: 8GB', 256, 8)

    def test_ram_labels_with_colon(self):
        for label in ('Memória RAM:', 'RAM:'):
            with self.subTest(label=label):
                self.assert_memory(f'Smartphone Armazenamento: 128GB {label} 6GB', 128, 6)

    def test_ram_one_two_three_gb(self):
        for ram in (1, 2, 3):
            with self.subTest(ram=ram):
                self.assert_memory(f'Celular Xiaomi Poco C71 64GB {ram}GB', 64, ram)

    def test_single_storage_at_least_32gb(self):
        for storage in (32, 64, 128, 256, 512):
            with self.subTest(storage=storage):
                self.assert_memory(f'Smartphone {storage}GB', storage, None)

    def test_invert_when_ram_is_32_or_more_and_storage_missing(self):
        self.assert_memory('Smartphone RAM: 128GB', 128, None)

    def test_invert_when_storage_less_than_ram(self):
        self.assert_memory('Smartphone RAM: 128GB Armazenamento: 8GB', 128, 8)

    def test_do_not_invert_valid_ram_and_storage(self):
        self.assert_memory('Smartphone RAM: 8GB Armazenamento: 256GB', 256, 8)

    def test_card_memory_does_not_create_false_storage(self):
        self.assert_memory('Smartphone RAM: 8GB', None, 8, 'Cartão de Memória: Até 2TB')


if __name__ == '__main__':
    unittest.main()
