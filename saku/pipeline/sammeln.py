"""Einmalig: Prüfungen für AE, SI, AP1 und WiSo aus dem Quellordner (samt ZIPs) nach data/pdfs kopieren.

    python -m saku.pipeline.sammeln [data/quellen] [--probe]

Die Originale bleiben unangetastet. In den ZIPs sind die Dateinamen cp437-kodiert.
Entschieden wird nach dem Deckblatt (siehe inventar.deckblatt), Dubletten über SHA-256
und über gleichen Termin, Bereich und Art (Text-PDF schlägt Scan).
"""

import argparse
import hashlib
import re
import unicodedata
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf
from rich.console import Console
from rich.table import Table

from saku import config
from saku.pipeline import inventar, pdf

QUELLE = config.DATEN / "quellen"
# Nie dabei, schon am Pfad erkennbar (spart die Texterkennung): Doppelungen (Bawü, merge), andere Berufe,
# Zwischenprüfungen und Prüfungen vor der AO 2020 (bis Winter 2020/21), Lernzettel, Buch, Lehrplan, Kataloge, Belegsätze
NIE = re.compile(
    r"Bawü|Zwischenprüfung|Lernzettel|Prüfungsvorbereitung|Fachinformatiker_19-12-13_EL|Prüfungskatalog|Pruefungsstatistik"
    r"|merge|Belegsatz|alte AO|_IT-System|\((?:ITSM|KSM|KDM|FIDV|FIDP|ITSE|ITK)\)|/(?:KSM|KDM|FIDV|FIDP|ITSE|ITK)/"
    r"|Prüfung (?:Sommer|Winter) (?:200\d|201\d|2020)|Prüfung Sommer (?:00|2021)", re.I)


def _name(info: zipfile.ZipInfo) -> str:
    name = info.filename
    if not info.flag_bits & 0x800:  # ohne UTF-8-Flag liest zipfile cp437; oft stecken trotzdem UTF-8-Bytes darin
        try:
            name = name.encode("cp437").decode("utf-8")
        except UnicodeDecodeError:
            pass
    return unicodedata.normalize("NFC", name)


def eintraege(quelle: Path) -> list[tuple[str, str, str | None]]:
    """(Anzeigename, Datei, ZIP-Mitglied) für jede PDF, auch in ZIPs."""
    liste = []
    for pfad in sorted(quelle.rglob("*")):
        rel = unicodedata.normalize("NFC", str(pfad.relative_to(quelle)))  # macOS speichert Namen zerlegt (NFD)
        if NIE.search(rel):
            continue
        if pfad.suffix.lower() == ".pdf":
            liste.append((rel, str(pfad), None))
        elif pfad.suffix.lower() == ".zip":
            with zipfile.ZipFile(pfad) as zf:
                liste += [(f"{rel}/{_name(i)}", str(pfad), i.filename) for i in zf.infolist()
                          if i.filename.lower().endswith(".pdf") and not NIE.search(_name(i))]
    return liste


def lesen(eintrag: tuple[str, str, str | None]) -> bytes:
    _, datei, mitglied = eintrag
    if mitglied is None:
        return Path(datei).read_bytes()
    with zipfile.ZipFile(datei) as zf:
        return zf.read(mitglied)


def pruefen(eintrag: tuple[str, str, str | None]) -> dict:
    """Hash, Seiten, Scan und Deckblatt; Scans liest Tesseract (nur die ersten zwei Seiten, 150 dpi)."""
    daten = lesen(eintrag)
    with pymupdf.open(stream=daten, filetype="pdf") as doc:
        scan = pdf.ist_scan(doc)
        texte = [" ".join(z[4] for z in pdf.ocr_seite(doc[i], dpi=150)) for i in range(min(2, len(doc)))] if scan \
            else [s.get_textpage().extractText() for s in doc]
        seiten = len(doc)
    return {"eintrag": eintrag, "sha256": hashlib.sha256(daten).hexdigest(), "seiten": seiten, "scan": scan,
            **inventar.deckblatt(texte, eintrag[0])}


def auswaehlen(gepruefte: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Übernommene Dokumente und (Dokument, Grund) für alle anderen."""
    rang = sorted(gepruefte, key=lambda m: (m["scan"], m["beruf"] not in inventar.UNSERE, -m["seiten"]))
    gewaehlt, raus, hashes, schluessel = [], [], {}, {}
    for m in rang:
        grund = inventar.ausschluss(m)
        k = (m["jahr"], m["saison"], m["format"], *inventar.teil_und_beruf(m), m["bereich"], m["art"])
        if not grund and m["sha256"] in hashes:
            grund = f"Dublette von {hashes[m['sha256']]['eintrag'][0]}"
        elif not grund and k in schluessel:
            grund = f"gleicher Termin/Bereich wie {schluessel[k]['eintrag'][0]}"
        hashes.setdefault(m["sha256"], m)
        if grund:
            raus.append((m, grund))
        else:
            schluessel[k] = m
            gewaehlt.append(m)
    return gewaehlt, raus


def ziel(m: dict, pdfs: Path) -> Path:
    teil, beruf = inventar.teil_und_beruf(m)
    ordner = f"{m['jahr']}-{m['saison']}-{teil}-{beruf}" + ("-frueher" if m["format"] == "frueher" else "")
    return pdfs / ordner / Path(m["eintrag"][0]).name


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m saku.pipeline.sammeln")
    parser.add_argument("quelle", nargs="?", default=str(QUELLE))
    parser.add_argument("--probe", action="store_true", help="nur anzeigen, nichts kopieren")
    args = parser.parse_args()

    liste = eintraege(Path(args.quelle))
    with ProcessPoolExecutor(pdf.OCR_PROZESSE) as pool:
        gepruefte = list(pool.map(pruefen, liste))
    gewaehlt, raus = auswaehlen(gepruefte)

    konsole = Console()
    tabelle = Table("Termin", "Format", "Bereich", "Art", "Seiten", "Scan", "Datei", title="Übernommen")
    for m in sorted(gewaehlt, key=lambda m: (m["jahr"], m["saison"], m["format"], str(m["bereich"]), m["art"])):
        tabelle.add_row(f"{m['saison']} {m['jahr']}", m["format"], m["bereich"] or "(alle)", m["art"],
                        str(m["seiten"]), "ja" if m["scan"] else "", m["eintrag"][0])
        if not args.probe:
            pfad = ziel(m, config.DATEN / "pdfs")
            pfad.parent.mkdir(parents=True, exist_ok=True)
            if not pfad.exists():
                pfad.write_bytes(lesen(m["eintrag"]))
    konsole.print(tabelle)
    tabelle = Table("Grund", "Datei", title="Nicht übernommen")
    for m, grund in sorted(raus, key=lambda r: r[1]):
        tabelle.add_row(grund, m["eintrag"][0])
    konsole.print(tabelle)


if __name__ == "__main__":
    main()
