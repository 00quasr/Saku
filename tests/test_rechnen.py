"""Rechentrainer: Generatoren, Kontrolle und Routen (nur erfundene Aufgaben)."""

import ipaddress
import itertools
import random
import re

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
    }
    for slug, namen in passt.items():
        for name in namen:
            art = rechnen.passend([name])
            assert art and art.slug == slug, name
    # früher zu breit: „Binär“, „Bandbreite“, „Übertragung“, „Strom“, „Speicher“, „Netz“, „Elektrische“, „IP-Adresse“
    for name in ["Bandbreitenmanagement mit QoS", "Übertragungsmedien im Gebäude",
                 "Datenstrom-Verarbeitung", "Speicherverwaltung im Betriebssystem", "Netzwerkmonitoring", "Elektrische Sicherheit prüfen",
                 "Energielabel und Gütesiegel", "NAT mit privaten Adressen", "Vertragsarten im Kaufrecht", "Laufzeit und Speicherbedarf",
                 "Fehlersuche im Netzwerk", "Hashwerte und digitale Signaturen", "Gruppenrichtlinien", None]:
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
    assert "Heute gerechnet" not in client.get("/").get_data(as_text=True)  # erst, wenn heute gerechnet wurde
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
    assert 'Heute gerechnet: <span class="zahl">3 · 33 %</span>' in heute and 'href="/rechnen/"' in heute
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
        code = re.search(r"```\n(.*?)```", a.frage, re.S)[1]
        ausgabe, variablen = _pseudocode_ausfuehren(code)
        if a.titel == "Fehlersuche":
            nummer = a.loesung["zeile"]
            fehlerhaft = re.search(r"`([^`]+)`, richtig wäre", a.rechenweg)[1]
            assert re.search(rf"^\s*{nummer}  \s*(.*)$", code, re.M)[1] == fehlerhaft
            assert ausgabe == _folge(re.search(r"gibt das Programm \*\*(.*?)\*\* aus", a.rechenweg)[1])
            continue
        assert ausgabe == _folge(re.search(r"Ausgabe: \*\*(.*?)\*\*", a.rechenweg)[1]), seed
        for name, wert in a.loesung.items():
            if a.titel == "Endwerte bestimmen":
                assert _folge(str(wert)) == _folge(str(variablen[name])), (seed, name)
        if a.titel == "Ausgabe bestimmen":
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
