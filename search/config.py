"""Parâmetros do mecanismo de recuperação."""
from indexer.config import INDEX_DIR

FIELD_WEIGHTS = {
    'model': 5.0,
    'name': 4.0,
    'storage_gb': 3.0,
    'ram_gb': 3.0,
    'brand': 2.0,
    'text': 1.0,
}
DEFAULT_LIMIT = 20
