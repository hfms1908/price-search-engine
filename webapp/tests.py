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
        self.assertContains(response, 'Página 2 de 3')
        self.assertContains(response, 'Produto 10')
        self.assertNotContains(response, 'Produto 0</summary>')

    def test_url_validation(self):
        self.assertIsNone(safe_offer_url('javascript:alert(1)'))
        self.assertIsNone(safe_offer_url('//example.com'))
        self.assertIsNone(safe_offer_url('https://user:pass@example.com'))
        self.assertEqual(safe_offer_url('https://example.com/a'), 'https://example.com/a')
