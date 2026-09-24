import time

from dataclasses import dataclass, field
from enum import Enum, auto

from crawler.seeds import get_source, get_source_name


class StopReason(Enum):
    NONE = auto()
    MAX_DOCUMENTS = auto()
    MAX_STORAGE = auto()
    MAX_EXECUTION_TIME = auto()
    MAX_REQUESTS = auto()


@dataclass
class CrawlStats:
    max_documents: int
    max_storage_bytes: int
    max_execution_seconds: float

    documents_added: int = 0
    documents_added_by_source: dict[str, int] = field(default_factory=dict)

    requests_processed: int = 0

    storage_bytes: int = 0
    storage_errors: int = 0

    http_errors: dict[int, int] = field(default_factory=dict)

    links_discovered_by_source: dict[str, int] = field(default_factory=dict)
    links_accepted_by_source: dict[str, int] = field(default_factory=dict)
    links_rejected_by_source: dict[str, int] = field(default_factory=dict)

    started_at: float = field(default_factory=time.monotonic)
    
    stop_reason: StopReason = StopReason.NONE

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def register_document(self, url: str, size_bytes: int) -> None:
        self.documents_added += 1
        self.storage_bytes += size_bytes

        source_id = get_source(url)

        self.documents_added_by_source[source_id] = (
            self.documents_added_by_source.get(source_id, 0) + 1
        )

    def register_http_error(self, status_code: int) -> None:
        self.http_errors[status_code] = (
            self.http_errors.get(status_code, 0) + 1
        )

    def register_links(
        self,
        source_url: str,
        discovered: int,
        accepted: int,
    ) -> None:
        source_id = get_source(source_url)

        rejected = discovered - accepted

        self.links_discovered_by_source[source_id] = (
            self.links_discovered_by_source.get(
                source_id,
                0,
            ) + discovered
        )

        self.links_accepted_by_source[source_id] = (
            self.links_accepted_by_source.get(
                source_id,
                0,
            ) + accepted
        )

        self.links_rejected_by_source[source_id] = (
            self.links_rejected_by_source.get(
                source_id,
                0,
            ) + rejected
        )

    def should_stop(self) -> bool:
        if self.documents_added >= self.max_documents:
            self.stop_reason = StopReason.MAX_DOCUMENTS
            return True
        
        if self.storage_bytes >= self.max_storage_bytes:
            self.stop_reason = StopReason.MAX_STORAGE
            return True
        
        if self.elapsed_seconds() >= self.max_execution_seconds:
            self.stop_reason = StopReason.MAX_EXECUTION_TIME
            return True
        
        return False

    def register_request(self) -> None:
        self.requests_processed += 1

    def register_storage_error(self) -> None:
        self.storage_errors += 1

    def register_stop_reason(self, reason: StopReason) -> None:
        self.stop_reason = reason

    def elapsed_hours(self) -> float:
        return self.elapsed_seconds() / 3600

    def summary(self) -> str:
        lines = [
            "\n=========================== RESUMO DA COLETA ===========================",
            f"Requisições processadas: {self.requests_processed}",
            f"Documentos adicionados.: {self.documents_added}",
            f"Erros de armazenamento.: {self.storage_errors}",
            f"Armazenamento total....: {self.storage_bytes / (1024 **3):.6f} GB",
            f"Tempo de execução......: {self.elapsed_hours():.4f} horas",
            f"Motivo da parada.......: {self.stop_reason.name}",
            "\nDocumentos por fonte:",
            f"  {'Fonte':<35}{'Documentos':>12}",
        ]

        if self.documents_added_by_source:
            for source_id in sorted(self.documents_added_by_source):
                source_name = get_source_name(source_id)

                lines.append(
                    f"  {source_name:<35}"
                    f"{self.documents_added_by_source[source_id]:>12}"
                )
        else:
            lines.append("  Nenhum documento armazenado.")

        lines.append("")
        lines.append("Links por fonte:")
        lines.append(
            f"  {'Fonte':<35}"
            f"{'Descobertos':>12}"
            f"{'Aceitos':>10}"
            f"{'Rejeitados':>12}"
        )
        
        all_sourd_ids = (
            set(self.links_discovered_by_source)
            | set(self.links_accepted_by_source)
            | set(self.links_rejected_by_source)
        )
        
        if all_sourd_ids:
            for source_id in sorted(all_sourd_ids):
                lines.append(
                    f"  {get_source_name(source_id):<35}"
                    f"{self.links_discovered_by_source.get(source_id, 0):>12}"
                    f"{self.links_accepted_by_source.get(source_id, 0):>10}"
                    f"{self.links_rejected_by_source.get(source_id, 0):>12}"
                )
        else:
            lines.append("  Nenhum link registrado.")

        lines.append("")
        lines.append("Erros HTTP:")

        if self.http_errors:
            for status_code, count in sorted(self.http_errors.items()):
                lines.append(f"  HTTP {status_code:<3} {count:>6}")
        else:
            lines.append("  Nenhum erro HTTP registrado.")

        lines.append("========================================================================")
        return "\n".join(lines)