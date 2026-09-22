import re

from crawlee.crawlers import ParselCrawlingContext


def resolve_encoding(context: ParselCrawlingContext) -> str:
    # 1. Meta tag HTML5: <meta charset="...">
    meta_charset = context.selector.xpath(
        "//meta[@charset]/@charset"
    ).get()

    if meta_charset:
        return meta_charset.strip().lower()

    # 2. Meta tag http-equiv
    meta_content_type = context.selector.xpath(
        '//meta[translate(@http-equiv, '
        '"ABCDEFGHIJKLMNOPQRSTUVWXYZ", '
        '"abcdefghijklmnopqrstuvwxyz")="content-type"]/@content'
    ).get()

    if meta_content_type:
        match = re.search(
            r"charset=([^\s;]+)",
            meta_content_type,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip().lower()

    # 3. Cabeçalho HTTP Content-Type
    header_content_type = context.http_response.headers.get(
        "content-type",
        ""
    )

    if header_content_type:
        match = re.search(
            r"charset=([^\s;]+)",
            header_content_type,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip().lower()

    # 4. Fallback
    return "utf-8"