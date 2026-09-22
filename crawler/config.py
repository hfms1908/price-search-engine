from pathlib import Path


# Diretórios
RAW_DIR = Path("data/raw")

# Limites da coleta
MAX_DOCUMENTS = 100
MAX_STORAGE_GB = 20
MAX_EXECUTION_HOURS = 24

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