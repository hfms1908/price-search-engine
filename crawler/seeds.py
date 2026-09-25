import random

from urllib.parse import urlparse


SOURCES = {
    "magazineluiza": {
        "name": "Magazine Luiza",
        "seed": "https://www.magazineluiza.com.br/busca/smartphone/",
        "domain": "magazineluiza.com.br",
    },
    "kabum": {
        "name": "KaBum",
        "seed": "https://www.kabum.com.br/celular-smartphone/smartphones",
        "domain": "kabum.com.br",
    },
    "fastshop": {
        "name": "Fast Shop",
        "seed": (
            "https://site.fastshop.com.br/"
            "celular-tablet-e-smartwatch/celular-e-smartphone"
        ),
        "domain": "fastshop.com.br",
    },
    "americanas": {
        "name": "Americanas",
        "seed": "https://www.americanas.com.br/celulares-e-smartphones",
        "domain": "americanas.com.br",
    },
    "mercadolivre": {
        "name": "Mercado Livre",
        "seed": "https://www.mercadolivre.com.br/c/celulares-e-telefones",
        "domain": "mercadolivre.com.br",
    },
    "extra": {
        "name": "Extra",
        "seed": (
            "https://www.extra.com.br/"
            "c/telefones-e-celulares/smartphones?filtro=c38_c326"
        ),
        "domain": "extra.com.br",
    },
    "casasbahia": {
        "name": "Casas Bahia",
        "seed": (
            "https://www.casasbahia.com.br/"
            "c/telefones-e-celulares?filtro=categoria-c38_c326"
        ),
        "domain": "casasbahia.com.br",
    },
    "amazon": {
        "name": "Amazon",
        "seed": (
            "https://www.amazon.com.br/"
            "gp/browse.html?node=16243890011"
            "&ref_=nav_em__wireless_smartphones_0_2_16_3"
        ),
        "domain": "amazon.com.br",
    },
    "samsung": {
        "name": "Samsung",
        "seed": "https://www.samsung.com/br/smartphones/all-smartphones/",
        "domain": "samsung.com",
    },
    "pontofrio": {
        "name": "Ponto Frio",
        "seed": (
            "https://www.pontofrio.com.br/"
            "c/telefones-e-celulares/smartphones?filtro=categoria-c38_c326"
        ),
        "domain": "pontofrio.com.br",
    },
    "carrefour": {
        "name": "Carrefour",
        "seed": (
            "https://www.carrefour.com.br/"
            "categoria/celulares-smartphones-e-smartwatches"
        ),
        "domain": "carrefour.com.br",
    },
    "oficinadosbits": {
        "name": "Oficina dos Bits",
        "seed": (
            "https://www.oficinadosbits.com.br/"
            "categoria/celulares-e-comunicacao-smartphone/"
        ),
        "domain": "oficinadosbits.com.br",
    },
    "zoom": {
        "name": "Zoom (Comparador)",
        "seed": "https://www.zoom.com.br/celular",
        "domain": "zoom.com.br",
    },
    "buscape": {
        "name": "Buscapé (Comparador)",
        "seed": "https://www.buscape.com.br/celular",
        "domain": "buscape.com.br",
    },
    "kalunga": {
        "name": "Kalunga",
        "seed": "https://www.kalunga.com.br/depto/telefonia/8",
        "domain": "kalunga.com.br",
    },
    "bemol": {
        "name": "Bemol",
        "seed": "https://www.bemol.com.br/celular-e-smartphone",
        "domain": "bemol.com.br",
    },
    "havan": {
        "name": "Havan",
        "seed": "https://www.havan.com.br/celulares-e-smartphones/",
        "domain": "havan.com.br",
    },
    "colombo": {
        "name": "Lojas Colombo",
        "seed": "https://www.colombo.com.br/produto/Smartphone-e-Celular",
        "domain": "colombo.com.br",
    },
    "shopee": {
        "name": "Shopee",
        "seed": "https://shopee.com.br/search?keyword=smartphone",
        "domain": "shopee.com.br",
    },
    "taqui": {
        "name": "taQi e mais",
        "seed": "https://www.taqi.com.br/telefones-e-celulares/celular-smartphone/cat50004",
        "domain": "taqi.com.br",
    },
    "casaevideo": {
        "name": "Casa & Vídeo",
        "seed": "https://www.casaevideo.com.br/telefones-e-celulares",
        "domain": "casaevideo.com.br",
    },
    "motorola": {
        "name": "Motorola",
        "seed": "https://www.motorola.com.br/smartphones",
        "domain": "motorola.com.br",
    },
}

SEED_URLS = [
    source["seed"]
    for source in SOURCES.values()
]

# Embaralha a ordem das URLs sementes
random.shuffle(SEED_URLS)

ALLOWED_DOMAINS = {
    source["domain"]
    for source in SOURCES.values()
}


def get_source(url: str) -> str | None:
    """
    Retorna o identificador da fonte associada à URL.

    Exemplos:
        www.kabum.com.br       -> kabum
        blog.kabum.com.br      -> kabum
        site.fastshop.com.br   -> fastshop

    Retorna None quando a URL não pertence
    a nenhuma fonte configurada.
    """

    hostname = urlparse(url).hostname

    if not hostname:
        return None

    hostname = hostname.lower()

    for source_id, source in SOURCES.items():
        domain = source["domain"].lower()

        if (hostname == domain or hostname.endswith(f".{domain}")):
            return source_id

    return None


def get_source_name(source_id: str) -> str:
    """
    Retorna o nome amigável da fonte.
    """
    if source_id is None:
        return "Desconhecida"

    source = SOURCES.get(source_id)

    if source is None:
        return source_id

    return source["name"]