import logging
import time

from collections import deque
from urllib.parse import urljoin, urldefrag, urlparse
from urllib.robotparser import RobotFileParser

import requests

from bs4 import BeautifulSoup

from crawler.stats import CrawlStats, StopReason
from crawler.storage import (
    save_document,
    document_exists,
    StorageError,
    get_storage_size,
)

from crawler.seeds import (
    SEED_URLS,
    ALLOWED_DOMAINS,
    get_source,
)

from crawler.filters import (
    should_crawl,
    is_allowed_content_type,
    is_blocked_page,
)

from crawler.config import (
    MAX_DOCUMENTS,
    MAX_STORAGE_GB,
    MAX_EXECUTION_HOURS,
    MAX_REQUESTS,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    RESPECT_ROBOTS_TXT,
    REQUEST_HEADERS,
    CollectionMode,
    COLLECTION_MODE,
)


logger = logging.getLogger("crawler")

logging.basicConfig(level=logging.INFO, format="[Crawler] %(levelname)s  %(message)s")


def get_encoding(response: requests.Response) -> str:
    """
    Obtém o encoding da resposta HTTP.
    """

    if response.encoding:
        return response.encoding

    if response.apparent_encoding:
        return response.apparent_encoding

    return "utf-8"


def extract_links(html: str, base_url: str) -> list[str]:
    """
    Extrai links do HTML utilizando Beautiful Soup.
    """

    soup = BeautifulSoup(html, "html.parser")

    links = []

    for element in soup.find_all("a", href=True):
        href = element.get("href")

        if not href:
            continue

        absolute_url = urljoin(base_url, href)

        # Remove fragmentos como #produto.
        absolute_url, _ = urldefrag(absolute_url)

        links.append(absolute_url)

    return links


def get_robot_parser(url: str, cache: dict[str, RobotFileParser]) -> RobotFileParser:
    """
    Obtém e mantém em cache o robots.txt de cada domínio.
    """

    parsed_url = urlparse(url)

    base_url = (
        f"{parsed_url.scheme}://{parsed_url.netloc}"
    )

    if base_url in cache:
        return cache[base_url]

    robots_url = urljoin(base_url, "/robots.txt")

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        parser.read()

    except Exception as error:
        logger.warning(f"Não foi possível ler robots.txt de {base_url}: {error}")

    cache[base_url] = parser

    return parser


def can_fetch(url: str, robots_cache: dict[str, RobotFileParser]) -> bool:
    """
    Verifica se a URL pode ser coletada segundo robots.txt.
    """

    if not RESPECT_ROBOTS_TXT:
        return True

    parser = get_robot_parser(url, robots_cache)

    user_agent = REQUEST_HEADERS.get("User-Agent", "*")

    return parser.can_fetch(user_agent, url)


def create_source_queues(seed_urls: list[str]) -> dict[str, deque[str]]:
    """
    Cria uma fila independente para cada fonte.
    """

    source_queues: dict[str, deque[str]] = {}

    for url in seed_urls:
        source_id = get_source(url)

        if source_id is None:
            logger.warning(f"Fonte não identificada para seed: {url}")
            continue

        if source_id not in source_queues:
            source_queues[source_id] = deque()

        source_queues[source_id].append(url)

    return source_queues


def create_source_rotation(source_queues: dict[str, deque[str]]) -> deque[str]:
    """
    Cria a fila responsável pela alternância entre as fontes.
    """

    return deque(source_queues.keys())


def add_links_to_queues(
    links: list[str],
    source_queues: dict[str, deque[str]],
    source_rotation: deque[str],
    queued_urls: set[str],
    visited_urls: set[str],
) -> None:
    """
    Adiciona os links descobertos à fila correspondente à sua fonte.
    """

    for link in links:

        if (link in visited_urls or link in queued_urls):
            continue

        source_id = get_source(link)

        if source_id is None:
            continue

        if source_id not in source_queues:
            source_queues[source_id] = deque()

        source_queue = source_queues[source_id]

        was_empty = not source_queue

        source_queue.append(link)
        queued_urls.add(link)

        # Se a fonte estava sem URLs e não está
        # participando da rotação, reinsere a fonte.
        if (was_empty and source_id not in source_rotation):
            source_rotation.append(source_id)


def get_next_url(
    source_queues: dict[str, deque[str]],
    source_rotation: deque[str],
) -> tuple[str | None, str | None]:
    """
    Obtém uma URL utilizando round-robin entre as fontes.
    """

    while source_rotation:

        source_id = source_rotation.popleft()

        source_queue = source_queues[source_id]

        if not source_queue:
            continue

        url = source_queue.popleft()

        # Se ainda existem URLs nessa fonte, ela volta para o final da rotação.
        if source_queue:
            source_rotation.append(source_id)

        return source_id, url

    return None, None


def request_handler(
    url: str,
    response: requests.Response,
    stats: CrawlStats,
) -> list[str]:
    """
    Processa uma página e retorna novos links.
    """

    if stats.should_stop():
        return []

    stats.register_request()

    # Verifica se a URL atende aos critérios de coleta.
    if not should_crawl(url, ALLOWED_DOMAINS):
        logger.info(f"URL ignorada pelo filtro: {url}")

        return []

    logger.info(f"Processando: {url}")

    content_type = response.headers.get("content-type", "")

    # Verifica se o conteúdo retornado é HTML.
    if not is_allowed_content_type(content_type):
        logger.info(
            f"Conteúdo ignorado: {url} "
            f"(Content-Type: "
            f"{content_type or 'não informado'})"
        )
        return []

    already_collected = document_exists(url)

    skip_storage = (
        COLLECTION_MODE == CollectionMode.INCREMENTAL
        and already_collected
    )

    if skip_storage:
        logger.info(f"Documento já coletado. Armazenamento ignorado: {url}")

    encoding = get_encoding(response)

    try:
        html = response.content.decode(encoding, errors="replace")

    except LookupError:
        logger.warning(
            f"Encoding desconhecido "
            f"'{encoding}' em {url}. "
            f"Utilizando UTF-8."
        )

        encoding = "utf-8"

        html = response.content.decode(encoding, errors="replace")

    # Verifica páginas de bloqueio.
    if is_blocked_page(html):
        logger.warning(f"Página de proteção/bloqueio detectada: {url}")
        return []

    # Armazena apenas quando necessário.
    if not skip_storage:

        if stats.should_stop():
            return []

        try:
            metadata = save_document(
                url=url,
                html=html,
                encoding=encoding,
                content_type=content_type,
                status_code=response.status_code,
            )

        except StorageError as error:
            stats.register_storage_error()
            logger.error(str(error))
            raise

        if already_collected:
            stats.register_updated_document(url, metadata["size_bytes"])

        else:
            stats.register_document(url, metadata["size_bytes"])

        logger.info(
            f"Documento salvo: "
            f"{metadata['html_file']} "
            f"({stats.documents_added}/"
            f"{MAX_DOCUMENTS})"
        )

    # Verifica novamente os limites antes de extrair os links.
    if stats.should_stop():
        logger.info(f"Critério de parada atingido: {stats.stop_reason.name}")
        return []

    links = extract_links(html, url)

    filtered_links = [
        link
        for link in links
        if should_crawl(link, ALLOWED_DOMAINS)
    ]

    stats.register_links(
        source_url=url,
        discovered=len(links),
        accepted=len(filtered_links),
    )

    return filtered_links


def fetch_url(session: requests.Session, url: str) -> requests.Response | None:

    for attempt in range(MAX_RETRIES + 1):

        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)

        except requests.RequestException as error:
            logger.warning(f"Erro ao acessar {url}: {error}")

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            return None

        if response.status_code in {
            429,
            500,
            502,
            503,
            504,
        }:
            logger.warning(
                f"HTTP {response.status_code} "
                f"em {url}. "
                f"Tentativa {attempt + 1}/"
                f"{MAX_RETRIES + 1}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
                continue

        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            logger.warning(f"Erro ao acessar {url}: {error}")

            return None

        return response

    return None


def main() -> None:

    # Tamanho em bytes dos documetnos já armazeanados.
    initial_storage_bytes = get_storage_size()

    stats = CrawlStats(
        max_documents=MAX_DOCUMENTS,
        max_storage_bytes=(MAX_STORAGE_GB * (1024 ** 3)),
        max_execution_seconds=(MAX_EXECUTION_HOURS* 3600),
        initial_storage_bytes=(initial_storage_bytes),
    )

    # Verifica se algum limite já foi atingido antes da coleta.
    if stats.should_stop():
        print(stats.summary())
        return

    session = requests.Session()

    # session.headers.update(REQUEST_HEADERS)

    # Fronteira de URLs.
    source_queues = create_source_queues(SEED_URLS)

    # Fila responsável pela alternância entre as fontes.
    source_rotation = create_source_rotation(source_queues)

    # Evita inserir repetidamente a mesma URL na fronteira.
    queued_urls = set(SEED_URLS)

    # URLs que já tiveram uma tentativa de requisição nesta execução.
    visited_urls = set()

    robots_cache = {}

    start_time = time.monotonic()

    # Momento da última requisição de cada fonte.
    last_request_time: dict[str, float] = {}

    while source_rotation:

        if stats.should_stop():
            break

        if (stats.requests_processed >= MAX_REQUESTS):
            stats.register_stop_reason(StopReason.MAX_REQUESTS)
            break

        elapsed = (time.monotonic() - start_time)

        if elapsed >= (MAX_EXECUTION_HOURS * 3600):
            stats.register_stop_reason(StopReason.MAX_EXECUTION_TIME)
            break

        source_id, url = get_next_url(source_queues, source_rotation)

        if url is None:
            break

        if url in visited_urls:
            continue

        visited_urls.add(url)

        if not should_crawl(url, ALLOWED_DOMAINS):
            continue

        if not can_fetch(url, robots_cache):
            logger.info(f"URL bloqueada pelo robots.txt: {url}"
            )
            continue

        # logger.info(f"Fonte selecionada: {source_id}")

        last_request = last_request_time.get(source_id)

        if last_request is not None:
            elapsed = time.monotonic() - last_request

            remaining_delay = REQUEST_DELAY_SECONDS - elapsed

            if remaining_delay > 0:
                time.sleep(remaining_delay)

        try:
            response = fetch_url(session, url)

            last_request_time[source_id] = time.monotonic()

            if response is None:
                continue

        except requests.RequestException as error:
            
            logger.warning(f"Erro ao acessar {url}: {error}")
            
            continue

        new_links = request_handler(url=url, response=response, stats=stats)

        add_links_to_queues(
            links=new_links,
            source_queues=source_queues,
            source_rotation=source_rotation,
            queued_urls=queued_urls,
            visited_urls=visited_urls,
        )

    print(stats.summary())


if __name__ == "__main__":
    main()