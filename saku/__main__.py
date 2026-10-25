"""Befehle: python -m saku init | assets | analyse | start | lernstand | paket | server"""

import argparse
import json
import os
import sqlite3
import threading
import webbrowser
from pathlib import Path

from saku import config, db


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m saku", description="Saku 咲く – AP2-Trainer")
    befehle = parser.add_subparsers(dest="befehl", required=True)

    befehle.add_parser("init", help="Datenbank anlegen")
    befehle.add_parser("assets", help="Oberflächen-Dateien und Schriften laden")

    analyse = befehle.add_parser("analyse", help="Prüfungs-PDFs analysieren")
    analyse.add_argument("--schritt", help="nur diesen Schritt ausführen")
    analyse.add_argument("--ohne-ki", action="store_true", help="nur lokale Schritte, kostenlos")
    analyse.add_argument("--ki", choices=["api", "claude-code"], default="api",
                         help="KI über die Claude-API oder das lokale Claude Code")

    start = befehle.add_parser("start", help="App öffnen")
    start.add_argument("--browser", action="store_true", help="im Standardbrowser statt im eigenen Fenster")

    lernstand = befehle.add_parser("lernstand", help="Lernstand als Datei sichern oder übernehmen, übersteht einen Neuaufbau")
    lernstand.add_argument("aktion", choices=["export", "import"])
    lernstand.add_argument("datei", type=Path, help="JSON-Datei")

    paket = befehle.add_parser("paket", help="Datenbank und Bilder als Archiv für Saku im Netz (docs/DEPLOY.md)")
    paket.add_argument("datei", type=Path, nargs="?", default=config.DATEN / "saku-paket.tar.gz",
                       help="Ziel, sonst data/saku-paket.tar.gz")

    befehle.add_parser("server", help="im Netz betreiben, z. B. auf Railway; nur mit SAKU_PASSWORT (docs/DEPLOY.md)")

    args = parser.parse_args()

    if args.befehl == "init":
        db.taeglich_sichern()  # nach einem Update migriert init; ohne Datenbank gibt es nichts zu sichern
        neu = db.init()
        print(f"Datenbank {'angelegt' if neu else 'vorhanden'}: {config.db_pfad()}")

    elif args.befehl == "assets":
        from saku.assets import laden
        laden()

    elif args.befehl == "analyse":
        from saku.pipeline import ausfuehren
        db.taeglich_sichern()  # vor Migrationen und Analyse
        db.init()
        ausfuehren(schritt=args.schritt, ohne_ki=args.ohne_ki, ki=args.ki)

    elif args.befehl == "start":
        starten(browser=args.browser)

    elif args.befehl == "lernstand":
        lernstand_datei(args.aktion, args.datei)

    elif args.befehl == "paket":
        paket_bauen(args.datei)

    elif args.befehl == "server":
        server()


def lernstand_datei(aktion: str, datei: Path) -> None:
    from saku.lernen import lernstand

    if aktion == "import":
        db.taeglich_sichern()  # vor dem Import, falls er etwas Ungewolltes übernimmt
    db.init()
    con = db.verbinden()
    try:
        if aktion == "export":
            datei.write_text(json.dumps(lernstand.exportieren(con), ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"Lernstand exportiert: {datei}")
            return
        try:
            zahlen = lernstand.importieren(con, json.loads(datei.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, sqlite3.Error) as fehler:  # zurückgerollt
            raise SystemExit(f"Import abgebrochen, nichts geändert: {fehler!r}")
        for bereich, (uebernommen, uebersprungen) in zahlen.items():
            print(f"{bereich}: {uebernommen} übernommen, {uebersprungen} übersprungen")
    finally:
        con.close()


def paket_bauen(datei: Path) -> None:
    from saku import paket

    try:
        inhalt = paket.bauen(datei)
    except FileNotFoundError as fehler:
        raise SystemExit(f"{fehler}: erst python -m saku init und analyse.")
    mb = lambda n: f"{n / 1e6:.1f} MB"
    print(f"Paket {datei}: {mb(inhalt['groesse'])}")
    print(f"  Datenbank {mb(inhalt['datenbank'])}, {inhalt['bilder']} Bilder ({mb(inhalt['bilder_bytes'])})"
          f"{', Projektdokumentation' if inhalt['projekt'] else ''}")
    if inhalt["ohne_datei"]:
        print(f"  {inhalt['ohne_datei']} Bildverweise ohne Datei unter data/aufgaben, die fehlen auch im Netz")
    print("Hochladen: Saku im Netz → Einstellungen → Daten → Paket übernehmen")


def server() -> None:
    """Produktionsbetrieb hinter einem HTTPS-Proxy (Railway): gunicorn mit einem Prozess, weil SQLite eine Datei ist, und
    Threads, weil Sensei per SSE streamt und jeder offene Stream einen belegt."""
    from gunicorn.app.base import BaseApplication

    from saku.web import create_app

    if not config.PASSWORT:
        raise SystemExit("SAKU_PASSWORT fehlt: im Netz startet Saku nur mit Anmeldung (docs/DEPLOY.md).")
    volume = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")  # setzt Railway, wenn ein Volume angehängt ist
    if os.getenv("RAILWAY_ENVIRONMENT_ID") and not (volume and config.DATEN.is_relative_to(Path(volume).resolve())):
        raise SystemExit(f"Der Datenordner {config.DATEN} liegt auf keinem Volume: der Lernstand wäre beim nächsten Deploy weg. "
                         "Volume unter /data anhängen (docs/DEPLOY.md).")
    db.taeglich_sichern()
    db.init()
    app = create_app(server=True)
    einstellungen = {
        "bind": f"0.0.0.0:{os.getenv('PORT') or config.PORT}",  # PORT setzt Railway
        "workers": 1, "worker_class": "gthread", "threads": 16,
        "accesslog": "-",
    }

    class Server(BaseApplication):
        def load_config(self):
            for schluessel, wert in einstellungen.items():
                self.cfg.set(schluessel, wert)

        def load(self):
            return app

    Server().run()


def starten(browser: bool = False) -> None:
    from saku.web import create_app

    db.taeglich_sichern()  # vor den Migrationen von init
    db.init()
    app = create_app()
    url = f"http://127.0.0.1:{config.PORT}/"

    if browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
        app.run(host="127.0.0.1", port=config.PORT, threaded=True)
        return

    import webview

    webview.settings["ALLOW_DOWNLOADS"] = True  # „Lernstand exportieren“ in den Einstellungen
    app.config["FENSTER"] = True
    threading.Thread(
        target=app.run,
        kwargs={"host": "127.0.0.1", "port": config.PORT, "threaded": True, "use_reloader": False},
        daemon=True,
    ).start()
    fensterfarbe = Fensterfarbe()
    fenster = webview.create_window("Saku 咲く", url, width=1320, height=900, min_size=(1024, 700),
                                    background_color="#141412", js_api=fensterfarbe)
    fensterfarbe._fenster = fenster
    fenster.events.before_show += lambda: fensterfarbe.setze("#141412")
    webview.start()


class Fensterfarbe:
    """macOS: Titelleiste ohne Titel und in der Farbe der Seite, damit Fenster und App eins sind.
    Die Seite meldet ihre Hintergrundfarbe (saku.js), auch nach einem Wechsel des Farbschemas."""

    _fenster = None  # mit Unterstrich: pywebview reicht nur öffentliche Namen an JavaScript weiter

    def setze(self, farbe: str) -> None:
        try:
            import AppKit
            from PyObjCTools import AppHelper
        except ImportError:  # nur auf macOS vorhanden
            return
        if not (self._fenster and isinstance(farbe, str) and len(farbe) == 7 and farbe.startswith("#")):
            return
        rot, gruen, blau = (int(farbe[i:i + 2], 16) / 255 for i in (1, 3, 5))

        def setzen():
            w = self._fenster.native
            w.setTitlebarAppearsTransparent_(True)
            w.setTitleVisibility_(AppKit.NSWindowTitleHidden)
            w.setBackgroundColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(rot, gruen, blau, 1.0))

        AppHelper.callAfter(setzen)


if __name__ == "__main__":
    main()
