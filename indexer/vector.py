"""Pré-cálculo vetorial TF-IDF (logaritmo na base 2) para o índice de ofertas.

Os pesos são compartilhados com o ranqueador para evitar divergências.
"""
import math
from collections import defaultdict
from collections.abc import Mapping
from search.config import FIELD_WEIGHTS

VECTOR_FORMAT_VERSION = 1
TF_FORMULA = '1 + log2(freq) if freq > 0 else 0'
IDF_FORMULA = '1 + log2((N + 1) / (df + 1))'


def tf_weight(frequency: float) -> float:
    return 1.0 + math.log2(frequency) if frequency > 0 else 0.0


def build_vector_index(inverted_index: Mapping, document_ids, field_weights=None) -> dict:
    """Gera IDF e normas L2; mantém compatibilidade numérica com VectorRanker."""
    weights = dict(FIELD_WEIGHTS if field_weights is None else field_weights)
    if not weights or any(
        not isinstance(weight, (int, float)) or isinstance(weight, bool)
        or not math.isfinite(weight) or weight < 0
        for weight in weights.values()
    ):
        raise ValueError('Pesos de campo devem ser números finitos não negativos')

    ids = set(document_ids)
    norms_squared = defaultdict(float)
    idf_values = {}
    n = len(ids)

    for term, postings in inverted_index.items():
        df = len(set(postings) & ids)
        if not df:
            continue
        
        idf = 1.0 + math.log2((n + 1) / (df + 1))
        idf_values[term] = idf
        for doc_id, fields in postings.items():
            if doc_id not in ids:
                continue
            
            weighted_tf = sum(
                weights.get(field, 0) * tf_weight(freq)
                for field, freq in fields.items() if freq > 0
            )
            norms_squared[doc_id] += (weighted_tf * idf) ** 2

    return {
        'format_version': VECTOR_FORMAT_VERSION,
        'tf_formula': TF_FORMULA,
        'idf_formula': IDF_FORMULA,
        'field_weights': weights,
        'document_count': n,
        'idf': idf_values,
        'document_norms': {
            doc_id: math.sqrt(norms_squared[doc_id])
            for doc_id in sorted(ids, key=lambda key: (0, int(key)) if key.isdigit() else (1, key))
        },
    }
