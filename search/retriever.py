"""Recuperação booleana usando diretamente as listas invertidas."""
from collections.abc import Mapping


def boolean_retrieve(inverted_index: Mapping, terms: list[str],
                     operator: str = 'AND', universe=None) -> set[str]:
    """AND: interseção; OR: união; NOT: complemento no universo informado.

    NOT significa documentos que não contêm NENHUM dos termos consultados.
    """
    operator = operator.upper()

    if operator not in {'AND', 'OR', 'NOT'}:
        raise ValueError('Operador booleano inválido: use AND, OR ou NOT')
    
    if not terms:
        return set()
    
    postings = [set(inverted_index.get(term, {})) for term in terms]
    
    if operator == 'AND':
        return set.intersection(*postings)
    
    matched = set.union(*postings)
    
    if operator == 'OR':
        return matched
    
    if universe is None:
        raise ValueError('O operador NOT exige o universo de documentos')
    
    return set(universe) - matched
