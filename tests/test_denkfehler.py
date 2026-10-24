"""Typische Denkfehler im Rechentrainer: erkannt mit derselben Toleranz wie die Lösung, gezeigt am Feld (nur erfundene Aufgaben)."""

import html
import ipaddress
import re

import pytest

from saku.lernen import rechnen
from saku.lernen.rechnen import Aufgabe, Feld
from saku.lernen.rechnen.basis import Art, de

HTMX = {"HX-Request": "true"}
# Arten mit typischen Fehlern; jede Variante soll mindestens einen haben
MIT_DIAGNOSE = ["subnetz", "uebertragung", "datenmenge", "speicher", "zahlensystem", "energie", "raid", "verfuegbarkeit", "backup",
                "kalkulation", "vergleich", "netzplan", "passwort", "schluessel", "verzug", "kuendigung", "urlaub", "monitor", "bandbreite"]


def _getippt(f: Feld, wert) -> str:
    """Der typische Wert so, wie man ihn eintippt: Zahlen auf die angezeigten Stellen."""
    return de(float(wert), f.stellen) if f.typ == "zahl" else str(wert)


def _alle(art: str, titel: str | None = None):
    for seed in range(150):
        a = rechnen.erzeugen(art, seed)
        if titel is None or a.titel == titel:
            yield seed, a


def test_mechanik_mit_derselben_toleranz_wie_die_loesung():
    a = Aufgabe("Frage", [Feld("hosts", "Hosts", 62, stellen=0, typisch=((64, "Mitgezählt."),)),
                          Feld("mib", "Größe", 1000, "MiB", typisch=((1024, "1.000 statt 1.024."),)),
                          Feld("netz", "Netz-ID", "10.0.0.64", typ="ip", typisch=(("10.0.0.127", "Vertauscht."),))],
                "Weg", toleranz=0.005)
    assert rechnen.denkfehler(a, {"hosts": "64", "mib": "1.024", "netz": "10.0.0.127"}) == \
        {"hosts": "Mitgezählt.", "mib": "1.000 statt 1.024.", "netz": "Vertauscht."}
    # Toleranz und Normalisierung wie bei stimmt: 0,5 % daneben, führende Nullen, Einheit dahinter
    assert rechnen.denkfehler(a, {"mib": "1.028 MiB", "netz": "010.000.000.127"}) == {"mib": "1.000 statt 1.024.", "netz": "Vertauscht."}
    assert rechnen.denkfehler(a, {"hosts": "62", "mib": "1.003", "netz": "10.0.0.64"}) == {}  # richtig: kein Hinweis
    assert rechnen.denkfehler(a, {"hosts": "63", "mib": "1.100", "netz": ""}) == {}  # falsch, aber kein typischer Fehler


def test_typische_werte_gleich_der_loesung_fallen_beim_erzeugen_weg(monkeypatch):
    def erzeugen(rng):
        return Aufgabe("Frage", [Feld("x", "X", 62, stellen=0, typisch=((62, "gleich"), (62.3, "gerundet gleich"), (64, "bleibt"))),
                                 Feld("t", "T", "SSH", typ="text", auch=("SFTP",), typisch=(("sftp", "auch richtig"), ("FTP", "bleibt")))],
                       "Weg")
    monkeypatch.setitem(rechnen.ARTEN, "probe", Art("probe", "Probe", "Netzwerk", "", (), erzeugen))
    a = rechnen.erzeugen("probe", 1)
    assert [h for f in a.felder for _, h in f.typisch] == ["bleibt", "bleibt"]
    assert rechnen.denkfehler(a, {"x": "62", "t": "SFTP"}) == {}


@pytest.mark.parametrize("art", MIT_DIAGNOSE)
def test_jeder_typische_fehler_ist_falsch_und_wird_erkannt(art):
    varianten = {}
    for seed, a in _alle(art):
        assert rechnen.denkfehler(a, {f.name: f.anzeige for f in a.felder}) == {}, seed  # die Lösung ist nie ein Denkfehler
        for f in a.felder:
            for wert, hinweis in f.typisch:
                getippt = _getippt(f, wert)
                assert hinweis.strip() and hinweis.endswith("."), (seed, f.name, hinweis)
                assert not rechnen.stimmt(f, getippt, a.toleranz), (seed, f.name, wert)
                assert rechnen.denkfehler(a, {f.name: getippt}).get(f.name), (seed, f.name, wert)
            varianten[a.titel] = varianten.get(a.titel, 0) + len(f.typisch)
    assert all(varianten.values()), varianten  # jede Variante hat welche


def test_gegenprobe_subnetz_mit_ipaddress():
    for _, a in _alle("subnetz", "Netz-ID und Broadcast"):
        netz = ipaddress.ip_interface(re.search(r"`([\d.]+/\d+)`", a.frage)[1]).network
        hinweise = rechnen.denkfehler(a, {"hosts": str(netz.num_addresses), "netz": str(netz.broadcast_address),
                                          "broadcast": str(netz.network_address)})
        assert "mitgezählt" in hinweise["hosts"] and "vertauscht" in hinweise["netz"] and hinweise["netz"] == hinweise["broadcast"]


def test_gegenprobe_schluessel_und_differenzkalkulation():
    for _, a in _alle("schluessel", "Schlüssel zählen"):
        n = int(re.search(r"\*\*(\d+) Personen\*\*", a.frage)[1])
        hinweise = rechnen.denkfehler(a, {"symmetrisch": str(n * n), "asymmetrisch": str(n)})
        assert "n²" in hinweise["symmetrisch"] and "Schlüsselpaare" in hinweise["asymmetrisch"]
        assert "durch 2" in rechnen.denkfehler(a, {"symmetrisch": str(n * (n - 1))})["symmetrisch"]
    for _, a in _alle("kalkulation", "Differenzkalkulation"):
        l = a.loesung
        vom_bvp = de(l["gewinn"] / l["bvp"] * 100)  # Gewinn auf den Barverkaufspreis bezogen statt auf die Selbstkosten
        assert "Grundwert sind die Selbstkosten" in rechnen.denkfehler(a, {"prozent": vom_bvp})["prozent"]


def test_gegenprobe_uebertragung_bit_byte_und_1000_statt_1024():
    for _, a in _alle("uebertragung", "Datenmenge in einer Zeit"):
        zahl, praefix = re.search(r"\*\*([\d,]+) (M|G)bit/s\*\*", a.frage).groups()
        bit = float(zahl.replace(",", ".")) * (1000 if praefix == "G" else 1) * 10 ** 6 * int(re.search(r"\*\*(\d+) Minuten", a.frage)[1]) * 60
        hinweise = rechnen.denkfehler(a, {"gb": de(bit / 10 ** 9), "gib": de(bit / 8 / 10 ** 9)})  # in Bit; durch 1.000³ statt 1.024³
        assert "Bit und Byte" in hinweise["gb"] and "1.000 statt 1.024" in hinweise["gib"]


def test_hinweis_auf_der_karte_und_im_sprint(client):
    seed, a = next(x for x in _alle("schluessel", "Schlüssel zählen"))
    n = int(re.search(r"\*\*(\d+) Personen\*\*", a.frage)[1])
    hinweis = a.felder[0].typisch[0][1]

    def pruefen(**daten):
        return client.post("/rechnen/schluessel/pruefen", data={"seed": seed} | daten, headers=HTMX).get_data(as_text=True)
    seite = pruefen(**{"feld-symmetrisch": str(n * n), "feld-asymmetrisch": str(2 * n)})
    assert "1 von 2 richtig." in seite and f'<span class="rechnen-denkfehler">{html.escape(hinweis)}</span>' in seite
    assert "rechnen-denkfehler" not in pruefen(**{f"feld-{f.name}": f.anzeige for f in a.felder})
    assert "rechnen-denkfehler" not in pruefen(**{"feld-symmetrisch": "1"})  # falsch, aber kein typischer Fehler
    sprint = client.post("/rechnen/sprint/lauf", data={"a": f"schluessel:{seed}", "start": "1",
                                                        "a1-symmetrisch": str(n * n)}).get_data(as_text=True)
    assert html.escape(hinweis) in sprint
