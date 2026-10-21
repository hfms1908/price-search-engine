"""Indexador invertido sequencial: um documento lógico por oferta."""
import json
import logging
import time
from collections import Counter, defaultdict
from pathlib import Path
from indexer.config import PROCESSED_DIR, INDEX_DIR
from indexer.tokenizer import tokenize
from indexer.stats import make_statistics
from indexer.storage import save_json

logger = logging.getLogger(__name__)

def capacity_term(value):
    if value is None or isinstance(value, bool): return None
    
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    
    if number <= 0: return None
    
    return f'{number:g}gb'

def product_fields(product):
    attributes = product.get('attributes') or {}
    
    result = {
        'name': product.get('name') or '',
        'brand': attributes.get('brand') or '',
        'model': attributes.get('model') or '',
        'text': product.get('text') or '',
        'ram_gb': capacity_term(attributes.get('ram_gb')) or '',
        'storage_gb': capacity_term(attributes.get('storage_gb')) or '',
    }
    
    return result

def build_index(processed_dir: Path = PROCESSED_DIR, index_dir: Path = INDEX_DIR) -> dict:
    """Lê JSONs processados e gera índice, mapa, produtos e estatísticas."""
    started = time.perf_counter()
    processed_dir, index_dir = Path(processed_dir), Path(index_dir)
    index = defaultdict(dict)
    products = {}
    document_map = {}
    seen_product_ids = set()
    read = 0
    
    for path in sorted(processed_dir.glob('*.json')):
        # Somente JSONs da etapa de processamento são entradas válidas.
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or not isinstance(data.get('products'), list):
            raise ValueError(f'Documento processado inválido: {path}')
        
        read += 1
        
        for product in data['products']:
            if not isinstance(product, dict):
                raise ValueError(f'Produto inválido em {path}')
            
            pid = product.get('product_id')
            if not isinstance(pid, str) or not pid:
                raise ValueError(f'Produto sem product_id em {path}')
            if pid in seen_product_ids:
                raise ValueError(f'product_id duplicado: {pid}')
            
            seen_product_ids.add(pid)
            doc_id = str(len(document_map) + 1)
            document_map[doc_id] = {'product_id': pid, 'source_file': path.name}
            attrs = product.get('attributes') or {}
            
            products[doc_id] = {
                'document_id': data.get('document_id'),
                'collected_at': data.get('collected_at'),
                'name': product.get('name'),
                'category': product.get('category'),
                'url': product.get('url') or data.get('url'),
                'attributes': attrs,
                'extraction_source': product.get('extraction_source'),
            }
            
            for field, value in product_fields(product).items():
                for term, count in Counter(tokenize(value)).items():
                    index[term].setdefault(doc_id, {})[field] = count
    
    ordered = {
        term: dict(sorted(entries.items(), key=lambda pair: int(pair[0])))
        for term, entries in sorted(index.items())
    }

    statistics = make_statistics(read, products, ordered, time.perf_counter() - started)
    sizes = {}
    sizes['inverted_index.json'] = save_json(index_dir / 'inverted_index.json', ordered, sort_keys=False)
    sizes['products.json'] = save_json(index_dir / 'products.json', products, sort_keys=False)
    sizes['document_map.json'] = save_json(index_dir / 'document_map.json', document_map, sort_keys=False)
    statistics['index_file_bytes'] = sizes['inverted_index.json']
    statistics['products_file_bytes'] = sizes['products.json']
    statistics['document_map_file_bytes'] = sizes['document_map.json']
    
    save_json(index_dir / 'statistics.json', statistics)
    
    return statistics

def print_report(stats):
    print('\n' + '=' * 52)
    print('RELATÓRIO DE INDEXAÇÃO')
    print('=' * 52)

    for label, key in (
        ('JSONs processados lidos', 'documents_read'),
        ('Produtos indexados', 'products_indexed'),
        ('Termos distintos', 'distinct_terms'),
        ('Listas de ocorrência', 'postings'),
        ('Ocorrências de termos', 'term_occurrences'),
        ('Tamanho do índice (bytes)', 'index_file_bytes'),
        ('Tempo (segundos)', 'elapsed_seconds'),
        ('Produtos/segundo', 'products_per_second'),
    ):
        print(f'{label + ":":30} {stats[key]}')
    
    print('-' * 52)
    for field, missing in stats.get('missing_attributes', {}).items():
        print(f'{"Sem " + field + ":":30} {missing}')
    
    print('=' * 52)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print_report(build_index())
