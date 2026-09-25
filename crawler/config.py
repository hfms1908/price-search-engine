from pathlib import Path

# Diretórios
RAW_DIR = Path("data/raw")

# Timeout
REQUEST_TIMEOUT = 10

# Tentativas de requisição
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5

# Limites da coleta e requisições
MAX_DOCUMENTS = 50_000
MAX_STORAGE_GB = 100
MAX_EXECUTION_HOURS = 24
MAX_REQUESTS = 10 * MAX_DOCUMENTS

# Intervalo mínimo entre requisições no mesmo domínio
REQUEST_DELAY_SECONDS = 3

# Políticas de acesso
RESPECT_ROBOTS_TXT = True

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/webp,*/*;q=0.8"
    ),
}

# REQUEST_HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) "
#         "Gecko/20100101 Firefox/143.0"
#     ),
#     "Accept": (
#         "text/html,application/xhtml+xml,"
#         "application/xml;q=0.9,"
#         "image/avif,image/webp,*/*;q=0.8"
#     ),
#     "Accept-Language": (
#         "pt-BR,pt;q=0.9,en-US;q=0.7,en;q=0.5"
#     ),
#     "Upgrade-Insecure-Requests": "1",
# }