"""Ranqueamento vetorial TF-IDF ponderado por campo e cosseno."""
import math
from collections import Counter, defaultdict
from collections.abc import Mapping
from search.config import FIELD_WEIGHTS


def tf_weight(frequency: float) -> float:
    """TF suavizado: 1 + log(tf), com zero para ausência."""
    return 1.0 + math.log2(frequency) if frequency > 0 else 0.0


class VectorRanker:
    """Pré-calcula normas dos documentos uma única vez por índice carregado."""

    def __init__(self, inverted_index: Mapping, document_ids, field_weights=None):
        self.index = inverted_index
        self.document_ids = set(document_ids)
        self.weights = dict(FIELD_WEIGHTS if field_weights is None else field_weights)
        
        if (not self.weights or
            any(not isinstance(w, (int, float))
                or not math.isfinite(w)
                or w < 0
                for w in self.weights.values()
            )
        ):
            raise ValueError('Pesos de campo devem ser números finitos não negativos')
        
        self.n = len(self.document_ids)
        self.norms_squared = defaultdict(float)
        self.idf = {}
        
        for term, postings in inverted_index.items():
            df = len(set(postings) & self.document_ids)
            if not df: continue
            
            idf = math.log2((self.n + 1) / (df + 1)) + 1
            self.idf[term] = idf
            
            for doc_id, fields in postings.items():
                if doc_id not in self.document_ids: continue
                
                weighted_tf = self._weighted_tf(fields)
                self.norms_squared[doc_id] += (weighted_tf * idf) ** 2

    def _weighted_tf(self, fields: dict[str, int]) -> float:
        """Calcula a frequência ponderada pelos pesos dos campos."""
        return sum(
            self.weights.get(field, 0) * tf_weight(freq)
            for field, freq in fields.items()
            if freq > 0
        )
    
    def rank(self, terms: list[str], candidates) -> list[tuple[str, float]]:
        """Retorna (doc_id, cosseno), em ordem decrescente; exclui score zero."""
        counts = Counter(terms)
        
        query_weights = {
            term: tf_weight(freq) * self.idf[term]
            for term, freq in counts.items()
            if term in self.idf
        }
        
        query_norm = math.sqrt(sum(value ** 2 for value in query_weights.values()))
        if not query_norm:
            return []
        
        candidates = set(candidates) & self.document_ids
        dots = defaultdict(float)
        
        for term, query_weight in query_weights.items():
            for doc_id, fields in self.index[term].items():
                if doc_id not in candidates: continue
                
                weighted_tf = self._weighted_tf(fields)
                dots[doc_id] += query_weight * weighted_tf * self.idf[term]
        
        results = []
        
        for doc_id, dot in dots.items():
            norm = math.sqrt(self.norms_squared[doc_id])
            
            if norm and dot > 0:
                results.append((doc_id, min(1.0, dot / (query_norm * norm))))
        
        return sorted(results, key=lambda item: (-item[1], int(item[0]) if item[0].isdigit() else item[0]))
