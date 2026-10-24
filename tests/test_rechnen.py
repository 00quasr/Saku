"""Rechentrainer: Generatoren, Kontrolle und Routen (nur erfundene Aufgaben)."""

import html
import ipaddress
import itertools
import random
import re
from pathlib import Path

import pytest

from saku.lernen import rechnen
from saku.lernen.rechnen import Feld
from saku.lernen.rechnen.basis import de

SEEDS = range(150)


def _alle(art: str, titel: str | None = None):
    for seed in SEEDS:
        a = rechnen.erzeugen(art, seed)
        if titel is None or a.titel == titel:
            yield seed, a


def _zahl(text: str) -> float:
    return float(text.replace(".", "").replace(",", "."))


@pytest.mark.parametrize("art", list(rechnen.ARTEN))
def test_jede_art_deterministisch_abwechslungsreich_und_selbst_lesbar(art):
    fragen = set()
    for seed, a in _alle(art):
        b = rechnen.erzeugen(art, seed)
        assert (a.frage, a.rechenweg, a.loesung) == (b.frage, b.rechenweg, b.loesung)
        assert a.art == art and a.titel and a.themen and a.felder and len({f.name for f in a.felder}) == len(a.felder)
        # was Saku als richtigen Wert anzeigt, muss die Kontrolle selbst als richtig erkennen
        assert all(rechnen.pruefen(a, {f.name: f.anzeige for f in a.felder}).values()), (seed, a.titel)
        leer = rechnen.pruefen(a, {})  # leer ist nur richtig, wo die Lösung leer ist (freie Plätze beim Hashing)
        assert all(leer[f.name] == (f.loesung == "") for f in a.felder)
        assert "Demo GmbH" in a.frage or any(f in a.frage for f in ("Muster AG", "Beispiel KG", "Fiktiv", "Probe & Partner"))
        fragen.add(a.frage)
    assert len(fragen) > len(SEEDS) * 0.6


def test_varianten_kommen_alle_vor():
    titel = {art: {a.titel for _, a in _alle(art)} for art in rechnen.ARTEN}
    assert len(titel["subnetz"]) == 6 and len(titel["datenmenge"]) == 5 and len(titel["energie"]) == 5
    assert all(len(t) >= 2 for t in titel.values())


# --- unabhängig nachgerechnet ------------------------------------------------

def test_subnetz_wie_ipaddress():
    for seed, a in _alle("subnetz"):
        l = a.loesung
        if a.titel == "Netz-ID und Broadcast":
            netz = ipaddress.ip_interface(re.search(r"`([\d.]+/\d+)`", a.frage)[1]).network
            assert (l["maske"], l["netz"], l["broadcast"]) == (str(netz.netmask), str(netz.network_address), str(netz.broadcast_address))
            assert l["hosts"] == netz.num_addresses - 2
        elif a.titel == "Erster und letzter Host":
            ip, maske = re.findall(r"`([\d.]+)`", a.frage)
            netz = ipaddress.ip_network(f"{ip}/{maske}", strict=False)
            hosts = list(itertools.islice(netz.hosts(), 1))
            assert l["praefix"] == netz.prefixlen and l["netz"] == str(netz.network_address)
            assert l["erster"] == str(hosts[0]) and l["letzter"] == str(netz.broadcast_address - 1)
        elif a.titel == "Präfix → Maske":
            netz = ipaddress.ip_network(f"0.0.0.0/{re.search(r'`/(\d+)`', a.frage)[1]}")
            assert l["maske"] == str(netz.netmask) and l["hosts"] == netz.num_addresses - 2
        elif a.titel == "Maske → Präfix":
            netz = ipaddress.ip_network(f"0.0.0.0/{re.search(r'`([\d.]+)`', a.frage)[1]}")
            assert l["praefix"] == netz.prefixlen and l["hosts"] == netz.num_addresses - 2
        elif a.titel == "Netz teilen":
            netz = ipaddress.ip_network(re.search(r"`([\d.]+/\d+)`", a.frage)[1])
            n, k = int(re.search(r"\*\*(\d+) gleich große", a.frage)[1]), int(re.search(r"\*\*(\d+)\. Subnetzes", a.frage)[1])
            teil = list(netz.subnets(new_prefix=netz.prefixlen + n.bit_length() - 1))[k - 1]
            assert l["praefix"] == teil.prefixlen and l["hosts"] == teil.num_addresses - 2
            assert (l["netz"], l["broadcast"]) == (str(teil.network_address), str(teil.broadcast_address))
        else:
            netz = ipaddress.ip_network(re.search(r"`([\d.]+/\d+)`", a.frage)[1])
            bedarf = int(re.search(r"mindestens (\d+) Hosts", a.frage)[1])
            p = max(q for q in range(netz.prefixlen + 1, 31) if 2 ** (32 - q) - 2 >= bedarf)
            assert (l["praefix"], l["hosts"], l["anzahl"]) == (p, 2 ** (32 - p) - 2, 2 ** (p - netz.prefixlen))


def test_netzplan_ueber_alle_wege():
    """Projektdauer = längster Weg; Gesamtpuffer = Projektdauer − längster Weg durch den Vorgang; der kritische Pfad ist eindeutig."""
    for seed, a in _alle("netzplan"):
        zeilen = re.findall(r"^\| ([A-H]) \| [^|]+ \| (\d+) \| ([^|]+) \|$", a.frage, re.M)
        dauer = {v: int(d) for v, d, _ in zeilen}
        vor = {v: [] if p.strip() == "–" else [x.strip() for x in p.split(",")] for v, _, p in zeilen}
        ende = zeilen[-1][0]

        def wege(v):  # alle Wege vom Start bis v
            return [[v]] if not vor[v] else [w + [v] for u in vor[v] for w in wege(u)]
        laenge = {tuple(w): sum(dauer[x] for x in w) for w in wege(ende)}
        projekt = max(laenge.values())
        laengste = ["-".join(w) for w, n in laenge.items() if n == projekt]
        l = a.loesung
        assert len(laengste) == 1 and l.get("pfad", laengste[0]) == laengste[0]
        assert l.get("dauer", projekt) == projekt
        x = re.search(r"Vorgang ([A-H])", a.frage.split("ermitteln Sie")[1])[1]
        gp = projekt - max(n for w, n in laenge.items() if x in w)
        assert l.get("gp", gp) == gp
        if "faz" in l:
            assert l["saz"] - l["faz"] == gp and l["fez"] - l["faz"] == l["sez"] - l["saz"] == dauer[x]


def test_datenmengen_nachgerechnet():
    einheiten = {"kB": 1e3, "MB": 1e6, "GB": 1e9, "KiB": 2 ** 10, "MiB": 2 ** 20, "GiB": 2 ** 30}
    for seed, a in _alle("datenmenge", "Bild"):
        b, h = map(_zahl, re.search(r"\*\*([\d.]+) × ([\d.]+) Pixeln", a.frage).groups())
        bit = int(m[1]) if (m := re.search(r"Farbtiefe von (\d+) Bit", a.frage)) else int(_zahl(re.search(r"mit ([\d.]+) Farben", a.frage)[1])).bit_length() - 1
        einheit = re.search(r"in Byte und in (\w+)", a.frage)[1]
        assert a.loesung["byte"] == b * h * bit / 8
        assert a.loesung["einheit"] == pytest.approx(b * h * bit / 8 / einheiten[einheit])
    for seed, a in _alle("speicher", "Was zeigt das Betriebssystem?"):
        wert, einheit = re.search(r"\*\*([\d.]+) (GB|TB)\*\*", a.frage).groups()
        exponent = {"GB": 3, "TB": 4}[einheit]
        assert a.loesung["anzeige"] == pytest.approx(_zahl(wert) * 1000 ** exponent / 1024 ** exponent)


def test_raid_kalkulation_zahlensysteme_ipv6():
    for seed, a in _alle("raid"):
        if m := re.search(r"\*\*RAID (\d+)\*\* aus \*\*(\d+) Festplatten\*\* mit je \*\*(\d+) TB", a.frage):
            level, n, tb = map(int, m.groups())
            assert a.loesung["nutz"] == {0: n, 1: 1, 5: n - 1, 6: n - 2, 10: n / 2}[level] * tb
            assert a.loesung["ausfall"] == {0: 0, 1: n - 1, 5: 1, 6: 2, 10: 1}[level]
    for seed, a in _alle("kalkulation", "Bezugskalkulation"):
        lep, rabatt, skonto, bezug = (_zahl(x) for x in re.findall(r": ([\d.,]+) (?:€|%)", a.frage))
        assert a.loesung["bzp"] == pytest.approx(lep * (1 - rabatt / 100) * (1 - skonto / 100) + bezug, abs=0.02)
    for seed, a in _alle("zahlensystem"):
        l = a.loesung
        if "binaer" in l and "hex" in l:
            assert int(l["binaer"], 2) == int(l["hex"], 16) == int(re.search(r"\*\*(\d+)\*\*", a.frage)[1])
        if "muster" in l:
            n = int(re.search(r"\*\*−(\d+)\*\*", a.frage)[1])
            assert int(l["muster"], 2) == (-n) & 0xFF and l["wert"] < 0
    for seed, a in _alle("ipv6"):
        if "kurz" in a.loesung:
            lang = re.search(r"`([0-9a-f:]+)`", a.frage)[1]
            assert a.loesung["kurz"] == ipaddress.ip_address(lang).compressed and "::" in a.loesung["kurz"]
        if "lang" in a.loesung:
            assert ipaddress.ip_address(a.loesung["lang"]) == ipaddress.ip_address(re.search(r"`([0-9a-f:]+)`", a.frage)[1])
            assert len(a.loesung["lang"]) == 39


# --- Kontrolle ---------------------------------------------------------------------

def test_zahlen_in_deutscher_schreibweise():
    feld = Feld("x", "Datenmenge", 1024, stellen=0)
    for richtig in ["1024", "1.024", "1 024", "1024 MiB", "1.024,0", " 1024,4 "]:
        assert rechnen.stimmt(feld, richtig), richtig
    for falsch in ["1.025", "1,024", "1023", "", "viel"]:
        assert not rechnen.stimmt(feld, falsch), falsch
    gerundet = Feld("x", "Datenmenge", 5.93262, "MiB")
    assert rechnen.stimmt(gerundet, "5,93") and rechnen.stimmt(gerundet, "5.93") and not rechnen.stimmt(gerundet, "5,9")
    assert rechnen.stimmt(gerundet, "5,9", toleranz=0.01)  # 1 % relativ
    assert rechnen.stimmt(Feld("x", "Kosten", 1234.5, "€"), "1.234,50 €") and rechnen.stimmt(Feld("n", "Netze", 65536, stellen=0), "2^16")


def test_text_ip_pfad_und_zahlensysteme():
    ip = Feld("netz", "Netz-ID", "192.168.1.10", typ="ip")
    assert all(rechnen.stimmt(ip, t) for t in ["192.168.1.10", " 192.168.001.010 ", "192.168.1.10/24"])
    assert not any(rechnen.stimmt(ip, t) for t in ["192.168.1.11", "192.168.1", "abc", ""])
    pfad = Feld("pfad", "Kritischer Pfad", "A-C-E-F", typ="pfad")
    assert all(rechnen.stimmt(pfad, t) for t in ["A-C-E-F", "a c e f", "A, C, E, F", "A → C → E → F", "ACEF"])
    assert not rechnen.stimmt(pfad, "A-C-F") and not rechnen.stimmt(pfad, "A-E-C-F")
    binaer, hexa = Feld("b", "Binär", "00101011", typ="binaer"), Feld("h", "Hex", "2B", typ="hex")
    assert all(rechnen.stimmt(binaer, t) for t in ["00101011", "0010 1011", "101011", "0b101011"])
    assert not rechnen.stimmt(binaer, "00101010") and not rechnen.stimmt(binaer, "zwei")
    assert all(rechnen.stimmt(hexa, t) for t in ["2B", "2b", "0x2B", "2Bh"]) and not rechnen.stimmt(hexa, "2C")
    v6 = Feld("kurz", "Kurzform", "2001:db8::5e:0:9b4f", typ="text")
    assert rechnen.stimmt(v6, "2001:DB8::5E:0:9B4F") and not rechnen.stimmt(v6, "2001:db8:0:0:0:5e:0:9b4f")
    wahl = Feld("sieger", "Sieger", "Beta Systeme", typ="text", optionen=["Alpha IT", "Beta Systeme"])
    assert rechnen.stimmt(wahl, "Beta Systeme") and not rechnen.stimmt(wahl, "Alpha IT")


def test_passende_art_zu_themen():
    """Erfundene, aber typisch formulierte Themennamen; nur der Name zählt, Teilwörter auch mitten im Wort."""
    passt = {
        "subnetz": ["Subnetze planen", "IPv4-Adressvergabe im Firmennetz", "IP-Adressierung im LAN", "IP-Konfiguration eines Druckers"],
        "uebertragung": ["Übertragungszeit im WAN", "Restoredauer einer Sicherung"],
        "ipv6": ["Adressierung mit IPv6"],
        "datenmenge": ["Datenmenge von Scans und Fotos", "Farbtiefe und Auflösung"],
        "speicher": ["Speichereinheiten (SI und IEC)", "Speichergrößen umrechnen", "Kapazitätsplanung für Fileserver"],
        "zahlensystem": ["Zahlensysteme umrechnen", "Hexadezimalzahlen"],
        "energie": ["Stromkosten am Arbeitsplatz", "Energieeffizienz von Servern", "Elektrische Größen am Netzteil", "USV-Auswahl"],
        "raid": ["RAID-Level vergleichen"],
        "kalkulation": ["Angebotskalkulation für Kunden", "Quantitativer Angebotsvergleich", "Handelskalkulation"],
        "vergleich": ["Leasing oder Kauf", "Kostenarten im IT-Betrieb", "Amortisation einer Investition"],
        "nutzwert": ["Nutzwertanalyse bei der Lieferantenwahl", "Entscheidungsmatrix"],
        "netzplan": ["Netzplantechnik", "Gantt-Diagramm erstellen", "Projektplanung und Termine"],
        "schreibtisch": ["Schreibtischtest mit Wertetabelle", "Kontrollstrukturen in Pseudocode", "Programmcode lesen und verstehen"],
        "sortieren": ["Sortierverfahren vergleichen", "Bubblesort und Quicksort"],
        "binaersuche": ["Suchalgorithmen im Array", "Binäre Suche"],
        "hashing": ["Hashtabellen und Kollisionen", "Assoziative Arrays"],
        "baum": ["Binärbaum durchlaufen", "Bäume und Graphen"],
        "stapel": ["Stack und Heap", "Warteschlangen im Druckdienst"],
        "verfuegbarkeit": ["Verfügbarkeit von Diensten", "Hochverfügbarkeit im Rechenzentrum", "MTBF und MTTR", "Redundanz im Netz"],
        "kuendigung": ["Kündigungsfristen im Arbeitsverhältnis", "Ausbildungsvertrag und Probezeit", "Grundlagen Arbeitsrecht"],
        "urlaub": ["Urlaubsanspruch berechnen", "Jugendarbeitsschutz in der Ausbildung"],
        "backup": ["Datensicherung im Büro", "Backupstrategien vergleichen", "Generationenprinzip"],
        "monitor": ["Peripheriegeräte auswählen", "Pixeldichte von Displays"],
        "bandbreite": ["PC-Komponenten und ihre Leistungsdaten", "Arbeitsspeicher aufrüsten"],
        "vlsm": ["IP-Adresskonzept für den Standort", "VLSM in der Praxis"],
        "routing": ["Statisches Routing", "Router und Gateways"],
        "eui64": ["SLAAC und EUI-64", "Autokonfiguration von Clients"],
        "ports": ["Portnummern und Dienste", "Firewallregeln", "Well-known Ports"],
        "osi": ["ISO/OSI-Referenzmodell", "OSI-Schichtenmodell", "Kopplungselemente im LAN", "TCP/IP-Modell"],
        "passwort": ["Passwortrichtlinien", "Brute-Force-Angriffe", "Sichere Kennwörter", "Passwörter speichern"],
        "schluessel": ["Symmetrische und asymmetrische Verschlüsselung", "Kryptografie im Alltag", "Public-Key-Verfahren"],
        "schutzbedarf": ["Schutzbedarfsfeststellung", "Schutzziele der Informationssicherheit", "IT-Grundschutz nach BSI"],
        "risiko": ["Risikoanalyse", "Risikomanagement im Projekt", "Risiken bewerten"],
        "pruefziffer": ["Paritätsprüfung", "Prüfziffern bei Barcodes", "ISBN und EAN-13"],
        "dsgvo": ["DSGVO und BDSG", "Meldung einer Datenpanne", "Bußgelder im Datenschutz"],
    }
    for slug, namen in passt.items():
        for name in namen:
            art = rechnen.passend([name])
            assert art and art.slug == slug, name
    # früher zu breit: „Binär“, „Bandbreite“, „Übertragung“, „Strom“, „Speicher“, „Netz“, „Elektrische“, „IP-Adresse“
    for name in ["Bandbreitenmanagement mit QoS", "Übertragungsmedien im Gebäude",
                 "Datenstrom-Verarbeitung", "Speicherverwaltung im Betriebssystem", "Netzwerkmonitoring", "Elektrische Sicherheit prüfen",
                 "Energielabel und Gütesiegel", "NAT mit privaten Adressen", "Laufzeit und Speicherbedarf",
                 "Fehlersuche im Netzwerk", "Hashwerte und digitale Signaturen", "Gruppenrichtlinien", "Netzwerkmonitoring",
                 "Bildschirmmasken entwerfen", "Namensauflösung mit DNS", "Qualitätssicherung", "Sozialversicherung",
                 # Stichworte der IT-Sicherheit und Ports nicht als Teilwort anderer Begriffe: Port, OSI, EAN, Schlüssel, Gefährdung
                 "Report im Teamtreffen", "Import und Export", "Git-Repository anlegen", "Clean Code", "Primärschlüssel und Fremdschlüssel",
                 "Gefährdungsbeurteilung am Arbeitsplatz", None]:
        assert rechnen.passend([name]) is None, name
    # mehrere Themen: das erste passende (Keiko sortiert nach Gewicht)
    assert rechnen.passend(["Scrum", "Netzplantechnik", "RAID-Level"]).slug == "netzplan"


def test_gemischt_bevorzugt_schwaches():
    rng = random.Random(1)
    quoten = {a: 1.0 for a in rechnen.ARTEN} | {"netzplan": 0.0}
    gezogen = [rechnen.gemischt(rng, quoten) for _ in range(2000)]
    assert gezogen.count("netzplan") > 3 * max(gezogen.count(a) for a in rechnen.ARTEN if a != "netzplan")
    assert set(gezogen) == set(rechnen.ARTEN)


def test_deutsche_zahlen_anzeigen():
    assert (de(1024), de(1.81899), de(0.5), de(16382), de(-14)) == ("1.024", "1,82", "0,5", "16.382", "-14")


# --- Routen (Demo-Datenbank) -----------------------------------------------------

HTMX = {"HX-Request": "true"}


def test_uebersicht_und_seitenleiste(client):
    html = client.get("/rechnen/").get_data(as_text=True)
    assert all(a.titel in html for a in rechnen.ARTEN.values()) and all(a.gruppe.replace("&", "&amp;") in html for a in rechnen.ARTEN.values())
    assert 'href="/rechnen/gemischt" data-taste="Enter"' in html and "Noch nicht gerechnet" in html
    assert 'href="/rechnen/"' in client.get("/").get_data(as_text=True)  # Seitenleiste
    assert client.get("/rechnen/gibtsnicht").status_code == 404


def test_aufgabe_hat_feste_adresse(client):
    weiter = client.get("/rechnen/subnetz")
    assert weiter.status_code == 302 and re.search(r"/rechnen/subnetz\?seed=\d+$", weiter.headers["Location"])
    eins, zwei = (client.get("/rechnen/netzplan?seed=42").get_data(as_text=True) for _ in range(2))
    frage = re.compile(r'rechnen-frage">(.*?)</div>', re.S)
    assert frage.search(eins)[1] == frage.search(zwei)[1] and 'name="seed" value="42"' in eins and "autofocus" in eins
    teil = client.get("/rechnen/netzplan?seed=42", headers=HTMX)
    assert teil.headers["HX-Push-Url"] == "/rechnen/netzplan?seed=42" and "<html" not in teil.get_data(as_text=True)
    assert re.search(r"/rechnen/\w+\?seed=\d+&gemischt=1$", client.get("/rechnen/gemischt").headers["Location"])
    assert 'hx-get="/rechnen/gemischt"' in client.post("/rechnen/raid/pruefen", data={"seed": 1, "gemischt": "1", "aufgeben": "1"},
                                                      headers=HTMX).get_data(as_text=True)


def test_pruefen_speichert_den_versuch(client, con):
    assert 'Rechnen <span class="zahl">0 / 5</span>' in client.get("/").get_data(as_text=True)  # Rechen-Tagesziel, Standard 5
    a = rechnen.erzeugen("subnetz", 7)
    n, erstes = len(a.felder), a.felder[0]
    richtig = {f"feld-{f.name}": f.anzeige for f in a.felder}

    def pruefen(**daten):
        return client.post("/rechnen/subnetz/pruefen", data={"seed": 7} | daten, headers=HTMX).get_data(as_text=True)
    html = pruefen(**richtig)
    assert "Richtig." in html and "Rechenweg" in html and 'data-taste="Enter"' in html and "Nächste Aufgabe" in html
    html = pruefen(**richtig | {f"feld-{erstes.name}": "falsch"})
    assert f"{n - 1} von {n} richtig." in html and f"<strong class=\"zahl\">{erstes.anzeige}</strong>" in html
    assert "Zählt als nicht gelöst" in pruefen(aufgeben="1")
    assert "Noch nichts eingetragen" in pruefen(**{f"feld-{erstes.name}": "  "})  # ↵ auf leerer Karte zählt nicht
    zeilen = [tuple(z) for z in con.execute("SELECT art, seed, richtig, felder_richtig, felder_gesamt FROM rechenuebung ORDER BY id")]
    assert zeilen == [("subnetz", 7, 1, n, n), ("subnetz", 7, 0, n - 1, n), ("subnetz", 7, 0, 0, n)]
    assert "1 von 3 zuletzt · 3 gerechnet" in client.get("/rechnen/").get_data(as_text=True)
    heute = client.get("/").get_data(as_text=True)
    assert 'Rechnen <span class="zahl">3 / 5</span>' in heute and 'href="/rechnen/gemischt"' in heute and "Heute gerechnet" not in heute
    # Rechnen zählt als Lerntag: Lernserie und Kalender, das Tagesziel bleibt, wie es war
    from saku.lernen import tagesziel
    assert tagesziel.lernserie(con) == 1 and tagesziel.tagesziel(con)["erledigt"] == 0
    assert '<span class="zahl">1</span> Tag in Folge' in heute
    assert client.post("/rechnen/subnetz/pruefen", data={}).status_code == 400


def test_einbindung_suche_ueben_themen(client, con):
    from saku.web.routen.suche import befehle
    assert ("calculator", "Rechnen: Subnetting") == befehle("subnetting")[0][:2]
    assert befehle("rechnen gemischt")[0][3] == ("rechnen.gemischt", {})
    assert '/rechnen/netzplan"' in client.get("/suche/?q=netzplan").get_data(as_text=True)

    def teilaufgabe(text):
        return con.execute("SELECT id FROM teilaufgabe WHERE text LIKE ?", (f"%{text}%",)).fetchone()[0]
    netzplan = client.get(f"/keiko/?teilaufgabe={teilaufgabe('kritischen Pfad')}").get_data(as_text=True)
    assert 'Ähnliches rechnen, mit immer neuen Zahlen: <a href="/rechnen/netzplan">Netzplan →</a>' in netzplan
    # nur der Themenname zählt: „Wirtschaftlichkeit“ (Stichworte Amortisation, Nutzwertanalyse) führt zu Kauf/Leasing/Miete
    assert 'href="/rechnen/vergleich"' in client.get(f"/keiko/?teilaufgabe={teilaufgabe('Nutzwertanalyse')}").get_data(as_text=True)
    assert "Ähnliches rechnen" not in client.get(f"/keiko/?teilaufgabe={teilaufgabe('Whitebox')}").get_data(as_text=True)

    thema = con.execute("SELECT id FROM thema WHERE name = 'Netzplan'").fetchone()[0]
    notiz = client.get(f"/niwa/thema/{thema}", headers=HTMX).get_data(as_text=True)
    assert 'href="/rechnen/netzplan">Netzplan →</a>' in notiz
    andere = con.execute("SELECT id FROM thema WHERE name = 'Rekursion'").fetchone()[0]
    assert "Ähnliches rechnen" not in client.get(f"/niwa/thema/{andere}", headers=HTMX).get_data(as_text=True)


# --- Schreibtischtest ----------------------------------------------------------------

def _pseudocode_ausfuehren(code: str) -> tuple[list[int], dict]:
    """Der angezeigte Pseudocode, Zeile für Zeile nach Python übersetzt (nur im Test, nur eigener Text)."""
    zeilen = []
    for zeile in code.splitlines():
        text = re.sub(r"^\s*\d+  ", "", zeile)
        einzug, befehl = re.match(r"(\s*)(.*)", text).groups()
        befehl = (befehl.replace(" DIV ", " // ").replace(" MOD ", " % ").replace("≠", "!=").replace("≤", "<=")
                  .replace("≥", ">=").replace(" = ", " == ").replace("länge(", "len(").replace(" ← ", " = "))
        if befehl.startswith("ENDE"):
            continue
        for muster, ersatz in [(r"WENN (.*) DANN", r"if \1:"), (r"SONST", "else:"), (r"SOLANGE (.*)", r"while \1:"),
                               (r"FÜR (\w+) = (.*) BIS (.*)", r"for \1 in range(\2, (\3) + 1):"), (r"AUSGABE (.*)", r"aus(\1)")]:
            befehl = re.sub(f"^{muster}$", ersatz, befehl)
        zeilen.append(einzug + befehl)
    ausgabe = []
    variablen = {"aus": lambda *werte: [ausgabe.extend(w if isinstance(w, list) else [w]) for w in werte]}
    exec("\n".join(zeilen), variablen)
    return ausgabe, variablen


def _folge(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"-?\d+", text)]


def test_schreibtisch_wie_python_und_wie_beschrieben():
    import math
    zwecke = [
        (r"Quersumme von (\d+)", lambda n: [sum(map(int, n))]),
        (r"Binärdarstellung von (\d+)", lambda n: [int(b) for b in reversed(f"{int(n):b}")]),
        (r"Teiler von (\d+) und (\d+)", lambda a, b: [math.gcd(int(a), int(b))]),
        (r"Fakultät (\d+)!", lambda n: [math.factorial(int(n))]),
        (r"Potenz (\d+) hoch (\d+)", lambda b, n: [int(b) ** int(n)]),
        (r"von (\d+) bis (\d+) addieren, die durch (\d+)", lambda a, b, k: [sum(i for i in range(int(a), int(b) + 1) if i % int(k) == 0),
                                                                          sum(1 for i in range(int(a), int(b) + 1) if i % int(k))]),
    ]
    for seed, a in _alle("schreibtisch"):
        # am Struktogramm steht derselbe Code erst im Rechenweg; das Struktogramm zeigt dieselben Zeilen
        code = re.search(r"```\n(.*?)```", a.frage if not a.struktogramm else a.rechenweg, re.S)[1]
        assert ("```" in a.frage) != bool(a.struktogramm) and a.titel.endswith("am Struktogramm") == bool(a.struktogramm)
        for zeile in code.splitlines():
            befehl = html.escape(re.sub(r"^\s*\d+  \s*", "", zeile), quote=False)
            assert befehl.startswith(("ENDE", "SONST")) or (befehl.removeprefix("WENN ").removesuffix(" DANN") in a.struktogramm) == bool(a.struktogramm)
        ausgabe, variablen = _pseudocode_ausfuehren(code)
        if a.titel == "Fehlersuche":
            nummer = a.loesung["zeile"]
            fehlerhaft = re.search(r"`([^`]+)`, richtig wäre", a.rechenweg)[1]
            assert re.search(rf"^\s*{nummer}  \s*(.*)$", code, re.M)[1] == fehlerhaft
            assert ausgabe == _folge(re.search(r"gibt das Programm \*\*(.*?)\*\* aus", a.rechenweg)[1])
            continue
        assert ausgabe == _folge(re.search(r"Ausgabe: \*\*(.*?)\*\*", a.rechenweg)[1]), seed
        for name, wert in a.loesung.items():
            if a.titel.startswith("Endwerte"):
                assert _folge(str(wert)) == _folge(str(variablen[name])), (seed, name)
        if a.titel.startswith("Ausgabe"):
            assert _folge(str(a.loesung["ausgabe"])) == ausgabe
        zweck = a.frage.split("\n")[0].split("Es soll ")[1]
        for muster, erwartet in zwecke:
            if m := re.search(muster, zweck):
                assert ausgabe == erwartet(*m.groups()), (seed, zweck)
        if "umkehren" in zweck:
            assert ausgabe == _folge(re.search(r"zahlen ← \[(.*?)\]", code)[1])[::-1]


def test_wertetabelle_als_eingabetabelle(client):
    seed, a = next((s, a) for s, a in _alle("schreibtisch", "Wertetabelle"))
    assert a.tabellen_felder == {f.name for f in a.felder} and len(a.tabelle) == len(a.tabelle[1:]) + 1
    html = client.get(f"/rechnen/schreibtisch?seed={seed}").get_data(as_text=True)
    assert html.count('<input name="feld-d') == len(a.felder) and 'class="rechnen-felder"' not in html
    daten = {"seed": seed, **{f"feld-{f.name}": f.anzeige for f in a.felder}, f"feld-{a.felder[0].name}": "999"}
    html = client.post("/rechnen/schreibtisch/pruefen", data=daten, headers=HTMX).get_data(as_text=True)
    assert f"{len(a.felder) - 1} von {len(a.felder)} richtig." in html and html.count("rechnen-zelle--falsch") == 1


def test_verhaeltnisse_als_bruch():
    acht_fuenf = Feld("v", "Seitenverhältnis", "8:5", typ="verhaeltnis")
    assert all(rechnen.stimmt(acht_fuenf, t) for t in ["8:5", "16:10", "16 : 10", "16/10", "16 zu 10", "1,6:1", "1.6:1", "32:20"])
    assert not any(rechnen.stimmt(acht_fuenf, t) for t in ["16:9", "5:8", "1,5:1", "16", "16:0", "", "acht zu fünf"])
    neun = Feld("v", "Seitenverhältnis", "16:9", typ="verhaeltnis")
    assert rechnen.stimmt(neun, "1,78:1") and rechnen.stimmt(neun, "1,7778:1") and not rechnen.stimmt(neun, "1,7:1")  # auf die getippten Stellen
    assert not rechnen.stimmt(Feld("v", "Seitenverhältnis", "43:18", typ="verhaeltnis"), "21:9")  # 2,389 ist nicht 2,333
    for seed, a in _alle("monitor", "Seitenverhältnis"):
        b, h = map(_zahl, re.search(r"\*\*([\d.]+) × ([\d.]+)\*\*", a.frage).groups())
        assert rechnen.stimmt(a.felder[0], f"{int(b)}:{int(h)}")  # auch ungekürzt ist das Verhältnis dasselbe


def test_listen_und_leere_zellen():
    liste = Feld("a", "Array", "3, 8, 1", typ="liste")
    assert all(rechnen.stimmt(liste, t) for t in ["3, 8, 1", "3 8 1", "[3; 8; 1]", "3-8-1", "03,8,1"])
    assert not rechnen.stimmt(liste, "3, 1, 8") and not rechnen.stimmt(liste, "3, 8")
    leer = Feld("z", "Zelle", "", typ="text")
    assert rechnen.stimmt(leer, "") and not rechnen.stimmt(leer, "5") and not rechnen.stimmt(Feld("z", "Zahl", 5, stellen=0), "")


def test_formelsammlung(client):
    from saku.web.routen.suche import befehle
    assert all("Beispiel" in a.formeln for a in rechnen.ARTEN.values())
    html = client.get("/rechnen/formeln").get_data(as_text=True)
    assert all(f'<article class="formel-art" id="{a.slug}">' in html for a in rechnen.ARTEN.values()) and 'onclick="print()"' in html
    assert 'href="/rechnen/formeln"' in client.get("/rechnen/").get_data(as_text=True)
    assert befehle("formelsammlung")[0][3] == ("rechnen.formeln", {})
    karte = client.post("/rechnen/raid/pruefen", data={"seed": 1, "aufgeben": "1"}, headers=HTMX).get_data(as_text=True)
    assert "Formeln: RAID" in karte and 'href="/rechnen/formeln#raid"' in karte  # dieselbe Quelle wie die Sammlung


# --- Algorithmen und Verfügbarkeit (Runde 3) -------------------------------------

def _array(text: str) -> list[int]:
    return _folge(re.search(r"`\[([\d, ]+)\]`", text)[1])


def test_sortieren_mit_eigenschaften():
    for seed, a in _alle("sortieren"):
        start, l = _array(a.frage), a.loesung
        if "Vertauschungen" in a.titel:
            inversionen = sum(1 for i in range(len(start)) for j in range(i + 1, len(start)) if start[i] > start[j])
            if a.titel.startswith("Bubblesort"):
                assert l["tausch"] == inversionen
            else:  # Selectionsort: ein Tausch je Stelle, an der das Minimum noch nicht steht
                rest, tausch = list(start), 0
                for i in range(len(rest) - 1):
                    k = rest.index(min(rest[i:]), i)
                    tausch += k != i
                    rest[i], rest[k] = rest[k], rest[i]
                assert l["tausch"] == tausch
            continue
        k = int(re.search(r"\*\*(\d)\. Durchlauf", a.frage)[1])
        nach = [l[f"i{i}"] for i in range(len(start))]
        assert sorted(nach) == sorted(start)
        if a.titel.startswith("Bubblesort"):
            assert nach[-k:] == sorted(start)[-k:]
        elif a.titel.startswith("Selectionsort"):
            assert nach[:k] == sorted(start)[:k]
        else:
            assert nach[:k + 1] == sorted(start[:k + 1]) and nach[k + 1:] == start[k + 1:]


def test_binaersuche_rekursiv_nachgerechnet():
    def suche(werte, x, links, rechts):
        if links > rechts:
            return []
        mitte = (links + rechts) // 2
        if werte[mitte] == x:
            return [x]
        return [werte[mitte]] + (suche(werte, x, mitte + 1, rechts) if werte[mitte] < x else suche(werte, x, links, mitte - 1))
    for seed, a in _alle("binaersuche"):
        werte, x = _array(a.frage), int(re.search(r"Gesucht wird \*\*(\d+)\*\*", a.frage)[1])
        erwartet = suche(werte, x, 0, len(werte) - 1)
        assert _folge(a.loesung["werte"]) == erwartet and a.loesung["anzahl"] == len(erwartet) <= len(werte).bit_length()
        assert (a.titel == "Gefunden") == (x in werte)


def test_hashing_und_baum_und_stapel():
    for seed, a in _alle("hashing"):
        m = int(re.search(r"m = (\d+)", a.frage)[1])
        tabelle_ = {}
        for k in _folge(re.search(r"nacheinander: \*\*(.*?)\*\*", a.frage)[1]):
            i = k % m
            while i in tabelle_:
                i = (i + 1) % m
            tabelle_[i] = k
        if "i0" in a.loesung:
            assert [a.loesung[f"i{i}"] for i in range(m)] == [tabelle_.get(i, "") for i in range(m)]
        else:
            k = int(re.search(r"Schlüssel \*\*(\d+)\*\*", a.frage)[1])
            assert tabelle_[a.loesung["index"]] == k
    for seed, a in _alle("baum"):
        schluessel = _folge(re.search(r"nacheinander:\n\n\*\*(.*?)\*\*", a.frage)[1])
        if "in" in a.loesung:
            assert _folge(a.loesung["in"]) == sorted(schluessel)
        if "pre" in a.loesung:  # die Preorder neu eingefügt ergibt denselben Baum, also wieder dieselbe Preorder
            from saku.lernen.rechnen.algorithmen import durchlauf, suchbaum
            pre = _folge(a.loesung["pre"])
            assert pre[0] == schluessel[0] and durchlauf(suchbaum(pre), "pre") == pre
        assert 3 <= a.loesung["hoehe"] <= len(schluessel)
    for seed, a in _alle("stapel"):
        inhalt, ausgabe = [], []
        for op, wert in re.findall(r"(\w+)\((\d*)\)", re.search(r"`(.*?)`", a.frage)[1]):
            if wert:
                inhalt.append(int(wert))
            else:
                ausgabe.append(inhalt.pop() if op == "pop" else inhalt.pop(0))
        assert _folge(a.loesung["ausgabe"]) == ausgabe and _folge(a.loesung["inhalt"]) == inhalt and inhalt


def test_verfuegbarkeit_nachgerechnet():
    def prozent(text):
        return _zahl(text) / 100
    for seed, a in _alle("verfuegbarkeit"):
        l = a.loesung
        if a.titel == "Ausfallzeit aus Prozent":
            v = prozent(re.search(r"Verfügbarkeit von \*\*([\d,]+) %", a.frage)[1])
            assert l["jahr"] == pytest.approx((1 - v) * 365 * 24) and l["monat"] == pytest.approx((1 - v) * 30 * 24 * 60)
        elif a.titel == "MTBF und MTTR":
            mtbf, mttr = (_zahl(x) for x in re.findall(r"\*\*([\d.]+) Stunden", a.frage))
            assert l["v"] == pytest.approx(100 * mtbf / (mtbf + mttr))
        elif a.titel == "Seriell und redundant":
            router, firewall, server, storage = (prozent(x) for x in re.findall(r": ([\d,]+) %", a.frage))
            n = int(re.search(r"\*\*(\d) redundanten", a.frage)[1])
            assert l["gesamt"] == pytest.approx(100 * router * firewall * (1 - (1 - server) ** n) * storage)
        else:
            stunden = int(re.search(r"höchstens \*\*(\d+) Stunde", a.frage)[1])
            angebot = prozent(re.search(r"SLA mit \*\*([\d,]+) %", a.frage)[1])
            assert l["noetig"] == pytest.approx(100 * (1 - stunden / 8760)) and (l["reicht"] == "Ja") == (angebot > 1 - stunden / 8760)


# --- WiSo (Runde 4) -------------------------------------------------------------------

MONATSNAMEN = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


def _zugang(text: str):
    """Der Zugang steht als „Mittwoch, 2. Februar 2028“ in der Frage."""
    from datetime import date
    m = re.search(r"\*\*\w+, (\d+)\. (\w+) (\d{4})\*\*", text)
    return date(int(m[3]), MONATSNAMEN.index(m[2]) + 1, int(m[1]))


def _tag(text: str):
    """Das erste Datum als TT.MM.JJJJ (Eintritt, Austritt, Geburtstag)."""
    from datetime import date
    t, mo, j = map(int, re.search(r"\*\*(\d\d)\.(\d\d)\.(\d{4})\*\*", text).groups())
    return date(j, mo, t)


def test_kuendigungstermine_anders_nachgerechnet():
    import calendar
    from datetime import date, timedelta

    def letzter(j, m):
        return date(j, m, calendar.monthrange(j, m)[1])

    def grund(z):  # Tag für Tag: erster 15. oder Monatsletzter mit mindestens 28 Tagen Abstand
        t = z + timedelta(days=1)
        while not ((t - z).days >= 28 and (t.day == 15 or t == letzter(t.year, t.month))):
            t += timedelta(days=1)
        return t

    def monatsende_mit_frist(z, n):  # Monatsende M ist erreichbar, wenn z spätestens am Letzten des Monats n Monate vor M liegt
        j, m = z.year, z.month
        while True:
            vor_j, vor_m = (j * 12 + m - 1 - n) // 12, (j * 12 + m - 1 - n) % 12 + 1
            if z <= letzter(vor_j, vor_m):
                return letzter(j, m)
            j, m = (j, m + 1) if m < 12 else (j + 1, 1)

    for seed, a in _alle("kuendigung"):
        l = a.loesung
        if "ende" not in l:
            assert l["frist"] == "Nur fristlos aus wichtigem Grund"
            continue
        zugang = _zugang(a.frage)
        ende = date(*reversed([int(x) for x in l["ende"].split(".")]))
        if a.titel in ("Kündigung durch den Arbeitnehmer",):
            assert ende == grund(zugang) and l["frist"].startswith("4 Wochen zum 15.")
        elif a.titel == "Kündigung in der Probezeit":
            assert (ende - zugang).days == 14
        elif a.titel == "Ausbildung: Kündigung":
            assert (ende - zugang).days in (0, 28) and ((ende - zugang).days == 0) == ("Probezeit läuft" in a.rechenweg)
        else:
            eintritt = _tag(a.frage)
            jahre = max(k for k in range(0, 40) if date(eintritt.year + k, eintritt.month, min(eintritt.day, 28)) <= zugang)
            monate = next((m for j, m in [(20, 7), (15, 6), (12, 5), (10, 4), (8, 3), (5, 2), (2, 1)] if jahre >= j), 0)
            assert ende == (monatsende_mit_frist(zugang, monate) if monate else grund(zugang)), (seed, jahre)


def test_urlaub_nachgerechnet():
    import math
    from datetime import date
    for seed, a in _alle("urlaub"):
        l = a.loesung
        if a.titel == "Werktage umrechnen":
            geburt, jahr = _tag(a.frage), int(re.search(r"im Jahr (\d{4})", a.frage)[1])
            alter = jahr - 1 - geburt.year  # Geburtstage liegen nie am 1. Januar
            assert l["werktage"] == {15: 30, 16: 27, 17: 25}.get(alter, 24)
            woche = int(re.search(r"an (\d) Tagen pro Woche", a.frage)[1])
            assert l["tage"] == pytest.approx(l["werktage"] / 6 * woche)
            continue
        urlaub_ = int(re.search(r"sieht (\d+) Arbeitstage", a.frage)[1])
        stichtag, jahr = _tag(a.frage), int(re.search(r"im Jahr (\d{4})", a.frage)[1])
        if a.titel.startswith("Eintritt"):
            voll = stichtag <= date(jahr, 6, 30)
            monate = (12 - stichtag.month) + (1 if stichtag.day == 1 else 0)
        else:
            voll = stichtag > date(jahr, 6, 30)
            monate = stichtag.month - (0 if stichtag.day > 15 else 1)
        if voll:
            assert l["anspruch"] == urlaub_ and l["art"].startswith("Voller")
        else:
            roh = urlaub_ * monate / 12
            assert roh % 1 == 0 or roh % 1 >= 0.5  # Reste unter einem halben Tag erzeugt Saku nicht
            assert l["anspruch"] == (math.ceil(roh) if roh % 1 >= 0.5 else roh) and l["art"].startswith("Anteilig"), seed


def test_datum_eingaben():
    feld = Feld("ende", "Ende", "31.03.2027", typ="datum")
    assert all(rechnen.stimmt(feld, t) for t in ["31.03.2027", "31.3.2027", "31.03.27", "31. 3. 2027", "2027-03-31"])
    assert not any(rechnen.stimmt(feld, t) for t in ["30.03.2027", "31.03.2026", "31.02.2027", "März", "31.03."])


def test_differenz_und_rueckwaertskalkulation():
    def wert(muster, text):
        return _zahl(re.search(muster, text)[1])
    for seed, a in _alle("kalkulation"):
        if a.titel not in ("Differenzkalkulation", "Rückwärtskalkulation"):
            continue
        f = a.frage
        r, s = wert(r"Liefererrabatt: ([\d,]+) %", f) / 100, wert(r"Liefererskonto: ([\d,]+) %", f) / 100
        bk, hk = wert(r"Bezugskosten: ([\d.,]+) €", f), wert(r"Handlungskostenzuschlag: ([\d,]+) %", f) / 100
        ks, kr = wert(r"Kundenskonto: ([\d,]+) %", f) / 100, wert(r"Kundenrabatt: ([\d,]+) %", f) / 100
        lvp = wert(r"\*\*([\d.,]+) € netto\*\*", f)
        bvp = lvp * (1 - kr) * (1 - ks)  # vom Hundert, ohne Zwischenrundung
        assert a.loesung["bvp"] == pytest.approx(bvp, abs=0.02)
        if a.titel == "Differenzkalkulation":
            sk = (wert(r"Listeneinkaufspreis: ([\d.,]+) €", f) * (1 - r) * (1 - s) + bk) * (1 + hk)
            assert a.loesung["sk"] == pytest.approx(sk, abs=0.03)
            assert a.loesung["gewinn"] == pytest.approx(bvp - sk, abs=0.05) and a.loesung["prozent"] == pytest.approx((bvp - sk) / sk * 100, abs=0.01)
        else:
            g = wert(r"\*\*([\d,]+) % Gewinn\*\*", f) / 100
            lep = (bvp / (1 + g) / (1 + hk) - bk) / (1 - s) / (1 - r)
            assert a.loesung["lep"] == pytest.approx(lep, abs=0.05)
            # Probe vorwärts: mit diesem Einkaufspreis kommt genau der Marktpreis heraus
            vor = (a.loesung["lep"] * (1 - r) * (1 - s) + bk) * (1 + hk) * (1 + g) / (1 - ks) / (1 - kr)
            assert vor == pytest.approx(lvp, abs=0.2)


# --- Rechen-Sprint ---------------------------------------------------------------------

def test_sprint_ablauf_punkte_note(client, con):
    from urllib.parse import parse_qs, urlparse
    from saku.lernen import simulation
    from saku.web.routen.suche import befehle
    assert 'href="/rechnen/sprint/neu" data-taste="Enter"' in client.get("/rechnen/sprint").get_data(as_text=True)
    assert 'href="/rechnen/sprint"' in client.get("/rechnen/").get_data(as_text=True)
    assert befehle("sprint")[0][3] == ("rechnen.sprint", {})

    adresse = client.get("/rechnen/sprint/neu").headers["Location"]
    q = parse_qs(urlparse(adresse).query)
    arten = [w.split(":")[0] for w in q["a"]]
    assert len(arten) == 5 == len(set(arten)) and all(a in rechnen.ARTEN for a in arten)
    html = client.get(adresse).get_data(as_text=True)
    assert html.count('class="sprint-aufgabe"') == 5 and html.count("autofocus") == 1 and 'id="sprint-uhr"' in html

    aufgaben = [rechnen.erzeugen(art, int(seed)) for art, seed in (w.split(":") for w in q["a"])]
    daten = {"a": q["a"], "start": q["start"][0]}
    daten |= {f"a1-{f.name}": f.anzeige for f in aufgaben[0].felder}  # erste ganz richtig
    zweite = aufgaben[1].felder
    daten |= {f"a2-{zweite[0].name}": zweite[0].anzeige or "x"}  # zweite: ein Feld (leer richtig gilt nicht für ganz leere Aufgaben)
    richtig_2 = sum(rechnen.pruefen(aufgaben[1], {zweite[0].name: zweite[0].anzeige or "x"}).values())
    erreicht = 20 + round(20 * richtig_2 / len(zweite), 1)
    html = client.post("/rechnen/sprint/lauf", data=daten).get_data(as_text=True)
    note = simulation.note(simulation.umrechnen(erreicht, 100))
    assert f"Note {note} · {simulation.NOTEN[note]}" in html and html.count('<details class="kontext"') == 5
    zeilen = con.execute("SELECT art, richtig FROM rechenuebung ORDER BY id").fetchall()
    assert [z[0] for z in zeilen] == arten and zeilen[0][1] == 1 and not any(z[1] for z in zeilen[2:])
    client.post("/rechnen/sprint/lauf", data=daten)  # neu laden schickt noch einmal ab: nicht doppelt zählen
    assert con.execute("SELECT COUNT(*) FROM rechenuebung").fetchone()[0] == 5
    assert client.post("/rechnen/sprint/lauf", data={"a": "gibtsnicht:1"}).status_code == 400
    assert client.get("/rechnen/sprint/lauf").headers["Location"].endswith("/rechnen/sprint")  # ohne Aufgaben: zur Startseite


def test_sprint_nur_im_umfang(client, con):
    from urllib.parse import parse_qs, urlparse
    from saku.db import setze_einstellung
    for pfad, teil, beruf in [("AP2-1201", "AP2", "1201"), ("AP2-1202", "AP2", "1202"), ("AP1", "AP1", "1201")]:
        setze_einstellung(con, "teil", teil)
        setze_einstellung(con, "beruf", beruf)
        erlaubt = set(rechnen.im_umfang(pfad))
        for _ in range(8):
            adresse = client.get("/rechnen/sprint/neu").headers["Location"]
            arten = [w.split(":")[0] for w in parse_qs(urlparse(adresse).query)["a"]]
            assert len(set(arten)) == 5 and set(arten) <= erlaubt, (pfad, arten)
    start = client.get("/rechnen/sprint").get_data(as_text=True)  # die Startseite sagt dasselbe
    assert "aus allen Arten" not in start and "Arten deiner Prüfung" in start


def test_gemischt_ohne_doppelte():
    rng = random.Random(3)
    for _ in range(50):
        gezogen = []
        for _ in range(5):
            gezogen.append(rechnen.gemischt(rng, {}, ohne=gezogen))
        assert len(set(gezogen)) == 5


# --- Routine: fällige Arten, Tagesziel, Lernpfad (Runde 5) ----------------------------

def test_faellig_leitner_regeln():
    from datetime import datetime, timedelta
    jetzt = datetime(2027, 3, 10, 12, 0)
    letzte = {"subnetz": [1, 1, 1, 1, 1], "raid": [1, 1, 0, 1, 0], "ipv6": [0, 0, 1, 1, 1, 1, 1], "netzplan": [1, 1, 1, 1, 0]}
    zuletzt = {"subnetz": jetzt - timedelta(days=2), "raid": jetzt - timedelta(days=1), "ipv6": jetzt - timedelta(days=1),
               "netzplan": jetzt - timedelta(days=8)}
    arten = ["subnetz", "raid", "ipv6", "netzplan", "energie"]
    # subnetz sitzt; raid 3 von 5; ipv6 zählt nur die letzten fünf (alle richtig bis auf eins → 80 % reicht);
    # netzplan länger als sieben Tage her; energie noch nie
    assert rechnen.faellig(arten, letzte, zuletzt, jetzt) == ["raid", "netzplan", "energie"]
    assert rechnen.faellig(["subnetz"], letzte, {"subnetz": jetzt - timedelta(days=7)}, jetzt) == []


def test_umfang_je_lernpfad():
    from saku.lernen.rechnen.plan import UMFANG
    ap1, ae, si = (set(rechnen.im_umfang(p)) for p in ("AP1", "AP2-1201", "AP2-1202"))
    algorithmen = {a for a, art in rechnen.ARTEN.items() if art.gruppe == "Algorithmen"}
    assert not ap1 & algorithmen and {"subnetz", "schreibtisch", "kuendigung"} <= ap1
    assert algorithmen <= ae and "schreibtisch" in ae and "subnetz" not in ae
    assert {"subnetz", "energie", "verfuegbarkeit", "kalkulation"} <= si and not si & algorithmen and "schreibtisch" not in si
    assert all(g in rechnen.GRUPPEN for gruppen in UMFANG.values() for g in gruppen)
    # IT-Sicherheit prüfen AP1 und AP2 beider Berufe; Ports und OSI gehören zum Netzwerk (AP1, Systemintegration)
    sicherheit = {a for a, art in rechnen.ARTEN.items() if art.gruppe == "IT-Sicherheit"}
    assert len(sicherheit) == 6 and sicherheit <= ap1 & ae & si
    assert {"ports", "osi"} <= ap1 & si and not {"ports", "osi"} & ae


def test_gemischt_bevorzugt_faellige(client, con):
    ae = rechnen.im_umfang("AP2-1201")  # Demo: AP2 Anwendungsentwicklung
    con.executemany("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt) VALUES (?, 1, 1, 1, 1)",
                    [(a,) for a in ae if a != "baum" for _ in range(5)])
    con.commit()
    for _ in range(15):
        assert re.match(r"/rechnen/baum\?", client.get("/rechnen/gemischt").headers["Location"])
    con.executemany("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt) VALUES ('baum', 1, 1, 1, 1)", [()] * 5)
    con.commit()
    # nichts mehr fällig: dann aus dem ganzen Umfang, nie außerhalb (Subnetting gehört nicht zur AP2 AE)
    gezogen = {re.match(r"/rechnen/(\w+)\?", client.get("/rechnen/gemischt").headers["Location"])[1] for _ in range(40)}
    assert gezogen <= set(ae) and len(gezogen) > 3


def test_rechen_tagesziel_einstellung_und_anzeige(client, con):
    assert client.post("/einstellungen/rechnen_ziel", data={"rechnen_ziel": "3"}).status_code == 200
    assert all(client.post("/einstellungen/rechnen_ziel", data={"rechnen_ziel": w}).status_code == 400 for w in ("abc", "51", "-1", ""))
    assert 'id="rechnen_ziel"' in client.get("/einstellungen").get_data(as_text=True)
    con.execute("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt) VALUES ('raid', 1, 1, 1, 1)")
    con.commit()
    heute = client.get("/").get_data(as_text=True)
    assert 'Rechnen <span class="zahl">1 / 3</span>' in heute and heute.count('class="klein heute-rechnen"') == 1
    uebersicht = client.get("/rechnen/").get_data(as_text=True)
    faellig = len(rechnen.im_umfang("AP2-1201"))  # Demo: AP2 AE, alles noch nie (raid gehört nicht dazu) gerechnet
    assert uebersicht.count('class="rechnen-faellig"') == faellig and f"· {faellig} fällig" in uebersicht
    assert 'Heute <span class="zahl">1 / 3</span>' in uebersicht
    nav = re.search(r'<nav id="nav".*?</nav>', uebersicht, re.S)[0]
    assert "['" not in nav  # die Seitenleiste zählt weiter fällige Teilaufgaben, nicht die Rechenarten
    # 0 schaltet das Ziel aus; dann steht nur, was heute gerechnet wurde, nicht doppelt
    client.post("/einstellungen/rechnen_ziel", data={"rechnen_ziel": "0"})
    heute = client.get("/").get_data(as_text=True)
    assert 'Heute gerechnet: <span class="zahl">1 · 100 %</span>' in heute and "Rechnen <span" not in heute
    assert 'class="klein rechnen-ziel"' not in client.get("/rechnen/").get_data(as_text=True)


def test_lernpfad_zeigt_rechentraining(client, con):
    station = dict(con.execute("SELECT s.id, th.name FROM station s JOIN station_thema st ON st.station_id = s.id "
                               "JOIN thema th ON th.id = st.thema_id").fetchall())
    nach_name = {name: s_id for s_id, name in station.items()}
    html = " ".join(client.get(f"/michi/{nach_name['Projektmanagement']}").get_data(as_text=True).split())
    # die Unterthemen zählen mit: Netzplan und Wirtschaftlichkeit
    assert "Rechentraining: <strong>Netzplan</strong> · noch nicht gerechnet" in html and 'href="/rechnen/netzplan"' in html
    assert 'href="/rechnen/vergleich"' in html
    con.executemany("INSERT INTO rechenuebung (art, seed, richtig, felder_richtig, felder_gesamt) VALUES ('netzplan', 1, ?, 1, 1)",
                    [(r,) for r in (0, 0, 1, 1, 0, 1, 1)])  # die letzten fünf: 1, 1, 0, 1, 1
    con.commit()
    html = " ".join(client.get(f"/michi/{nach_name['Projektmanagement']}").get_data(as_text=True).split())
    assert '<span class="zahl">4 von 5</span> zuletzt richtig' in html
    assert "Rechentraining" not in client.get(f"/michi/{nach_name['Anforderungen']}").get_data(as_text=True)


def test_rechnen_verlinkt_die_echten_pruefungsaufgaben(client, con):
    """Gegenrichtung zu „Ähnliches rechnen“: Übersicht und geprüfte Karte nennen die Teilaufgaben zur Art und öffnen Üben mit
    genau diesen Themen. Netzplan hat in der Demo zwei (Sommer 2023), Subnetting keine."""
    netzplan = con.execute("SELECT id FROM thema WHERE name = 'Netzplan'").fetchone()[0]
    zeile = ('In deinen Prüfungen: <span class="zahl">2</span> Teilaufgaben zu Netzplan · zuletzt Sommer 2023 · '
             f'<a href="/keiko/?thema={netzplan}">üben →</a>')
    assert rechnen.themen_je_art([(netzplan, "Netzplan"), (1, "Normalisierung"), (2, "Scrum")]) == {"netzplan": [netzplan], "normalform": [1]}
    uebersicht = client.get("/rechnen/").get_data(as_text=True)
    assert zeile in uebersicht and "zu Subnetting" not in uebersicht
    # die Karte erst nach dem Prüfen, unter dem Rechenweg
    assert "In deinen Prüfungen" not in client.get("/rechnen/netzplan?seed=1").get_data(as_text=True)
    karte = client.post("/rechnen/netzplan/pruefen", data={"seed": 1, "aufgeben": "1"}, headers=HTMX).get_data(as_text=True)
    assert zeile in karte and karte.index("Rechenweg") < karte.index(zeile)
    # „üben →“ öffnet genau diese zwei Teilaufgaben
    ueben = client.get(f"/keiko/?thema={netzplan}").get_data(as_text=True)
    assert "Netzplan" in ueben and '<span class="klein zahl">0 / 2</span>' in ueben  # Fortschritt der Runde
    # nur im Umfang: in AP1 kam keine davon dran
    con.execute("UPDATE einstellung SET wert = 'AP1' WHERE schluessel = 'teil'")
    con.commit()
    assert "In deinen Prüfungen" not in client.get("/rechnen/").get_data(as_text=True)



# --- Datensicherung, Monitor, Bandbreite (Runde 7) ------------------------------------------

def test_backup_nachgerechnet():
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"]
    for seed, a in _alle("backup"):
        l, f = a.loesung, a.frage
        if a.titel == "Großvater-Vater-Sohn":
            arbeitstage, wochen, monate = (int(x) for x in re.search(r"an (\d) Arbeitstagen.*?aufbewahrt (\d) Wochen.*?aufbewahrt (\d+) Monate", f, re.S).groups())
            assert l["medien"] == (arbeitstage - 1) + wochen + monate
            continue
        gesamt = _zahl(re.search(r"([\d.]+) GB\*?\*? ?(?:Daten|\))", f)[1])
        d = int(re.search(r"mit (?:zusammen )?\*?\*?(\d+) GB", f.split("ändern sich")[1])[1])
        inkrementell = "inkrementell" in a.titel
        if a.titel.startswith("Datenmenge"):
            tag = tage.index(re.search(r"sichert der (\w+)", f)[1])
            assert l["tag"] == (d if inkrementell else tag * d)
            assert l["woche"] == gesamt + (4 * d if inkrementell else 10 * d)
        else:
            ausfall = tage.index(re.search(r"\*\*(\w+)morgen\*\*", f)[1])
            erwartet = tage[:ausfall] if inkrementell else ([tage[0], tage[ausfall - 1]] if ausfall > 1 else [tage[0]])
            assert rechnen.stimmt(a.felder[0], ", ".join(erwartet)) and l["menge"] == gesamt + (ausfall - 1) * d
    tage_feld = Feld("t", "Tage", "Montag, Donnerstag", typ="wochentage")
    assert all(rechnen.stimmt(tage_feld, t) for t in ["Mo, Do", "Montag (voll) und Donnerstag", "mo do"])
    assert not any(rechnen.stimmt(tage_feld, t) for t in ["Do, Mo", "Montag", "Mo, Di, Do", ""])


def test_backup_saetze_vollstaendig():
    for seed, a in _alle("backup"):
        if a.titel.startswith("Datenmenge"):  # „Inkrementell sichert, was sich seit der letzten Sicherung geändert hat, …“
            assert re.match(r"1\. \w+ sichert, was sich seit der letzten (Voll)?[Ss]icherung geändert hat, also", a.rechenweg), a.rechenweg
        elif a.titel == "Großvater-Vater-Sohn":
            assert "wie viele Daten stehen höchstens auf allen Bändern zusammen?" in a.frage


def test_wochentage_mit_endung_und_ohne_artikel():
    """„Montags“ und „Dienstagabend“ beginnen mit einem Wochentag und zählen; „die“ und „mit“ sind keine Abkürzungen."""
    feld = Feld("t", "Tage", "Montag, Donnerstag", typ="wochentage")
    assert all(rechnen.stimmt(feld, t) for t in ["Montags, Donnerstags", "Montag, Donnerstagabend", "Mo., Do.",
                                                 "Die Vollsicherung vom Montag und die Differenzielle vom Donnerstag",
                                                 "Montag mit Donnerstag"])
    assert not any(rechnen.stimmt(feld, t) for t in ["Montag, die Mittwochssicherung, Donnerstag", "Donnerstags, Montags"])


def test_monitor_und_bandbreite_nachgerechnet():
    import math
    for seed, a in _alle("monitor"):
        l, f = a.loesung, a.frage
        if a.titel == "Pixeldichte":
            b, h = map(_zahl, re.search(r"\*\*([\d.]+) × ([\d.]+) Pixel\*\*", f).groups())
            d = _zahl(re.search(r"\*\*([\d,]+) Zoll\*\*", f)[1])
            assert l["ppi"] == pytest.approx(math.sqrt(b * b + h * h) / d)
        elif a.titel == "Seitenverhältnis":
            b, h = map(_zahl, re.search(r"\*\*([\d.]+) × ([\d.]+)\*\*", f).groups())
            x, y = _folge(l["verhaeltnis"])
            assert x * h == y * b and math.gcd(x, y) == 1
        elif a.titel == "Breite und Höhe":
            d = _zahl(re.search(r"\*\*([\d,]+) Zoll\*\*", f)[1])
            x, y = map(int, re.search(r"\*\*(\d+):(\d+)\*\*", f).groups())
            assert l["breite"] / l["hoehe"] == pytest.approx(x / y) and math.hypot(l["breite"], l["hoehe"]) == pytest.approx(d * 2.54)
        else:
            dpi = int(re.search(r"\*\*(\d+) dpi\*\*", f)[1])
            assert l["breite"] == pytest.approx({"10 × 15 cm": 10, "13 × 18 cm": 13, "DIN A4": 21, "DIN A5": 14.8, "20 × 30 cm": 20}[
                re.search(r"Format \*\*(.+?)\*\*", f)[1]] / 2.54 * dpi, abs=0.5)
    for seed, a in _alle("bandbreite"):
        l, f = a.loesung, a.frage
        if a.titel == "Arbeitsspeicher":
            mt = int(re.search(r"-(\d{4})\*\*", f)[1]) if "vom Typ" in f else 2 * _zahl(re.search(r"\*\*([\d.]+) MHz", f)[1])
            kanaele = int(re.search(r"\*\*(\d) Kan", f)[1])
            assert (l["effektiv"], l["kanal"], l["gesamt"]) == (mt, mt * 8, pytest.approx(mt * 8 * kanaele / 1000))
        elif a.titel == "PCIe-Lanes":
            gen, lanes = map(int, re.search(r"PCIe-(\d)\.0-x(\d+)", f).groups())
            je_lane = {2: 0.5, 3: 0.9846, 4: 1.9692, 5: 3.9385}[gen]  # GB/s je Richtung laut PCI-SIG
            assert l["lane"] == pytest.approx(je_lane, abs=0.0005) and l["gesamt"] == pytest.approx(je_lane * lanes, abs=0.01)
        else:
            gb = int(re.search(r"\*\*(\d+) GB\*\*", f)[1])
            assert l["sata"] == pytest.approx(gb * 1000 / 600) and l["faktor"] > 5


def test_seitenverhaeltnis_verlangt_das_exakte_und_erklaert_gerundete_namen():
    """1366 × 768 ist exakt 683:384, im Handel heißt es 16:9 (wie 21:9 für 3440 × 1440, exakt 43:18). Die Frage darf deshalb
    nicht „die übliche Schreibweise“ anbieten, die die Kontrolle dann ablehnt; der Rechenweg nennt den gerundeten Namen."""
    gesehen = set()
    for seed in range(1500):
        a = rechnen.erzeugen("monitor", seed)
        if a.titel != "Seitenverhältnis":
            continue
        assert "exakte" in a.frage and "üblichen Schreibweise" not in a.frage
        if gerundet := {"683:384": "16:9", "43:18": "21:9"}.get(a.loesung["verhaeltnis"]):
            gesehen.add(gerundet)
            assert f"als {gerundet} bezeichnet, das ist aber gerundet" in a.rechenweg and not rechnen.stimmt(a.felder[0], gerundet)
    assert gesehen == {"16:9", "21:9"}


# --- VLSM, Routing, EUI-64 (Runde 8) -------------------------------------------------------

def test_vlsm_wie_ipaddress():
    for seed, a in _alle("vlsm"):
        basis = ipaddress.ip_network(re.search(r"`([\d.]+/\d+)`", a.frage)[1])
        bedarf = dict(re.findall(r"^- (.+?): (\d+) Hosts$", a.frage, re.M))
        netze = {}
        for zeile in a.tabelle[1:]:
            name, netz, praefix, bc = zeile[0], *(f.loesung for f in zeile[1:])
            netze[name] = n = ipaddress.ip_network(f"{netz}/{praefix}")
            assert str(n.broadcast_address) == bc and n.subnet_of(basis)
            hosts = int(bedarf[name])
            assert n.num_addresses - 2 >= hosts > n.num_addresses // 2 - 2  # so klein wie möglich
        # größte zuerst und lückenlos ab dem Netzanfang
        sortiert = sorted(netze.values(), key=lambda n: -n.num_addresses)
        assert sortiert[0].network_address == basis.network_address
        assert all(int(b.network_address) == int(a_.broadcast_address) + 1 for a_, b in zip(sortiert, sortiert[1:]))


def test_routing_longest_prefix_wie_ipaddress():
    for seed, a in _alle("routing"):
        eintraege = [(ipaddress.ip_network("0.0.0.0/0" if z.startswith("0.0.0.0") else z), h)
                     for z, h in re.findall(r"^\| ([\d./]+)(?: \(Default\))? \| (R\d) \|$", a.frage, re.M)]
        assert len(eintraege) == 5 and any(n.prefixlen == 0 for n, _ in eintraege)
        for f in a.felder:
            ziel = ipaddress.ip_address(re.search(r"für ([\d.]+)", f.label)[1])
            p, h, n = max((n.prefixlen, h, n) for n, h in eintraege if ziel in n)
            assert f.loesung == (h if f.label.startswith("Next Hop") else ("0.0.0.0/0 (Default)" if p == 0 else str(n)))
        praefixe = sorted({max(p for p, _ in [(n.prefixlen, h) for n, h in eintraege if ipaddress.ip_address(re.search(r"für ([\d.]+)", f.label)[1]) in n])
                           for f in a.felder})
        assert praefixe[0] == 0 and len(praefixe) == 3  # Default, mittlerer und längster Präfix kommen je einmal dran


def test_eui64_unabhaengig_ueber_zeichenketten():
    for seed, a in _alle("eui64"):
        if a.titel == "EUI-64 rückwärts: MAC":  # vorwärts aus der gefundenen MAC muss wieder die Adresse entstehen
            mac = a.loesung["mac"].split(":")
            mac[0] = f"{int(mac[0], 16) ^ 0b10:02x}"
            iid = "".join(mac[:3] + ["ff", "fe"] + mac[3:]).lower()
            link = re.search(r"`(fe80:[0-9a-f:]+)`", a.frage)[1]
            assert ipaddress.ip_address(link) == ipaddress.ip_address("fe80::" + ":".join(iid[i:i + 4] for i in range(0, 16, 4)))
            continue
        mac = re.search(r"MAC-Adresse \*\*([0-9A-F:-]+)\*\*", a.frage)[1].replace("-", ":").split(":")
        mac[0] = f"{int(mac[0], 16) ^ 0b10:02x}"  # U/L-Bit umdrehen
        iid = "".join(mac[:3] + ["ff", "fe"] + mac[3:]).lower()
        iid = ":".join(iid[i:i + 4] for i in range(0, 16, 4))
        praefix = ipaddress.ip_network(re.search(r"Präfix `([0-9a-f:]+/64)`", a.frage)[1])
        assert ipaddress.ip_address(f"::{iid}") == ipaddress.ip_address(f"::{a.loesung['iid']}")
        assert a.loesung["global"] == ipaddress.ip_address(f"{praefix.network_address.exploded[:19]}:{iid}").compressed
        assert a.loesung["link"] == ipaddress.ip_address(f"fe80::{iid}").compressed
    feld = Feld("g", "Global", "2001:db8::21a:2bff:fe3c:4d5e", typ="ipv6")
    assert all(rechnen.stimmt(feld, t) for t in ["2001:db8::21a:2bff:fe3c:4d5e", "2001:0DB8:0:0:021A:2BFF:FE3C:4D5E"])
    assert not rechnen.stimmt(feld, "2001:db8::21a:2bff:fe3c:4d5f") and not rechnen.stimmt(feld, "kein")
    assert rechnen.stimmt(Feld("i", "Interface-ID", "21a:2bff:fe3c:4d5e", typ="ipv6"), "021A:2BFF:FE3C:4D5E")
    # IPv6-Felder (EUI-64) so breit wie die IPv6-Textfelder (Kürzen, Ausschreiben): eine globale Adresse hat bis zu 39 Zeichen
    css = (Path(__file__).parents[1] / "saku" / "web" / "static" / "css" / "bereiche" / "rechnen.css").read_text(encoding="utf-8")
    assert re.search(r"^:is\(\.rechnen-feld--text, \.rechnen-feld--ipv6\) \.input \{ width: 24rem; \}", css, re.M)
    # wie bei IPv4 („10.0.0.0/24“) zählt die Adresse, eine angehängte Präfixlänge stört nicht
    assert rechnen.stimmt(feld, "2001:db8::21a:2bff:fe3c:4d5e/64") and rechnen.stimmt(Feld("n", "Netz", "10.0.0.0", typ="ip"), "10.0.0.0/24")


# --- IT-Sicherheit, Ports und OSI ------------------------------------------------------

def _mit(a, **eingaben) -> dict[str, bool]:
    """Die Musterlösung, nur die genannten Felder anders eingegeben: welche Felder gelten als richtig?"""
    return rechnen.pruefen(a, {f.name: f.anzeige for f in a.felder} | eingaben)


def _zeichenvorrat(text: str) -> int:
    n = sum(z for klasse, z in (("Kleinbuchstaben", 26), ("Großbuchstaben", 26), ("Ziffern", 10)) if klasse in text)
    return n + (int(m[1]) if (m := re.search(r"(\d+) erlaubten Sonderzeichen", text)) else 0)


def test_passwortstaerke_nachgerechnet():
    import math
    raten = {"1.000": 1e3, "1 Million": 1e6, "1 Milliarde": 1e9, "10 Milliarden": 1e10, "100 Milliarden": 1e11}
    einheiten = {"Jahren": 365 * 24 * 3600, "Tagen": 24 * 3600, "Stunden": 3600, "Minuten": 60}
    for seed, a in _alle("passwort"):
        l = a.loesung
        if a.titel == "Brute-Force-Dauer":
            n = _zeichenvorrat(re.search(r"erlaubt sind (.*?)\.", a.frage)[1])
            laenge = int(re.search(r"genau \*\*(\d+) Zeichen", a.frage)[1])
            rate = raten[re.search(r"\*\*(1\.000|1 Million|1 Milliarde|10 Milliarden|100 Milliarden)", a.frage)[1]]
            einheit = einheiten[re.search(r"Angriffs in (\w+) im", a.frage)[1]]
            assert l["vorrat"] == n and l["kombinationen"] == n ** laenge
            assert l["max"] == pytest.approx(n ** laenge / rate / einheit) and l["mittel"] == pytest.approx(l["max"] / 2)
            assert rechnen.stimmt(a.felder[1], f"{n}^{laenge}")  # als Potenz getippt
            mantisse, exponent = f"{n ** laenge:.2e}".split("e")  # gerundet wie im Rechenweg: 2,18 · 10^14
            assert rechnen.stimmt(a.felder[1], f"{mantisse.replace('.', ',')} · 10^{int(exponent)}", a.toleranz)
            falsch = _mit(a, kombinationen=str(n * laenge), mittel=de(l["max"]), vorrat=str(n - 10))
            assert not (falsch["kombinationen"] or falsch["mittel"] or falsch["vorrat"]) and falsch["max"]
        elif a.titel == "Entropie und Mindestlänge":
            n = _zeichenvorrat(re.search(r"Passwörter aus (.*?)\.", a.frage)[1])
            laenge, ziel = int(re.search(r"\*\*(\d+) Zeichen\*\*", a.frage)[1]), int(re.search(r"\*\*(\d+) Bit\*\*", a.frage)[1])
            mindest = next(m for m in range(1, 200) if m * math.log(n, 2) >= ziel)
            assert (l["vorrat"], l["mindest"]) == (n, mindest) and l["bisher"] == pytest.approx(laenge * math.log(n) / math.log(2))
            assert not _mit(a, mindest=str(mindest - 1))["mindest"]  # abgerundet reicht nicht
        else:
            (la, ta), (lb, tb) = re.findall(r"\*\*Regel [AB]:\*\* (\d+) Zeichen aus (.*)", a.frage)
            ea, eb = int(la) * math.log2(_zeichenvorrat(ta)), int(lb) * math.log2(_zeichenvorrat(tb))
            assert (l["a"], l["b"]) == (pytest.approx(ea), pytest.approx(eb)) and l["staerker"] == ("Regel A" if ea > eb else "Regel B")
            assert not _mit(a, staerker="Regel B" if ea > eb else "Regel A")["staerker"]
    assert {a.loesung["staerker"] for _, a in _alle("passwort", "Passwortregeln vergleichen")} == {"Regel A", "Regel B"}


def test_schluesselanzahl_und_welcher_schluessel():
    zehn = next(a for s in range(5000) if (a := rechnen.erzeugen("schluessel", s)).titel == "Schlüssel zählen" and "**10 Personen**" in a.frage)
    assert zehn.loesung == {"symmetrisch": 45, "asymmetrisch": 20}
    erwartet = {"Nachricht verschlüsseln": "Öffentlicher Schlüssel des Empfängers", "Nachricht entschlüsseln": "Privater Schlüssel des Empfängers",
                "Sitzungsschlüssel verschlüsseln": "Öffentlicher Schlüssel des Empfängers",
                "Sitzungsschlüssel entschlüsseln": "Privater Schlüssel des Empfängers",
                "Nachrichtentext verschlüsseln": "Symmetrischer Sitzungsschlüssel", "Nachrichtentext entschlüsseln": "Symmetrischer Sitzungsschlüssel",
                "Nachricht signieren (ihren Hashwert)": "Privater Schlüssel des Absenders", "Signatur prüfen": "Öffentlicher Schlüssel des Absenders"}
    for seed, a in _alle("schluessel"):
        l = a.loesung
        if a.titel == "Schlüssel zählen":
            n = int(re.search(r"\*\*(\d+) Personen", a.frage)[1])
            assert l == {"symmetrisch": len(list(itertools.combinations(range(n), 2))), "asymmetrisch": 2 * n}
            assert not _mit(a, symmetrisch=str(n * (n - 1)))["symmetrisch"]  # Paare doppelt gezählt
        elif a.titel == "Neue Teilnehmer":
            n = int(re.search(r"ihre \*\*(\d+) Standorte", a.frage)[1])
            k = int(m[1]) if (m := re.search(r"\*\*(\d+) neue Standorte", a.frage)) else 1
            vorher, nachher = (len(list(itertools.combinations(range(x), 2))) for x in (n, n + k))
            assert l == {"dazu": nachher - vorher, "gesamt": nachher, "asymmetrisch": 2 * k}
            falsch = _mit(a, dazu=str(k * (k - 1) // 2), asymmetrisch=str(2 * (n + k)))  # nur die Neuen untereinander; alle neu
            assert not falsch["dazu"] and not falsch["asymmetrisch"] and falsch["gesamt"]
        else:
            assert all(f.loesung == erwartet[f.label] and f.loesung in f.optionen for f in a.felder)
            assert ("Symmetrischer Sitzungsschlüssel" in a.felder[0].optionen) == ("hybrid" in a.frage)
            andere = [f.name for f in a.felder if f.loesung != "Privater Schlüssel des Absenders"]
            assert not any(_mit(a, **dict.fromkeys(andere, "Privater Schlüssel des Absenders"))[x] for x in andere)


STUFE = {"normal": 0, "hoch": 1, "sehr hoch": 2}


def test_schutzbedarf_maximumprinzip_ueber_die_kette():
    hinweise = set()
    for seed, a in _alle("schutzbedarf", "Schutzbedarf vererben"):
        zeilen = re.findall(r"^\| ([^|]+) \| (normal|hoch|sehr hoch) \| (normal|hoch|sehr hoch) \| (normal|hoch|sehr hoch) \| ([^|]+) \|$",
                            a.frage, re.M)
        auf = {name: re.findall(r"S\d", server) for name, *_, server in zeilen}
        werte = {name: [STUFE[w] for w in (v, i, av)] for name, v, i, av, _ in zeilen}
        raum = set(re.search(r"Die Server (S\d) und (S\d) stehen im Serverraum", a.frage).groups())
        ziel = re.search(r"des Servers \*\*(S\d)\*\*", a.frage)[1]
        for g in range(3):
            server = max(werte[x][g] for x in werte if ziel in auf[x])
            im_raum = max(werte[x][g] for x in werte if raum & set(auf[x]))
            assert (STUFE[a.loesung[f"s{g}"]], STUFE[a.loesung[f"r{g}"]]) == (server, im_raum)
        # typisch falsch: der Raum wie der Server (Maximum nur über ein System)
        assert not all(_mit(a, **{f"r{g}": a.loesung[f"s{g}"] for g in range(3)}).values())
        assert "(Cluster)" in a.frage or "Verteilungseffekt" not in a.rechenweg
        hinweise |= {h for h in ("Kumulationseffekt", "Verteilungseffekt") if h in a.rechenweg}
    assert hinweise == {"Kumulationseffekt", "Verteilungseffekt"}
    woerter = {"Vertraulichkeit": ("öffnen", "Verteiler", "liest", "liegen", "Konkurrent"),
               "Integrität": ("ändert", "doppelt", "verfälscht", "beschädigt"),
               "Verfügbarkeit": ("nicht erreichbar", "nicht arbeiten", "fällt", "steht", "ausgefallen")}
    for seed, a in _alle("schutzbedarf", "Grundwerte erkennen"):
        vorfaelle = re.findall(r"^\d\. (.*)$", a.frage, re.M)
        for f, text in zip(a.felder, vorfaelle):
            assert [g for g, w in woerter.items() if any(x in text for x in w)] == [f.loesung], text


def _haeufigkeit(text: str) -> float:
    if m := re.fullmatch(r"einmal in (\d+) Jahren", text):
        return 1 / int(m[1])
    if m := re.fullmatch(r"mit (\d+) % Wahrscheinlichkeit im Jahr", text):
        return int(m[1]) / 100
    return {"einmal im Jahr": 1, "zweimal im Jahr": 2, "viermal im Jahr": 4}[text]


def test_risikobewertung_nachgerechnet():
    for seed, a in _alle("risiko"):
        l = a.loesung
        if a.titel == "Risiko pro Jahr":
            zeilen = re.findall(r"^\| ([A-D]) \| [^|]+ \| ([^|]+) \| ([\d.,]+) € \|$", a.frage, re.M)
            risiko = {x: _haeufigkeit(t) * _zahl(s) for x, t, s in zeilen}
            assert all(l[x] == pytest.approx(r) for x, r in risiko.items())
            rang = sorted(risiko, key=risiko.get, reverse=True)
            assert rechnen.stimmt(a.felder[-1], "".join(rang)) and not rechnen.stimmt(a.felder[-1], "".join(reversed(rang)))
        elif a.titel == "Lohnt sich die Maßnahme?":
            h1 = _haeufigkeit(re.search(r"rechnet man (.*?) mit einem", a.frage)[1])
            schaden = _zahl(re.search(r"Schaden je Fall beträgt \*\*([\d.,]+) €", a.frage)[1])
            einmalig, jahre = re.search(r"einmalig \*\*([\d.,]+) €\*\* bei einer Nutzungsdauer von \*\*(\d) Jahren", a.frage).groups()
            laufend = _zahl(m[1]) if (m := re.search(r"laufend \*\*([\d.,]+) € pro Jahr", a.frage)) else 0
            h2 = _haeufigkeit(m[1]) if (m := re.search(r"Häufigkeit auf \*\*(.*?)\*\*", a.frage)) else h1
            s2 = _zahl(m[1]) if (m := re.search(r"Schaden je Fall auf \*\*([\d.,]+) €", a.frage)) else schaden
            kosten = _zahl(einmalig) / int(jahre) + laufend
            nutzen = h1 * schaden - h2 * s2 - kosten
            assert (l["vorher"], l["nachher"], l["kosten"], l["nutzen"]) == pytest.approx((h1 * schaden, h2 * s2, kosten, nutzen))
            assert l["lohnt"] == ("Ja" if nutzen > 0 else "Nein") and abs(nutzen) >= 100
            falsch = _mit(a, kosten=de(_zahl(einmalig) + laufend), lohnt="Nein" if nutzen > 0 else "Ja")
            assert not falsch["kosten"] and not falsch["lohnt"]  # einmalige Kosten nicht verteilt
        else:
            niedrig, mittel = map(int, re.search(r"1 bis (\d+): niedrig, \d+ bis (\d+): mittel", a.frage).groups())
            w = {"selten": 1, "möglich": 2, "wahrscheinlich": 3, "häufig": 4}
            s = {"gering": 1, "spürbar": 2, "erheblich": 3, "existenzbedrohend": 4}
            for i, (_, ws, ss) in enumerate(re.findall(r"^\| ([^|]+) \| (\w+) \| (\w+) \|$", a.frage, re.M)[1:]):
                wert = w[ws] * s[ss]
                assert l[f"w{i}"] == wert and l[f"k{i}"] == ("niedrig" if wert <= niedrig else "mittel" if wert <= mittel else "hoch")
                assert not _mit(a, **{f"w{i}": str(w[ws] + s[ss])}).get(f"w{i}") or w[ws] * s[ss] == w[ws] + s[ss]


def _ean_gueltig(ziffern: str) -> bool:
    z = [int(c) for c in ziffern]
    return (sum(z[0::2]) + 3 * sum(z[1::2])) % 10 == 0


def test_pruefziffern_paritaet_xor_gegenproben():
    from saku.lernen.rechnen.sicherheit import pruefziffer
    # selbst durchgerechnet: 4·1 + 0·3 + 1·1 + 2·3 + … + 0·3 = 89 → 1; 9·1 + 7·3 + 8·1 + 3·3 + … + 8·3 = 123 → 7
    assert pruefziffer([4, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0]) == 1 and _ean_gueltig("4012345678901")
    assert pruefziffer([9, 7, 8, 3, 1, 2, 3, 4, 5, 6, 7, 8]) == 7 and not _ean_gueltig("9783123456788")
    for seed, a in _alle("pruefziffer"):
        l = a.loesung
        if a.titel.endswith("-Prüfziffer"):
            zwoelf = re.search(r"`(\d{12})`", a.frage)[1]
            assert _ean_gueltig(zwoelf + str(l["pz"])) and not any(_ean_gueltig(zwoelf + str(d)) for d in range(10) if d != l["pz"])
        elif a.titel.endswith(" prüfen"):
            assert l["gueltig"] == ("Ja" if _ean_gueltig(re.search(r"`(\d{13})`", a.frage)[1]) else "Nein")
            assert not _mit(a, gueltig="Nein" if l["gueltig"] == "Ja" else "Ja")["gueltig"]
        elif a.titel == "Paritätsbit":
            wort, empfangen = re.findall(r"`([01]+)`", a.frage)
            assert (l["gerade"], l["ungerade"]) == (wort.count("1") % 2, 1 - wort.count("1") % 2)
            assert l["fehler"] == ("Ja" if empfangen.count("1") % 2 else "Nein")
            assert not _mit(a, gerade=str(l["ungerade"]))["gerade"]
        else:
            eingang, schluessel = (int(b.replace(" ", ""), 2) for b in re.findall(r"`([01 ]{9})`", a.frage))
            assert int(l["binaer"], 2) == int(l["hex"], 16) == eingang ^ schluessel
            if eingang | schluessel != eingang ^ schluessel:  # mit ODER statt XOR gerechnet
                assert not _mit(a, binaer=f"{eingang | schluessel:08b}")["binaer"]


def test_dsgvo_bussgeld_und_meldefrist():
    from datetime import datetime, timedelta
    monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    for seed, a in _alle("dsgvo"):
        l = a.loesung
        if a.titel == "Bußgeldrahmen":
            artikel = int(re.search(r"\(Art\. (\d+) DSGVO\)", a.frage)[1])
            absatz = 4 if artikel in (8, 11, 42, 43) or 25 <= artikel <= 39 else 5
            assert absatz == 5 or artikel not in (5, 6, 7, 9) and not 12 <= artikel <= 22 and not 44 <= artikel <= 49
            wert, groesse = re.search(r"betrug \*\*([\d.,]+) (Mio|Mrd)\. €", a.frage).groups()
            umsatz = _zahl(wert) * (1000 if groesse == "Mrd" else 1)
            fest, prozent = (10, 2) if absatz == 4 else (20, 4)
            assert l["absatz"] == f"Art. 83 Abs. {absatz}" and l["anteil"] == pytest.approx(umsatz * prozent / 100)
            assert l["hoechst"] == pytest.approx(max(fest, umsatz * prozent / 100))
            assert not _mit(a, hoechst=de(min(fest, umsatz * prozent / 100)))["hoechst"]  # der niedrigere Betrag
        else:
            def zeitpunkt(text):
                m = re.search(rf"{text} \**\w+, (\d+)\. (\w+) (\d+) um (\d\d):(\d\d) Uhr", a.frage)
                return datetime(int(m[3]), monate.index(m[2]) + 1, int(m[1]), int(m[4]), int(m[5]))
            kenntnis, vorfall = zeitpunkt("erst am"), zeitpunkt("und zwar am")
            frist = kenntnis + timedelta(hours=72)
            assert frist.hour == kenntnis.hour and vorfall < kenntnis  # keine Zeitumstellung dazwischen
            assert (l["datum"], l["uhrzeit"], l["tag"]) == (frist.strftime("%d.%m.%Y"), frist.strftime("%H:%M"), tage[frist.weekday()])
            ab_vorfall = vorfall + timedelta(hours=72)  # typisch falsch: ab dem Vorfall gerechnet
            assert not all(_mit(a, datum=ab_vorfall.strftime("%d.%m.%Y"), uhrzeit=ab_vorfall.strftime("%H:%M")).values())
            assert rechnen.stimmt(a.felder[1], f"{frist.hour}.{frist:%M} Uhr") and rechnen.stimmt(a.felder[2], tage[frist.weekday()][:2])


# unabhängig von saku: IANA-Standardports, die mit UDP und die von Anfang an verschlüsselten
IANA = {20: "FTP", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 67: "DHCP", 68: "DHCP", 69: "TFTP", 80: "HTTP", 110: "POP3",
        123: "NTP", 143: "IMAP", 161: "SNMP", 389: "LDAP", 443: "HTTPS", 445: "SMB", 465: "SMTPS", 514: "Syslog", 587: "SMTP", 636: "LDAPS",
        993: "IMAPS", 995: "POP3S", 3389: "RDP"}
UDP_PORTS, TLS_PORTS = {67, 68, 69, 123, 161, 514}, {22, 443, 465, 636, 993, 995}


def test_ports_wie_iana():
    besondere = {"FTP-Daten (aktiver Modus)": 20, "FTP-Steuerverbindung": 21, "DHCP-Server": 67, "DHCP-Client": 68,
                 "SMTP zwischen Mailservern": 25, "SMTP-Submission (STARTTLS)": 587, "SMTPS (implizites TLS)": 465}
    for seed, a in _alle("ports"):
        for f in a.felder:
            if a.titel == "Port → Protokoll":
                port = int(f.label.removeprefix("Port "))
                assert f.loesung == IANA[port] and rechnen.stimmt(f, f" {IANA[port].lower()} ")  # Groß- und Kleinschreibung egal
                assert not rechnen.stimmt(f, "HTTP" if port != 80 else "HTTPS")
            elif a.titel == "Protokoll → Port":
                assert f.loesung == besondere[f.label] if f.label in besondere else f.label.split(" ")[0] == IANA[f.loesung]
                assert not rechnen.stimmt(f, str(f.loesung + 1))
            else:
                name, frage = f.label.split(": ")
                port = besondere.get(name) or next(p for p, n in IANA.items() if n == name.split(" ")[0])
                assert {"Port": port, "TCP oder UDP?": "UDP" if port in UDP_PORTS else "TCP",
                        "verschlüsselt?": "Ja" if port in TLS_PORTS else "Nein"}[frage] == f.loesung
                # nicht eindeutig, also nie gefragt: DNS und HTTPS auch über die andere Transportart, SNMP und SMB je nach Version
                assert not (frage == "TCP oder UDP?" and port in (53, 443)) and not (frage == "verschlüsselt?" and port in (161, 445))
    feld = next(f for _, a in _alle("ports", "Port → Protokoll") for f in a.felder if f.label == "Port 22")
    assert all(rechnen.stimmt(feld, t) for t in ["SSH", "ssh", "SFTP", "scp"]) and not rechnen.stimmt(feld, "Telnet")


def test_osi_schichten():
    schicht = {"Hub": 1, "Repeater": 1, "Twisted-Pair-Kabel": 1, "Glasfaserkabel": 1, "Bit": 1, "Switch": 2, "Bridge": 2, "MAC-Adresse": 2,
               "Frame (Rahmen)": 2, "PPP": 2, "Router": 3, "IP": 3, "ICMP": 3, "IP-Adresse": 3, "Paket": 3, "TCP": 4, "UDP": 4,
               "Portnummer": 4, "Segment": 4, "HTTP": 7, "DNS": 7, "SMTP": 7, "FTP": 7, "DHCP": 7}
    namen = {1: "Bitübertragungsschicht", 2: "Sicherungsschicht", 3: "Vermittlungsschicht", 4: "Transportschicht", 7: "Anwendungsschicht"}
    tcp_ip = {1: "Netzzugangsschicht", 2: "Netzzugangsschicht", 3: "Internetschicht", 4: "Transportschicht", 7: "Anwendungsschicht"}
    for seed, a in _alle("osi"):
        for f in a.felder:
            if a.titel == "OSI-Schicht zuordnen":
                assert f.loesung == schicht[f.label] and rechnen.stimmt(f, f"Schicht {schicht[f.label]}")
                assert not rechnen.stimmt(f, str(schicht[f.label] % 7 + 1))
            else:
                begriff, art = f.label.split(": ")
                assert f.loesung == (namen if art == "OSI-Schicht" else tcp_ip)[schicht[begriff]] and f.loesung in f.optionen


def test_sicherheit_auf_der_seite(client):
    html = client.get("/rechnen/").get_data(as_text=True)
    assert "IT-Sicherheit" in html and 'href="/rechnen/dsgvo"' in html and 'href="/rechnen/ports"' in html
    assert all(f'id="{art}"' in client.get("/rechnen/formeln").get_data(as_text=True) for art in ("passwort", "schutzbedarf", "osi"))
    from saku.web.routen.suche import befehle
    assert befehle("passwort")[0][:2] == ("calculator", "Rechnen: Passwortstärke")
    seed, a = next(x for x in _alle("ports", "Port → Protokoll"))
    karte = client.get(f"/rechnen/ports?seed={seed}").get_data(as_text=True)
    assert all(f'name="feld-{f.name}"' in karte for f in a.felder)
    klein = {f"feld-{f.name}": f.loesung.lower() for f in a.felder}  # tolerant: „https“ wie „HTTPS“
    assert "Richtig." in client.post("/rechnen/ports/pruefen", data={"seed": seed} | klein, headers=HTMX).get_data(as_text=True)
    seed, a = next(x for x in _alle("schutzbedarf", "Schutzbedarf vererben"))
    karte = client.get(f"/rechnen/schutzbedarf?seed={seed}").get_data(as_text=True)
    assert karte.count('<select class="select"') == 6 and ">sehr hoch</option>" in karte
    weg = client.post("/rechnen/schutzbedarf/pruefen", data={"seed": seed, "aufgeben": "1"}, headers=HTMX).get_data(as_text=True)
    assert "Hier ist der Rechenweg." in weg and "Maximumprinzip" in weg and "Formeln: Schutzbedarf" in weg


# --- Datenbanken: SQL in der Sandbox, ER-Modell, Normalisierung (Runde 8) -------------

SQL_ARTEN = ("select", "join", "aendern")

# typische Fehler: der erste passende wird gemacht; jeder muss laufen und als falsch erkannt werden
TYPISCH_FALSCH = [
    (r"LEFT JOIN", "JOIN"),
    (r"IS NOT NULL", "IS NULL"),
    (r" IS NULL", " = NULL"),
    (r"DISTINCT ", ""),
    (r"LIKE '%?([^'%]+)%'", r"= '\1'"),
    (r"IN \('([^']*)', '[^']*'\)", r"= '\1'"),
    (r"(\S+) BETWEEN (\S+) AND (\S+);", r"\1 > \2 AND \1 < \3;"),
    (r"AVG\(", "MIN("), (r"MAX\(", "MIN("), (r"MIN\(", "MAX("), (r"SUM\(", "MAX("),
    (r">=", ">"), (r"<=", "<"), (r" > ", " >= "), (r" < ", " <= "),
    (r" \* [\d.]+ AS", " AS"),
    (r"NULL\);", "'NULL');"),
    (r",\n    FOREIGN KEY [^\n]*(?=\n\);)", ""),  # der letzte Fremdschlüssel fehlt
    (r"\nWHERE .*;", ";"),
    (r"ORDER BY (\S+?)( DESC)?([,;])", lambda m: f"ORDER BY {m[1]}{'' if m[2] else ' DESC'}{m[3]}"),
]


def _typisch_falsch(loesung: str) -> str:
    for muster, ersatz in TYPISCH_FALSCH:
        if re.search(muster, loesung):
            return re.sub(muster, ersatz, loesung, count=1)
    raise AssertionError(f"kein typischer Fehler für {loesung}")


@pytest.mark.parametrize("art", SQL_ARTEN)
def test_sql_musterloesung_laeuft_und_typische_fehler_fallen_auf(art):
    from saku.lernen import sql
    for seed, a in _alle(art):
        (feld,) = a.felder
        assert feld.typ == "sql" and a.sandbox and "Tabellen ansehen" in a.frage and "```sql" in a.rechenweg
        sql.testen(*a.sandbox, {seed: feld.loesung})  # läuft und liefert Zeilen bzw. ändert etwas
        assert rechnen.sql_vergleich(a, feld.loesung)["ergebnis"] == 3
        falsch = rechnen.sql_vergleich(a, _typisch_falsch(feld.loesung))
        assert "fehler" not in falsch and falsch["ergebnis"] < 3 and falsch["hinweise"], (seed, a.titel, feld.loesung)
        assert not rechnen.pruefen(a, {"sql": "SELECT 1"})["sql"] and not rechnen.pruefen(a, {"sql": "SELEKT"})["sql"]


def test_sql_erklaerung_schreibt_nur_den_satzanfang_gross():
    weg = next(a.rechenweg for _, a in _alle("aendern", "DELETE") if "Karten bereits abgeholt" in a.frage)
    assert "Deren Karten bereits abgeholt sind:" in weg  # str.capitalize machte daraus „Deren karten …“


def test_sql_daten_lassen_typische_fehler_auffallen():
    from saku.lernen.rechnen.datenbanken import SZENARIEN
    for s in SZENARIEN:
        wer, was, vorgang = s.tabellen
        assert all(6 <= len(t.zeilen) <= 12 for t in s.tabellen)
        assert len(set(wer.werte(1))) == len(wer.zeilen)  # Namen eindeutig: GROUP BY Name ist so gut wie GROUP BY Schlüssel
        assert set(vorgang.werte(1)) <= set(wer.werte(0)) and set(vorgang.werte(2)) <= set(was.werte(0))
        assert len(set(wer.werte(0)) - set(vorgang.werte(1))) >= 2 and set(was.werte(0)) - set(vorgang.werte(2))  # ohne Partner
        assert None in wer.werte(3) and None in vorgang.werte(5)  # NULL-Werte
        preise, anzahl = was.werte(3), [vorgang.werte(1).count(k) for k in wer.werte(0)]
        assert len(set(preise)) < len(preise) and any(anzahl.count(n) > 1 for n in anzahl if n)  # Gleichstand
        assert all(sum(n.startswith(a) for n in wer.werte(1)) >= 3 for a in s.w["anfaenge"])
        treffer = [sum(w in t and w != t for t in was.werte(1)) for w in s.w["teilwoerter"]]  # LIKE '%…%' findet mehr als =
        assert min(treffer) >= 1 and max(treffer) >= 2


def test_pruefen_fuehrt_sql_und_pseudocode_nur_einmal_aus(client, monkeypatch):
    from saku.lernen import sql
    from saku.lernen.rechnen import pseudocode
    aufrufe = []
    for modul, name in ((sql, "pruefen"), (pseudocode, "vergleich")):
        echt = getattr(modul, name)
        monkeypatch.setattr(modul, name, lambda *x, echt=echt: aufrufe.append(1) or echt(*x))
    for art in ("join", "algorithmus"):
        seed, a = next(_alle(art))
        aufrufe.clear()
        html = client.post(f"/rechnen/{art}/pruefen", data={"seed": seed, f"feld-{a.felder[0].name}": a.felder[0].loesung},
                           headers={"HX-Request": "true"}).get_data(as_text=True)
        assert "Richtig." in html and len(aufrufe) == 1, art  # nicht noch einmal für rechnen.pruefen


def test_create_table_prueft_schluessel_nicht_die_datentypen():
    from saku.lernen import sql
    seed, a = next((seed, a) for seed, a in _alle("aendern") if a.titel == "CREATE TABLE" and "FOREIGN KEY" in a.felder[0].loesung
                   and " NOT NULL" in a.felder[0].loesung)
    loesung = a.felder[0].loesung
    andere_typen = loesung.replace("INTEGER", "INT").replace("TEXT", "VARCHAR(50)").replace("REAL", "DECIMAL(8,2)")
    assert rechnen.sql_vergleich(a, andere_typen)["ergebnis"] == 3
    ohne_fk = rechnen.sql_vergleich(a, _typisch_falsch(loesung))
    assert ohne_fk["ergebnis"] == 2 and any("Fremdschlüssel auf" in h and "fehlt" in h for h in ohne_fk["hinweise"])
    ohne_pflicht = rechnen.sql_vergleich(a, loesung.replace(" NOT NULL", "", 1))
    assert ohne_pflicht["ergebnis"] == 2 and any("NOT NULL fehlt" in h for h in ohne_pflicht["hinweise"])
    assert "Primärschlüssel fehlt" in " ".join(rechnen.sql_vergleich(a, re.sub(r" PRIMARY KEY|,\n    PRIMARY KEY \([^)]*\)", "", loesung))["hinweise"])
    assert rechnen.sql_vergleich(a, "PRAGMA foreign_keys = ON")["fehler"].startswith("Nicht erlaubt")  # die Sandbox bleibt dicht
    # temporäre Tabellen (im Vergleich unsichtbar) verdecken weder die Schema-Abfragen (sonst Fehler 500) noch die eigene Tabelle
    verdeckt = "\nCREATE TEMP TABLE pragma_table_info (x);\nCREATE TEMP TABLE pragma_foreign_key_list (x);"
    assert rechnen.sql_vergleich(a, loesung + verdeckt)["ergebnis"] == 3
    ohne_schluessel = re.sub(r"\s+(PRIMARY KEY|NOT NULL)\b|,\n    (PRIMARY|FOREIGN) KEY [^\n]*", "", loesung)
    assert rechnen.sql_vergleich(a, f"{ohne_schluessel}\n{loesung.replace('CREATE TABLE', 'CREATE TEMP TABLE')}")["ergebnis"] == 2
    with pytest.raises(sql.SqlFehler):
        sql.schluessel(*a.sandbox, "SELECT * FROM pragma_table_info('kunde')")


def _er_beziehungen(a):
    from saku.lernen.rechnen.datenbanken import ER
    _, _, ent, slots = next(e for e in ER if e[0] == a.titel)
    return ent, [next(v for v in slot if v[3] in a.frage) for slot in slots]


def test_er_modell_nachgerechnet():
    kard = {"1:1": "1 : 1", "1:n": "1 : n", "n:m": "n : m"}
    for seed, a in _alle("ermodell"):
        ent, bez = _er_beziehungen(a)
        nm = [b for b in bez if b[2] == "n:m"]
        felder = {f.name: f for f in a.felder}
        assert felder["tabellen"].loesung == len(ent) + len(nm)  # jede n:m-Beziehung bringt eine Zwischentabelle
        x, y = re.fullmatch(r"Kardinalität (.+) : (.+)", felder["kard"].label).groups()
        b = next(b for b in bez if {b[0], b[1]} == {x, y})
        assert felder["kard"].loesung == (kard[b[2]] if b[:2] == (x, y) else "n : 1")
        x, y = re.fullmatch(r"Fremdschlüssel für (.+) – (.+) steht in", felder["fk"].label).groups()
        b = next(b for b in bez if b[:2] == (x, y))
        assert felder["fk"].loesung == ("eine eigene Zwischentabelle" if b[2] == "n:m" else ent[y][0]) and b[2] != "1:1"
        assert ("zw_pk" in felder) == bool(nm) and (not nm or felder["zw_pk"].loesung.endswith("zusammen"))
        if "fks" in felder:
            assert felder["fks"].loesung == len(bez) + len(nm)
        assert all(f.loesung in f.optionen for f in a.felder if f.optionen)
        assert a.rechenweg.count("Zwischentabelle ") >= len(nm) and all(f"{ent[b[0]][0]}_{ent[b[1]][0]} (" in a.rechenweg for b in nm)


def _normalform_selbst(schluessel: set, fds: list, atomar: bool) -> int:
    """Unabhängig nachgerechnet: teilweise Abhängigkeit → 1. NF, Nichtschlüssel → Nichtschlüssel → 2. NF."""
    if not atomar:
        return 0
    nicht = set().union(*(set(r) for _, r in fds)) - schluessel
    if any(set(l) < schluessel and set(r) & nicht for l, r in fds):
        return 1
    return 2 if any(set(l) & nicht and set(r) & nicht for l, r in fds) else 3


def test_normalisierung_nachgerechnet():
    from saku.lernen.rechnen.datenbanken import ANOMALIEN, NORMALFORMEN
    gesehen = set()
    for seed, a in _alle("normalform"):
        f = a.frage
        schluessel = set(re.findall(r"`(\w+)`", re.search(r"Primärschlüssel: (.+?)\. Es gelten", f)[1]))
        fds = [(re.findall(r"`(\w+)`", l), re.findall(r"`(\w+)`", r)) for l, r in re.findall(r"^- (.+?) → (.+)$", f, re.M)]
        zeilen = [z for z in f.splitlines() if z.startswith("| ") and "---" not in z][1:]
        nf = _normalform_selbst(schluessel, fds, atomar="<br>" not in f)
        l = a.loesung
        assert l["nf"] == NORMALFORMEN[nf] and l["tabellen"] == len({tuple(x) for x, _ in fds}), seed
        assert len(zeilen) >= 3 and (nf != 1 or len(schluessel) == 2) and (nf != 2 or len(schluessel) == 1)
        if nf == 3:
            assert l["tabellen"] == 1 and "anomalie" not in l and "**Fall:**" not in f
        else:
            fall = f.split("**Fall:** ")[1]
            assert l["anomalie"] == ANOMALIEN[0 if "soll erfasst werden" in fall else 1 if "geändert" in fall else 2]
        gesehen.add((nf, l.get("anomalie")))
    assert {nf for nf, _ in gesehen} == {0, 1, 2, 3} and len(gesehen) >= 9


def test_datenbanken_im_umfang_und_nicht_im_sprint(client, con):
    from urllib.parse import parse_qs, urlparse
    ap1, ae, si = (set(rechnen.im_umfang(p)) for p in ("AP1", "AP2-1201", "AP2-1202"))
    datenbanken = {a for a, x in rechnen.ARTEN.items() if x.gruppe == "Datenbanken"}
    assert datenbanken == {*SQL_ARTEN, "ermodell", "normalform"} and datenbanken <= ae and datenbanken <= ap1 and not datenbanken & si
    assert {a for a, x in rechnen.ARTEN.items() if not x.sprint} == {*SQL_ARTEN, "algorithmus"}  # Pseudocode schreiben auch nicht
    for _ in range(25):  # Demo: AP2 AE, Datenbanken gehören dazu, SQL aber nicht in den Sprint
        arten = {w.split(":")[0] for w in parse_qs(urlparse(client.get("/rechnen/sprint/neu").headers["Location"]).query)["a"]}
        assert not arten & set(SQL_ARTEN)
    assert "ohne SQL" in client.get("/rechnen/sprint").get_data(as_text=True)
    from saku.web.routen.suche import befehle
    assert befehle("normalisierung")[0][3] == ("rechnen.aufgabe", {"art": "normalform"})


def test_datenbanken_passen_zu_themen():
    passt = {"select": ["SQL: SELECT, JOIN, GROUP BY", "Datenbankabfragen"], "join": ["Joins und Aggregatfunktionen"],
             "aendern": ["Datenmanipulation mit INSERT und UPDATE"], "normalform": ["Normalisierung: 1. NF bis 3. NF", "Normalformen"],
             "ermodell": ["Entity-Relationship-Modell", "Datenmodellierung", "Kardinalitäten im ER-Diagramm"]}
    for slug, namen in passt.items():
        assert all(rechnen.passend([n]).slug == slug for n in namen), slug
    assert [a.slug for a in rechnen.passende(["SQL: SELECT, JOIN, GROUP BY"])] == list(SQL_ARTEN)  # der Lernpfad zeigt alle drei
    for name in ["Joint Venture", "Client-Server-Modell", "Software-Updates einspielen", "Anomalieerkennung im Netz", "Middleware"]:
        assert rechnen.passend([name]) is None, name


def test_sql_aufgabe_ausfuehren_pruefen_aufgeben(client, con):
    seed, a = next((seed, a) for seed, a in _alle("join") if a.titel == "Ohne Partner")
    loesung = a.felder[0].loesung
    tabelle = re.search(r"FROM (\w+)", loesung)[1]
    html = client.get(f"/rechnen/join?seed={seed}").get_data(as_text=True)
    assert '<textarea class="textarea editor" id="feld-sql" name="feld-sql"' in html and "autofocus" in html
    assert 'data-sql-ausfuehren' in html and f'hx-get="/rechnen/join/tabellen?seed={seed}"' in html and "⌘↵ führt aus" in html

    tabellen = client.get(f"/rechnen/join/tabellen?seed={seed}", headers=HTMX).get_data(as_text=True)
    assert "Beispieldaten" in tabellen and tabellen.count('<figure class="sql-tabelle"') == 3 and "sql-null" in tabellen
    ergebnis = client.post("/rechnen/join/sql", data={"seed": seed, "feld-sql": loesung}, headers=HTMX).get_data(as_text=True)
    assert re.search(r"\d Zeilen", ergebnis) and '<figure class="sql-tabelle"' in ergebnis
    assert "SQLite meldet" in client.post("/rechnen/join/sql", data={"seed": seed, "feld-sql": "SELEKT *"}).get_data(as_text=True)
    assert "Nicht erlaubt" in client.post("/rechnen/join/sql", data={"seed": seed, "feld-sql": "ATTACH 'x.db' AS x"}).get_data(as_text=True)
    assert client.post("/rechnen/join/sql", data={"feld-sql": loesung}).status_code == 400
    assert client.get("/rechnen/ermodell/tabellen?seed=1").status_code == 404  # ohne Sandbox
    assert client.get("/rechnen/gibtsnicht/tabellen?seed=1").status_code == 404

    def pruefen(**daten):
        return client.post("/rechnen/join/pruefen", data={"seed": seed} | daten, headers=HTMX).get_data(as_text=True)
    # läuft nicht: Meldung, die Anweisung bleibt stehen, gespeichert wird nichts
    html = pruefen(**{"feld-sql": f"SELECT * FROM {tabelle} WHERE"})
    assert "SQLite meldet" in html and "Korrigier die Anweisung" in html and f"SELECT * FROM {tabelle} WHERE</textarea>" in html
    assert con.execute("SELECT COUNT(*) FROM rechenuebung").fetchone()[0] == 0
    html = pruefen(**{"feld-sql": loesung})
    assert "Richtig." in html and "rechnen-sql--richtig" in html and 'class="language-sql"' in html and "Formeln: SQL" in html
    html = pruefen(**{"feld-sql": _typisch_falsch(loesung)})  # INNER statt LEFT JOIN: alle fehlen
    assert "Leider falsch." in html and re.search(r"\d Zeilen? fehl", html) and "Erwartet" in html and "Dein Ergebnis" in html
    html = pruefen(aufgeben="1")
    assert "Hier ist der Rechenweg." in html and "Ergebnis der Musterlösung" in html
    assert [tuple(z) for z in con.execute("SELECT art, richtig, felder_richtig, felder_gesamt FROM rechenuebung ORDER BY id")] == \
        [("join", 1, 1, 1), ("join", 0, 0, 1), ("join", 0, 0, 1)]
    # Daten ändern: verglichen wird der Tabellenstand, die Abweichung steht dabei
    seed, a = next((seed, a) for seed, a in _alle("aendern") if a.titel == "UPDATE")
    html = client.post("/rechnen/aendern/pruefen", data={"seed": seed, "feld-sql": _typisch_falsch(a.felder[0].loesung)},
                       headers=HTMX).get_data(as_text=True)
    assert "Leider falsch." in html and re.search(r"Tabelle \w+: \d+ Zeilen? fehl", html)
