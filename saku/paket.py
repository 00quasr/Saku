"""Paket für Saku im Netz (docs/DEPLOY.md): genau das, was die Web-App aus data/ braucht, als ein Archiv.

Drin: saku.db als stimmige Kopie, die Bildausschnitte unter aufgaben/, auf die sie verweist, und die Projektdokumentation
für das Fachgespräch. Nicht drin: quellen/ und pdfs/ (die PDFs), backups/, modelle/ (Vektormodell), .env.
Hochgeladen in den Einstellungen ersetzt es Katalog und Bilder; der Lernstand von dort bleibt."""

import re
import shutil
import sqlite3
import tarfile
import tempfile
from pathlib import Path

from saku import config, db

# Pfade im Archiv; was nicht passt, packt Saku nicht ein und nimmt es beim Hochladen nicht an
ERLAUBT = re.compile(r"saku\.db|projekt/(text\.md|name\.txt)|aufgaben/[^\s\"'()\[\]<>\\]+?\.(png|jpe?g|webp)", re.I)
BILD = re.compile(r"aufgaben/[^\s\"'()\[\]<>\\]+?\.(?:png|jpe?g|webp)", re.I)  # in JSON-Listen und Markdown (/bild/…)
GRENZE = 2 * 1024**3  # Bytes, gepackt und entpackt


def erlaubt(name: str) -> bool:
    return bool(ERLAUBT.fullmatch(name)) and ".." not in name.split("/")


def bilder(con: sqlite3.Connection, daten: Path) -> tuple[list[str], int]:
    """Bildausschnitte, auf die die Datenbank irgendwo verweist und die es unter daten/aufgaben gibt; dazu die Zahl der
    Verweise ohne Datei. Durchsucht jede Tabelle: Abbildungen stehen auch nur im Markdown der Teilaufgaben."""
    verweise = set()
    for (tabelle,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall():
        for zeile in con.execute(f'SELECT * FROM "{tabelle}"'):
            verweise.update(m for wert in zeile if isinstance(wert, str) for m in BILD.findall(wert))
    ordner = (daten / "aufgaben").resolve()
    da = sorted(v for v in verweise if erlaubt(v) and (daten / v).resolve().is_relative_to(ordner) and (daten / v).is_file())
    return da, len(verweise) - len(da)


def bauen(ziel: Path, daten: Path | None = None) -> dict:
    """Schreibt das Paket nach ziel (.tar.gz) und sagt, was drin ist."""
    daten = daten or config.DATEN
    if not config.db_pfad(daten).exists():
        raise FileNotFoundError(f"Keine Datenbank in {daten}")
    with tempfile.TemporaryDirectory() as tmp:
        kopie = Path(tmp) / "saku.db"
        db.kopieren(config.db_pfad(daten), kopie)
        con = sqlite3.connect(kopie)
        try:
            namen, fehlen = bilder(con, daten)
        finally:
            con.close()
        projekt = [f"projekt/{n}" for n in ("text.md", "name.txt") if (daten / "projekt" / n).is_file()]
        teil = ziel.with_name(ziel.name + ".teil")
        with tarfile.open(teil, "w:gz") as tar:
            tar.add(kopie, "saku.db")
            for name in [*namen, *projekt]:
                tar.add(daten / name, name)
        teil.replace(ziel)
        return {"datenbank": kopie.stat().st_size, "bilder": len(namen), "bilder_bytes": sum((daten / n).stat().st_size for n in namen),
                "ohne_datei": fehlen, "projekt": bool(projekt), "groesse": ziel.stat().st_size}


def pruefen(archiv: Path) -> list[tarfile.TarInfo]:
    """Die Einträge, wenn das Archiv ein Paket von Saku ist: nur reguläre Dateien unter erlaubten Pfaden (keine Links,
    kein ../), mit saku.db, entpackt nicht über GRENZE. Sonst ValueError mit dem Grund."""
    try:
        with tarfile.open(archiv, "r:gz") as tar:
            eintraege = tar.getmembers()
    except (tarfile.TarError, EOFError, OSError) as fehler:
        raise ValueError(f"Kein Paket von Saku (.tar.gz): {fehler}") from None
    for e in eintraege:
        if not e.isfile() or not erlaubt(e.name):
            raise ValueError(f"Unerwarteter Eintrag im Paket: {e.name}")
    if "saku.db" not in {e.name for e in eintraege}:
        raise ValueError("Im Paket fehlt saku.db.")
    if sum(e.size for e in eintraege) > GRENZE:
        raise ValueError("Das Paket ist entpackt zu groß.")
    return eintraege


def einspielen(archiv: Path, daten: Path) -> dict:
    """Übernimmt ein geprüftes Paket in den laufenden Datenordner: sichert die alte Datenbank, spielt die neue über die
    Backup-API ein (offene Verbindungen sehen danach den neuen Stand), bringt sie auf das aktuelle Schema, übernimmt den
    Lernstand von vorher und tauscht die Bilder. Gibt die Zahlen des Lernstand-Imports zurück."""
    from saku.lernen import lernstand
    from saku.sensei import vektoren

    pruefen(archiv)
    neu = daten / ".paket-neu"
    shutil.rmtree(neu, ignore_errors=True)
    try:
        with tarfile.open(archiv, "r:gz") as tar:
            tar.extractall(neu, filter="data")  # filter: zusätzlich zu pruefen kein Pfad aus neu hinaus
        try:
            pruef = sqlite3.connect(f"file:{neu / 'saku.db'}?mode=ro", uri=True)
            try:
                version = pruef.execute("PRAGMA user_version").fetchone()[0]
                if not version or not pruef.execute("SELECT 1 FROM sqlite_master WHERE name = 'teilaufgabe'").fetchone():
                    raise ValueError("saku.db im Paket ist keine Datenbank von Saku.")
            finally:
                pruef.close()
        except sqlite3.DatabaseError:
            raise ValueError("saku.db im Paket ist keine SQLite-Datenbank.") from None
        if version > max(db.MIGRATIONEN):
            raise ValueError("Das Paket stammt aus einer neueren Saku-Version: erst diese hier neu deployen.")

        pfad = config.db_pfad(daten)
        db.sichern(pfad, erzwingen=True)
        con = db.verbinden(pfad)
        try:
            bisher = lernstand.exportieren(con)
            del bisher["einstellungen"]  # die aus dem Paket gelten
            quelle = sqlite3.connect(neu / "saku.db")
            try:
                quelle.backup(con)
            finally:
                quelle.close()
        finally:
            con.close()
        db.init(pfad)  # ein Paket aus einer älteren Saku-Version
        con = db.verbinden(pfad)
        try:
            zahlen = lernstand.importieren(con, bisher)
        finally:
            con.close()
        vektoren._cache.clear()  # gleich viele Vektoren hieße sonst: alter Zwischenspeicher

        if (neu / "aufgaben").is_dir():
            alt = daten / ".aufgaben-alt"
            shutil.rmtree(alt, ignore_errors=True)
            if (daten / "aufgaben").exists():
                (daten / "aufgaben").rename(alt)
            (neu / "aufgaben").rename(daten / "aufgaben")
            shutil.rmtree(alt, ignore_errors=True)
        for datei in (neu / "projekt").glob("*"):
            (daten / "projekt").mkdir(exist_ok=True)
            datei.replace(daten / "projekt" / datei.name)
        return zahlen
    finally:
        shutil.rmtree(neu, ignore_errors=True)


if __name__ == "__main__":  # Selbsttest: python -m saku.paket
    assert erlaubt("saku.db") and erlaubt("aufgaben/3f2a/2b-1.png") and erlaubt("projekt/text.md")
    assert not any(map(erlaubt, ["../saku.db", "aufgaben/../../etc/passwd.png", "/saku.db", ".env", "quellen/a.pdf",
                                 "aufgaben/a.pdf", "modelle/x.onnx", "backups/saku-2026-01-01.db", "projekt/x.md"]))
    print("ok")
