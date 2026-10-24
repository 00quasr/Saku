"""Fahrplan als Kalenderdatei (RFC 5545): Zeilen, Faltung, Pflichtfelder, Meilensteine und Lern-Termin (Demo-Daten)."""

import re
from datetime import date, datetime, time, timedelta, timezone

from saku import db
from saku.lernen import fahrplan, kalender


def _parsen(roh: bytes) -> list[dict]:
    """Prüft Zeilenenden und Faltung, entfaltet und liefert die VEVENTs als {Name: Wert} (VALARM als eigener Eintrag)."""
    assert roh.endswith(b"\r\n") and b"\n" not in roh.replace(b"\r\n", b"")  # nur CRLF
    assert all(len(z) <= 75 for z in roh.split(b"\r\n"))  # gefaltet bei 75 Oktetten
    zeilen = roh.decode("utf-8").replace("\r\n ", "").split("\r\n")[:-1]
    assert zeilen[0] == "BEGIN:VCALENDAR" and zeilen[-1] == "END:VCALENDAR" and "VERSION:2.0" in zeilen
    assert any(z.startswith("PRODID:") for z in zeilen)
    termine, stapel = [], []
    for z in zeilen:
        name, _, wert = z.partition(":")
        if name == "BEGIN":
            stapel.append({})
        elif name == "END":
            fertig = stapel.pop()
            if wert == "VALARM":
                stapel[-1]["VALARM"] = fertig
            elif wert == "VEVENT":
                termine.append(fertig)
        elif stapel:
            stapel[-1][name] = wert
    assert not stapel
    return termine


def test_falten_und_maskieren():
    lang = "DESCRIPTION:" + "Prüfungsstoff wiederholen, Übungen; Grüße " * 6
    gefaltet = kalender.falten(lang).encode()
    assert all(len(z) <= 75 for z in gefaltet.split(b"\r\n")) and b"\r\n " in gefaltet
    assert gefaltet.decode().replace("\r\n ", "") == lang  # entfaltet wie vorher, kein Umlaut zerteilt
    assert kalender.text("a,b;c\\d\ne") == "a\\,b\\;c\\\\d\\ne"
    assert kalender.falten("kurz") == "kurz"


def test_meilensteine(con):
    heute = date.today()
    termin = date.fromisoformat(db.einstellung(con, "pruefungstermin"))
    m = {t["uid"]: t["tag"] for t in fahrplan.meilensteine(con, heute)}
    # 14 neue, Tagesziel 10 am Tag: Station 1 (3), 2 (2) und 4 (4) heute, 5 (4) und 6 (1) morgen; 3 und 7 haben keine
    stationen = {s["titel"]: s["id"] for s in con.execute("SELECT id, titel FROM station")}
    assert {u: t for u, t in m.items() if u.startswith("station-")} == {
        f"station-{stationen['Projektmanagement']}": heute, f"station-{stationen['Modellierung mit UML']}": heute,
        f"station-{stationen['Algorithmen']}": heute, f"station-{stationen['Datenbanken']}": heute + timedelta(days=1),
        f"station-{stationen['Qualitätssicherung']}": heute + timedelta(days=1)}
    assert m["alle-gesehen"] == heute + timedelta(days=1)
    assert m["puffer"] == termin - timedelta(days=7) and m["pruefung-ap2"] == termin and "pruefung-ap1" not in m


def test_route_mit_lern_termin(client, con):
    termin = date.fromisoformat(db.einstellung(con, "pruefungstermin"))
    antwort = client.get("/fahrplan.ics", query_string={"lernen": "1", "uhrzeit": "07:30", "dauer": "45"})
    assert antwort.status_code == 200 and antwort.mimetype == "text/calendar"
    assert antwort.headers["Content-Disposition"] == "attachment; filename=saku-fahrplan.ics"
    termine = _parsen(antwort.data)
    for t in termine:  # Pflichtfelder je Termin
        assert t["UID"].endswith("@saku") and re.fullmatch(r"\d{8}T\d{6}Z", t["DTSTAMP"])
        assert "DTSTART" in t or "DTSTART;VALUE=DATE" in t
    assert len({t["UID"] for t in termine}) == len(termine)
    pruefung = next(t for t in termine if t["UID"] == "pruefung-ap2@saku")
    assert pruefung["DTSTART;VALUE=DATE"] == f"{termin:%Y%m%d}" and pruefung["DTEND;VALUE=DATE"] == f"{termin + timedelta(days=1):%Y%m%d}"
    assert pruefung["SUMMARY"] == "Prüfung AP2"
    lernen = next(t for t in termine if "RRULE" in t)
    assert lernen["DTSTART"] == f"{date.today():%Y%m%d}T073000" and lernen["DURATION"] == "PT45M"
    assert lernen["RRULE"] == f"FREQ=DAILY;UNTIL={termin - timedelta(days=1):%Y%m%d}T235959"  # bis zum Tag vor der Prüfung
    assert lernen["VALARM"]["ACTION"] == "DISPLAY" and lernen["VALARM"]["TRIGGER"].startswith("-PT")
    # stabil: ein zweiter Download hat dieselben Termine
    assert [t["UID"] for t in _parsen(client.get("/fahrplan.ics").data)] == [t["UID"] for t in termine if "RRULE" not in t]
    assert 'action="/fahrplan.ics"' in client.get("/fahrplan").get_data(as_text=True)


def test_route_prueft_eingaben_und_ohne_termin(client, con):
    assert client.get("/fahrplan.ics", query_string={"lernen": "1", "uhrzeit": "25:99"}).status_code == 400
    assert client.get("/fahrplan.ics", query_string={"lernen": "1", "dauer": "1000"}).status_code == 400
    assert client.get("/fahrplan.ics", query_string={"lernen": "1", "dauer": "nan"}).status_code == 400
    db.setze_einstellung(con, "pruefungstermin", "")
    termine = _parsen(client.get("/fahrplan.ics", query_string={"lernen": "1"}).data)
    assert termine and not any("RRULE" in t or t["UID"].startswith("pruefung") for t in termine)  # ohne Termin kein Lern-Termin


def test_datei_ohne_termine():
    roh = kalender.datei([], kalender.lern_termin(date(2026, 1, 5), time(18), 30, 3), datetime(2026, 1, 5, 12, tzinfo=timezone.utc))
    (lernen,) = _parsen(roh.encode())
    assert lernen["DTSTAMP"] == "20260105T120000Z" and lernen["RRULE"] == "FREQ=DAILY;UNTIL=20260107T235959"
    assert kalender.lern_termin(date(2026, 1, 5), time(18), 30, 0) is None
