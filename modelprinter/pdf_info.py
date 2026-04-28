from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pikepdf


@dataclass(slots=True)
class PdfPageSize:
    """Dimensioni della prima pagina PDF in millimetri."""

    width_mm: float
    height_mm: float

    @property
    def cups_custom_media(self) -> str:
        """Opzione IPP/CUPS Custom.WIDTHxHEIGHTmm arrotondata al millimetro."""
        width = max(1, round(self.width_mm))
        height = max(1, round(self.height_mm))
        # IPP Everywhere ragiona su `media`; `PageSize` può lasciare A4 nello spool.
        return f"media=Custom.{width}x{height}mm"


def read_first_page_size(pdf_path: Path) -> PdfPageSize:
    """Legge il MediaBox della prima pagina considerando anche la rotazione."""
    with pikepdf.Pdf.open(pdf_path) as pdf:
        page = pdf.pages[0]
        left, bottom, right, top = [float(value) for value in page.MediaBox]
        rotation = int(page.get("/Rotate", 0)) % 360

    # PDF: 72 punti per pollice, 25.4 mm per pollice. Matematica, non magia.
    width_mm = abs(right - left) * 25.4 / 72
    height_mm = abs(top - bottom) * 25.4 / 72
    if rotation in {90, 270}:
        width_mm, height_mm = height_mm, width_mm
    return PdfPageSize(width_mm=width_mm, height_mm=height_mm)
