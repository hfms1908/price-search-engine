"""Extração de ofertas de smartphones e tablets em HTML de lojas virtuais."""
import hashlib
import html as html_lib
import json
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from processor.classifier import classify_document
from processor.extractor import extract_attributes, parse_price, fill_missing_from_url
from processor.normalizer import normalize_capacities

CARD_SELECTORS = ('[itemtype*="schema.org/Product"]', '[data-product-id]', '[data-testid="product-card"]', '.product-card', '.product-item', 'article.product')
PRICE_RE = re.compile(r'R\$\s*([\d.,]+)')


def _walk_json(obj):
    if isinstance(obj, list):
        for x in obj: yield from _walk_json(x)
    elif isinstance(obj, dict):
        types = obj.get('@type', [])
        
        if isinstance(types, str): types = [types]
        
        if any(str(t).split('/')[-1].lower() == 'product' for t in types): yield obj
        
        for k,v in obj.items():
            if k != '@context': yield from _walk_json(v)


def _price_from_offers(offers):
    if isinstance(offers, list):
        for item in offers:
            value = _price_from_offers(item)
            if value is not None: return value
    
    if isinstance(offers, dict):
        if str(offers.get('priceCurrency','BRL')).upper() != 'BRL': return None
        
        for key in ('price', 'lowPrice'):
            value = parse_price(offers.get(key))
            if value is not None: return value
        
        return _price_from_offers(offers.get('priceSpecification'))
    
    return None


def _product(name, description, url, price=None, source='html'):
    name = normalize_capacities(html_lib.unescape(str(name or '').strip()))
    
    description = normalize_capacities(
        BeautifulSoup(html_lib.unescape(str(description or '')), 'html.parser').get_text(' ', strip=True)
    )[:1000]
    
    classification = classify_document(name, '', url)
    if not classification['relevant']: return None
    
    attrs = extract_attributes(name, description)
    # A URL é fonte secundária: preenche somente campos ausentes no HTML.
    attrs = fill_missing_from_url(attrs, url)
    
    if not (
        attrs['model'] or
        (
            attrs['brand']
            and (attrs['storage_gb'] is not None or attrs['ram_gb'] is not None)
            and re.search(r'\b(smartphone|celular|tablet|iphone|ipad)\b',name,re.I)
        )
    ): return None
    
    attrs['price_brl'] = price
    
    return {
        'name': name,
        'category': classification['category'],
        'url': url,
        'attributes': attrs,
        'text':f'{name} {description}'.strip(),
        'extraction_source':source
    }


def _node_price(node):
    if not node: return None
    
    for value in (node.get('content'), node.get('data-price'), node.get('value')):
        price = parse_price(value)
        if price is not None: return price
    
    match = PRICE_RE.search(node.get_text(' ',strip=True))
    
    return parse_price(match.group(1)) if match else None


def extract_products(html: str, page_url: str, page_title: str = '', cleaned_text: str = '', soup=None) -> list[dict]:
    # Parse parcial primeiro: JSON-LD é o caminho mais barato e confiável.
    from bs4 import SoupStrainer
    scripts_soup = BeautifulSoup(html, 'lxml', parse_only=SoupStrainer('script'))
    found = []
    
    for script in scripts_soup.find_all('script', type=re.compile(r'ld\+json',re.I)):
        try:
            data = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue
        
        for obj in _walk_json(data):
            link = obj.get('url') or page_url
            if isinstance(link,dict): link = link.get('@id') or page_url
            
            description=obj.get('description','')
            if not isinstance(description,str): description = ''
            
            brand = obj.get('brand')
            if isinstance(brand,dict): brand = brand.get('name','')
            
            name = obj.get('name','')
            if brand and str(brand).casefold() not in str(name).casefold(): name = f'{brand} {name}'
            
            p = _product(name,description,urljoin(page_url,str(link)),_price_from_offers(obj.get('offers')),'json_ld')
            if p: found.append(p)
    
    # Completa preços ausentes somente por correspondência exata de URL do cartão.
    # Não usa preços globais da página, que podem pertencer a outros produtos.
    if found and any(p['attributes']['price_brl'] is None for p in found):
        soup = soup or BeautifulSoup(html, 'lxml')
        prices_by_url = {}
        
        for card in soup.select(', '.join(CARD_SELECTORS)):
            link = card.select_one('a[href]')
            if not link: continue
            
            target = urljoin(page_url, link.get('href', '')).split('?', 1)[0].rstrip('/')
            
            price_node = (
                card.select_one('[data-testid="product-card::price"]')
                or card.select_one('[itemprop="price"], [data-price], .price, [data-area="price"]')
            )
            price = _node_price(price_node)
            if price is not None: prices_by_url[target] = price
        
        for p in found:
            if p['attributes']['price_brl'] is None:
                p['attributes']['price_brl'] = prices_by_url.get(p['url'].split('?', 1)[0].rstrip('/'))
    
    # JSON-LD costuma ser mais confiável do que cards genéricos; evita duplicações.
    if not found:
        soup = soup or BeautifulSoup(html, 'lxml')
        
        for card in soup.select(', '.join(CARD_SELECTORS)):
            heading = card.select_one('[itemprop="name"], h2, h3, h4, .product-name, .product-title')
            link = card.select_one('a[href]')
            
            name = heading.get_text(' ',strip=True) if heading else (link.get_text(' ',strip=True) if link else '')
            if not name: continue
            
            url = urljoin(page_url,link.get('href','')) if link else page_url
            
            price_node = (
                card.select_one('[data-testid="product-card::price"]')
                or card.select_one('[itemprop="price"], [data-price], .price, [data-area="price"]')
            )
            price = _node_price(price_node)
            
            p = _product(name,'',url,price,'html_card')
            if p: found.append(p)
    
    # Fallback apenas em URL de detalhe, nunca em listagens ou categorias.
    path = urlparse(page_url).path
    is_detail = bool(re.search(r'/(?:produto|product)/[^/]+|/p(?:/|$)',path,re.I))
    if not found and is_detail:
        soup = soup or BeautifulSoup(html, 'lxml')
        h1 = soup.find('h1')
        name = h1.get_text(' ',strip=True) if h1 else page_title.split('|')[0].strip()
        price = None
        
        for node in soup.select('[itemprop="price"], meta[property="product:price:amount"], meta[property="og:price:amount"]')[:8]:
            price = _node_price(node)
            if price is not None: break
        
        p = _product(name,'',page_url,price,'detail_fallback')
        if p: found.append(p)
    
    unique = {}
    for p in found:
        key = (p['url'].rstrip('/'), p['name'].casefold())
        if (
            key not in unique
            or (unique[key]['attributes']['price_brl'] is None and p['attributes']['price_brl'] is not None)
        ):
            unique[key] = p
    
    return list(unique.values())


def product_id(document_id, product):
    return hashlib.sha256(f"{document_id}|{product['url']}|{product['name'].casefold()}".encode()).hexdigest()
