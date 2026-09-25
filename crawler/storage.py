import hashlib
import json
from datetime import datetime
from typing import Any

from crawler.config import RAW_DIR


class StorageError(Exception):
    """Erro durante o armazenamento de um documento."""
    pass


def generate_document_id(url: str) -> str:
    """Gera um identificador baseado na URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def save_document(
    url: str,
    html: str,
    encoding: str,
    content_type: str,
    status_code: int,
) -> dict[str, Any]:
    """Salva o HTML coletado e seus metadados."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    collected_at = datetime.now()
    document_id = generate_document_id(url)

    # O diretório data/raw começa vazio em cada execução.
    html_filename = f"{document_id}.html"
    json_filename = f"{document_id}.json"

    html_path = RAW_DIR / html_filename
    json_path = RAW_DIR / json_filename

    try:
        html_path.write_text(html, encoding="utf-8")
        size_bytes = html_path.stat().st_size

        metadata = {
            "document_id": document_id,
            "url": url,
            "collected_at": collected_at.isoformat(),
            "status_code": status_code,
            "content_type": content_type,
            "original_encoding": encoding,
            "stored_encoding": "utf-8",
            "size_bytes": size_bytes,
            "html_file": html_filename,
        }

        json_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
    except OSError as error:
        if html_path.exists():
            html_path.unlink()
        if json_path.exists():
            json_path.unlink()
        raise StorageError(f"Erro ao armazenar documento: {url}") from error

    return metadata


def get_storage_size() -> int:
    total_bytes = 0
    if not RAW_DIR.exists():
        return total_bytes

    for file_path in RAW_DIR.glob("*.html"):
        try:
            total_bytes += file_path.stat().st_size
        except OSError:
            continue

    return total_bytes
