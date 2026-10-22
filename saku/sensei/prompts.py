"""Prompts für Sensei, wörtlich aus docs/SENSEI.md.

Systemprompt und Kontextblock bleiben byte-stabil, damit das Prompt-Caching greift:
die Modus-Anweisung steht deshalb nicht im System, sondern hinter dem Kontext.
"""

import base64
import json
import sqlite3
from html import escape
from pathlib import Path

from saku.db import liste
from saku.lernen import antwort

SYSTEM = """Du bist Sensei, ein geduldiger Tutor für die IHK-Abschlussprüfung Teil 2 (AP2).
Du hilfst einer Person in der Ausbildung, echte Prüfungsaufgaben zu verstehen und zu lösen.

Regeln:
- Antworte auf Deutsch, in der Du-Form, klar und knapp. Nutze Markdown sparsam.
- Der Lösungshinweis ist deine Referenz. Er zeigt eine mögliche Lösung;
  andere fachlich richtige Antworten sind ebenfalls gültig.
- Rechne Schritt für Schritt und prüfe jedes Ergebnis, bevor du es nennst.
- Wenn du dir unsicher bist, sag es offen.
- Beziehe dich nur auf Aufgaben aus dem Kontext und nenne sie mit ihrer Kennung
  in eckigen Klammern, z. B. [T123]. Erfinde keine Prüfungsinhalte."""

ANWEISUNG = {
    "tipp": """Gib genau einen Denkanstoß in höchstens drei Sätzen.
Verrate weder das Ergebnis noch den vollständigen Lösungsweg.""",
    "erklaeren": """Erkläre den Lösungsweg Schritt für Schritt: zuerst das Grundprinzip in einem Satz,
dann die Schritte, zum Schluss typische Fehler bei dieser Art von Aufgabe.""",
    "variante": """Erstelle eine neue Aufgabe, die dieselbe Fähigkeit prüft, mit anderen Werten und
einer anderen Situation, im Stil einer AP2-Aufgabe. Gib danach unter der Überschrift
„Lösung“ eine vollständige Musterlösung.""",
    "thema": """Erkläre das Thema in höchstens 200 Wörtern so, wie es in der AP2 gebraucht wird.
Nenne danach die typischen Aufgabentypen dazu, gestützt auf die Beispiele im Kontext.""",
    "pruefen": """Bewerte die Antwort der Person im Vergleich zum Lösungshinweis wie ein IHK-Prüfer. Schätze die Punkte,
nenne, was richtig ist und was fehlt, und gib in einem Satz einen Hinweis, wie die Antwort vollständig wird.
Beachte den Operator: Bei „nennen“ genügen Stichworte, bei „erläutern“ oder „begründen“ gibt es ohne Begründung
oder Beispiel nur Teilpunkte.""",
    "chat": "Beantworte die Frage mit den Aufgaben im Kontext und nenne deine Quellen als [T123].",
}

# Antwort prüfen: Schema aus SENSEI.md (bewertung_abgeben), als JSON-Schema für strukturiert()
BEWERTUNG = {
    "type": "object",
    "properties": {
        "punkte": {"type": "number", "description": "geschätzte Punkte"},
        "max_punkte": {"type": "number"},
        "richtig": {"type": "array", "items": {"type": "string"}},
        "fehlt": {"type": "array", "items": {"type": "string"}},
        "hinweis": {"type": "string", "description": "ein Satz, wie die Antwort vollständig wird"},
    },
    "required": ["punkte", "max_punkte", "richtig", "fehlt", "hinweis"],
    "additionalProperties": False,
}

OHNE_LOESUNG = "(Kein offizieller Lösungshinweis vorhanden.)"
NUR_BILD = "(Der Lösungshinweis liegt nur als Bild bei.)"

# Eine Teilaufgabe mit allem, was der Kontextblock braucht
_TEILAUFGABE = """
SELECT t.id, t.kennung, t.text, t.punkte, t.typ, t.bilder, t.loesung_text, t.loesung_bilder,
       t.inhalt, t.antwort, t.loesung_inhalt, a.einleitung_inhalt, p.ausgangssituation_inhalt,
       a.nummer, a.einleitung, p.bereich, p.ausgangssituation, v.termin
FROM teilaufgabe t
JOIN aufgabe a ON a.id = t.aufgabe_id
JOIN pruefung p ON p.id = a.pruefung_id
JOIN v_teilaufgabe v ON v.teilaufgabe_id = t.id
WHERE t.id = ?
"""


def zahl(wert) -> str:
    """6.0 → '6', 1.5 → '1,5'"""
    if wert is None:
        return ""
    return f"{wert:g}".replace(".", ",")


def teilaufgabe(con: sqlite3.Connection, teilaufgabe_id: int) -> sqlite3.Row | None:
    return con.execute(_TEILAUFGABE, (teilaufgabe_id,)).fetchone()


def themen(con: sqlite3.Connection, teilaufgabe_id: int) -> str:
    zeilen = con.execute(
        "SELECT th.name FROM teilaufgabe_thema tt JOIN thema th ON th.id = tt.thema_id "
        "WHERE tt.teilaufgabe_id = ? ORDER BY tt.gewicht DESC, th.name", (teilaufgabe_id,))
    return ", ".join(z["name"] for z in zeilen)


def kontext(con: sqlite3.Connection, t: sqlite3.Row) -> str:
    """Kontextblock <aufgabe …> einer Teilaufgabe (Zeile aus teilaufgabe())."""
    attribute = {
        "kennung": f"T{t['id']}",
        "termin": t["termin"],
        "bereich": t["bereich"],
        "punkte": zahl(t["punkte"]),
        "thema": themen(con, t["id"]),
    }
    kopf = " ".join(f'{k}="{escape(v)}"' for k, v in attribute.items())
    return (
        f"<aufgabe {kopf}>\n"
        f"  <ausgangssituation>{t['ausgangssituation_inhalt'] or t['ausgangssituation'] or ''}</ausgangssituation>\n"
        f"  <einleitung>{t['einleitung_inhalt'] or t['einleitung'] or ''}</einleitung>\n"
        f"  <teilaufgabe>{t['inhalt'] or t['text']}\n{antwort.als_text(json.loads(t['antwort'] or 'null'))}</teilaufgabe>\n"
        f"  <loesungshinweis>{t['loesung_inhalt'] or t['loesung_text'] or (NUR_BILD if liste(t['loesung_bilder']) else OHNE_LOESUNG)}</loesungshinweis>\n"
        "</aufgabe>"
    )


def hat_loesung(t: sqlite3.Row) -> bool:
    return bool(t["loesung_inhalt"] or t["loesung_text"] or liste(t["loesung_bilder"]))


def bilder(t: sqlite3.Row, daten: Path) -> list[dict]:
    """Bildausschnitte als Inhaltsblöcke für die API: die Teilaufgabe, wenn sie vor allem aus einer
    Grafik besteht, und der Lösungshinweis, wenn es ihn nur als Bild gibt (je höchstens zwei)."""
    pfade = []
    if t["typ"] in ("zeichnen", "tabelle") or len(t["text"].strip()) < 80:
        pfade += liste(t["bilder"])[:2]
    if not t["loesung_text"]:
        pfade += liste(t["loesung_bilder"])[:2]
    return [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                     "data": base64.standard_b64encode((daten / p).read_bytes()).decode()}}
        for p in pfade if (daten / p).is_file()
    ]


def thema_kontext(con: sqlite3.Connection, thema_id: int) -> str | None:
    """Thema mit seinen Stichworten und den punktstärksten Teilaufgaben als Beispiele."""
    th = con.execute("SELECT name, stichworte, beschreibung FROM thema WHERE id = ?", (thema_id,)).fetchone()
    if th is None:
        return None
    ids = [z[0] for z in con.execute(
        "SELECT z.teilaufgabe_id FROM v_zuordnung z JOIN v_teilaufgabe v ON v.teilaufgabe_id = z.teilaufgabe_id "
        "WHERE z.thema_id = ? ORDER BY z.gewicht * v.punkte_gewichtet DESC, v.termin_index DESC, z.teilaufgabe_id LIMIT 8",
        (thema_id,))]
    beschreibung = "\n".join(x for x in (th["stichworte"], th["beschreibung"]) if x)
    bloecke = [kontext(con, t) for i in ids if (t := teilaufgabe(con, i))]
    return "\n".join([f'<thema name="{escape(th["name"])}">{beschreibung}</thema>', *bloecke])


def nachricht(kontext_text: str, anweisung: str, bild_bloecke: list[dict] | None = None) -> dict:
    """Nutzernachricht: Bilder und Kontext zuerst (cachebar), danach die wechselnde Anweisung."""
    return {"role": "user", "content": [
        *(bild_bloecke or []),
        {"type": "text", "text": kontext_text, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": anweisung},
    ]}


FACHGESPRAECH = """Du bist Prüferin oder Prüfer im IHK-Fachgespräch zur betrieblichen Projektarbeit (Fachinformatiker/-in).
Grundlage ist die Projektdokumentation unten. Führe das Gespräch wie in der echten Prüfung, etwa 15 Minuten lang:
- Stelle immer genau eine Frage. Wechsle zwischen Entscheidungen im Projekt (Warum diese Lösung? Welche Alternativen?
  Was würdest du heute anders machen?) und Fachwissen rund um das Projekt (z. B. Datenbanken, Netzwerk, Sicherheit,
  Wirtschaftlichkeit, Qualitätssicherung, Projektmanagement).
- Nach jeder Antwort: eine kurze Rückmeldung in ein bis zwei Sätzen (was überzeugt, was ein Prüfer vermisst), dann
  die nächste Frage. Sag keine Musterlösung vor.
- Schreibt die Person „Auswertung“, fasse Stärken, Schwächen und eine Notentendenz nach IHK-Schlüssel zusammen.
Antworte auf Deutsch, knapp und freundlich-sachlich."""


def fachgespraech_system(projekt_text: str) -> str:
    """Systemprompt mit der Projektdokumentation (cachebar, bleibt über das ganze Gespräch gleich)."""
    return f"{FACHGESPRAECH}\n\n<projektdokumentation>\n{projekt_text[:40000]}\n</projektdokumentation>"
