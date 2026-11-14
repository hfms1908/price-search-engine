"""Extração de atributos a partir do nome de UMA oferta, sem misturar produtos."""
import re
import html as html_lib
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse
from processor.config import BRANDS, MODEL_PATTERNS
from processor.normalizer import normalize_capacities

MODEL_PATTERN = re.compile(r'\b(?:' + '|'.join(MODEL_PATTERNS.values()) + r')\b', re.I)
CAPACITY = re.compile(r'(?<![\w])(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>GB|TB|MB)\b', re.I)
RAM = re.compile(
    r'(?<![\w])(\d+(?:[.,]\d+)?)\s*(GB|TB|MB)\s*(?:de\s*)?(?:ram|mem[oó]ria\s+ram)\b(?!\s*:)'
    r'|\b(?:ram|mem[oó]ria\s+ram)\s*(?::\s*|de\s+|\s+)(\d+(?:[.,]\d+)?)\s*(GB|TB|MB)\b', re.I
)
STORAGE = re.compile(
    r'(?<![\w])(\d+(?:[.,]\d+)?)\s*(GB|TB|MB)\s*(?:de\s*)?(?:armazenamento(?:\s+interno)?|mem[oó]ria\s+interna|rom)\b(?!\s*:)'
    r'|\b(?:armazenamento(?:\s+interno)?|mem[oó]ria\s+interna|rom)\s*(?::\s*|de\s+|\s+)(\d+(?:[.,]\d+)?)\s*(GB|TB|MB)\b', re.I
)
# Remove a capacidade de cartões externos antes de procurar RAM ou armazenamento.
# A expressão para no primeiro valor de capacidade para não consumir o próximo atributo.
CARD_MEMORY = re.compile(
    r'\b(?:cart[aã]o\s+de\s+mem[oó]ria|(?:cart[aã]o\s+)?micro\s*sd|'
    r'mem[oó]ria\s+expans[ií]vel|expans[aã]o\s+(?:por\s+)?cart[aã]o)\b'
    r'(?:(?![.;\n]|\b(?:mem[oó]ria\s+ram|ram|mem[oó]ria\s+interna|armazenamento)\b).){0,100}?'
    r'\b\d+(?:[.,]\d+)?\s*(?:GB|TB|MB)\b', re.I
)
CARD_FLAG = re.compile(r'\b(?:cart[aã]o\s+de\s+mem[oó]ria|micro\s*sd)\b', re.I)


def _without_card_memory(value):
    """Descarta capacidade de cartão externo, preservando atributos seguintes."""
    value = CARD_MEMORY.sub(' ', value)
    # Rótulos sem capacidade não devem modificar outras especificações.
    return value

PRICE = re.compile(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})')

def _gb(value, unit):
    amount = float(value.replace(',','.'))
    
    factor = {
        'mb': 1 / 1024,
        'gb': 1,
        'tb': 1024
    }
    
    return round(amount * factor[unit.lower()], 3)

def _match_capacity(match):
    return _gb(match.group(1) or match.group(3),match.group(2) or match.group(4)) if match else None

def _clean(value):
    return normalize_capacities(html_lib.unescape(BeautifulSoup(str(value or ''),'html.parser').get_text(' ',strip=True)))

def extract_attributes(title: str, text: str = '', url: str = '') -> dict:
    name = _without_card_memory(_clean(title))
    # Texto complementar só é usado quando descreve o mesmo produto (fornecido pelo chamador).
    detail = _without_card_memory(_clean(text)[:1800])
    brand = None
    
    for key, display in BRANDS.items():
        if re.search(r'(?<!\w)'+re.escape(key)+r'(?!\w)',name,re.I):
            brand = display
            break
    
    if brand is None and re.search(r'\b(?:iphone|ipad)\b',name,re.I): brand = 'Apple'
    if brand is None and re.search(r'\bgalaxy\b',name,re.I): brand = 'Samsung'
    
    model_match = MODEL_PATTERN.search(name)
    model = model_match.group(0) if model_match else None
    
    ram = _match_capacity(RAM.search(name))
    if ram is None: ram = _match_capacity(RAM.search(detail))
    
    # Capacidade sem rótulo: 1GB a 12GB indica RAM e 64GB ou mais indica armazenamento.
    # Não inferir 16GB/32GB nem capacidades em MB.
    # Somente o nome da oferta é usado para evitar dados de outros produtos.
    if ram is None:
        capacities = [
            _gb(m.group('num'), m.group('unit'))
            for m in CAPACITY.finditer(name)
            if m.group('unit').lower() == 'gb'
        ]
        
        ram_candidates = [v for v in capacities if v in (1, 2, 3, 4, 6, 8, 10, 12)]
        if ram_candidates:
            ram = ram_candidates[0]

    storage = _match_capacity(STORAGE.search(name))
    
    # Em títulos de smartphones, 32/64/128/256/512GB ou 1/2TB sem RAM são armazenamento.
    # Evita tratar 4G/5G, 50MP (câmera), e memória RAM como armazenamento.
    if storage is None:
        masked = RAM.sub(' ',name)
        candidates = [
            _gb(m.group('num'), m.group('unit'))
            for m in CAPACITY.finditer(masked)
            if m.group('unit').lower() in ('gb','tb')
        ]
        
        plausible = [v for v in candidates if v>=64 and (ram is None or v > ram)]
        if plausible: storage = max(plausible)
        # Capacidade isolada de 32 GB representa armazenamento.
        elif len(candidates) == 1 and candidates[0] >= 32 and ram is None:
            storage = candidates[0]
    
    if storage is None: storage = _match_capacity(STORAGE.search(detail))

    # Uma capacidade >= 32 GB atribuída à RAM pode ser armazenamento.
    # Quando o armazenamento é menor, os campos foram trocados.
    if ram is not None and ram >= 32 and (storage is None or storage < ram):
        storage, ram = ram, storage

    # Nunca obter preço de um texto genérico da página ou de outros produtos.
    pm = PRICE.search(name)
    price = parse_price(pm.group(1)) if pm else None
    
    attributes = {
        'brand': brand,
        'model': model,
        'ram_gb': ram,
        'storage_gb': storage,
        'price_brl':price
    }
    
    # A URL é uma fonte secundária. Nunca substitui dados já obtidos do HTML.
    # Não utilizar URLs de categorias, buscas ou páginas genéricas.
    if url and any(attributes[key] is None for key in ('brand','model','ram_gb','storage_gb')):
        path = unquote(urlparse(url).path)
        parts = [part for part in path.split('/') if part]
        
        is_detail = bool(
            re.search(r'/(?:produto|product)/[^/]+', path, re.I)
            or re.search(r'/p(?:/|$)', path, re.I)
            or (parts and re.search(r'(?:celular|smartphone|tablet|iphone|ipad)-', parts[-1], re.I))
        )
        
        if is_detail and parts:
            slug = re.sub(r'[-_]+', ' ', parts[-1])
            # Extrair atributos do slug isoladamente evita cruzar capacidades
            # de um produto com números que aparecem no título de outro.
            fallback = extract_attributes(slug)
            for key in ('brand', 'model', 'ram_gb', 'storage_gb'):
                if attributes[key] is None:
                    attributes[key] = fallback[key]
    
    return attributes


def parse_price(value):
    """Converte preços monetários; recusa strings com parcelas e unidades."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if value > 0 else None
    
    if not isinstance(value,str): return None
    
    # O Unicode \u00a0 representa o caractere espaço não separável (Non-Breaking Space, ou NBSP).
    value = value.strip().replace('R$','').replace('\u00a0','').replace(' ','')
    if not re.fullmatch(r'\d[\d.,]*',value): return None
    
    if ',' in value:
        value = value.replace('.','').replace(',','.')
    elif value.count('.') > 1:
        value = value.replace('.','')
    
    try:
        number = float(value)
        return number if number > 0 else None
    except ValueError:
        return None


def fill_missing_from_url(attributes: dict, product_url: str) -> dict:
    """Complementa atributos ausentes usando somente o caminho da URL da oferta.

    Não substitui dados obtidos do HTML. Ignora query string, domínio e fragmento,
    que frequentemente contêm parâmetros de rastreamento ou nomes de outras ofertas.
    """
    from urllib.parse import unquote, urlsplit

    result = attributes.copy()
    missing = ('brand', 'model', 'ram_gb', 'storage_gb')
    if all(result.get(field) is not None for field in missing):
        return result
    
    path = unquote(urlsplit(product_url or '').path).strip('/')
    if not path:
        return result
    
    slug = path.rsplit('/', 1)[-1]
    if not slug or len(slug) < 8:
        return result
    
    # A URL não deve fornecer preço, nem sobrescrever atributos extraídos do HTML.
    slug_text = re.sub(r'[-_]+', ' ', slug)
    inferred = extract_attributes(slug_text)
    
    for field in missing:
        if result.get(field) is None and inferred.get(field) is not None:
            result[field] = inferred[field]
    
    return result
