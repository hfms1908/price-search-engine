import time
from dataclasses import dataclass, field
from enum import Enum, auto


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
    started_at: float = field(
        default_factory=time.monotonic
    )

    stop_reason: StopReason = StopReason.NONE

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def register_document(
        self,
        size_bytes: int,
    ) -> None:
        self.documents_saved += 1
        self.storage_bytes += size_bytes

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

    def summary(self) -> str:
        return (
            "\n"
            "========== RESUMO DA COLETA ==========\n"
            f"Documentos salvos : {self.documents_saved}\n"
            f"Dados armazenados : {self.storage_gb():.6f} GB\n"
            f"Tempo de execução  : {self.elapsed_hours():.4f} horas\n"
            f"Motivo da parada   : {self.stop_reason.name}\n"
            "======================================"
        )