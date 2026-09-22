import asyncio

from crawlee.crawlers import ParselCrawler, ParselCrawlingContext

from crawler.encoding import resolve_encoding
from crawler.storage import save_document
from crawler.stats import CrawlStats, StopReason
from crawler.seeds import SEED_URLS

from crawler.config import (
    MAX_DOCUMENTS,
    MAX_STORAGE_GB,
    MAX_EXECUTION_HOURS,
    RESPECT_ROBOTS_TXT,
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

    context.log.info(f"Processando: {url}")

    content = await context.http_response.read()

    encoding = resolve_encoding(context)

    try:
        html = content.decode(encoding, errors="replace")
    
    except LookupError:
        context.log.warning(
            f"Encoding desconhecido '{encoding}' em {url}. Utilizando UTF-8."
        )

        encoding = "utf-8"

        html = content.decode(encoding, errors="replace")

    async with stats_lock:

        try:
            metadata = save_document(
                url=url,
                html=html,
                encoding=encoding,
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

    if stats.should_stop():
        context.log.info(
            f"Critério de parada atingido: "
            f"{stats.stop_reason.name}"
        )
        return

    # Descobre novos links
    await context.enqueue_links()


async def main() -> None:

    stats = CrawlStats(
        max_documents=MAX_DOCUMENTS,
        max_storage_bytes=MAX_STORAGE_GB * (1024 ** 3),
        max_execution_seconds=MAX_EXECUTION_HOURS * 3600,
    )

    stats_lock = asyncio.Lock()

    crawler = ParselCrawler(
        max_requests_per_crawl=MAX_DOCUMENTS,
        respect_robots_txt_file=RESPECT_ROBOTS_TXT,
    )


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