from pathlib import Path

RAW_DIR = Path('data/raw')
PROCESSED_DIR = Path('data/processed')
MIN_TEXT_LENGTH = 40

# Número de processos: núcleos físicos menos um, mantendo ao menos um worker.
# None permite detectar automaticamente; um inteiro positivo força o valor.
MAX_WORKERS = None
# Número de documentos por tarefa. Um documento favorece o balanceamento.
CHUNK_SIZE = 1


# Vocabulário compartilhado de marcas e famílias de modelos.
BRANDS = {
    'samsung': 'Samsung',
    'apple': 'Apple',
    'motorola': 'Motorola',
    'xiaomi': 'Xiaomi',
    'redmi': 'Redmi',
    'poco': 'POCO',
    'realme': 'Realme',
    'infinix': 'Infinix',
    'asus': 'Asus',
    'oppo': 'Oppo',
    'honor': 'Honor',
    'jovi': 'Jovi',
    'vivo': 'Vivo',
    'hmd': 'HMD',
    'nokia': 'Nokia',
    'huawei': 'Huawei',
    'positivo': 'Positivo',
    'multilaser': 'Multilaser',
    'intelbras': 'Intelbras',
    'philco': 'Philco',
    'tcl': 'TCL',
    'zte': 'ZTE',
    'lenovo': 'Lenovo',
    'obabox': 'Obabox',
    'blackview': 'Blackview',
}

# Expressões regulares de famílias de modelos, extensíveis por fabricante.
MODEL_PATTERNS = {
    'galaxy': 'galaxy\\s+(?:s\\d{1,2}(?:\\s+(?:ultra|plus|fe))?|a\\d{1,2}|z\\s*(?:flip|fold)\\d*|tab\\s+[a-z]\\d*|m\\d{1,2})',
    'iphone': 'iphone\\s*\\d{1,2}(?:\\s+(?:pro\\s+max|pro|plus))?',
    'ipad': 'ipad(?:\\s+(?:air|pro|mini))?',
    'moto': 'moto\\s*g\\d{1,3}',
    'redmi': 'redmi\\s+(?:note\\s*)?\\d{1,2}',
    'poco': 'poco\\s*[a-z]\\d{1,2}',
    'samsung_a': r'samsung\s+a\d{2,3}',
    'motorola_edge': r'(?:motorola\s+)?edge\s+\d{2,3}(?:\s+(?:pro|fusion|neo|ultra))?',
    'realme': r'realme\s+(?:c\d{2,3}|\d{1,2}(?:\s+pro)?)',
    'infinix': r'infinix\s+(?:note|hot|smart|gt|zero)\s*\d{1,3}[a-z]?',
    'positivo': r'positivo\s+p\d{2,3}',
}
