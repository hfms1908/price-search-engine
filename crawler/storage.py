import hashlib
import json
from datetime import datetime
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
    content_type: str,
    status_code: int,
) -> dict[str, Any]:
    """Salva o HTML coletado e seus metadados."""

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    collected_at = datetime.now()

    document_id = generate_document_id(url)

    base_name = document_id

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

        first_collected_at = collected_at.isoformat(),

        metadata = {
            "document_id": document_id,
            "url": url,
            "first_collected_at": first_collected_at,
            "last_collected_at": first_collected_at,
            "status_code": status_code,
            "content_type": content_type,
            "original_encoding": encoding,
            "stored_encoding": "utf-8",
            "size_bytes": size_bytes,
            "html_file": html_filename,
        }

        if json_path.exists():
            try:
                old_metadata = json.loads(
                    json_path.read_text(encoding="utf-8")
                )

                first_collected_at = old_metadata.get(
                    "first_collected_at",
                    first_collected_at,
                ),

            except (json.JSONDecodeError):
                pass

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


def document_exists(url: str) -> bool:
    document_id = generate_document_id(url)

    html_path = RAW_DIR / f"{document_id}.html"
    json_path = RAW_DIR / f"{document_id}.json"

    return html_path.exists() and json_path.exists()


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