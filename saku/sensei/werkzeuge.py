"""Ausbaustufe: Werkzeuge für exakte Rechnungen. Sensei ruft das Werkzeug auf, Python rechnet.

Sprachmodelle können sich verrechnen; bei Rechenaufgaben (typ 'berechnen') bekommt Sensei deshalb
`zahlensystem_umrechnen` und eine eigene Tool-Use-Schleife statt client.stream().
"""

import json
import sqlite3
from collections.abc import Iterator

from saku import config
from saku.sensei import client

BASEN = {"binaer": 2, "dezimal": 10, "hexadezimal": 16}

ZAHLENSYSTEM = {
    "name": "zahlensystem_umrechnen",
    "description": "Rechnet eine ganze Zahl exakt zwischen binär, dezimal und hexadezimal um. "
                   "Nutze das Werkzeug für jede Umrechnung, statt selbst zu rechnen.",
    "input_schema": {
        "type": "object",
        "properties": {
            "zahl": {"type": "string", "description": "die Zahl, z. B. 1011, 255 oder FF"},
            "von": {"type": "string", "enum": list(BASEN), "description": "Zahlensystem der Zahl"},
        },
        "required": ["zahl", "von"],
        "additionalProperties": False,
    },
}

RUNDEN = 5  # höchstens so viele Werkzeug-Runden, falls das Modell nicht aufhört


def zahlensystem_umrechnen(zahl: str, von: str) -> dict:
    """'FF', 'hexadezimal' → {'binaer': '11111111', 'dezimal': '255', 'hexadezimal': 'FF'}"""
    wert = int(zahl.strip().replace(" ", "").replace("_", ""), BASEN[von])
    return {"binaer": format(wert, "b"), "dezimal": str(wert), "hexadezimal": format(wert, "X")}


def ergebnis(block) -> dict:
    """tool_result für einen tool_use-Block; Fehler gehen als is_error zurück an Sensei."""
    try:
        if block.name != ZAHLENSYSTEM["name"]:
            raise KeyError(block.name)
        return {"type": "tool_result", "tool_use_id": block.id,
                "content": json.dumps(zahlensystem_umrechnen(**block.input), ensure_ascii=False)}
    except (KeyError, TypeError, ValueError) as fehler:
        return {"type": "tool_result", "tool_use_id": block.id, "is_error": True,
                "content": f"Nicht umrechenbar: {fehler}"}


def stream(con: sqlite3.Connection, zweck: str, system: str, nachrichten: list[dict], *,
           rolle: str = "stark", aufwand: str | None = "medium", max_tokens: int = 16000) -> Iterator[str]:
    """Wie client.stream(), aber Sensei darf zwischendurch rechnen lassen."""
    import anthropic

    if not client.verfuegbar():
        raise client.KiFehler("Kein API-Schlüssel gesetzt (ANTHROPIC_API_KEY in .env).")
    modell = config.MODELLE[rolle]
    endpunkt, parameter = client._anfrage(modell, system, max_tokens, aufwand)
    nachrichten = list(nachrichten)
    for _ in range(RUNDEN):
        try:
            with endpunkt.stream(messages=nachrichten, tools=[ZAHLENSYSTEM], **parameter) as antwort:
                yield from antwort.text_stream
                final = antwort.get_final_message()
        except anthropic.APIError as fehler:
            raise client.KiFehler(f"Claude-API: {fehler}") from fehler
        u = final.usage
        ein = u.input_tokens + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0)
        client._protokoll(con, zweck, modell, ein, u.output_tokens, False)
        if final.stop_reason != "tool_use":
            return
        # Die ganze Antwort zurückgeben (samt Denk-Blöcken), dann alle Ergebnisse in einer Nachricht
        nachrichten += [{"role": "assistant", "content": final.content},
                        {"role": "user", "content": [ergebnis(b) for b in final.content if b.type == "tool_use"]}]
        yield "\n\n"
    raise client.KiFehler("Sensei hat zu oft gerechnet und keine Antwort gegeben.")
