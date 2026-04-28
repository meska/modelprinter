from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from .jobs import JobStore
from .pdf_info import read_first_page_size
from .printing import CupsPrinter


def create_app() -> Flask:
    """Factory Flask: una pagina, upload PDF, preview, stampa."""
    app_root = Path(os.getenv("MODELPRINTER_APP_ROOT", Path.cwd()))
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(app_root / "templates"),
        static_folder=str(app_root / "static"),
    )
    app.config.update(
        MAX_CONTENT_LENGTH=int(os.getenv("MODELPRINTER_MAX_UPLOAD_MB", "80")) * 1024 * 1024,
        JOB_ROOT=Path(os.getenv("MODELPRINTER_JOB_ROOT", "/var/lib/modelprinter/jobs")),
        MIN_STROKE_WIDTH=os.getenv("MODELPRINTER_MIN_STROKE_WIDTH", "1"),
        CUPS_PRINTER=os.getenv("MODELPRINTER_CUPS_PRINTER", "Canon_TC_20"),
        CUPS_OPTIONS=[
            option.strip()
            for option in os.getenv("MODELPRINTER_CUPS_OPTIONS", "InputSlot=MainRoll,CutMedia=Auto,sides=one-sided").split(",")
            if option.strip()
        ],
    )

    store = JobStore(app.config["JOB_ROOT"], app.config["MIN_STROKE_WIDTH"])
    printer = CupsPrinter(app.config["CUPS_PRINTER"], app.config["CUPS_OPTIONS"])

    @app.get("/")
    def index():
        """Pagina unica: dropzone, preview e pulsante stampa."""
        return render_template(
            "index.html",
            printer_name=app.config["CUPS_PRINTER"],
            min_stroke_width=app.config["MIN_STROKE_WIDTH"],
        )

    def _request_value(name: str, default: str) -> str:
        """Legge valori da form o JSON senza far casino coi tipi."""
        if request.is_json:
            return str((request.get_json(silent=True) or {}).get(name) or default)
        return str(request.form.get(name) or default)

    def _decimal_text(value: Decimal) -> str:
        """Decimal senza notazione scientifica, più leggibile per la UI."""
        if value == value.to_integral_value():
            return str(int(value))
        return format(value.normalize(), "f").rstrip("0").rstrip(".") or "0"

    def _requested_width() -> str:
        """Valida lo spessore richiesto: libero, ma non folle."""
        raw_width = _request_value("strokeWidth", app.config["MIN_STROKE_WIDTH"])
        try:
            width = Decimal(str(raw_width))
        except InvalidOperation as exc:
            raise ValueError("Spessore tratto non valido") from exc
        if width < Decimal("0.1") or width > Decimal("10"):
            raise ValueError("Lo spessore deve stare tra 0.1 e 10")
        return _decimal_text(width)

    def _requested_scale() -> str:
        """Valida la scala percentuale reale del PDF."""
        raw_scale = _request_value("scalePercent", "100")
        try:
            scale = Decimal(str(raw_scale))
        except InvalidOperation as exc:
            raise ValueError("Scala non valida") from exc
        if scale < Decimal("10") or scale > Decimal("300"):
            raise ValueError("La scala deve stare tra 10% e 300%")
        return _decimal_text(scale)

    def _job_payload(job):
        """JSON comune per upload e rigenerazione preview."""
        return {
            "ok": True,
            "jobId": job.job_id,
            "filename": job.original_name,
            "previewUrl": f"/jobs/{job.job_id}/pdf",
            "strokeWidth": _requested_width(),
            "scalePercent": _requested_scale(),
            "stats": {
                "streamsSeen": job.stats.streams_seen,
                "strokeWidthsSeen": job.stats.stroke_widths_seen,
                "strokeWidthsChanged": job.stats.stroke_widths_changed,
                "strokeOperationsSeen": job.stats.stroke_operations_seen,
                "formXobjectsSeen": job.stats.form_xobjects_seen,
            },
            "pageSize": {
                "widthMm": round(job.page_size.width_mm),
                "heightMm": round(job.page_size.height_mm),
            },
        }

    @app.post("/upload")
    def upload_pdf():
        """Riceve il PDF, crea la copia ispessita e torna JSON per la preview."""
        upload = request.files.get("pdf")
        if upload is None:
            return jsonify({"ok": False, "error": "Nessun PDF ricevuto"}), 400

        try:
            job = store.create_from_upload(upload, minimum_width=_requested_width(), scale_percent=_requested_scale())
            store.delete_old_jobs()
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

        return jsonify(_job_payload(job))

    @app.post("/jobs/<job_id>/stroke")
    def change_stroke_width(job_id: str):
        """Rigenera la preview usando lo spessore scelto dall'utente."""
        try:
            job = store.reprocess(job_id, _requested_width(), scale_percent=_requested_scale())
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

        return jsonify(_job_payload(job))

    @app.get("/jobs/<job_id>/pdf")
    def preview_pdf(job_id: str):
        """Serve il PDF modificato, usato sia da iframe sia da download."""
        try:
            pdf_path = store.get_processed_pdf(job_id)
        except FileNotFoundError:
            return "PDF non trovato", 404
        return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)

    @app.post("/jobs/<job_id>/print")
    def print_pdf(job_id: str):
        """Stampa il PDF modificato con CUPS."""
        try:
            pdf_path = store.get_processed_pdf(job_id)
        except FileNotFoundError:
            return jsonify({"ok": False, "error": "PDF non trovato"}), 404

        page_size = read_first_page_size(pdf_path)
        result = printer.print_pdf(pdf_path, extra_options=[page_size.cups_custom_media])
        return jsonify(
            {
                "ok": result.ok,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        ), (200 if result.ok else 500)

    @app.get("/healthz")
    def healthz():
        """Healthcheck banale per systemd/nginx: vivo e rispondo."""
        return "ok\n"

    return app


app = create_app()
