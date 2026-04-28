from pathlib import Path

from modelprinter.pdf_tools import PdfStrokeThickener


def test_example_pdf_is_processed(tmp_path: Path) -> None:
    # Test reale col PDF mandato da Marco: se non esplode, semo già messi ben.
    source = Path('/Users/meska/.openclaw/media/inbound/pattern_plotter_top_rubashka_dlya_beremennykh_vykroyka_502---02c87c7d-b4ce-439e-9cec-f34b9d38474b.pdf')
    destination = tmp_path / 'processed.pdf'

    stats = PdfStrokeThickener('1').thicken(source, destination)

    assert destination.exists()
    assert destination.stat().st_size > 0
    assert stats.streams_seen > 0
