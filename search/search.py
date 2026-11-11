"""Interface de recuperação para os artefatos JSON gerados pelo indexador.

Executar na raiz do projeto: python -m search.search 'Samsung Galaxy S25 256GB'
"""
import argparse
import json
from pathlib import Path
from search.config import DEFAULT_LIMIT, INDEX_DIR
from search.query import query_terms
from search.ranker import VectorRanker
from search.retriever import boolean_retrieve


class SearchEngine:
    def __init__(self, index_dir=INDEX_DIR, *, field_weights=None):
        directory = Path(index_dir)
        def load(filename):
            return json.loads((directory / filename).read_text(encoding='utf-8'))
        
        self.inverted_index = load('inverted_index.json')
        self.products = load('products.json')
        self.document_map = load('document_map.json')
        
        if set(self.products) != set(self.document_map):
            raise ValueError('products.json e document_map.json não correspondem à mesma indexação')
        
        for term, postings in self.inverted_index.items():
            if not set(postings) <= set(self.products):
                raise ValueError(f'Índice contém doc_id desconhecido no termo {term!r}')
        
        self.ranker = VectorRanker(self.inverted_index, self.products, field_weights)

    def search(self, query: str, *, operator='OR', ranking='vector', limit=DEFAULT_LIMIT):
        """Consulta simples com AND/OR/NOT e ordenação vetorial ou booleana.

        NOT com ranking='boolean' retorna os documentos complementares sem score
        textual. A opção NOT com ranking vetorial é rejeitada porque documentos
        excluídos não contêm os termos e não têm relevância textual positiva.
        """
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError('limit deve ser inteiro não negativo')
        
        operator = operator.upper()
        
        if ranking not in {'vector', 'boolean'}:
            raise ValueError('ranking deve ser vector ou boolean')
        
        if operator == 'NOT' and ranking == 'vector':
            raise ValueError('NOT exige ranking=boolean')
        
        terms = query_terms(query)
        candidates = boolean_retrieve(self.inverted_index, terms, operator, self.products)
        
        if ranking == 'vector':
            scored = self.ranker.rank(terms, candidates)
        else:
            scored = [(doc_id, None) for doc_id in sorted(candidates, key=lambda x: int(x) if x.isdigit() else x)]
        
        results = []
        
        for doc_id, score in scored[:limit]:
            results.append({
                'doc_id': doc_id,
                'score': round(score, 6) if score is not None else None,
                'product_id': self.document_map[doc_id]['product_id'],
                'source_file': self.document_map[doc_id]['source_file'],
                **self.products[doc_id],
            })
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Busca booleana e vetorial no índice de produtos')
    parser.add_argument('query', help='Consulta textual')
    parser.add_argument('--index-dir', type=Path, default=INDEX_DIR)
    parser.add_argument('--operator', choices=['AND', 'OR', 'NOT'], default='OR')
    parser.add_argument('--ranking', choices=['vector', 'boolean'], default='vector')
    parser.add_argument('--limit', type=int, default=DEFAULT_LIMIT)
    
    args = parser.parse_args()
    
    engine = SearchEngine(args.index_dir)
    
    print(json.dumps(
            engine.search(args.query, operator=args.operator, ranking=args.ranking, limit=args.limit),
            ensure_ascii=False, indent=2
        )
    )


if __name__ == '__main__':
    main()
