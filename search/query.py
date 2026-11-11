"""Tokenização das consultas consistente com a indexação."""
from indexer.tokenizer import tokenize


def query_terms(query: str) -> list[str]:
    return tokenize(query)
