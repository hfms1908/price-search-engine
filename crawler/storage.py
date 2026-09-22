import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from crawler.config import RAW_DIR


class StorageError(Exception):
    """Erro durante o armazenamento de um documento."""
    pass


def generate_document_id(url: str) -> str:
    """Gera um identificador único baseado na URL."""

    return hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:16]


def save_document(
    url: str,
    html: str,
    encoding: str,
    status_code: int,
) -> dict[str, Any]:
    """Salva o HTML coletado e seus metadados."""

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    collected_at = datetime.now()

    document_id = generate_document_id(url)

    timestamp = collected_at.strftime(
        "%Y%m%d_%H%M%S"
    )

    base_name = (
        f"{timestamp}_{document_id}"
    )

    html_filename = f"{base_name}.html"
    json_filename = f"{base_name}.json"

    html_path = RAW_DIR / html_filename
    json_path = RAW_DIR / json_filename

    try:
        # Salva o HTML normalizado em UTF-8
        html_path.write_text(
            html,
            encoding="utf-8",
        )

        # Obtém o tamanho real do arquivo salvo
        size_bytes = html_path.stat().st_size

        metadata = {
            "document_id": document_id,
            "url": url,
            "collected_at": collected_at.isoformat(),
            "status_code": status_code,
            "original_encoding": encoding,
            "stored_encoding": "utf-8",
            "size_bytes": size_bytes,
            "html_file": html_filename,
        }

        json_path.write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=4,
            ),
            encoding="utf-8",
        )
    except OSError as error:
        # Remove HTML incompleto ou sem JSON
        if html_path.exists():
            html_path.unlink()

        if json_path.exists():
            json_path.unlink()

        raise StorageError(
            f"Erro ao armazenar documento: {url}"
        ) from error

    return metadata