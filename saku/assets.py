"""Lädt einmalig alle Fremddateien nach static/vendor und static/fonts (danach läuft Saku offline)."""

import re
import subprocess
import sys
from pathlib import Path

STATIC = Path(__file__).parent / "web" / "static"
NPM = "https://cdn.jsdelivr.net/npm"
GFONTS = "https://raw.githubusercontent.com/google/fonts/main/ofl/shipporimincho"

# (Ziel relativ zu static/, Quelle)
DATEIEN = [
    ("vendor/basecoat.cdn.min.css", f"{NPM}/basecoat-css@1.0.2/dist/basecoat.cdn.min.css"),
    ("vendor/basecoat.all.min.js", f"{NPM}/basecoat-css@1.0.2/dist/js/all.min.js"),
    ("vendor/LICENSE-basecoat.md", f"{NPM}/basecoat-css@1.0.2/LICENSE.md"),
    ("vendor/htmx.min.js", f"{NPM}/htmx.org@2.0.11/dist/htmx.min.js"),
    ("vendor/LICENSE-htmx", f"{NPM}/htmx.org@2.0.11/LICENSE"),
    ("vendor/sse.min.js", f"{NPM}/htmx-ext-sse@2.2.4/dist/sse.min.js"),
    ("vendor/LICENSE-htmx-ext-sse", f"{NPM}/htmx-ext-sse@2.2.4/LICENSE"),
    ("vendor/force-graph.min.js", f"{NPM}/force-graph@1.52.0/dist/force-graph.min.js"),
    ("vendor/LICENSE-force-graph", f"{NPM}/force-graph@1.52.0/LICENSE"),
    ("vendor/lucide-sprite.svg", f"{NPM}/lucide-static@1.61.0/sprite.svg"),
    ("vendor/LICENSE-lucide", f"{NPM}/lucide-static@1.61.0/LICENSE"),
    ("fonts/inter.woff2", f"{NPM}/@fontsource-variable/inter@5.3.0/files/inter-latin-wght-normal.woff2"),
    ("fonts/LICENSE-inter", f"{NPM}/@fontsource-variable/inter@5.3.0/LICENSE"),
    ("fonts/jetbrains-mono.woff2",
     f"{NPM}/@fontsource-variable/jetbrains-mono@5.3.0/files/jetbrains-mono-latin-wght-normal.woff2"),
    ("fonts/LICENSE-jetbrains-mono", f"{NPM}/@fontsource-variable/jetbrains-mono@5.3.0/LICENSE"),
    ("fonts/LICENSE-shippori-mincho.txt", f"{GFONTS}/OFL.txt"),
]

# Shippori Mincho ist mehrere MB groß; Saku braucht nur die Zeichen aus zeichen.txt
MINCHO = {600: "ShipporiMincho-SemiBold.ttf", 700: "ShipporiMincho-Bold.ttf"}


def _laden(url: str, ziel: Path) -> None:
    # curl statt urllib: nutzt die Zertifikate des Systems (python.org-Builds auf macOS haben keine)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    teil = ziel.with_suffix(ziel.suffix + ".teil")
    subprocess.run(["curl", "-fsSL", "--retry", "2", "-o", str(teil), url], check=True)
    teil.rename(ziel)


def laden() -> None:
    for ziel, url in DATEIEN:
        pfad = STATIC / ziel
        if pfad.exists():
            continue
        print(f"  lade {ziel}")
        _laden(url, pfad)

    # Alle Kanji und Kana aus Templates und Code; kommt ein neues Zeichen dazu, wird die Schrift neu reduziert
    zeichen = STATIC / "fonts" / "zeichen.txt"
    quellen = [*STATIC.parent.rglob("*.html"), *STATIC.parent.parent.rglob("*.py")]
    alle = sorted({c for q in quellen for c in re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]", q.read_text(encoding="utf-8"))})
    alt = set(zeichen.read_text(encoding="utf-8").strip()) if zeichen.exists() else set()
    neu = "".join(sorted(alt | set(alle)))
    if set(neu) != alt:
        zeichen.write_text(neu + "\n", encoding="utf-8")
        for gewicht in MINCHO:
            (STATIC / "fonts" / f"shippori-mincho-{gewicht}.woff2").unlink(missing_ok=True)

    for gewicht, name in MINCHO.items():
        ziel = STATIC / "fonts" / f"shippori-mincho-{gewicht}.woff2"
        if ziel.exists():
            continue
        ttf = STATIC / "fonts" / name
        print(f"  lade und reduziere {name}")
        _laden(f"{GFONTS}/{name}", ttf)
        subprocess.run(
            [sys.executable, "-m", "fontTools.subset", str(ttf),
             f"--text-file={zeichen}", "--unicodes=U+0020-00FF,U+2013-2026,U+2190-2193,U+2423,U+2318",
             "--flavor=woff2", f"--output-file={ziel}"],
            check=True,
        )
        ttf.unlink()
    print("Alle Oberflächen-Dateien sind da.")
