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

    def __init__(self, inverted_index: Mapping, document_ids, field_weights=None,
                 vector_index: Mapping | None = None):
        self.index = inverted_index
        self.document_ids = set(document_ids)
        self.weights = dict(FIELD_WEIGHTS if field_weights is None else field_weights)
        
        if (not self.weights or
            any(not isinstance(w, (int, float))
                or isinstance(w, bool)
                or not math.isfinite(w)
                or w < 0
                for w in self.weights.values()
            )
        ):
            raise ValueError('Pesos de campo devem ser números finitos não negativos')
        
        self.n = len(self.document_ids)
        self.norms_squared = defaultdict(float)
        self.idf = {}

        if vector_index is not None:
            self._load_precomputed(vector_index)
        else:
            self._calculate_vectors()

    def _load_precomputed(self, vector_index: Mapping) -> None:
        """Carrega IDF e normas previamente calculados pelo indexador."""
        from indexer.vector import VECTOR_FORMAT_VERSION, TF_FORMULA, IDF_FORMULA

        if (vector_index.get('format_version') != VECTOR_FORMAT_VERSION
            or vector_index.get('tf_formula') != TF_FORMULA
            or vector_index.get('idf_formula') != IDF_FORMULA):
            raise ValueError('vector_index.json possui versão ou fórmulas incompatíveis')
        if vector_index.get('field_weights') != self.weights:
            raise ValueError('vector_index.json possui pesos de campos incompatíveis')
        if vector_index.get('document_count') != self.n:
            raise ValueError('vector_index.json possui quantidade de documentos incompatível')

        idf = vector_index.get('idf')
        norms = vector_index.get('document_norms')
        if not isinstance(idf, dict) or set(idf) != set(self.index):
            raise ValueError('vector_index.json possui vocabulário incompatível')
        if not isinstance(norms, dict) or set(norms) != self.document_ids:
            raise ValueError('vector_index.json possui documentos incompatíveis')
        if any(not isinstance(v, (int, float)) or isinstance(v, bool)
               or not math.isfinite(v) or v <= 0 for v in idf.values()):
            raise ValueError('vector_index.json possui valores IDF inválidos')
        if any(not isinstance(v, (int, float)) or isinstance(v, bool)
               or not math.isfinite(v) or v < 0 for v in norms.values()):
            raise ValueError('vector_index.json possui normas inválidas')

        self.idf = dict(idf)
        self.norms_squared = {doc_id: norm * norm for doc_id, norm in norms.items()}

    def _calculate_vectors(self) -> None:
        """Compatibilidade com índices antigos que não possuem vector_index.json."""
        for term, postings in self.index.items():
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
