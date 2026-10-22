"""Claude-Anbindung für Pipeline und Sensei: Cache, Protokoll, API oder lokales Claude Code.

strukturiert() liefert JSON nach Schema – über die API oder (Erstlauf der Pipeline) über `claude -p`.
stream() liefert Text Stück für Stück – nur über die API.
"""

import base64
import hashlib
import json
import os
import sqlite3
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

from saku import config


class KiFehler(RuntimeError):
    """Die KI ist gerade nicht erreichbar oder hat nicht wie erwartet geantwortet."""


# Modelle mit serverseitigem Fallback, falls eine Anfrage abgelehnt wird
MIT_FALLBACK = {"claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1"}

_client = None


def verfuegbar() -> bool:
    """Ist ein API-Schlüssel gesetzt? Ohne ihn sind die Sensei-Knöpfe ausgegraut."""
    return bool(config.API_KEY)


def anthropic_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.API_KEY or None)
    return _client


def _anfrage(modell: str, system: str, max_tokens: int, aufwand: str | None) -> tuple:
    """Messages-Endpunkt und gemeinsame Parameter; der Systemprompt ist cachebar."""
    parameter = {
        "model": modell,
        "max_tokens": max_tokens,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
    }
    if aufwand:
        parameter["output_config"] = {"effort": aufwand}
    if modell in MIT_FALLBACK:
        parameter |= {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        return anthropic_client().beta.messages, parameter
    return anthropic_client().messages, parameter


def _protokoll(con: sqlite3.Connection, zweck: str, modell: str, ein: int, aus: int, cache: bool) -> None:
    con.execute(
        "INSERT INTO ki_aufruf (zweck, modell, tokens_ein, tokens_aus, aus_cache) VALUES (?, ?, ?, ?, ?)",
        (zweck, modell, ein, aus, int(cache)),
    )
    con.commit()


def _tokens_ein(usage) -> int:
    get = usage.get if isinstance(usage, dict) else lambda k, d=0: getattr(usage, k, d) or 0
    return sum(get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def strukturiert(con: sqlite3.Connection, zweck: str, rolle: str, system: str, text: str,
                 schema: dict, *, ki: str = "api", aufwand: str | None = "low", max_tokens: int = 4000,
                 bilder: Sequence[tuple[str, Path | bytes]] = ()) -> dict:
    """Antwort als dict nach JSON-Schema (Schema mit additionalProperties: false und required).
    bilder: (Name, Pfad oder Bytes), z. B. ("A1", …); Claude sieht sie mit diesem Namen. Bytes nur über die API.

    Gleiche Anfrage, gleiche Antwort: Treffer kommen aus ki_cache, egal über welchen Weg sie entstanden.
    """
    modell = config.MODELLE[rolle]
    inhalt = [[name, hashlib.sha256(_bytes(bild)).hexdigest()] for name, bild in bilder]
    schluessel = hashlib.sha256(
        json.dumps([modell, system, text, schema] + ([inhalt] if inhalt else []), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    treffer = con.execute("SELECT antwort FROM ki_cache WHERE schluessel = ?", (schluessel,)).fetchone()
    if treffer:
        _protokoll(con, zweck, modell, 0, 0, True)
        return json.loads(treffer[0])

    if ki == "claude-code":
        daten, ein, aus = _claude_code(modell, system, text, schema, bilder)
    else:
        daten, ein, aus = _api(modell, system, text, schema, aufwand, max_tokens, bilder)

    con.execute(
        "INSERT OR REPLACE INTO ki_cache (schluessel, modell, antwort) VALUES (?, ?, ?)",
        (schluessel, modell, json.dumps(daten, ensure_ascii=False)),
    )
    _protokoll(con, zweck, modell, ein, aus, False)
    return daten


def _api(modell, system, text, schema, aufwand, max_tokens, bilder=()) -> tuple[dict, int, int]:
    import anthropic

    if not verfuegbar():
        raise KiFehler("Kein API-Schlüssel gesetzt (ANTHROPIC_API_KEY in .env).")
    endpunkt, parameter = _anfrage(modell, system, max_tokens, aufwand)
    parameter.setdefault("output_config", {})["format"] = {"type": "json_schema", "schema": schema}
    try:
        inhalt = [block for name, bild in bilder for block in (
            {"type": "text", "text": f"Bild {name}:"},
            {"type": "image", "source": {"type": "base64", "media_type": _bildtyp(_bytes(bild)),
                                         "data": base64.b64encode(_bytes(bild)).decode()}})]
        antwort = endpunkt.create(messages=[{"role": "user", "content": inhalt + [{"type": "text", "text": text}]}], **parameter)
    except anthropic.APIError as fehler:
        raise KiFehler(f"Claude-API: {fehler}") from fehler
    if antwort.stop_reason in ("refusal", "max_tokens"):
        raise KiFehler(f"Claude-API hat nicht vollständig geantwortet ({antwort.stop_reason}).")
    roh = next(b.text for b in antwort.content if b.type == "text")
    return json.loads(roh), _tokens_ein(antwort.usage), antwort.usage.output_tokens


def _bytes(bild: Path | bytes) -> bytes:
    return bild if isinstance(bild, bytes) else bild.read_bytes()


def _bildtyp(roh: bytes) -> str:
    """Medientyp an den ersten Bytes erkennen (hochgeladene Zeichnungen können JPEG oder WebP sein)."""
    if roh.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if roh[:4] == b"RIFF" and roh[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


def _ohne_schluessel() -> dict:
    """Umgebung für claude -p ohne API-Schlüssel: sonst rechnet Claude Code über die API ab statt über das Abo
    (load_dotenv legt den Schlüssel aus .env in os.environ)."""
    return {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}


def _claude_code(modell, system, text, schema, bilder=()) -> tuple[dict, int, int]:
    # Bilder liest Claude Code selbst: nur das Read-Werkzeug, nur im Ordner der Bilder
    if any(isinstance(b, bytes) for _, b in bilder):
        raise KiFehler("Hochgeladene Bilder gehen nur über die API.")
    werkzeuge = ["--tools", "Read", "--allowedTools", "Read",
                 "--add-dir", os.path.commonpath([str(pfad.parent) for _, pfad in bilder])] if bilder else ["--tools", ""]
    if bilder:
        text += "\n\nBilder (lies jedes mit dem Read-Werkzeug, bevor du antwortest):\n" + "\n".join(
            f"- {name}: {pfad}" for name, pfad in bilder)
    befehl = [
        "claude", "-p", "--model", modell, "--system-prompt", system,
        "--json-schema", json.dumps(schema), "--output-format", "json",
        *werkzeuge, "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence",
    ]
    try:
        lauf = subprocess.run(befehl, input=text, capture_output=True, text=True, timeout=600, check=True, env=_ohne_schluessel())
        daten = json.loads(lauf.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as fehler:
        raise KiFehler(f"Claude Code antwortet nicht: {fehler}") from fehler
    if daten.get("is_error") or "structured_output" not in daten:
        raise KiFehler(f"Claude Code: {daten.get('result') or 'keine strukturierte Antwort'}")
    usage = daten.get("usage", {})
    return daten["structured_output"], _tokens_ein(usage), usage.get("output_tokens", 0)


def stream(con: sqlite3.Connection, zweck: str, system: str, nachrichten: list[dict], *,
           rolle: str = "stark", aufwand: str | None = "medium", max_tokens: int = 16000) -> Iterator[str]:
    """Text der Antwort Stück für Stück (für Server-Sent Events). Wirft KiFehler, wenn Sensei nicht erreichbar ist."""
    import anthropic

    if not verfuegbar():
        raise KiFehler("Kein API-Schlüssel gesetzt (ANTHROPIC_API_KEY in .env).")
    modell = config.MODELLE[rolle]
    endpunkt, parameter = _anfrage(modell, system, max_tokens, aufwand)
    try:
        with endpunkt.stream(messages=nachrichten, **parameter) as antwort:
            yield from antwort.text_stream
            final = antwort.get_final_message()
    except anthropic.APIError as fehler:
        raise KiFehler(f"Claude-API: {fehler}") from fehler
    _protokoll(con, zweck, modell, _tokens_ein(final.usage), final.usage.output_tokens, False)
