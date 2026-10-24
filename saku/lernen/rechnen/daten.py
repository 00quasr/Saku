"""Daten & Medien: Datenmengen von Bildern, Scans, Audio und Video, Speichereinheiten, Zahlensysteme."""

import math

from saku.lernen.rechnen.basis import BYTE, FAKTOR, FIRMEN, Aufgabe, Feld, art, de, hoch, schritte, tabelle

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "datenmenge": """- Bild: Breite · Höhe · Farbtiefe (Bit) : 8 = Byte
- Farbtiefe aus Farbanzahl: 2ᵇ Farben → b Bit (256 → 8, 65.536 → 16, 16,7 Mio. → 24)
- Scan: Breite in Zoll · dpi und Höhe in Zoll · dpi ergeben die Pixel
- Audio: Abtastrate · Bit je Abtastwert · Kanäle · Sekunden : 8 = Byte
- Video: Bild in Byte · Bilder je Sekunde · Sekunden
- Anzahl Dateien auf einem Datenträger: Kapazität : Dateigröße, abrunden

*Beispiel:* 1.920 × 1.080 Pixel, 24 Bit: 1.920 · 1.080 · 24 : 8 = 6.220.800 Byte ≈ 5,93 MiB""",
    "speicher": """- Dezimalpräfixe (Hersteller): 1 kB = 10³, 1 MB = 10⁶, 1 GB = 10⁹, 1 TB = 10¹² Byte
- Binärpräfixe (Betriebssystem): 1 KiB = 1.024, 1 MiB = 1.024², 1 GiB = 1.024³, 1 TiB = 1.024⁴ Byte
- Umrechnen immer über Byte: Wert · Faktor der alten Einheit : Faktor der neuen Einheit
- Scheinbarer Verlust GB → GiB: 1 − 10⁹ : 1.024³ ≈ 6,87 %, TB → TiB ≈ 9,05 %

*Beispiel:* 2 TB = 2 · 10¹² Byte : 1.024⁴ ≈ 1,82 TiB""",
    "zahlensystem": """- Stellenwerte binär: 128, 64, 32, 16, 8, 4, 2, 1; hexadezimal: 16³ = 4.096, 16² = 256, 16, 1
- Dezimal → binär: Stellenwerte von links füllen, solange der Rest reicht (oder fortlaufend durch 2 teilen, Reste von unten lesen)
- Binär ↔ hexadezimal: je 4 Bit sind eine Hex-Ziffer (A = 10 … F = 15)
- Zweierkomplement (8 Bit): Betrag binär, alle Bits invertieren, + 1; höchstes Bit 1 heißt negativ; Bereich −128 bis 127

*Beispiel:* 45 = 32 + 8 + 4 + 1 = `0010 1101` = 2D; −45 = `1101 0010` + 1 = `1101 0011`""",
}


AUFLOESUNGEN = [(800, 600), (1024, 768), (1280, 720), (1920, 1080), (2560, 1440), (3840, 2160), (4000, 3000), (6000, 4000)]
# Farbtiefe in Bit → wie sie in der Aufgabe stehen kann
FARBEN = {1: "Schwarz-Weiß", 8: "256 Farben", 16: "65.536 Farben", 24: "16.777.216 Farben (True Color)"}


def _ziel(rng, byte: float) -> str:
    """Passende Einheit fürs Ergebnis, zufällig dezimal oder binär."""
    stufe = next(s for s in ("TB", "GB", "MB", "kB") if byte >= BYTE[s]) if byte >= 1000 else "kB"
    return rng.choice([stufe, stufe[0].upper() + "iB" if stufe != "kB" else "KiB"])


def _byte_weg(byte: float, einheit: str) -> str:
    return f"In {einheit}: {de(byte, 0)} Byte : {FAKTOR[einheit]} = **{de(byte / BYTE[einheit])} {einheit}**"


def _praefix_hinweis(einheit: str) -> str:
    if "i" in einheit:
        ausgeschrieben = "" if einheit == "KiB" else f" = {de(BYTE[einheit])} Byte"
        return f"Binärpräfix: 1 {einheit} = {FAKTOR[einheit]} Byte{ausgeschrieben}."
    return f"Dezimalpräfix: 1 {einheit} = {FAKTOR[einheit]} Byte."


@art("datenmenge", "Datenmenge", "Daten & Medien", "Bilder, Scans, Audio und Video: wie groß wird die Datei?",
     ("Datenmenge", "Farbtiefe", "Abtastrate", "Dateigröße"), formeln=FORMELN["datenmenge"])
def datenmenge(rng):
    return rng.choice([_bild, _scan, _audio, _video, _fotos_auf_karte])(rng)


def _bild(rng):
    breite, hoehe = rng.choice(AUFLOESUNGEN)
    bit = rng.choice(list(FARBEN)[1:])
    byte = breite * hoehe * bit / 8
    einheit = _ziel(rng, byte)
    farben = rng.random() < 0.4
    tiefe = f"mit {FARBEN[bit]}" if farben else f"mit einer Farbtiefe von {bit} Bit"
    frage = (f"Die Marketingabteilung der {rng.choice(FIRMEN)} speichert eine Grafik mit **{de(breite)} × {de(hoehe)} Pixeln** "
             f"{tiefe} unkomprimiert.\n\nBerechnen Sie die Datenmenge in Byte und in {einheit} (zwei Nachkommastellen). "
             f"{_praefix_hinweis(einheit)}")
    weg = [f"Farbtiefe: {de(2 ** bit)} Farben = 2{hoch(bit)} → {bit} Bit je Pixel"] if farben else []
    weg += [f"Pixel: {de(breite)} · {de(hoehe)} = {de(breite * hoehe)}",
            f"Bit: {de(breite * hoehe)} · {bit} Bit = {de(breite * hoehe * bit)} Bit",
            f"Byte: : 8 = **{de(byte, 0)} Byte**", _byte_weg(byte, einheit)]
    felder = [Feld("byte", "Datenmenge", byte, "Byte", stellen=0), Feld("einheit", "Datenmenge", byte / BYTE[einheit], einheit)]
    return Aufgabe(frage, felder, schritte(*weg), toleranz=0.005, titel="Bild")


def _scan(rng):
    vorlage, breite, hoehe = rng.choice([("ein Foto", 6, 4), ("ein Foto", 7, 5), ("ein Zertifikat", 8, 10), ("einen Bauplan", 11, 17)])
    dpi = rng.choice([150, 200, 300, 600, 1200])
    bit, art_ = rng.choice([(1, "schwarz-weiß (1 Bit)"), (8, "in Graustufen (8 Bit)"), (24, "in Farbe (24 Bit)")])
    pixel = breite * dpi * hoehe * dpi
    byte = pixel * bit / 8
    einheit = _ziel(rng, byte)
    frage = (f"Im Büro der {rng.choice(FIRMEN)} wird {vorlage} im Format **{breite} × {hoehe} Zoll** mit **{dpi} dpi** "
             f"{art_} eingescannt.\n\nBerechnen Sie die Anzahl der Pixel und die Datenmenge in {einheit} (zwei Nachkommastellen). "
             f"{_praefix_hinweis(einheit)}")
    weg = schritte(
        f"Breite: {breite} Zoll · {dpi} dpi = {de(breite * dpi)} Pixel, Höhe: {hoehe} Zoll · {dpi} dpi = {de(hoehe * dpi)} Pixel",
        f"Pixel: {de(breite * dpi)} · {de(hoehe * dpi)} = **{de(pixel)}**",
        f"Byte: {de(pixel)} · {bit} Bit : 8 = {de(byte, 0)} Byte",
        _byte_weg(byte, einheit),
    )
    felder = [Feld("pixel", "Pixel", pixel, stellen=0), Feld("einheit", "Datenmenge", byte / BYTE[einheit], einheit)]
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="Scan")


def _dauer_text(s: int) -> str:
    if s >= 3600:
        return f"{de(s / 3600)} {'Stunde' if s == 3600 else 'Stunden'}"
    minuten, sekunden = divmod(s, 60)
    return " ".join(t for t in (f"{minuten} min" if minuten else "", f"{sekunden} s" if sekunden else "") if t)


def _audio(rng):
    rate, bit = rng.choice([44100, 48000, 96000]), rng.choice([16, 24])
    kanaele, name = rng.choice([(1, "Mono"), (2, "Stereo")])
    sekunden = rng.choice([45, 90, 150, 180, 210, 240, 252, 300, 600, 1800, 3600])
    was = "Musik für die Telefon-Warteschleife" if sekunden < 600 else "eine Podcast-Folge für die Website"
    bits = rate * bit * kanaele * sekunden
    byte = bits / 8
    einheit = _ziel(rng, byte)
    frage = (f"Die {rng.choice(FIRMEN)} nimmt {was} von **{_dauer_text(sekunden)}** unkomprimiert "
             f"auf: Abtastrate **{de(rate)} Hz**, **{bit} Bit**, **{name}**.\n\nBerechnen Sie die Datenmenge in Byte "
             f"und in {einheit} (zwei Nachkommastellen). {_praefix_hinweis(einheit)}")
    weg = schritte(
        f"Dauer: {_dauer_text(sekunden)} = {de(sekunden)} s",
        f"Bit: {de(rate)} Hz · {bit} Bit · {kanaele} Kanal{'e' if kanaele > 1 else ''} · {de(sekunden)} s = {de(bits)} Bit",
        f"Byte: : 8 = **{de(byte, 0)} Byte**",
        _byte_weg(byte, einheit),
    )
    felder = [Feld("byte", "Datenmenge", byte, "Byte", stellen=0), Feld("einheit", "Datenmenge", byte / BYTE[einheit], einheit)]
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="Audio")


def _video(rng):
    breite, hoehe = rng.choice([(1280, 720), (1920, 1080), (3840, 2160)])
    fps, sekunden = rng.choice([24, 25, 30, 50, 60]), rng.choice([10, 30, 60, 120, 300])
    bild = breite * hoehe * 3
    byte = bild * fps * sekunden
    einheit = rng.choice(["GB", "GiB"])
    frage = (f"Eine Überwachungskamera der {rng.choice(FIRMEN)} zeichnet **{_dauer_text(sekunden)}** unkomprimiertes Video auf: "
             f"**{de(breite)} × {de(hoehe)} Pixel**, **24 Bit** Farbtiefe, **{fps} Bilder pro Sekunde**.\n\n"
             f"Berechnen Sie die Datenmenge eines Einzelbildes in Byte und die gesamte Datenmenge in {einheit} "
             f"(zwei Nachkommastellen). {_praefix_hinweis(einheit)}")
    weg = schritte(
        f"Einzelbild: {de(breite)} · {de(hoehe)} · 24 Bit : 8 = **{de(bild)} Byte**",
        f"Bilder: {fps} fps · {de(sekunden)} s = {de(fps * sekunden)}",
        f"Gesamt: {de(bild)} Byte · {de(fps * sekunden)} = {de(byte)} Byte",
        _byte_weg(byte, einheit),
    )
    felder = [Feld("bild", "Einzelbild", bild, "Byte", stellen=0), Feld("gesamt", "Gesamt", byte / BYTE[einheit], einheit)]
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="Video")


def _fotos_auf_karte(rng):
    breite, hoehe = rng.choice([(4000, 3000), (5000, 4000), (6000, 4000)])
    karte, kompression = rng.choice([16, 32, 64, 128, 256]), rng.choice([0, 10, 15, 20, 25])
    mb = round(breite * hoehe * 3 * (kompression or 100) / 100 / 10 ** 6, 6)
    anzahl = math.floor(karte * 1000 / mb + 1e-9)
    satz = f" Durch JPEG-Kompression ist jedes Foto nur noch **{kompression} %** so groß." if kompression else " Die Fotos werden unkomprimiert gespeichert."
    frage = (f"Eine Kamera der {rng.choice(FIRMEN)} macht Fotos mit **{de(breite)} × {de(hoehe)} Pixeln** und **24 Bit** "
             f"Farbtiefe.{satz}\n\nWie groß ist ein Foto in MB, und wie viele Fotos passen auf eine Speicherkarte mit **{karte} GB**? "
             "(1 MB = 10⁶ Byte, 1 GB = 10⁹ Byte)")
    weg = [f"Foto: {de(breite)} · {de(hoehe)} · 3 Byte = {de(breite * hoehe * 3)} Byte = {de(breite * hoehe * 3 / 10 ** 6)} MB"]
    if kompression:
        weg.append(f"Komprimiert: {de(breite * hoehe * 3 / 10 ** 6)} MB · {de(kompression / 100)} = **{de(mb)} MB**")
    weg += [f"Karte: {karte} GB = {de(karte * 1000)} MB",
            f"Anzahl: {de(karte * 1000)} : {de(mb)} = {de(karte * 1000 / mb)} → abrunden, ein angefangenes Foto passt nicht: "
            f"**{de(anzahl)} Fotos**"]
    felder = [Feld("foto", "Größe je Foto", mb, "MB"), Feld("anzahl", "Fotos auf der Karte", anzahl, stellen=0)]
    return Aufgabe(frage, felder, schritte(*weg), titel="Fotos auf der Speicherkarte")


# --- Speichereinheiten ---------------------------------------------------

@art("speicher", "Speichereinheiten", "Daten & Medien", "kB/KiB, GB/GiB, TB/TiB umrechnen: was zeigt das Betriebssystem?",
     ("Speichereinheit", "Speichergröße", "Binärpräfix", "Kapazitätsplanung"), formeln=FORMELN["speicher"])
def speicher(rng):
    return rng.choice([_anzeige, _umrechnen, _dateien_auf_stick])(rng)


def _anzeige(rng):
    wert, einheit = rng.choice([(256, "GB"), (500, "GB"), (512, "GB"), (960, "GB"), (1, "TB"), (2, "TB"), (4, "TB"),
                                (8, "TB"), (12, "TB"), (16, "TB")])
    ziel = einheit[0] + "iB"
    angezeigt = wert * BYTE[einheit] / BYTE[ziel]
    verlust = (1 - angezeigt / wert) * 100
    geraet = "eine SSD" if einheit == "GB" else "eine Festplatte"
    frage = (f"Die {rng.choice(FIRMEN)} kauft {geraet} mit **{de(wert)} {einheit}**. Das Betriebssystem rechnet mit Binärpräfixen "
             f"und zeigt die Kapazität in {ziel} an.\n\nWelche Kapazität zeigt das Betriebssystem an, und wie viel Prozent scheinen "
             "gegenüber der Herstellerangabe zu „fehlen“? (zwei Nachkommastellen)")
    weg = schritte(
        f"Hersteller rechnet dezimal: {de(wert)} {einheit} = {de(wert)} · {FAKTOR[einheit]} Byte = {de(wert * BYTE[einheit])} Byte",
        f"Betriebssystem rechnet binär: : {FAKTOR[ziel]} = : {de(BYTE[ziel])} → **{de(angezeigt)} {ziel}**",
        f"Anteil: {de(angezeigt, 4)} : {de(wert)} = {de(angezeigt / wert * 100)} % → es „fehlen“ **{de(verlust)} %**. "
        "Es fehlt nichts, nur die Einheit ist eine andere.",
    )
    felder = [Feld("anzeige", "Angezeigte Kapazität", angezeigt, ziel), Feld("verlust", "Scheinbar fehlend", verlust, "%")]
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="Was zeigt das Betriebssystem?")


def _umrechnung(rng) -> tuple[float, str, str]:
    while True:
        wert = rng.choice([1.5, 2, 3.5, 4, 8, 16, 32, 64, 128, 250, 500, 750])
        von, nach = rng.sample(list(BYTE), 2)
        if ("i" in von) != ("i" in nach) and 0.01 <= wert * BYTE[von] / BYTE[nach] <= 10 ** 7:
            return wert, von, nach


def _umrechnen(rng):
    erste = zweite = _umrechnung(rng)
    while zweite[1:] == erste[1:]:
        zweite = _umrechnung(rng)
    frage = (f"Für die Kapazitätsplanung der {rng.choice(FIRMEN)} müssen Angaben aus Datenblättern verglichen werden.\n\n"
             f"Rechnen Sie um: **{de(erste[0])} {erste[1]}** in {erste[2]} und **{de(zweite[0])} {zweite[1]}** in {zweite[2]} "
             "(zwei Nachkommastellen). Dezimalpräfixe (kB, MB, GB, TB) rechnen mit 1.000, Binärpräfixe (KiB, MiB, GiB, TiB) mit 1.024.")
    felder, weg = [], []
    for i, (wert, von, nach) in enumerate((erste, zweite), start=1):
        byte = wert * BYTE[von]
        felder.append(Feld(f"wert{i}", f"{de(wert)} {von}", byte / BYTE[nach], nach))
        weg.append(f"{de(wert)} {von} = {de(wert)} · {FAKTOR[von]} Byte = {de(byte, 0)} Byte; : {FAKTOR[nach]} "
                   f"= **{de(byte / BYTE[nach])} {nach}**")
    return Aufgabe(frage, felder, schritte(*weg), toleranz=0.005, titel="Einheiten umrechnen")


def _dateien_auf_stick(rng):
    stick = rng.choice([16, 32, 64, 128])
    groesse, einheit = rng.choice([(2.5, "MiB"), (4.5, "MiB"), (1.2, "MiB"), (25, "MiB"), (350, "KiB"), (700, "KiB")])
    kapazitaet = stick * 10 ** 9 / BYTE[einheit]
    anzahl = math.floor(kapazitaet / groesse + 1e-9)
    frage = (f"Ein Kunde der {rng.choice(FIRMEN)} möchte eingescannte Dokumente mit je **{de(groesse)} {einheit}** auf einem "
             f"USB-Stick mit **{stick} GB** weitergeben.\n\nRechnen Sie die Kapazität des Sticks in {einheit} um (zwei "
             "Nachkommastellen) und ermitteln Sie, wie viele Dokumente höchstens darauf passen.")
    weg = schritte(
        f"Kapazität: {stick} GB = {stick} · 10⁹ Byte; : {FAKTOR[einheit]} = **{de(kapazitaet)} {einheit}**",
        f"Anzahl: {de(kapazitaet)} : {de(groesse)} = {de(kapazitaet / groesse)} → abrunden: **{de(anzahl)} Dokumente**",
    )
    felder = [Feld("kapazitaet", "Kapazität", kapazitaet, einheit), Feld("anzahl", "Dokumente", anzahl, stellen=0)]
    return Aufgabe(frage, felder, weg, titel="Dateien auf dem Stick")


# --- Zahlensysteme ---------------------------------------------------------

def _binaer(n: int, stellen: int = 8) -> str:
    return f"{n:0{stellen}b}"


def _gruppiert(bits: str) -> str:
    return " ".join(bits[i:i + 4] for i in range(0, len(bits), 4))


def _stellenwerte(n: int) -> str:
    """Stellenwerttabelle für 8 Bit, darunter die Summe."""
    bits = _binaer(n)
    werte = [128 >> i for i in range(8)]
    summe = " + ".join(str(w) for w, b in zip(werte, bits) if b == "1") or "0"
    return tabelle([str(w) for w in werte], [list(bits)]) + f"\n\n{summe} = **{n}**"


def _nibbles(bits: str) -> str:
    return ", ".join(f"`{bits[i:i + 4]}` = {int(bits[i:i + 4], 2):X}" for i in range(0, len(bits), 4))


@art("zahlensystem", "Zahlensysteme", "Daten & Medien", "Dezimal, binär, hexadezimal und Zweierkomplement",
     ("Zahlensystem", "Binärzahl", "Dualzahl", "Hexadezimal", "Zweierkomplement"), formeln=FORMELN["zahlensystem"])
def zahlensystem(rng):
    return rng.choice([_dez_bin, _bin_dez, _hex_dez, _zweierkomplement])(rng)


def _dez_bin(rng):
    n = rng.randint(20, 255)
    bits = _binaer(n)
    frage = (f"In der Konfiguration eines Switches der {rng.choice(FIRMEN)} ist der Wert **{n}** (dezimal) einzutragen, das Gerät "
             "erwartet ihn aber binär und hexadezimal.\n\nWandeln Sie die Zahl in eine 8-Bit-Binärzahl und in eine Hexadezimalzahl um.")
    weg = (f"Stellenwerte von links nach rechts füllen, solange der Rest reicht:\n\n{_stellenwerte(n)}\n\n"
           f"Binär: **{_gruppiert(bits)}**. Hexadezimal je 4 Bit: {_nibbles(bits)} → **{n:02X}**")
    felder = [Feld("binaer", "Binär (8 Bit)", bits, typ="binaer"), Feld("hex", "Hexadezimal", f"{n:02X}", typ="hex")]
    return Aufgabe(frage, felder, weg, titel="Dezimal → binär und hexadezimal")


def _bin_dez(rng):
    n = rng.randint(20, 255)
    bits = _binaer(n)
    frage = (f"Ein Diagnoseprogramm der {rng.choice(FIRMEN)} zeigt das Statusbyte **{_gruppiert(bits)}** an.\n\n"
             "Geben Sie den Wert dezimal und hexadezimal an.")
    weg = (f"Stellenwerte der gesetzten Bits addieren:\n\n{_stellenwerte(n)}\n\n"
           f"Hexadezimal je 4 Bit: {_nibbles(bits)} → **{n:02X}**")
    felder = [Feld("dezimal", "Dezimal", n, stellen=0), Feld("hex", "Hexadezimal", f"{n:02X}", typ="hex")]
    return Aufgabe(frage, felder, weg, titel="Binär → dezimal und hexadezimal")


def _hex_dez(rng):
    n = rng.randint(4096, 65535)
    ziffern = f"{n:04X}"
    bits = _binaer(n, 16)
    teile = [int(z, 16) * 16 ** (3 - i) for i, z in enumerate(ziffern)]
    frage = (f"In einem Speicherabbild findet die IT der {rng.choice(FIRMEN)} den 16-Bit-Wert **{ziffern}h**.\n\n"
             "Geben Sie den Wert dezimal und als 16-Bit-Binärzahl an.")
    weg = schritte(
        "Dezimal: " + " + ".join(f"{int(z, 16)} · 16{hoch(3 - i)}" for i, z in enumerate(ziffern))
        + " = " + " + ".join(de(t) for t in teile) + f" = **{de(n)}**",
        "Binär: jede Hex-Ziffer wird zu 4 Bit: " + ", ".join(f"{z} = `{int(z, 16):04b}`" for z in ziffern)
        + f" → **{_gruppiert(bits)}**",
    )
    felder = [Feld("dezimal", "Dezimal", n, stellen=0), Feld("binaer", "Binär (16 Bit)", bits, typ="binaer")]
    return Aufgabe(frage, felder, weg, titel="Hexadezimal → dezimal und binär")


def _zweierkomplement(rng):
    a = rng.randint(2, 127)
    muster = _binaer(256 - a)
    b = rng.randint(129, 255)
    frage = (f"Ein Temperatursensor im Serverraum der {rng.choice(FIRMEN)} liefert vorzeichenbehaftete 8-Bit-Werte im "
             f"Zweierkomplement.\n\n1. Wie wird der Wert **−{a}** gespeichert?\n2. Welchen Dezimalwert hat das Byte "
             f"**{_gruppiert(_binaer(b))}**?")
    invertiert_a = _binaer(255 - a)
    invertiert_b = _binaer(255 - b)
    weg = schritte(
        f"+{a} binär: `{_gruppiert(_binaer(a))}` → alle Bits invertieren: `{_gruppiert(invertiert_a)}` → + 1 = **{_gruppiert(muster)}**",
        f"`{_gruppiert(_binaer(b))}`: höchstes Bit ist 1, also negativ. Invertieren: `{_gruppiert(invertiert_b)}` → + 1 = "
        f"`{_gruppiert(_binaer(256 - b))}` = {256 - b} → **−{256 - b}**",
    )
    felder = [Feld("muster", f"−{a} im Zweierkomplement", muster, typ="binaer"),
              Feld("wert", f"{_gruppiert(_binaer(b))} als Dezimalzahl", b - 256, stellen=0)]
    return Aufgabe(frage, felder, weg, titel="Zweierkomplement")
