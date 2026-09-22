from pathlib import PurePosixPath
from urllib.parse import urlparse


ALLOWED_EXTENSIONS = {
    "",
    ".html",
    ".htm",
}


def is_allowed_domain(url: str, allowed_domains: set[str]) -> bool:
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname

    if hostname is None:
        return False

    hostname = hostname.lower()

    return hostname in {
        domain.lower()
        for domain in allowed_domains
    }


def is_allowed_extension(url: str) -> bool:
    parsed_url = urlparse(url)

    extension = PurePosixPath(parsed_url.path).suffix.lower()

    return extension in ALLOWED_EXTENSIONS


def should_crawl(url: str, allowed_domains: set[str]) -> bool:

    if not is_allowed_domain(
        url,
        allowed_domains,
    ):
        return False

    if not is_allowed_extension(url):
        return False

    return True


def is_allowed_content_type(content_type: str) -> bool:
    if not content_type:
        return False

    media_type = content_type.split(";", 1)[0].strip().lower()

    return media_type in {
        "text/html",
        "text/xml",
        "application/xhtml+xml",
    }