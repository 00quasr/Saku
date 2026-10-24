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
        assert not any(rechnen.pruefen(a, {}).values())
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
    }
    for slug, namen in passt.items():
        for name in namen:
            art = rechnen.passend([name])
            assert art and art.slug == slug, name
    # früher zu breit: „Binär“, „Bandbreite“, „Übertragung“, „Strom“, „Speicher“, „Netz“, „Elektrische“, „IP-Adresse“
    for name in ["Binärbäume und Graphen", "Binäre Suche", "Bandbreitenmanagement mit QoS", "Übertragungsmedien im Gebäude",
                 "Datenstrom-Verarbeitung", "Speicherverwaltung im Betriebssystem", "Netzwerkmonitoring", "Elektrische Sicherheit prüfen",
                 "Energielabel und Gütesiegel", "NAT mit privaten Adressen", "Vertragsarten im Kaufrecht", "Laufzeit und Speicherbedarf",
                 "Fehlersuche im Netzwerk", None]:
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
    assert all(a.titel in html for a in rechnen.ARTEN.values()) and all(g.replace("&", "&amp;") in html for g in rechnen.GRUPPEN)
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
