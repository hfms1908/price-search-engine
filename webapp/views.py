"""Interface Django para consultar o índice gerado pelo projeto."""
import math
from functools import lru_cache
from urllib.parse import urlsplit

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden, JsonResponse
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


def warmup(request):
    """Aquece o cache de busca; acessível apenas via loopback local."""
    remote_addr = request.META.get('REMOTE_ADDR', '')
    if remote_addr not in ('127.0.0.1', '::1'):
        return HttpResponseForbidden('Aquecimento disponível apenas localmente.')
    
    try:
        get_search_engine()
    except (OSError, ValueError, KeyError) as exc:
        return JsonResponse({'status': 'error', 'detail': 'Falha ao carregar o índice.'}, status=503)
    
    return JsonResponse({'status': 'ready'})


def home(request):
    query = request.GET.get('q', '').strip()[:200]
    operator = request.GET.get('operator', 'AND').upper()
    ranking = request.GET.get('ranking', 'vector').lower()
    if operator not in ('AND', 'OR', 'NOT'):
        operator = 'AND'
    if ranking not in ('vector', 'boolean'):
        ranking = 'vector'
    if operator == 'NOT':
        ranking = 'boolean'
    
    sort = request.GET.get('sort', 'relevance').lower()
    if sort not in ('relevance', 'price_asc', 'price_desc'):
        sort = 'relevance'
    
    results = []
    page_obj = None
    page_numbers = ()
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
                    price_value = float(price) if price is not None else None
                    if price_value is not None and (not math.isfinite(price_value) or price_value < 0):
                        price_value = None
                except (ValueError, TypeError, OverflowError):
                    price_value = None
                
                price = (f'R$ {price_value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
                         if price_value is not None else None)
                
                results.append({
                    'name': product.get('name') or 'Produto sem nome',
                    'description': description[:500],
                    'store_url': safe_offer_url(product.get('url')),
                    'brand': attributes.get('brand'),
                    'model': attributes.get('model'),
                    'ram': attributes.get('ram_gb'),
                    'storage': attributes.get('storage_gb'),
                    'price': price,
                    'price_value': price_value,
                    'score': f"{product['score']:.4f}" if product.get('score') is not None else None,
                })
            
            # Ordena o conjunto recuperado antes da paginação. A ordem por relevância
            # permanece intacta, inclusive para produtos sem preço.
            if sort == 'price_asc':
                results.sort(key=lambda item: (item['price_value'] is None,
                                               item['price_value'] if item['price_value'] is not None else 0))
            elif sort == 'price_desc':
                results.sort(key=lambda item: (item['price_value'] is None,
                                               -item['price_value'] if item['price_value'] is not None else 0))
            
            page_obj = Paginator(results, PAGE_SIZE).get_page(request.GET.get('page'))
            
            # Janela de até cinco páginas, centralizada na página atual sempre que possível.
            total = page_obj.paginator.num_pages
            start = max(1, min(page_obj.number - 2, total - 4))
            page_numbers = range(start, min(start + 5, total + 1))
        
        except (OSError, ValueError, KeyError) as exc:
            error = 'Não foi possível consultar o índice. Verifique os arquivos em data/index/.'
    
    return render(request, 'webapp/home.html', {
        'query': query, 'operator': operator, 'ranking': ranking,
        'page_obj': page_obj, 'page_numbers': page_numbers, 'sort': sort, 'error': error,
    })
