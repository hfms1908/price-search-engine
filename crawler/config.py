from pathlib import Path
from enum import Enum, auto

# Diretórios
RAW_DIR = Path("data/raw")

# Timeout
REQUEST_TIMEOUT = 10

# Tentativas de requisição
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# Limites da coleta e requisições
MAX_DOCUMENTS = 100
MAX_STORAGE_GB = 20
MAX_EXECUTION_HOURS = 24
MAX_REQUESTS = 1_000_000

# Intervalo mínimo entre requisições no mesmo domínio
REQUEST_DELAY_SECONDS = 2

# Políticas de acesso
RESPECT_ROBOTS_TXT = True

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) "
        "Gecko/20100101 Firefox/143.0"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": (
        "pt-BR,pt;q=0.9,en-US;q=0.7,en;q=0.5"
    ),
    "Upgrade-Insecure-Requests": "1",
}


class CollectionMode(Enum):
    INCREMENTAL = auto()
    REFRESH = auto()


COLLECTION_MODE = CollectionMode.INCREMENTAL