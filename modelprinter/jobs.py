from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .pdf_info import PdfPageSize
from .pdf_tools import PdfStrokeThickener, StrokeStats


@dataclass(slots=True)
class ModelPrintJob:
    """Un job caricato: originale, PDF ritoccato e metadati minimi."""

    job_id: str
    original_name: str
    source_pdf: Path
    processed_pdf: Path
    created_at: datetime
    stats: StrokeStats
    page_size: PdfPageSize


class JobStore:
    """Archivio semplice su filesystem: basta e avanza per una pagina interna."""

    def __init__(self, root: Path, minimum_width: str = "1") -> None:
        self.root = root
        self.minimum_width = minimum_width
        self.root.mkdir(parents=True, exist_ok=True)

    def create_from_upload(self, upload: FileStorage, minimum_width: str | None = None, scale_percent: str = "100") -> ModelPrintJob:
        """Salva il PDF uploadato e crea subito la versione stampabile."""
        original_name = secure_filename(upload.filename or "model.pdf") or "model.pdf"
        if not original_name.lower().endswith(".pdf"):
            raise ValueError("Carica un file PDF, mona ma con affetto 🍷")

        job_id = uuid.uuid4().hex
        job_dir = self.root / job_id
        job_dir.mkdir(parents=True, exist_ok=False)

        source_pdf = job_dir / f"original-{original_name}"
        upload.save(source_pdf)

        return self.reprocess(job_id, minimum_width or self.minimum_width, scale_percent=scale_percent, original_name=original_name)

    def reprocess(self, job_id: str, minimum_width: str, scale_percent: str = "100", original_name: str | None = None) -> ModelPrintJob:
        """Rigenera il PDF stampabile partendo dall'originale già caricato."""
        job_dir = self._safe_job_dir(job_id)
        source_pdf = self.get_source_pdf(job_id)
        original_name = original_name or source_pdf.name.removeprefix("original-")
        processed_pdf = job_dir / f"print-{original_name}"

        thickener = PdfStrokeThickener(minimum_width, scale_percent=scale_percent)
        stats = thickener.thicken(source_pdf, processed_pdf)
        from .pdf_info import read_first_page_size

        page_size = read_first_page_size(processed_pdf)

        return ModelPrintJob(
            job_id=job_id,
            original_name=original_name,
            source_pdf=source_pdf,
            processed_pdf=processed_pdf,
            created_at=datetime.now(timezone.utc),
            stats=stats,
            page_size=page_size,
        )

    def get_source_pdf(self, job_id: str) -> Path:
        """Ritorna il PDF originale caricato."""
        job_dir = self._safe_job_dir(job_id)
        candidates = sorted(job_dir.glob("original-*.pdf"))
        if not candidates:
            raise FileNotFoundError(job_id)
        return candidates[0]

    def get_processed_pdf(self, job_id: str) -> Path:
        """Ritorna il PDF pronto stampa per un job esistente."""
        job_dir = self._safe_job_dir(job_id)
        candidates = sorted(job_dir.glob("print-*.pdf"))
        if not candidates:
            raise FileNotFoundError(job_id)
        return candidates[0]

    def delete_old_jobs(self, keep_last: int = 200) -> int:
        """Pulizia rozza ma efficace: tiene solo gli ultimi N job."""
        job_dirs = sorted(
            [path for path in self.root.iterdir() if path.is_dir()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        removed = 0
        for old_dir in job_dirs[keep_last:]:
            shutil.rmtree(old_dir, ignore_errors=True)
            removed += 1
        return removed

    def _safe_job_dir(self, job_id: str) -> Path:
        """Evita path traversal: job_id deve essere UUID hex secco."""
        if not job_id or any(char not in "0123456789abcdef" for char in job_id):
            raise FileNotFoundError(job_id)
        job_dir = self.root / job_id
        if not job_dir.is_dir():
            raise FileNotFoundError(job_id)
        return job_dir
