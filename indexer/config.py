"""Parâmetros independentes da etapa de processamento."""
from pathlib import Path

PROCESSED_DIR = Path('data/processed')
INDEX_DIR = Path('data/index')
USE_STEMMING = False  # Mantido desligado para preservar identificadores comerciais.
REMOVE_STOPWORDS = True
# Stopwords conservadoras; não remove pro, plus, ultra, fe, max, nem termos de modelo.
STOPWORDS = frozenset({'a','as','o','os','de','da','das','do','dos','e','em','na','nas','no','nos','um','uma','uns','umas','com','para','por','que','ao','aos','seu','sua','seus','suas'})
FIELDS = ('name', 'brand', 'model', 'text', 'ram_gb', 'storage_gb')
