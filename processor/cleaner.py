"""Extrai texto legível preservando informações do produto."""
import re
from bs4 import BeautifulSoup

REMOVE_TAGS = ('script', 'style', 'noscript', 'svg', 'iframe', 'template')
NOISE_SELECTORS = ('nav', 'footer', 'header', '[role="navigation"]', '[aria-label="breadcrumb"]', '.newsletter', '#newsletter', '.cookie-banner')


def clean_html(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    for tag in soup.find_all(REMOVE_TAGS):
        tag.decompose()
    for tag in soup.select(', '.join(NOISE_SELECTORS)):
        tag.decompose()
    # Não limitar a <main>: em várias lojas o produto fica fora desse elemento.
    root = soup.body or soup
    text = re.sub(r'\s+', ' ', root.get_text(' ', strip=True)).strip()
    return {'title': title, 'text': text}
