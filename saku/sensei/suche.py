"""Frag Sensei: Kontext für den Chat (RAG) und Quellen-Links.

1. Das schnelle Modell macht aus der Frage 3 bis 5 Suchbegriffe.
2. FTS5 `suche` liefert die besten 8 Teilaufgaben (bm25).
3. Daraus werden Kontextblöcke für das starke Modell.
"""

import re
import sqlite3
from html import escape

from markupsafe import Markup

from saku.sensei import client, prompts, vektoren

SYSTEM_SUCHE = """Du bildest Suchbegriffe für eine Volltextsuche über IHK-Prüfungsaufgaben (AP2).
Gib drei bis fünf kurze deutsche Fachbegriffe oder Wortstämme zurück, die in passenden
Aufgaben oder Lösungshinweisen wörtlich vorkommen würden. Jeder Begriff hat mindestens drei Zeichen."""

BEGRIFFE = {
    "type": "object",
    "properties": {"begriffe": {"type": "array", "items": {"type": "string"}}},
    "required": ["begriffe"],
    "additionalProperties": False,
}

QUELLE = re.compile(r"\[(T\d+(?:\s*[,;]\s*T\d+)*)\]")


def suchbegriffe(con: sqlite3.Connection, frage: str) -> list[str]:
    antwort = client.strukturiert(con, "suche", "schnell", SYSTEM_SUCHE, frage, BEGRIFFE)
    # Trigramm-Suche findet erst ab 3 Zeichen etwas
    return [b.strip() for b in antwort["begriffe"] if len(b.strip()) >= 3][:5]


def treffer(con: sqlite3.Connection, begriffe: list[str], anzahl: int = 8) -> list[int]:
    """IDs der besten Teilaufgaben; jeder Begriff ist eine Phrase, verknüpft mit OR."""
    if not begriffe:
        return []
    ausdruck = " OR ".join('"' + b.replace('"', '""') + '"' for b in begriffe)
    zeilen = con.execute(
        "SELECT teilaufgabe_id FROM suche WHERE suche MATCH ? ORDER BY bm25(suche) LIMIT ?", (ausdruck, anzahl))
    return [int(z[0]) for z in zeilen]


def kontext(con: sqlite3.Connection, frage: str, dazu: tuple[int, ...] = ()) -> str:
    """Kontextblöcke zur Frage; `dazu` sind Teilaufgaben, die die Seite gerade zeigt."""
    # Stichworte (Volltext) und Bedeutung (Vektoren) zusammen: findet auch Aufgaben mit anderen Worten
    umfang = {z[0] for z in con.execute("SELECT teilaufgabe_id FROM v_teilaufgabe")}
    nah = [i for i, _ in vektoren.suchen(con, "teilaufgabe", frage, n=8, erlaubt=umfang, schwelle=0.35)]
    ids = list(dict.fromkeys([*dazu, *vektoren.verschmelzen(treffer(con, suchbegriffe(con, frage)), nah)[:8]]))
    bloecke = [prompts.kontext(con, t) for i in ids if (t := prompts.teilaufgabe(con, i))]
    return "\n".join(bloecke) or "(Zu dieser Frage wurden keine passenden Aufgaben gefunden.)"


def quellen_links(con: sqlite3.Connection, html: str) -> Markup:
    """[T123] → Link „Winter 2024/25 · Aufgabe 3 b“, der die Teilaufgabe in Keiko öffnet."""
    ids = {int(k[1:]) for gruppe in QUELLE.findall(html) for k in re.split(r"\s*[,;]\s*", gruppe)}
    if not ids:
        return Markup(html)
    marken = ",".join("?" * len(ids))
    namen = {
        z["teilaufgabe_id"]: f"{z['termin']} · Aufgabe {z['aufgabe_nr']} {z['kennung']}"
        for z in con.execute(f"SELECT teilaufgabe_id, termin, aufgabe_nr, kennung FROM v_teilaufgabe "
                             f"WHERE teilaufgabe_id IN ({marken})", list(ids))
    }

    def link(kennung: str) -> str:
        i = int(kennung[1:])
        if i not in namen:
            return kennung
        return f'<a class="quelle" href="/keiko/?teilaufgabe={i}">{escape(namen[i])}</a>'

    def ersetzen(m: re.Match) -> str:
        teile = re.split(r"\s*[,;]\s*", m.group(1))
        if not any(int(k[1:]) in namen for k in teile):
            return m.group(0)
        return " ".join(link(k) for k in teile)

    return Markup(QUELLE.sub(ersetzen, html))
