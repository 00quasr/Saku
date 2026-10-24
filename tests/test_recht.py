"""Recht & Verträge: jede Art unabhängig nachgerechnet bzw. aus den Merkmalen der Fälle hergeleitet, typische Fehler fallen durch,
Gegenproben von Hand, Routen (nur erfundene Aufgaben)."""

import math
import re
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction

from saku.lernen import rechnen
from saku.lernen.rechnen import recht

SEEDS = range(300)
HTMX = {"HX-Request": "true"}
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
DATUM = re.compile(rf"(\d{{1,2}})\. ({'|'.join(MONATE)}) (\d{{4}})|(\d\d)\.(\d\d)\.(\d{{4}})")
ARTEN = ("vertragsart", "angebot", "gewaehrleistung", "maengel", "verzug", "lizenz")


def _alle(art: str, titel: str):
    for seed in SEEDS:
        a = rechnen.erzeugen(art, seed)
        if a.titel == titel:
            yield seed, a


def _daten(text: str) -> list[date]:
    """Alle Daten der Frage in ihrer Reihenfolge, „Freitag, 21. Juli 2028“ wie „21.07.2028“."""
    return [date(int(m[3]), MONATE.index(m[2]) + 1, int(m[1])) if m[1] else date(int(m[6]), int(m[5]), int(m[4]))
            for m in DATUM.finditer(text)]


def _euro(text: str) -> list[Fraction]:
    return [Fraction(z.replace(".", "").replace(",", ".")) for z in re.findall(r"(-?[\d.]+,\d\d) €", text)]


def _cent(x: Fraction) -> float:
    """Kaufmännisch auf Cent, exakt mit dem Bruch gerechnet (alle Beträge hier sind positiv)."""
    return math.floor(x * 100 + Fraction(1, 2)) / 100


def _plus_jahre(d: date, n: int) -> date:
    """Anders als wiso.plus_monate: Jahr ersetzen, den 29. Februar auf den 28. (§ 188 Abs. 3 BGB)."""
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return date(d.year + n, 2, 28)


def _ostern(j: int) -> date:
    """Ostersonntag nach der Gaußschen Osterformel (gregorianisch)."""
    a, b, c = j % 19, j // 100, j % 100
    d, e, f = b // 4, b % 4, (b + 8) // 25
    h = (19 * a + b - d - (b - f + 1) // 3 + 15) % 30
    l = (32 + 2 * e + 2 * (c // 4) - h - c % 4) % 7
    m = (a + 11 * h + 22 * l) // 451
    return date(j, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def _feiertage(jahr: int) -> set[date]:
    """Gesetzliche Feiertage aller Länder: feste, die von Ostern abhängigen und der Buß- und Bettag."""
    fest = [(1, 1), (1, 6), (3, 8), (5, 1), (8, 8), (8, 15), (9, 20), (10, 3), (10, 31), (11, 1), (12, 25), (12, 26)]
    buss = next(date(jahr, 11, t) for t in range(16, 23) if date(jahr, 11, t).weekday() == 2)
    return {date(jahr, m, t) for m, t in fest} | {_ostern(jahr) + timedelta(days=n) for n in (-2, 1, 39, 50, 60)} | {buss}


def _sicherer_werktag(d: date) -> bool:
    return d.weekday() < 5 and d not in _feiertage(d.year)


def _falsch(a, **eingaben) -> bool:
    """Mit diesen Eingaben (sonst die Musterlösung) ist mindestens ein Feld falsch."""
    return not all(rechnen.pruefen(a, {f.name: f.anzeige for f in a.felder} | eingaben).values())


# --- Bausteine, von Hand gerechnet ------------------------------------------------------

def test_gegenproben_von_hand():
    from saku.lernen.rechnen.wiso import plus_monate
    # Gewährleistung: 2 Jahre ab Ablieferung, der 29. Februar endet am 28. Februar (§ 188 Abs. 3 BGB)
    assert plus_monate(date(2027, 3, 17), 24) == date(2029, 3, 17) and plus_monate(date(2028, 2, 29), 24) == date(2030, 2, 28)
    # Minderung: 1.200 · 1.000 : 1.500 = 800; 1.000 · 700 : 1.200 = 583,333… → 583,33
    assert recht.minderung(1200, 1500, 1000) == Decimal("800.00") and recht.minderung(1000, 1200, 700) == Decimal("583.33")
    # Verzugszinsen: 2.000 € · 10,27 % · 30 : 365 = 16,8822 → 16,88 (Beispiel im Merkblatt);
    # Verbraucher bei Basiszinssatz −0,88 %: 5.000 € · 4,12 % · 61 : 365 = 34,4274 → 34,43
    assert recht.verzugszinsen(2000, Decimal("10.27"), 30) == Decimal("16.88")
    assert recht.verzugszinsen(5000, Decimal("-0.88") + 5, 61) == Decimal("34.43")
    # Verzug nach § 286 Abs. 3: Zugang 01.03.2027, die 30 Tage enden am 31.03.2027, Verzug ab 01.04.2027 (Beispiel im Merkblatt)
    assert date(2027, 3, 1) + timedelta(days=30) == date(2027, 3, 31)
    merkblatt = " ".join(rechnen.ARTEN[a].formeln for a in ARTEN).replace("{,}", ",").replace(r"\,\text{€}", " €")  # LaTeX wie gesetzt
    for beispiel in ("16,88 €", "800 €", "25.01.2029", "18.01.2030", "6.400 €", "5.400 €", "31. März"):
        assert beispiel in merkblatt, beispiel


def test_werktag_meidet_alle_feiertage():
    """Die Abkürzung in recht.werktag (ganze Osterspanne) gegen echte Feiertage aller Länder, 2026 bis 2035."""
    for jahr in range(2026, 2036):
        assert not any(recht.werktag(d) for d in _feiertage(jahr)), jahr
    assert recht.werktag(date(2027, 7, 14)) and not recht.werktag(date(2027, 7, 17))  # Mittwoch ja, Samstag nein


def test_varianten_und_merkblatt():
    titel = {art: {rechnen.erzeugen(art, s).titel for s in SEEDS} for art in ARTEN}
    assert titel == {
        "vertragsart": {"Welcher Vertrag?", "Wer schuldet was?"},
        "angebot": {"Rechtzeitige Annahme", "Freibleibendes Angebot", "Bestellung im Webshop", "Verspätete Annahme",
                    "Geänderte Annahme", "Angebot am Telefon", "Schweigen auf ein Angebot"},
        "gewaehrleistung": {"Gewährleistung oder Garantie?", "Beweislast", "Abweichende Vereinbarung"},
        "maengel": {"Mangelart erkennen", "Reihenfolge der Mängelrechte", "Minderung berechnen"},
        "verzug": {"Verzugsbeginn", "Verzugszinsen"},
        "lizenz": {"Passendes Lizenzmodell", "Was erlaubt die Lizenz?", "Lizenzkosten vergleichen"},
    }
    for art in ARTEN:  # Paragraphen im Merkblatt, ein Beispiel, und die Gruppe
        a = rechnen.ARTEN[art]
        assert a.gruppe == "Recht & Verträge" and "Beispiel" in a.formeln and ("§" in a.formeln or art == "lizenz") and a.sprint


# --- Vertragsarten ------------------------------------------------------------------------

def _vertrag_aus_merkmalen(text: str) -> str:
    if "Finanzierungsgesellschaft" in text:
        return "Leasingvertrag"
    if "aus eigen" in text:
        return "Werklieferungsvertrag"
    if re.search(r"Tagessatz|nach Stunden|Stundensatz", text):
        return "Dienstvertrag"
    if re.search(r"[Gg]ebühr|Entgelt", text):
        return "Mietvertrag"
    if re.search(r"Festpreis|Abnahme|fehlerfrei", text):
        return "Werkvertrag"
    assert re.search(r"kauft|bestellt|erwirbt", text), text
    return "Kaufvertrag"


def test_vertragsarten_aus_den_merkmalen():
    for seed, a in _alle("vertragsart", "Welcher Vertrag?"):
        faelle = re.findall(r"^\d\. (.*)$", a.frage, re.M)
        assert [f.loesung for f in a.felder] == [_vertrag_aus_merkmalen(t) for t in faelle], seed
        assert len({f.loesung for f in a.felder}) == 3
        # Erfolg oder Tätigkeit verwechselt
        tausch = {"Werkvertrag": "Dienstvertrag", "Dienstvertrag": "Werkvertrag", "Mietvertrag": "Leasingvertrag",
                  "Leasingvertrag": "Mietvertrag", "Werklieferungsvertrag": "Werkvertrag", "Kaufvertrag": "Mietvertrag"}
        assert _falsch(a, v1=tausch[a.felder[0].loesung])
    # alle Situationen einmal: die Merkmale passen zur Tabelle
    for vertrag, texte in recht.SITUATIONEN.items():
        assert all(_vertrag_aus_merkmalen(t) == vertrag for t in texte), vertrag


def test_pflichten_wer_schuldet_was():
    for seed, a in _alle("vertragsart", "Wer schuldet was?"):
        anbieterin = re.match(r"Die (.+?) (?:verkauft|richtet|vermietet)", a.frage)[1]
        for f in a.felder:
            zahlt = re.search(r"zahlen|abnehmen|zurückgeben", f.label)
            assert f.loesung.startswith(anbieterin) != bool(zahlt), (seed, f.label)
            assert _falsch(a, **{f.name: next(o for o in f.optionen if o != f.loesung)})
        assert " der der " not in a.frage and " die der " not in a.frage


# --- Angebot und Annahme ------------------------------------------------------------------

def test_angebot_und_annahme_nach_den_regeln():
    for seed in SEEDS:
        a = rechnen.erzeugen("angebot", seed)
        t, l = a.frage, a.loesung
        daten = _daten(t)
        assert all(d.weekday() < 5 for d in daten), (seed, daten)  # Zugang immer an Wochentagen
        if "Webshop" in t:
            soll = ("Bestellung der Kundin", "Keine Annahme", "Nein")
        elif "Hören wir" in t:
            soll = ("Angebot des Lieferers", "Keine Annahme", "Nein")
        elif re.search(r"„(freibleibend|unverbindlich)“", t):
            soll = ("Bestellung der Kundin", "Lieferung der Ware" if "liefert" in t else "Auftragsbestätigung des Lieferers", "Ja")
        else:
            if "am Telefon" in t:
                neuer_antrag = True
            else:
                bis, eingang = daten[1], daten[2]
                assert _sicherer_werktag(bis) and "gültig bis" in t
                neuer_antrag = eingang > bis or bool(re.search(r"Rabatt|Skonto|will aber nur", t))
            if neuer_antrag:  # § 150: die Kundin stellt den Antrag, der Lieferer nimmt an oder nicht
                ja = "einverstanden" in t
                soll = ("Bestellung der Kundin", "Auftragsbestätigung des Lieferers" if ja else "Keine Annahme", "Ja" if ja else "Nein")
            else:
                soll = ("Angebot des Lieferers", "Bestellung der Kundin", "Ja")
        assert (l["antrag"], l["annahme"], l["vertrag"]) == soll, (seed, a.titel)
    # typische Fehler: verspätete Bestellung als Annahme, Schweigen als Annahme, Webshop-Artikel als Angebot
    seed, a = next(_alle("angebot", "Verspätete Annahme"))
    assert _falsch(a, antrag="Angebot des Lieferers") and _falsch(a, annahme="Bestellung der Kundin")
    seed, a = next(_alle("angebot", "Schweigen auf ein Angebot"))
    assert _falsch(a, vertrag="Ja")
    seed, a = next(_alle("angebot", "Bestellung im Webshop"))
    assert _falsch(a, antrag="Angebot des Lieferers") and _falsch(a, annahme="Auftragsbestätigung des Lieferers")


# --- Gewährleistung und Garantie ----------------------------------------------------------

def test_gewaehrleistung_und_garantie_nachgerechnet():
    for seed, a in _alle("gewaehrleistung", "Gewährleistung oder Garantie?"):
        kauf, ablieferung, fehler = _daten(a.frage)
        jahre = int(re.search(r"\*\*(\d) Jahre? Garantie", a.frage)[1])
        ende, garantie = _plus_jahre(ablieferung, 2), _plus_jahre(kauf, jahre)
        assert _daten(a.loesung["ende"])[0] == ende and _daten(a.loesung["garantie"])[0] == garantie, seed
        assert _sicherer_werktag(ende) and _sicherer_werktag(garantie)
        soll = {(True, True): "Gewährleistung und Garantie", (True, False): "Nur Gewährleistung", (False, True): "Nur Garantie",
                (False, False): "Kein Anspruch"}[(fehler <= ende, fehler <= garantie)]
        assert a.loesung["anspruch"] == soll
        assert _falsch(a, ende=_plus_jahre(kauf, 2).strftime("%d.%m.%Y"))  # Frist ab Kaufvertrag statt ab Ablieferung
    anspruch = {a.loesung["anspruch"] for _, a in _alle("gewaehrleistung", "Gewährleistung oder Garantie?")}
    assert len(anspruch) == 4


def test_beweislast_nur_beim_verbrauchsgueterkauf_und_ein_jahr():
    gesehen = set()
    for seed, a in _alle("gewaehrleistung", "Beweislast"):
        ablieferung, fehler = _daten(a.frage)
        verbraucher = "Privatkundin" in a.frage
        verkaeufer = verbraucher and fehler <= _plus_jahre(ablieferung, 1)  # § 477 BGB
        assert a.loesung["vgk"] == ("Ja" if verbraucher else "Nein")
        assert a.loesung["beweis"].startswith("Der Verkäufer" if verkaeufer else "Der Käufer"), seed
        assert _daten(a.loesung["ende"])[0] == _plus_jahre(ablieferung, 2)
        gesehen.add((verbraucher, verkaeufer))
        if not verbraucher:
            assert _falsch(a, beweis=recht.BEWEIS[0])  # Beweislastumkehr auch zwischen Unternehmern: falsch
    assert gesehen == {(True, True), (True, False), (False, False)}


def test_abweichende_vereinbarung_nach_paragraf_476():
    for seed, a in _alle("gewaehrleistung", "Abweichende Vereinbarung"):
        t = a.frage
        verbraucher, gebraucht = "Privatkundin" in t, "gebrauchte" in t.split(".")[0]
        ausschluss = re.search(r"Ausschluss|ausgeschlossen", t)
        if verbraucher:  # kein Ausschluss, neu nie unter 2 Jahre, gebraucht 1 Jahr nur mit Hinweis und gesonderter Vereinbarung
            if not ausschluss and gebraucht and "ausdrücklich und gesondert vereinbart" in t:
                soll = ("Ja", "1 Jahr ab Ablieferung")
            else:
                soll = ("Nein", "2 Jahre ab Ablieferung")
        else:  # zwischen Unternehmern einzeln ausgehandelt: wirksam
            assert "einzeln ausgehandelt" in t and (gebraucht or not ausschluss)
            soll = ("Ja", "Keine Gewährleistung" if ausschluss else "1 Jahr ab Ablieferung")
        assert (a.loesung["wirksam"], a.loesung["frist"]) == soll, (seed, t)
        if verbraucher and ausschluss:
            assert _falsch(a, frist="Keine Gewährleistung")
    assert {(a.loesung["wirksam"], a.loesung["frist"]) for _, a in _alle("gewaehrleistung", "Abweichende Vereinbarung")} == {
        ("Ja", "1 Jahr ab Ablieferung"), ("Nein", "2 Jahre ab Ablieferung"), ("Ja", "Keine Gewährleistung")}


# --- Mängelrechte -------------------------------------------------------------------------

def _mangel_aus_merkmalen(text: str) -> str:
    if re.search(r"Urheberrecht|Patent", text):
        return "Rechtsmangel"
    if re.search(r"montiert|Montageanleitung|baut .* ein", text):
        return "Montagemangel"
    zahlen = [int(z) for z in re.findall(r"\b\d+\b", text)]
    if "Zoll" not in text and re.search("bestellt", text, re.I) and len(zahlen) == 2 and zahlen[1] < zahlen[0]:
        return "Zuweniglieferung"
    if re.search(r"Bestellt war|[Ss]tatt der bestellten", text):
        return "Falschlieferung"
    return "Sachmangel"


def test_mangelart_aus_den_merkmalen():
    for art, (_, texte) in recht.MAENGEL.items():
        assert all(_mangel_aus_merkmalen(t) == art for t in texte), art
    for seed, a in _alle("maengel", "Mangelart erkennen"):
        faelle = re.findall(r"^\d\. (.*)$", a.frage, re.M)
        assert [f.loesung for f in a.felder] == [_mangel_aus_merkmalen(t) for t in faelle], seed


def test_reihenfolge_nacherfuellung_vor_ruecktritt():
    gesehen = set()
    for seed, a in _alle("maengel", "Reihenfolge der Mängelrechte"):
        preis, kosten = _euro(a.frage)
        if "gerade entdeckt" in a.frage:
            soll = {"recht": "Zuerst Nacherfüllung", "ruecktritt": "Nein", "minderung": "Nein", "wahl": recht.WAHL[0]}
            assert _falsch(a, ruecktritt="Ja") and _falsch(a, recht="Rücktritt oder Minderung")  # Rücktritt vor Nacherfüllung
            assert _falsch(a, wahl=recht.WAHL[1])  # die Wahl hat die Käuferin (§ 439 Abs. 1)
        elif "Verjährung" in a.frage:
            soll = {"recht": "Keine Mängelrechte mehr", "ruecktritt": "Nein", "minderung": "Nein"}
        else:  # Nacherfüllung gescheitert: Rücktritt nur bei erheblichem Mangel (über 5 % des Preises), Minderung immer
            soll = {"recht": "Rücktritt oder Minderung", "ruecktritt": "Ja" if kosten > preis * Fraction(5, 100) else "Nein",
                    "minderung": "Ja"}
            assert abs(kosten / preis - Fraction(5, 100)) >= Fraction(3, 100)  # weit weg von der Grenze
        assert a.loesung == soll, seed
        gesehen.add((soll["recht"], soll["ruecktritt"]))
    assert len(gesehen) == 4


def test_minderung_nachgerechnet():
    for seed, a in _alle("maengel", "Minderung berechnen"):
        preis, ohne, mit = _euro(a.frage)
        gemindert = preis * mit / ohne
        assert a.loesung["preis"] == _cent(gemindert) and a.loesung["erstattung"] == _cent(preis - Fraction(str(a.loesung["preis"])))
        falsch = preis - (ohne - mit)  # die Wertdifferenz einfach abgezogen
        assert preis != ohne and _falsch(a, preis=f"{float(falsch):.2f}".replace(".", ","))


# --- Zahlungsverzug -----------------------------------------------------------------------

def test_verzugsbeginn_nach_paragraf_286():
    gesehen = set()
    for seed, a in _alle("verzug", "Verzugsbeginn"):
        t = a.frage
        daten = _daten(t)
        zugang, stichtag = daten[0], daten[-1]
        assert zugang.weekday() < 5
        verbraucher = "Privatkunden" in t
        if "Im Vertrag ist vereinbart" in t:
            grund, ab = 1, daten[1] + timedelta(days=1)
            assert _sicherer_werktag(daten[1])
        elif "Mahnung zu" in t:
            grund, ab = 0, daten[1]
            if verbraucher:
                assert "Hinweis" in t and "enthält die Rechnung nicht" in t  # sonst wäre er nach 30 Tagen schon in Verzug
            else:
                assert ab < zugang + timedelta(days=31)  # früher als die 30-Tage-Regel
        else:
            grund, ab = 2, zugang + timedelta(days=31)
            assert _sicherer_werktag(zugang + timedelta(days=30)) and (not verbraucher or "weist ausdrücklich darauf hin" in t)
        assert a.loesung == {"grund": recht.GRUENDE[grund], "ab": ab.strftime("%d.%m.%Y"), "stichtag": "Ja" if stichtag >= ab else "Nein"}
        assert abs((stichtag - ab).days) >= 3
        if verbraucher and grund == 0:  # ohne Hinweis zählt die 30-Tage-Regel nicht
            assert _falsch(a, ab=(zugang + timedelta(days=31)).strftime("%d.%m.%Y"))
        gesehen.add((grund, verbraucher, a.loesung["stichtag"]))
    assert len(gesehen) >= 10


def test_verzugszinsen_nachgerechnet():
    gesehen = set()
    for seed, a in _alle("verzug", "Verzugszinsen"):
        t = a.frage
        betrag = _euro(t)[0]
        basis = Fraction(re.search(r"Basiszinssatz von \*\*(-?[\d,]+) %", t)[1].replace(",", "."))
        verbraucher = "Privatkunden" in t
        daten = _daten(t)
        erster = daten[1] + timedelta(days=1) if "Im Vertrag ist vereinbart" in t else daten[0] + timedelta(days=31)
        zahlung = daten[-1]
        assert (erster.year, erster.month < 7) == (zahlung.year, zahlung.month < 7)  # ein Basiszinssatz für den ganzen Zeitraum
        tage = (zahlung - erster).days + 1
        satz = basis + (5 if verbraucher else 9)
        zinsen = betrag * satz / 100 * tage / 365
        assert a.loesung == {"satz": float(satz), "tage": tage, "zinsen": _cent(zinsen), "pauschale": 0.0 if verbraucher else 40.0}, seed
        andere = basis + (9 if verbraucher else 5)  # 9 statt 5 Prozentpunkte bei Verbrauchern (und umgekehrt)
        assert _falsch(a, satz=f"{float(andere):.2f}".replace(".", ","))
        assert _falsch(a, zinsen=f"{float(betrag * andere / 100 * tage / 365):.2f}".replace(".", ","))
        assert _falsch(a, zinsen=f"{float(betrag * satz / 100 * (tage - 1) / 365):.2f}".replace(".", ","))  # einen Tag zu wenig
        assert _falsch(a, pauschale="40" if verbraucher else "0")
        gesehen.add((verbraucher, basis < 0))
    assert len(gesehen) == 4


# --- Softwarelizenzen ---------------------------------------------------------------------

LIZENZ_MERKMALE = [("OEM-Lizenz", r"vorinstalliert|nur zusammen mit dem Gerät"), ("Volumenlizenz", r"Mengenrabatt|zentrale"),
                   ("Abonnement (Subscription)", r"je Benutzer und Monat|jährlich je Benutzer"),
                   ("Freeware", r"Quellcode ist nicht veröffentlicht|Quellcode bleibt beim Hersteller"),
                   ("Open-Source-Lizenz", r"Quellcode öffentlich|Quellcode jeder einsehen"),
                   ("Einzelplatzlizenz", r"genau einem Rechner|genau diesen Rechner")]


def _erlaubt_nach_regeln(text: str) -> bool:
    if "GNU GPL" in text:  # Copyleft erst bei Weitergabe, Geld verlangen erlaubt
        return "ohne den Quellcode" not in text
    if "MIT-Lizenz" in text or "BSD" in text:  # permissiv: Hinweis behalten, nicht mit den Urhebern werben
        return not re.search(r"entfernt|wirbt", text)
    return "löscht ihre eigene Installation" in text  # Erschöpfung; Freeware ändern, Unterlizenz, gekündigtes Abo: nein


def test_lizenzen_nach_den_regeln():
    for seed, a in _alle("lizenz", "Passendes Lizenzmodell"):
        for f, text in zip(a.felder, re.findall(r"^\d\. (.*)$", a.frage, re.M)):
            assert [art for art, muster in LIZENZ_MERKMALE if re.search(muster, text)] == [f.loesung], (seed, text)
    for seed, a in _alle("lizenz", "Was erlaubt die Lizenz?"):
        for f, text in zip(a.felder, re.findall(r"^\d\. (.*)$", a.frage, re.M)):
            assert f.loesung == ("Ja" if _erlaubt_nach_regeln(text) else "Nein"), (seed, text)
    gpl = next(a for _, a in _alle("lizenz", "Was erlaubt die Lizenz?") if "ohne den Quellcode" in a.frage)
    feld = next(f.name for f, text in zip(gpl.felder, re.findall(r"^\d\. (.*)$", gpl.frage, re.M)) if "ohne den Quellcode" in text)
    assert _falsch(gpl, **{feld: "Ja"})  # GPL-Code verändert verkaufen, ohne Quellcode: nicht erlaubt


def test_lizenzkosten_nachgerechnet():
    gesehen = set()
    for seed, a in _alle("lizenz", "Lizenzkosten vergleichen"):
        t = a.frage
        nutzer, jahre = (int(x) for x in re.search(r"\*\*(\d+) Benutzer\*\*, voraussichtlich \*\*(\d) Jahre", t).groups())
        preis, abo = _euro(t)
        wartung = int(re.search(r"für (\d+) % des Lizenzpreises", t)[1])
        w_jahre = jahre - 1 if "ab dem zweiten Jahr" in t else jahre
        kauf = nutzer * preis * (1 + Fraction(wartung, 100) * w_jahre)
        miete = nutzer * abo * 12 * jahre
        assert a.loesung == {"kauf": _cent(kauf), "abo": _cent(miete), "guenstiger": "Kauf mit Wartung" if kauf < miete else "Abonnement"}
        gesehen.add(a.loesung["guenstiger"])
    assert len(gesehen) == 2


# --- Einbindung ---------------------------------------------------------------------------

def test_themen_umfang_und_suche():
    passt = {"vertragsart": ["Vertragsarten im Kaufrecht", "Werkvertrag und Dienstvertrag", "Werklieferungsvertrag"],
             "angebot": ["Angebot und Annahme", "Vertragsschluss im Internet", "Willenserklärungen"],
             "gewaehrleistung": ["Gewährleistung und Garantie", "Beweislastumkehr beim Verbrauchsgüterkauf", "Sachmängelhaftung"],
             "maengel": ["Mängelrechte des Käufers", "Mangelhafte Lieferung", "Nacherfüllung und Rücktritt", "Mängelrüge"],
             "verzug": ["Zahlungsverzug und Mahnung", "Verzugszinsen berechnen", "Mahnwesen"],
             "lizenz": ["Softwarelizenzen", "Open-Source-Lizenzen", "Lizenzmodelle", "Urheberrecht an Software", "Freeware"]}
    for slug, namen in passt.items():
        assert all(rechnen.passend([n]).slug == slug for n in namen), slug
    # „Leasing“ bleibt beim Kostenvergleich, „Kündigung“ und „Ausbildungsvertrag“ bei WiSo
    assert rechnen.passend(["Leasing oder Kauf"]).slug == "vergleich" and rechnen.passend(["Ausbildungsvertrag"]).slug == "kuendigung"
    for name in ["Erwerbsminderungsrente", "Cloud-Modelle: IaaS, PaaS, SaaS", "Lieferverzug", "Annahmeverzug", "Kaufmännische Berufe"]:
        assert rechnen.passend([name]) is None, name

    ap1, ae, si = (set(rechnen.im_umfang(p)) for p in ("AP1", "AP2-1201", "AP2-1202"))
    assert set(ARTEN) <= ap1 and not set(ARTEN) & (ae | si)
    from saku.web.routen.suche import befehle
    assert befehle("zahlungsverzug")[0][:2] == ("calculator", "Rechnen: Zahlungsverzug")
    assert befehle("gewährleistung")[0][3] == ("rechnen.aufgabe", {"art": "gewaehrleistung"})


def test_recht_auf_der_seite(client, con):
    html = client.get("/rechnen/").get_data(as_text=True)
    assert "Recht &amp; Verträge" in html and all(f'href="/rechnen/{art}"' in html for art in ARTEN)
    formeln = client.get("/rechnen/formeln").get_data(as_text=True)
    assert all(f'<article class="formel-art" id="{art}">' in formeln for art in ARTEN) and "§ 286" in formeln

    seed, a = next(_alle("verzug", "Verzugszinsen"))
    karte = client.get(f"/rechnen/verzug?seed={seed}").get_data(as_text=True)
    assert all(f'name="feld-{f.name}"' in karte for f in a.felder) and "Basiszinssatz" in karte

    def pruefen(art, seed, **daten):
        return client.post(f"/rechnen/{art}/pruefen", data={"seed": seed} | daten, headers=HTMX).get_data(as_text=True)
    richtig = {f"feld-{f.name}": f.anzeige for f in a.felder}
    assert "Richtig." in pruefen("verzug", seed, **richtig)
    assert "3 von 4 richtig." in pruefen("verzug", seed, **richtig | {"feld-pauschale": "40" if a.loesung["pauschale"] == 0 else "0"})
    weg = pruefen("verzug", seed, aufgeben="1")
    assert "Hier ist der Rechenweg." in weg and "Formeln: Zahlungsverzug" in weg and 'href="/rechnen/formeln#verzug"' in weg

    seed, a = next(_alle("angebot", "Verspätete Annahme"))  # Auswahlfelder
    karte = client.get(f"/rechnen/angebot?seed={seed}").get_data(as_text=True)
    assert karte.count('<select class="select"') == 3 and ">Keine Annahme</option>" in karte
    assert "Richtig." in pruefen("angebot", seed, **{f"feld-{f.name}": f.loesung for f in a.felder})
    assert "Leider falsch." in pruefen("angebot", seed, **{"feld-antrag": "Angebot des Lieferers", "feld-annahme": "Bestellung der Kundin",
                                                           "feld-vertrag": "Ja" if a.loesung["vertrag"] == "Nein" else "Nein"})
    assert [tuple(z) for z in con.execute("SELECT art, richtig FROM rechenuebung ORDER BY id")] == \
        [("verzug", 1), ("verzug", 0), ("verzug", 0), ("angebot", 1), ("angebot", 0)]
