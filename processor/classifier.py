"""Classificação conservadora de páginas de smartphones e tablets."""
import re
from urllib.parse import urlparse
from processor.config import BRANDS, MODEL_PATTERNS

CATEGORY = re.compile(r'\b(smartphones?|celulares?|tablets?|iphones?|ipads?)\b', re.I)
BRAND = re.compile(r'\b(?:' + '|'.join(re.escape(key) for key in BRANDS) + r')\b', re.I)
MODEL = re.compile(r'\b(?:' + '|'.join(MODEL_PATTERNS.values()) + r')\b', re.I)
EXCLUDED = re.compile(r'\b(geladeira|refrigerador|fog[aã]o|lava\s+e\s+seca|televisor|smart\s*tv|colch[aã]o|roupa\s+de\s+cama|liquidificador|micro-ondas)\b', re.I)
PRODUCT_PATH = re.compile(r'/(?:produto|product|p)/', re.I)


def classify_document(title: str, text: str, url: str = '') -> dict:
    """Classifica com prioridade ao título; texto genérico sozinho não basta."""
    title = title or ''
    text = text or ''
    path = urlparse(url).path
    title_category = CATEGORY.search(title)
    title_model = MODEL.search(title)
    title_brand = BRAND.search(title)
    title_excluded = EXCLUDED.search(title)
    path_category = CATEGORY.search(path.replace('-', ' '))
    if title_excluded and not title_category and not title_model:
        return {'relevant': False, 'category': None, 'reason': 'titulo_fora_do_escopo'}
    relevant = bool(title_category or title_model or (path_category and title_brand))
    if not relevant:
        return {'relevant': False, 'category': None, 'reason': 'sem_evidencia_no_titulo_ou_url'}
    evidence = ' '.join([title, path.replace('-', ' ')])
    is_tablet = bool(re.search(r'\b(tablets?|ipads?|galaxy\s+tab)\b', evidence, re.I))
    category = 'tablet' if is_tablet else 'smartphone'
    return {'relevant': True, 'category': category, 'reason': 'titulo_ou_url'}
