"""Text mit Koordinaten aus PDFs, für Scans per Tesseract (das Ergebnis wird je Datei zwischengespeichert)."""

import json
import os
from pathlib import Path

import pymupdf

from saku import config

# Tesseract nutzt sonst je Seite alle Kerne; parallel laufen ohnehin mehrere Prozesse
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
# shortcut: halbe Kernzahl für parallele Texterkennung, bei Bedarf über SAKU_OCR_PROZESSE einstellen
OCR_PROZESSE = int(os.getenv("SAKU_OCR_PROZESSE", max(1, (os.cpu_count() or 2) // 2)))


def ist_scan(doc: pymupdf.Document) -> bool:
    """Haben die meisten Seiten kaum Text, ist es ein Scan."""
    leer = sum(len(seite.get_textpage().extractText().strip()) < 100 for seite in doc)
    return leer > len(doc) / 2


def _zeilen(seite: pymupdf.Page, textpage=None) -> list[list]:
    zeilen = []
    for block in (textpage or seite.get_textpage()).extractDICT()["blocks"]:
        for zeile in block.get("lines", []):
            text = " ".join("".join(s["text"] for s in zeile["spans"]).split())
            if text:
                zeilen.append([round(v, 1) for v in zeile["bbox"]] + [text])
    return zeilen


def ocr_seite(seite: pymupdf.Page, dpi: int = 300, daten: Path | None = None) -> list[list]:
    tessdata = (daten or config.DATEN) / "tessdata"
    textpage = seite.get_textpage_ocr(language="deu", tessdata=str(tessdata), dpi=dpi, full=True)
    return _zeilen(seite, textpage)


def seiten(pfad: Path, scan: bool, cache: Path | None = None, daten: Path | None = None) -> list[dict]:
    """Je Seite Breite, Höhe und Zeilen [x0, y0, x1, y1, text]. OCR-Ergebnisse landen in `cache`."""
    if scan and cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    with pymupdf.open(pfad) as doc:
        ergebnis = [
            {"breite": round(s.rect.width, 1), "hoehe": round(s.rect.height, 1),
             "zeilen": ocr_seite(s, daten=daten) if scan else _zeilen(s)}
            for s in doc
        ]
    if scan and cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(ergebnis, ensure_ascii=False), encoding="utf-8")
    return ergebnis


def text(seite: dict) -> str:
    """Zeilen von oben nach unten als Fließtext."""
    return "\n".join(z[4] for z in sorted(seite["zeilen"], key=lambda z: (round(z[1] / 4), z[0])))
