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

    for domain in allowed_domains:
        domain = domain.lower()

        if (hostname == domain or hostname.endswith(f".{domain}")):
            return True
    
    return False


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


def is_blocked_page(html: str) -> bool:
    indicators = (
        "sec-if-cpt-container",
        "scf-akamai-protected-by",
        "Powered and protected by",
    )

    html_lower = html.lower()

    return any(
        indicator.lower() in html_lower
        for indicator in indicators
    )