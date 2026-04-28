from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

POINTS_PER_MM = Decimal("72") / Decimal("25.4")
TOP_MARGIN_MM = Decimal("10")
from pathlib import Path

import pikepdf
from pikepdf.models import parse_content_stream, unparse_content_stream


@dataclass(slots=True)
class StrokeStats:
    """Statistiche basilari per capire se il PDF xe stà toccà davvero."""

    streams_seen: int = 0
    stroke_widths_seen: int = 0
    stroke_widths_changed: int = 0
    stroke_operations_seen: int = 0
    form_xobjects_seen: int = 0


class PdfStrokeThickener:
    """Aumenta a una soglia minima gli spessori vettoriali dei PDF."""

    def __init__(self, minimum_width: Decimal | str | int = Decimal("1"), scale_percent: Decimal | str | int = Decimal("100")) -> None:
        try:
            self.minimum_width = Decimal(str(minimum_width))
            self.scale_factor = Decimal(str(scale_percent)) / Decimal("100")
        except InvalidOperation as exc:
            raise ValueError(f"Parametri PDF non validi: tratto={minimum_width}, scala={scale_percent}") from exc
        self.stats = StrokeStats()
        self._seen_objects: set[tuple[int, int]] = set()

    def thicken(self, source: Path, destination: Path) -> StrokeStats:
        """Legge `source`, riscrive gli spessori sottili e salva `destination`."""
        self.stats = StrokeStats()
        self._seen_objects.clear()

        with pikepdf.Pdf.open(source) as pdf:
            for page in pdf.pages:
                self._process_page(pdf, page)
                self._scale_page(page)
                self._add_roll_leading_margin(page)
                self._rotate_landscape_page_for_roll(page)
            pdf.save(destination)

        return self.stats

    def _process_page(self, pdf: pikepdf.Pdf, page: pikepdf.Page) -> None:
        """Sistema lo stream pagina e poi gli oggetti riutilizzati dentro la pagina."""
        self._rewrite_content_stream(page, lambda data: setattr(page, "Contents", pdf.make_stream(data)))
        self._process_xobjects(page.get("/Resources", {}))

    def _scale_page(self, page: pikepdf.Page) -> None:
        """Scala davvero il PDF, non solo lo zoom della preview."""
        if self.scale_factor == Decimal("1"):
            return

        left, bottom, right, top = [Decimal(str(value)) for value in page.MediaBox]
        width = right - left
        height = top - bottom
        scale = self._pdf_number(self.scale_factor)
        page.contents_add(f"q {scale} 0 0 {scale} 0 0 cm\n".encode(), prepend=True)
        page.contents_add(b"\nQ\n")
        page.MediaBox = pikepdf.Array([left, bottom, left + width * self.scale_factor, bottom + height * self.scale_factor])
        if "/CropBox" in page:
            page.CropBox = page.MediaBox

    @staticmethod
    def _add_roll_leading_margin(page: pikepdf.Page) -> None:
        """Aggiunge 10 mm di bianco in testa al foglio, così la TC-20 non taglia."""
        left, bottom, right, top = [Decimal(str(value)) for value in page.MediaBox]
        margin_points = TOP_MARGIN_MM * POINTS_PER_MM
        width = right - left
        height = top - bottom

        if width > height:
            # Dopo la rotazione per rullo, questa dimensione diventa la lunghezza verticale.
            page.MediaBox = pikepdf.Array([left, bottom, right + margin_points, top])
            if "/CropBox" in page:
                page.CropBox = page.MediaBox
            return

        page.contents_add(f"q 1 0 0 1 0 {PdfStrokeThickener._pdf_number(margin_points)} cm\n".encode(), prepend=True)
        page.contents_add(b"\nQ\n")
        page.MediaBox = pikepdf.Array([left, bottom, right, top + margin_points])
        if "/CropBox" in page:
            page.CropBox = page.MediaBox

    @staticmethod
    def _rotate_landscape_page_for_roll(page: pikepdf.Page) -> None:
        """Mostra/stampa i fogli larghi in verticale: più naturale per il rullo."""
        left, bottom, right, top = [float(value) for value in page.MediaBox]
        width = abs(right - left)
        height = abs(top - bottom)
        if width <= height:
            return

        current_rotation = int(page.get("/Rotate", 0)) % 360
        page["/Rotate"] = (current_rotation + 90) % 360

    def _process_xobjects(self, resources: object) -> None:
        """Scende dentro i Form XObject: tanti disegni tecnici stanno proprio là."""
        try:
            xobjects = resources.get("/XObject", {}) if resources else {}
        except AttributeError:
            return

        for _name, xobject in list(xobjects.items()):
            try:
                subtype = xobject.get("/Subtype")
            except AttributeError:
                continue

            if subtype != pikepdf.Name("/Form"):
                # Immagini raster: no ghe xe un tratto PDF da ingrassare.
                continue

            object_id = self._object_id(xobject)
            if object_id in self._seen_objects:
                continue

            self._seen_objects.add(object_id)
            self.stats.form_xobjects_seen += 1
            self._rewrite_content_stream(xobject, xobject.write)
            self._process_xobjects(xobject.get("/Resources", {}))

    def _rewrite_content_stream(self, stream_owner: object, writer) -> None:
        """Riscrive solo gli operatori `w`, lasciando stare tutto il resto."""
        try:
            instructions = parse_content_stream(stream_owner)
        except Exception:
            # Alcuni stream PDF strani non sono parsabili: meglio saltarli che rompere il file.
            return

        # Forziamo lo spessore già all'inizio: se un PDF non dichiara `w`, ci pensiamo noi.
        rewritten = [
            pikepdf.ContentStreamInstruction(
                [self._pdf_number(self.minimum_width)],
                pikepdf.Operator("w"),
            )
        ]
        changed = True
        self.stats.streams_seen += 1
        self.stats.stroke_widths_changed += 1

        for instruction in instructions:
            operator = str(instruction.operator)
            if operator in {"S", "s", "B", "B*", "b", "b*"}:
                self.stats.stroke_operations_seen += 1

            if operator == "w" and len(instruction.operands) == 1:
                self.stats.stroke_widths_seen += 1
                current = self._as_decimal(instruction.operands[0])
                if current != self.minimum_width:
                    # Non è più un minimo: xe proprio lo spessore globale scelto.
                    instruction = pikepdf.ContentStreamInstruction(
                        [self._pdf_number(self.minimum_width)],
                        pikepdf.Operator("w"),
                    )
                    self.stats.stroke_widths_changed += 1
                    changed = True
            rewritten.append(instruction)

        if changed:
            writer(unparse_content_stream(rewritten))

    @staticmethod
    def _as_decimal(value: object) -> Decimal | None:
        """Converte i numeri PDF in Decimal in modo tollerante."""
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _pdf_number(value: Decimal) -> int | Decimal:
        """Quando il numero è intero, lo scrive intero: PDF più pulito."""
        if value == value.to_integral_value():
            return int(value)
        return value

    @staticmethod
    def _object_id(obj: object) -> tuple[int, int]:
        """Usa objgen se c'è, altrimenti ripiega sull'id Python."""
        try:
            return tuple(obj.objgen)  # type: ignore[arg-type, return-value]
        except Exception:
            return (id(obj), 0)
