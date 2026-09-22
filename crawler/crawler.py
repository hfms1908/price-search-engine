import asyncio

from crawlee.crawlers import (
    BasicCrawlingContext,
    ParselCrawler,
    ParselCrawlingContext
)
from crawlee.request_loaders import ThrottlingRequestManager
from crawlee.storages import RequestQueue
from crawlee import HttpHeaders

from crawler.encoding import resolve_encoding
from crawler.storage import save_document
from crawler.stats import CrawlStats, StopReason
from crawler.seeds import SEED_URLS, ALLOWED_DOMAINS
from crawler.filters import should_crawl, is_allowed_content_type

from crawler.config import (
    MAX_DOCUMENTS,
    MAX_STORAGE_GB,
    MAX_EXECUTION_HOURS,
    RESPECT_ROBOTS_TXT,
    REQUEST_HEADERS,
)


async def request_handler(
    context: ParselCrawlingContext,
    stats: CrawlStats,
    stats_lock: asyncio.Lock,
) -> None:

    if stats.should_stop():
        return

    async with stats_lock:
        stats.register_request()

    url = context.request.url

    # Verifica se a URL atende aos critérios de coleta
    if not should_crawl(url, ALLOWED_DOMAINS):
        context.log.info(f"URL ignorada pelo filtro: {url}")
        return

    context.log.info(f"Processando: {url}")

    # Verifica se o conteúdo retornado é HTML
    content_type = context.http_response.headers.get("content-type", "")

    if not is_allowed_content_type(content_type):
        context.log.info(
            f"Conteúdo ignorado: {url} "
            f"(Content-Type: {content_type or 'não informado'})"
        )
        return

    # Lê o conteúdo da resposta
    content = await context.http_response.read()

    encoding = resolve_encoding(context)

    # Decodifica o conteúdo
    try:
        html = content.decode(encoding, errors="replace")
    
    except LookupError:
        context.log.warning(
            f"Encoding desconhecido '{encoding}' em {url}. Utilizando UTF-8."
        )

        encoding = "utf-8"

        html = content.decode(encoding, errors="replace")

    # Região crítica: verifica limite, salva e contabiliza o documento
    async with stats_lock:

        try:
            metadata = save_document(
                url=url,
                html=html,
                encoding=encoding,
                content_type=content_type,
                status_code=context.http_response.status_code,
            )
        
        except StorageError as error:
            stats.register_storage_error()
            context.log.error(str(error))
            raise

        stats.register_document(metadata["size_bytes"])

        context.log.info(
            f"Documento salvo: {metadata['html_file']} "
            f"({stats.documents_saved}/{MAX_DOCUMENTS})"
        )

    # Verifica se algum limite foi atingido
    if stats.should_stop():
        context.log.info(
            f"Critério de parada atingido: "
            f"{stats.stop_reason.name}"
        )
        return

    links = await context.extract_links(strategy="all")

    filtered_links = [
        request
        for request in links
        if should_crawl(request.url, ALLOWED_DOMAINS)
    ]

    await context.add_requests(filtered_links)


async def main() -> None:

    stats = CrawlStats(
        max_documents=MAX_DOCUMENTS,
        max_storage_bytes=MAX_STORAGE_GB * (1024 ** 3),
        max_execution_seconds=MAX_EXECUTION_HOURS * 3600,
    )

    stats_lock = asyncio.Lock()

    request_queue = await RequestQueue.open()

    request_manager = ThrottlingRequestManager(
        request_queue,
        domains=list(ALLOWED_DOMAINS),
        request_manager_opener=RequestQueue.open,
    )

    crawler = ParselCrawler(
        request_manager=request_manager,
        max_requests_per_crawl=MAX_DOCUMENTS,
        respect_robots_txt_file=RESPECT_ROBOTS_TXT,
    )

    @crawler.pre_navigation_hook
    async def setup_request(context: BasicCrawlingContext,) -> None:
        context.request.headers |= HttpHeaders(REQUEST_HEADERS)

    @crawler.router.default_handler
    async def handler(context: ParselCrawlingContext) -> None:
        await request_handler(
            context,
            stats,
            stats_lock,
        )

    try:
        async with asyncio.timeout(MAX_EXECUTION_HOURS * 3600):
            await crawler.run(SEED_URLS)

    except TimeoutError:

        async with stats_lock:
            stats.register_stop_reason(StopReason.MAX_EXECUTION_TIME)

        print(
            f"Tempo máximo de execução atingido: "
            f"{MAX_EXECUTION_HOURS} horas."
        )

    print(stats.summary())


if __name__ == "__main__":
    asyncio.run(main())