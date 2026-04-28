from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PrintResult:
    """Risultato di stampa, con stdout/stderr per debug rapido."""

    ok: bool
    returncode: int
    stdout: str
    stderr: str


class CupsPrinter:
    """Piccolo wrapper per CUPS: modelprinter parla con `lp`."""

    def __init__(self, printer_name: str, default_options: list[str] | None = None) -> None:
        self.printer_name = printer_name
        self.default_options = default_options or []

    def print_pdf(self, pdf_path: Path, extra_options: list[str] | None = None) -> PrintResult:
        """Invia un PDF alla Canon TC-20 / stampante CUPS configurata."""
        options = [*self.default_options, *(extra_options or [])]
        command = ["lp", "-d", self.printer_name]
        for option in options:
            # Ogni opzione resta separata, cussì no ghe femo far magie alla shell.
            command.extend(["-o", option])
        command.append(str(pdf_path))

        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        return PrintResult(
            ok=completed.returncode == 0,
            returncode=completed.returncode,
            stdout=completed.stdout.strip(),
            stderr=completed.stderr.strip(),
        )
