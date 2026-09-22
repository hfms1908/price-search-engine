import re
import asyncio
import hashlib
from datetime import datetime
from pathlib import Path

from crawlee.crawlers import ParselCrawler, ParselCrawlingContext

from crawler.encoding import resolve_encoding
from crawler.config import (
    MAX_DOCUMENTS,
    MAX_STORAGE_GB,
    MAX_EXECUTION_HOURS,
    RESPECT_ROBOTS_TXT,
)


RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)


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

        # Cria um nome único para o arquivo
        url_hash = hashlib.sha256(
            url.encode("utf-8")
        ).hexdigest()[:16]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = RAW_DIR / f"{timestamp}_{url_hash}.html"

        # Salva o HTML bruto
        filename.write_text(
            html,
            encoding="utf-8"
        )

        context.log.info(
            f"Arquivo salvo: {filename}"
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