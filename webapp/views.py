"""Interface Django para consultar o índice gerado pelo projeto."""
from functools import lru_cache
from urllib.parse import urlsplit

from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render

from search.search import SearchEngine

PAGE_SIZE = 10
MAX_RESULTS = 1000


@lru_cache(maxsize=1)
def get_search_engine():
    """Mantém o índice e as normas vetoriais carregados por processo."""
    return SearchEngine(settings.BASE_DIR / 'data' / 'index')


def safe_offer_url(value):
    """Permite apenas URLs externas HTTP(S) com host definido."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        return value
    except ValueError:
        return None


def home(request):
    query = request.GET.get('q', '').strip()[:200]
    operator = request.GET.get('operator', 'OR').upper()
    ranking = request.GET.get('ranking', 'vector').lower()
    if operator not in ('AND', 'OR', 'NOT'):
        operator = 'OR'
    if ranking not in ('vector', 'boolean'):
        ranking = 'vector'
    if operator == 'NOT':
        ranking = 'boolean'

    results = []
    page_obj = None
    error = None
    if query:
        try:
            matches = get_search_engine().search(
                query, operator=operator, ranking=ranking, limit=MAX_RESULTS,
            )
            for product in matches:
                attributes = product.get('attributes') or {}
                description = product.get('text') or product.get('description') or ''
                if not isinstance(description, str):
                    description = str(description)
                price = attributes.get('price_brl')
                try:
                    price = f'R$ {float(price):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') if price is not None else None
                except (ValueError, TypeError):
                    price = None
                results.append({
                    'name': product.get('name') or 'Produto sem nome',
                    'description': description[:500],
                    'store_url': safe_offer_url(product.get('url')),
                    'brand': attributes.get('brand'),
                    'model': attributes.get('model'),
                    'ram': attributes.get('ram_gb'),
                    'storage': attributes.get('storage_gb'),
                    'price': price,
                    'score': f"{product['score']:.4f}" if product.get('score') is not None else None,
                })
            page_obj = Paginator(results, PAGE_SIZE).get_page(request.GET.get('page'))
        except (OSError, ValueError, KeyError) as exc:
            error = 'Não foi possível consultar o índice. Verifique os arquivos em data/index/.'
    return render(request, 'webapp/home.html', {
        'query': query, 'operator': operator, 'ranking': ranking,
        'page_obj': page_obj, 'error': error,
    })
