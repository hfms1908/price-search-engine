"""Métricas da construção do índice e qualidade dos dados de entrada."""
from collections import Counter


def make_statistics(documents_read, products, inverted_index, elapsed):
    postings = sum(len(entries) for entries in inverted_index.values())
    
    occurrences = sum(
        sum(sum(fields.values()) for fields in entries.values())
        for entries in inverted_index.values()
    )
    
    fields = ('brand', 'model', 'ram_gb', 'storage_gb', 'price_brl')
    
    missing = {
        field: sum(
            product.get('attributes', {}).get(field) is None
            for product in products.values()
        )
        for field in fields
    }
    
    sources = Counter(
        product.get('extraction_source') or 'unknown'
        for product in products.values()
    )
    
    return {
        'documents_read': documents_read,
        'products_indexed': len(products),
        'distinct_terms': len(inverted_index),
        'postings': postings,
        'term_occurrences': occurrences,
        'missing_attributes': missing,
        'products_by_extraction_source': dict(sorted(sources.items())),
        'elapsed_seconds': round(elapsed, 4),
        'products_per_second': round(len(products) / elapsed, 2) if elapsed > 0 else 0,
    }
