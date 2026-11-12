from unittest.mock import patch
from django.test import SimpleTestCase
from django.urls import reverse
from .views import get_search_engine, safe_offer_url


class SearchPageTests(SimpleTestCase):
    def setUp(self):
        get_search_engine.cache_clear()

    def test_home_without_query_does_not_load_index(self):
        with patch('webapp.views.get_search_engine') as loader:
            response = self.client.get(reverse('home'))
            self.assertEqual(response.status_code, 200)
            loader.assert_not_called()

    @patch('webapp.views.get_search_engine')
    def test_description_and_store_link(self, loader):
        loader.return_value.search.return_value = [{
            'name': 'Galaxy S25', 'text': 'Descrição do aparelho',
            'url': 'https://example.com/oferta',
            'attributes': {'brand': 'Samsung', 'price_brl': 4299.9}, 'score': .92,
        }]
        response = self.client.get('/', {'q': 'galaxy'})
        self.assertContains(response, '<details', html=False)
        self.assertContains(response, 'Descrição do aparelho')
        self.assertContains(response, 'https://example.com/oferta')
        self.assertContains(response, 'R$ 4.299,90')
        self.assertContains(response, 'target="_blank"')

    @patch('webapp.views.get_search_engine')
    def test_unsafe_url_is_not_rendered(self, loader):
        loader.return_value.search.return_value = [{
            'name': 'Produto', 'url': 'javascript:alert(1)', 'attributes': {}, 'score': None,
        }]
        response = self.client.get('/', {'q': 'produto'})
        self.assertNotContains(response, 'Visitar loja')
        self.assertContains(response, 'Descrição não disponível')

    @patch('webapp.views.get_search_engine')
    def test_not_forces_boolean_ranking(self, loader):
        loader.return_value.search.return_value = []
        self.client.get('/', {'q': 'iphone', 'operator': 'NOT', 'ranking': 'vector'})
        self.assertEqual(loader.return_value.search.call_args.kwargs['ranking'], 'boolean')

    @patch('webapp.views.get_search_engine')
    def test_pagination(self, loader):
        loader.return_value.search.return_value = [
            {'name': f'Produto {i}', 'attributes': {}, 'score': .2} for i in range(22)
        ]
        response = self.client.get('/', {'q': 'produto', 'page': 2})
        self.assertContains(response, 'aria-current="page">2</span>')
        self.assertContains(response, 'Produto 10')
        self.assertNotContains(response, 'Produto 0</summary>')

    def test_url_validation(self):
        self.assertIsNone(safe_offer_url('javascript:alert(1)'))
        self.assertIsNone(safe_offer_url('//example.com'))
        self.assertIsNone(safe_offer_url('https://user:pass@example.com'))
        self.assertEqual(safe_offer_url('https://example.com/a'), 'https://example.com/a')

class SortingAndPaginationTests(SimpleTestCase):
    @staticmethod
    def sample_products(count=60):
        return [
            {'name': f'Oferta {i:02d}', 'attributes': {'price_brl': (None if i % 7 == 0 else float(100 + i))}, 'score': 1 - i / 100}
            for i in range(count)
        ]

    @patch('webapp.views.get_search_engine')
    def test_default_operator_and_relevance(self, loader):
        loader.return_value.search.return_value = self.sample_products(3)
        response = self.client.get('/', {'q': 'galaxy'})
        self.assertEqual(loader.return_value.search.call_args.kwargs['operator'], 'AND')
        self.assertEqual(response.context['sort'], 'relevance')
        self.assertEqual([p['name'] for p in response.context['page_obj']], ['Oferta 00', 'Oferta 01', 'Oferta 02'])

    @patch('webapp.views.get_search_engine')
    def test_ascending_price_missing_last(self, loader):
        loader.return_value.search.return_value = self.sample_products(15)
        response = self.client.get('/', {'q': 'galaxy', 'sort': 'price_asc'})
        ordered = response.context['page_obj'].paginator.object_list
        prices = [p['price_value'] for p in ordered]
        self.assertEqual(prices, sorted((p for p in prices if p is not None)) + [None] * 3)

    @patch('webapp.views.get_search_engine')
    def test_descending_price_missing_last(self, loader):
        loader.return_value.search.return_value = self.sample_products(15)
        response = self.client.get('/', {'q': 'galaxy', 'sort': 'price_desc'})
        prices = [p['price_value'] for p in response.context['page_obj'].paginator.object_list]
        self.assertEqual(prices, sorted((p for p in prices if p is not None), reverse=True) + [None] * 3)

    @patch('webapp.views.get_search_engine')
    def test_pagination_five_pages_and_links(self, loader):
        loader.return_value.search.return_value = self.sample_products(100)
        response = self.client.get('/', {'q': 'galaxy', 'page': 5, 'sort': 'price_asc', 'operator': 'OR'})
        self.assertEqual(list(response.context['page_numbers']), [3, 4, 5, 6, 7])
        self.assertContains(response, 'aria-current="page"')
        self.assertContains(response, 'page=1')
        self.assertContains(response, 'page=10')
        self.assertContains(response, 'page=4')
        self.assertContains(response, 'page=6')
        self.assertContains(response, 'sort=price_asc')
        self.assertContains(response, 'operator=OR')

    @patch('webapp.views.get_search_engine')
    def test_pagination_windows_at_boundaries(self, loader):
        loader.return_value.search.return_value = self.sample_products(100)
        first = self.client.get('/', {'q': 'galaxy', 'page': 1})
        last = self.client.get('/', {'q': 'galaxy', 'page': 10})
        self.assertEqual(list(first.context['page_numbers']), [1, 2, 3, 4, 5])
        self.assertEqual(list(last.context['page_numbers']), [6, 7, 8, 9, 10])

    @patch('webapp.views.get_search_engine')
    def test_invalid_sort_falls_back_to_relevance(self, loader):
        loader.return_value.search.return_value = self.sample_products(2)
        response = self.client.get('/', {'q': 'galaxy', 'sort': 'invalid'})
        self.assertEqual(response.context['sort'], 'relevance')


class WarmupTests(SimpleTestCase):
    def setUp(self):
        get_search_engine.cache_clear()

    @patch('webapp.views.get_search_engine')
    def test_warmup_loads_engine_without_query(self, loader):
        response = self.client.get('/warmup/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ready')
        loader.assert_called_once_with()

    @patch('webapp.views.get_search_engine')
    def test_warmup_rejects_non_local_requests(self, loader):
        response = self.client.get('/warmup/', REMOTE_ADDR='192.0.2.10')
        self.assertEqual(response.status_code, 403)
        loader.assert_not_called()

    @patch('webapp.views.get_search_engine', side_effect=OSError('Índice ausente'))
    def test_warmup_reports_index_error(self, loader):
        response = self.client.get('/warmup/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['status'], 'error')
