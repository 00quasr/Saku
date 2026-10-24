"""Fahrplan als Kalenderdatei (iCalendar, RFC 5545), nur mit der Standardbibliothek: ganztägige Termine aus
fahrplan.meilensteine und auf Wunsch ein täglicher Lern-Termin mit Erinnerung bis zur Prüfung."""

from datetime import date, datetime, time, timedelta, timezone

PRODID = "-//Saku//Fahrplan//DE"


def text(wert: str) -> str:
    """TEXT-Wert maskieren (RFC 5545, 3.3.11)."""
    return wert.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def falten(zeile: str) -> str:
    """Zeilen über 75 Oktette falten (3.1): jede Folgezeile beginnt mit einem Leerzeichen, UTF-8-Zeichen bleiben ganz."""
    teile, aktuell, laenge = [], "", 0
    for zeichen in zeile:
        if laenge + len(zeichen.encode()) > 75:
            teile.append(aktuell)
            aktuell, laenge = " ", 1
        aktuell += zeichen
        laenge += len(zeichen.encode())
    return "\r\n".join([*teile, aktuell])


def datei(termine: list[dict], lernen: dict | None = None, jetzt: datetime | None = None) -> str:
    """termine: {tag, titel, text, uid}, ganztägig und ohne belegte Zeit. lernen: {start, minuten, bis}; start ist eine
    Ortszeit ohne Zone (floating, gilt in der Zeitzone des Kalenders), bis der letzte Tag der Wiederholung."""
    stempel = f"DTSTAMP:{(jetzt or datetime.now(timezone.utc)).astimezone(timezone.utc):%Y%m%dT%H%M%SZ}"
    zeilen = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
              "X-WR-CALNAME:Saku – Fahrplan"]
    for t in termine:
        zeilen += ["BEGIN:VEVENT", f"UID:{t['uid']}@saku", stempel, f"DTSTART;VALUE=DATE:{t['tag']:%Y%m%d}",
                   f"DTEND;VALUE=DATE:{t['tag'] + timedelta(days=1):%Y%m%d}", f"SUMMARY:{text(t['titel'])}",
                   f"DESCRIPTION:{text(t['text'])}", "TRANSP:TRANSPARENT", "END:VEVENT"]
    if lernen:
        zeilen += ["BEGIN:VEVENT", "UID:lernen-taeglich@saku", stempel, f"DTSTART:{lernen['start']:%Y%m%dT%H%M%S}",
                   f"DURATION:PT{lernen['minuten']}M", f"RRULE:FREQ=DAILY;UNTIL={lernen['bis']:%Y%m%d}T235959",
                   "SUMMARY:Lernen mit Saku",
                   f"DESCRIPTION:{text('Tagesziel: neue Teilaufgaben und fällige Wiederholungen. Bis zur Prüfung jeden Tag ein Stück.')}",
                   "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-PT10M", "DESCRIPTION:Gleich lernen mit Saku", "END:VALARM",
                   "END:VEVENT"]
    zeilen.append("END:VCALENDAR")
    return "".join(falten(z) + "\r\n" for z in zeilen)


def lern_termin(heute: date, uhrzeit: time, minuten: int, tage_bis_pruefung: int | None) -> dict | None:
    """Täglicher Lern-Termin ab heute bis zum Tag vor der Prüfung; ohne künftigen Termin keiner."""
    if not tage_bis_pruefung or tage_bis_pruefung < 1:
        return None
    return {"start": datetime.combine(heute, uhrzeit), "minuten": minuten, "bis": heute + timedelta(days=tage_bis_pruefung - 1)}
