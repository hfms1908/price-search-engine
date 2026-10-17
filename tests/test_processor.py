import unittest
from processor.cleaner import clean_html
from processor.normalizer import normalize_capacities


class ProcessorTests(unittest.TestCase):
    def test_clean_html(self):
        result = clean_html('<html><head><title>Galaxy S25</title><script>ruido()</script></head><body><nav>Menu</nav><main>Samsung 8 GB RAM e 256 GB</main></body></html>')
        self.assertEqual(result['title'], 'Galaxy S25')
        self.assertEqual(result['text'], 'Samsung 8 GB RAM e 256 GB')

    def test_capacities(self):
        self.assertEqual(normalize_capacities('8 GB / 256 GB, 6/GB, 1 TB'), '8gb / 256gb, 6gb, 1tb')
        self.assertEqual(normalize_capacities('R$ 2.499,90 Galaxy S25'), 'R$ 2.499,90 Galaxy S25')


if __name__ == '__main__':
    unittest.main()
