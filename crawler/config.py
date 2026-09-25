from pathlib import Path

# Diretórios
RAW_DIR = Path("data/raw")

# Timeout
REQUEST_TIMEOUT = 10

# Tentativas de requisição
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# Limites da coleta e requisições
MAX_DOCUMENTS = 50_000_000
MAX_STORAGE_GB = 20
MAX_EXECUTION_HOURS = 24
MAX_REQUESTS = 10 * MAX_DOCUMENTS

# Intervalo mínimo entre requisições no mesmo domínio
REQUEST_DELAY_SECONDS = 3

# Políticas de acesso
RESPECT_ROBOTS_TXT = True