"""Tokenização e agrupamento de consultas, consistentes com a indexação."""
from indexer.tokenizer import tokenize


def query_groups(query: str) -> list[list[str]]:
    """Aspas simples ou duplas agrupam termos com AND interno.

    Qualquer tipo de aspas pode fechar o grupo. Texto sem aspas mantém
    cada termo como um grupo independente para o operador selecionado.
    """
    groups = []
    outside = []
    quoted = []
    inside = False
    
    def flush_outside():
        for term in tokenize(''.join(outside)):
            groups.append([term])
        outside.clear()

    for char in query:
        if char in ('"', "'"):
            if inside:
                terms = tokenize(''.join(quoted))
                if terms:
                    groups.append(terms)
                quoted.clear()
                inside = False
            else:
                flush_outside()
                inside = True
        elif inside:
            quoted.append(char)
        else:
            outside.append(char)

    if inside:
        # Aspas não fechadas: interpreta o restante como grupo.
        terms = tokenize(''.join(quoted))
        if terms:
            groups.append(terms)
    
    flush_outside()
    
    return groups


def query_terms(query: str) -> list[str]:
    return tokenize(query)
