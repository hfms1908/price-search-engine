"""Análise léxica comum à indexação e às consultas."""
import re
import unicodedata
from indexer.config import REMOVE_STOPWORDS, STOPWORDS, USE_STEMMING
# Códigos com hífen, números e capacidades permanecem termos únicos.
TOKEN_RE = re.compile(r'\d+(?:\.\d+)?(?:gb|tb|mb)\b|[a-z0-9]+(?:-[a-z0-9]+)*')
CAPACITY_RE = re.compile(r'(?<!\w)(\d+(?:[.,]\d+)?)\s*/?\s*(gb|tb|mb)\b', re.I)


def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKD', str(text or ''))
    text = ''.join(c for c in text if not unicodedata.combining(c)).lower()

    return CAPACITY_RE.sub(lambda m: m.group(1).replace(',', '.') + m.group(2).lower(), text)


def tokenize(text: str, remove_stopwords: bool = REMOVE_STOPWORDS, stemming: bool = USE_STEMMING) -> list[str]:
    terms = TOKEN_RE.findall(normalize(text))
    
    if remove_stopwords:
        terms = [t for t in terms if t not in STOPWORDS]
    
    if stemming:
        try:
            from nltk.stem import RSLPStemmer
            stemmer = RSLPStemmer()
        except (ImportError, LookupError) as exc:
            raise RuntimeError('Stemming exige nltk e o recurso rslp instalado') from exc
        
        # Não radicalizar modelos, capacidades, nomes curtos ou identificadores alfanuméricos.
        terms = [stemmer.stem(t) if t.isalpha() and len(t) > 4 and t not in {'ultra','plus'} else t for t in terms]
    
    return terms
