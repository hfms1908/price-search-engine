import time

from dataclasses import dataclass, field
from enum import Enum, auto
from urllib.parse import urlparse


class StopReason(Enum):
    NONE = auto()
    MAX_DOCUMENTS = auto()
    MAX_STORAGE = auto()
    MAX_EXECUTION_TIME = auto()


@dataclass
class CrawlStats:
    max_documents: int
    max_storage_bytes: int
    max_execution_seconds: float

    documents_saved: int = 0
    storage_bytes: int = 0
    requests_processed: int = 0
    storage_errors: int = 0

    documents_by_domain: dict[str, int] = field(default_factory=dict)
    http_errors: dict[int, int] = field(default_factory=dict)

    links_discovered_by_domain: dict[str, int] = field(default_factory=dict)
    links_accepted_by_domain: dict[str, int] = field(default_factory=dict)
    links_rejected_by_domain: dict[str, int] = field(default_factory=dict)

    started_at: float = field(default_factory=time.monotonic)
    
    stop_reason: StopReason = StopReason.NONE

    @staticmethod
    def get_hostname(url: str) -> str:
        hostname = urlparse(url).hostname

        if not hostname:
            return "unknown"

        hostname = hostname.lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return hostname

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def register_document(self, url: str, size_bytes: int) -> None:
        self.documents_saved += 1
        self.storage_bytes += size_bytes

        hostname = self.get_hostname(url)

        self.documents_by_domain[hostname] = (
            self.documents_by_domain.get(hostname, 0) + 1
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
        hostname = self.get_hostname(source_url)

        rejected = discovered - accepted

        self.links_discovered_by_domain[hostname] = (
            self.links_discovered_by_domain.get(
                hostname,
                0,
            ) + discovered
        )

        self.links_accepted_by_domain[hostname] = (
            self.links_accepted_by_domain.get(
                hostname,
                0,
            ) + accepted
        )

        self.links_rejected_by_domain[hostname] = (
            self.links_rejected_by_domain.get(
                hostname,
                0,
            ) + rejected
        )

    def should_stop(self) -> bool:
        if self.documents_saved >= self.max_documents:
            self.stop_reason = StopReason.MAX_DOCUMENTS
            return True

        if self.storage_bytes >= self.max_storage_bytes:
            self.stop_reason = StopReason.MAX_STORAGE
            return True

        if self.elapsed_seconds() >= self.max_execution_seconds:
            self.stop_reason = StopReason.MAX_EXECUTION_TIME
            return True

        return False

    def storage_gb(self) -> float:
        return self.storage_bytes / (1024 ** 3)

    def elapsed_hours(self) -> float:
        return self.elapsed_seconds() / 3600

    def register_request(self) -> None:
        self.requests_processed += 1

    def register_storage_error(self) -> None:
        self.storage_errors += 1

    def register_stop_reason(
        self,
        reason: StopReason,
    ) -> None:
        self.stop_reason = reason

    def summary(self) -> str:
        lines = [
            "",
            "=========================== RESUMO DA COLETA ===========================",
            f"Requisições processadas: {self.requests_processed}",
            f"Documentos salvos......: {self.documents_saved}",
            f"Erros de armazenamento.: {self.storage_errors}"
            f"Dados armazenados......: {self.storage_gb():.6f} GB",
            f"Tempo de execução......: {self.elapsed_hours():.4f} horas",
            f"Motivo da parada.......: {self.stop_reason.name}",
            "",
            "Documentos por domínio.: ",
        ]

        if self.documents_by_domain:
            for domain, count in sorted(
                self.documents_by_domain.items(),
                key=lambda item: item[1],
                reverse=True,
            ):
                lines.append(f"  {domain:<30} {count:>6}")
        else:
            lines.append("  Nenhum documento armazenado.")

        lines.append("Links por domínio......:")
        lines.append(
            f"  {'Domínio':<35}"
            f"{'Descobertos':>12}"
            f"{'Aceitos':>10}"
            f"{'Rejeitados':>12}"
        )

        all_domains = (
            set(self.links_discovered_by_domain)
            | set(self.links_accepted_by_domain)
            | set(self.links_rejected_by_domain)
        )

        if all_domains:
            for domain in sorted(all_domains):
                discovered = (self.links_discovered_by_domain.get(domain, 0))

                accepted = (self.links_accepted_by_domain.get(domain, 0))

                rejected = (self.links_rejected_by_domain.get(domain, 0))

                lines.append(
                    f"  {domain:<35}"
                    f"{discovered:>12}"
                    f"{accepted:>10}"
                    f"{rejected:>12}"
                )
        else:
            lines.append(
                "  Nenhum link registrado."
            )

        lines.append("")
        lines.append("Erros HTTP.............:")

        if self.http_errors:
            for status_code, count in sorted(
                self.http_errors.items()
            ):
                lines.append(f"  HTTP {status_code:<3} {count:>6}")
        else:
            lines.append("  Nenhum erro HTTP registrado.")

        lines.append("========================================================================")

        return "\n".join(lines)