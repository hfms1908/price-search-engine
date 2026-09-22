import asyncio

from crawlee.crawlers import ParselCrawler, ParselCrawlingContext

from crawler.encoding import resolve_encoding
from crawler.storage import save_document
from crawler.config import (
    MAX_DOCUMENTS,
    MAX_STORAGE_GB,
    MAX_EXECUTION_HOURS,
    RESPECT_ROBOTS_TXT,
)


async def main() -> None:

    crawler = ParselCrawler(
        max_requests_per_crawl=MAX_DOCUMENTS,
        respect_robots_txt_file=RESPECT_ROBOTS_TXT,
    )

    @crawler.router.default_handler
    async def request_handler(context: ParselCrawlingContext) -> None:

        url = context.request.url

        context.log.info(f"Processando: {url}")

        # HTML recebido pelo crawler
        content = await context.http_response.read()

        encoding = resolve_encoding(context)

        try:
            html = content.decode(
                encoding,
                errors="replace",
            )
        except LookupError:
            context.log.warning(
                f"Encoding desconhecido '{encoding}' em {url}. Utilizando UTF-8."
            )

            encoding = "utf-8"

            html = content.decode(
                encoding,
                errors="replace",
            )

        metadata = save_document(
            url=url,
            html=html,
            encoding=encoding,
            status_code=context.http_response.status_code,
        )

        context.log.info(
            f"Documento salvo: {metadata['html_file']}"
        )

        # Descobre novos links
        await context.enqueue_links()

    await crawler.run(
        [
            "https://books.toscrape.com/"
        ]
    )


if __name__ == "__main__":
    asyncio.run(main())