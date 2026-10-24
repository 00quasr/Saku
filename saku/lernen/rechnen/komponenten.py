"""Strom & Hardware: Monitore und Druck (Pixeldichte, Seitenverhältnis, Maße, dpi) und Bandbreiten von RAM, PCIe und SSDs."""

import math

from saku.lernen.rechnen.basis import BIT_BYTE, FIRMEN, Aufgabe, Feld, art, de, schritte

FORMELN = {
    "monitor": """- Pixel auf der Diagonale: √(Breite² + Höhe²) nach Pythagoras
- Pixeldichte PPI = Pixel auf der Diagonale : Diagonale in Zoll
- Seitenverhältnis: Breite und Höhe durch ihren größten gemeinsamen Teiler (1920 × 1080 → 16 : 9)
- Bildschirmbreite = Diagonale · a : √(a² + b²), Höhe = Diagonale · b : √(a² + b²) bei a : b; 1 Zoll = 2,54 cm
- Druck: Pixel = Länge in Zoll · dpi = Länge in cm : 2,54 · dpi
- *Typische Fehler:* Breite + Höhe statt Pythagoras, Zoll und cm nicht oder falsch herum umgerechnet, die gerundete Handelsbezeichnung (16:9) statt des exakten Verhältnisses

*Beispiel:* 1920 × 1080 auf 24 Zoll: √(1920² + 1080²) ≈ 2.202,9 Pixel : 24 ≈ 91,8 PPI""",
    "bandbreite": """- Arbeitsspeicher: Bandbreite = effektive Transferrate (MT/s) · Busbreite (64 Bit) : 8, je Kanal; mehrere Kanäle multiplizieren
- DDR (Double Data Rate): zwei Transfers je Takt, also effektiv = 2 · realer Takt (DDR4-3200 läuft mit 1.600 MHz)
- PCIe je Lane und Richtung: Transferrate (GT/s) · Leitungscode : 8; bis 2.0 8b/10b, ab 3.0 128b/130b
  (1.0: 0,25 · 2.0: 0,5 · 3.0: 0,985 · 4.0: 1,969 · 5.0: 3,938 GB/s); x4 = vier Lanes
- SATA III: 6 Gbit/s · 8/10 : 8 = 600 MB/s; Übertragungszeit = Datenmenge : Datenrate
- *Typische Fehler:* den realen DDR-Takt nicht verdoppelt (oder DDR4-3200 noch einmal), Bit nicht durch 8 geteilt, Kanäle oder Lanes vergessen, die Leitungscodierung vergessen

*Beispiel:* DDR4-3200 im Dual-Channel: 3.200 MT/s · 64 Bit : 8 = 25.600 MB/s je Kanal, zusammen 51,2 GB/s""",
}


@art("monitor", "Monitor und Druck", "Strom & Hardware", "Pixeldichte, Seitenverhältnis, Bildschirmmaße, Pixel aus dpi",
     ("Peripherie", "Pixeldichte", "Ausgabegerät"), formeln=FORMELN["monitor"])
def monitor(rng):
    return rng.choice([_ppi, _seitenverhaeltnis, _masse, _druck])(rng)


AUFLOESUNGEN = [(1366, 768), (1920, 1080), (1920, 1200), (2560, 1440), (2560, 1600), (3440, 1440), (3840, 2160)]
DIAGONALEN = [13.3, 14, 15.6, 21.5, 24, 27, 32, 34]


def _ppi(rng):
    (b, h), d = rng.choice(AUFLOESUNGEN), rng.choice(DIAGONALEN)
    diagonale = math.hypot(b, h)
    frage = (f"Die {rng.choice(FIRMEN)} vergleicht Monitore. Einer hat **{de(b)} × {de(h)} Pixel** auf **{de(d)} Zoll** Diagonale.\n\n"
             "Wie viele Pixel liegen auf der Diagonale, und wie hoch ist die Pixeldichte in PPI? (eine Nachkommastelle)")
    weg = schritte(f"Pixel auf der Diagonale: √({de(b)}² + {de(h)}²) = √{de(b * b + h * h)} = **{de(diagonale, 1)}**",
                   f"PPI = {de(diagonale, 1)} : {de(d)} Zoll = **{de(diagonale / d, 1)} PPI**")
    pythagoras = "Die Diagonale kommt aus Pythagoras: √(Breite² + Höhe²)."
    felder = [Feld("diagonale", "Pixel auf der Diagonale", diagonale, stellen=1, typisch=((b + h, pythagoras),)),
              Feld("ppi", "Pixeldichte", diagonale / d, "PPI", stellen=1, typisch=((b / d, pythagoras), ((b + h) / d, pythagoras)))]
    return Aufgabe(frage, felder, weg, toleranz=0.002, titel="Pixeldichte")


def _seitenverhaeltnis(rng):
    b, h = rng.choice(AUFLOESUNGEN + [(1280, 1024), (1600, 900), (1680, 1050)])
    t = math.gcd(b, h)
    frage = (f"Im Datenblatt eines Monitors der {rng.choice(FIRMEN)} steht die Auflösung **{de(b)} × {de(h)}**.\n\n"
             "Geben Sie das exakte Seitenverhältnis an (gekürzt wie 8:5 oder gleichwertig wie 16:10) und die Gesamtzahl der Pixel.")
    weg = schritte(f"Größter gemeinsamer Teiler von {b} und {h}: {t}",
                   f"{b} : {t} = {b // t}, {h} : {t} = {h // t} → **{b // t}:{h // t}**"
                   + {(43, 18): " (im Handel als 21:9 bezeichnet, das ist aber gerundet)",
                      (683, 384): " (im Handel als 16:9 bezeichnet, das ist aber gerundet)",
                      (8, 5): " (gleichwertig und üblicher: 16:10)"}.get((b // t, h // t), ""),
                   f"Pixel: {de(b)} · {de(h)} = **{de(b * h)}**")
    gerundet = {(43, 18): "21:9", (683, 384): "16:9"}.get((b // t, h // t))
    felder = [Feld("verhaeltnis", "Seitenverhältnis", f"{b // t}:{h // t}", typ="verhaeltnis",
                   typisch=((gerundet, "Das ist die gerundete Handelsbezeichnung; exakt gekürzt kommt etwas anderes heraus."),) if gerundet else ()),
              Feld("pixel", "Pixel", b * h, stellen=0)]
    return Aufgabe(frage, felder, weg, titel="Seitenverhältnis")


def _masse(rng):
    d, (a, b) = rng.choice([24, 27, 32, 15.6, 34]), rng.choice([(16, 9), (16, 10), (21, 9), (4, 3)])
    wurzel = math.hypot(a, b)
    breite, hoehe = d * a / wurzel * 2.54, d * b / wurzel * 2.54
    frage = (f"Für den Arbeitsplatz der {rng.choice(FIRMEN)} soll ein Monitor mit **{de(d)} Zoll** Diagonale im Format **{a}:{b}** auf "
             "einen Monitorarm. Wie breit und wie hoch ist das sichtbare Bild in cm? (eine Nachkommastelle, 1 Zoll = 2,54 cm)")
    weg = schritte(f"Diagonale im Verhältnis: √({a}² + {b}²) = {de(wurzel, 3)}",
                   f"Breite: {de(d)} · {a} : {de(wurzel, 3)} = {de(d * a / wurzel, 2)} Zoll · 2,54 = **{de(breite, 1)} cm**",
                   f"Höhe: {de(d)} · {b} : {de(wurzel, 3)} = {de(d * b / wurzel, 2)} Zoll · 2,54 = **{de(hoehe, 1)} cm**")
    zoll = "Das sind Zoll; mal 2,54 ergibt cm."
    geteilt = "Du hast durch 2,54 geteilt; von Zoll nach cm wird mit 2,54 multipliziert."
    felder = [Feld("breite", "Breite", breite, "cm", stellen=1, typisch=((breite / 2.54, zoll), (breite / 2.54 ** 2, geteilt))),
              Feld("hoehe", "Höhe", hoehe, "cm", stellen=1, typisch=((hoehe / 2.54, zoll), (hoehe / 2.54 ** 2, geteilt)))]
    return Aufgabe(frage, felder, weg, toleranz=0.003, titel="Breite und Höhe")


def _druck(rng):
    format_, (b_cm, h_cm) = rng.choice([("10 × 15 cm", (10, 15)), ("13 × 18 cm", (13, 18)), ("DIN A4", (21, 29.7)),
                                        ("DIN A5", (14.8, 21)), ("20 × 30 cm", (20, 30))])
    dpi = rng.choice([150, 300, 600])
    b_px, h_px = round(b_cm / 2.54 * dpi), round(h_cm / 2.54 * dpi)
    frage = (f"Die Marketingabteilung der {rng.choice(FIRMEN)} will ein Foto im Format **{format_}** mit **{dpi} dpi** drucken.\n\n"
             "Wie viele Pixel braucht das Bild mindestens in der Breite und in der Höhe? (auf ganze Pixel gerundet, 1 Zoll = 2,54 cm)")
    weg = schritte(f"Breite: {de(b_cm)} cm : 2,54 = {de(b_cm / 2.54, 3)} Zoll · {dpi} dpi = **{de(b_px)} Pixel**",
                   f"Höhe: {de(h_cm)} cm : 2,54 = {de(h_cm / 2.54, 3)} Zoll · {dpi} dpi = **{de(h_px)} Pixel**",
                   f"Zusammen {de(b_px * h_px / 1e6, 1)} Megapixel")
    cm = "Du hast cm wie Zoll genommen; erst durch 2,54 teilen."
    mal = "Du hast mit 2,54 multipliziert; von cm nach Zoll wird durch 2,54 geteilt."
    felder = [Feld("breite", "Breite", b_px, "Pixel", stellen=0, typisch=((b_cm * dpi, cm), (round(b_cm * 2.54 * dpi), mal))),
              Feld("hoehe", "Höhe", h_px, "Pixel", stellen=0, typisch=((h_cm * dpi, cm), (round(h_cm * 2.54 * dpi), mal)))]
    return Aufgabe(frage, felder, weg, toleranz=0.002, titel="Druck: Pixel aus dpi")


# --- Bandbreite -----------------------------------------------------------------

# PCIe je Lane und Richtung (PCI-SIG, Spezifikationen 1.0 bis 5.0): Transferrate in GT/s und Leitungscode;
# 8b/10b bis 2.0 (20 % Verlust), 128b/130b ab 3.0. Datenrate in GB/s = GT/s · Nutzbits/Bits : 8.
PCIE = {1: (2.5, 8 / 10), 2: (5, 8 / 10), 3: (8, 128 / 130), 4: (16, 128 / 130), 5: (32, 128 / 130)}
# SATA III: 6 Gbit/s mit 8b/10b (Serial ATA Revision 3.0) → 600 MB/s
SATA_MB = 6000 * 8 / 10 / 8


def pcie_lane(gen: int) -> float:
    """GB/s je Lane und Richtung."""
    gt, code = PCIE[gen]
    return gt * code / 8


@art("bandbreite", "Bandbreite von Bus und Speicher", "Strom & Hardware", "RAM: Takt × Busbreite, DDR und Kanäle; PCIe-Lanes; SATA gegen NVMe",
     ("PC-Komponent", "Leistungsdaten", "Arbeitsspeicher", "Bussystem", "PCIe"), formeln=FORMELN["bandbreite"])
def bandbreite(rng):
    return rng.choice([_ram, _pcie, _ssd])(rng)


def _ram(rng):
    typ, effektiv = rng.choice([("DDR4", 2400), ("DDR4", 2666), ("DDR4", 3200), ("DDR5", 4800), ("DDR5", 5600), ("DDR5", 6400)])
    kanaele = rng.choice([1, 2, 2, 4])
    je_kanal = effektiv * 64 / 8  # MB/s
    real = effektiv / 2
    angabe_real = rng.random() < 0.5
    angabe = f"mit einem realen Takt von **{de(real)} MHz** (Double Data Rate)" if angabe_real else f"vom Typ **{typ}-{effektiv}**"
    frage = (f"Ein Server der {rng.choice(FIRMEN)} hat Arbeitsspeicher {angabe}, Busbreite 64 Bit je Kanal, betrieben mit "
             f"**{kanaele} {'Kanal' if kanaele == 1 else 'Kanälen'}**.\n\nWie hoch ist die effektive Transferrate (MT/s), die Bandbreite je "
             "Kanal (MB/s) und die gesamte Bandbreite (GB/s, 1 GB = 1.000 MB)?")
    weg = schritte(f"Effektive Transferrate: {'2 · ' + de(real) + ' MHz = ' if angabe_real else typ + '-' + str(effektiv) + ' heißt '}"
                   f"**{de(effektiv)} MT/s** (zwei Transfers je Takt)",
                   f"Je Kanal: {de(effektiv)} MT/s · 64 Bit : 8 = **{de(je_kanal)} MB/s**",
                   f"Gesamt: {kanaele} · {de(je_kanal)} MB/s = {de(kanaele * je_kanal)} MB/s = **{de(kanaele * je_kanal / 1000, 1)} GB/s**")
    if angabe_real:
        ddr = [(real, "DDR überträgt zweimal je Takt: effektiv = 2 · realer Takt.")]
    else:
        ddr = [(2 * effektiv, f"{typ}-{effektiv} nennt schon die effektive Transferrate; nicht noch einmal verdoppeln.")]
    kanal = [(e * 64 / 8, h) for e, h in ddr] + [(je_kanal * 8, BIT_BYTE)]
    felder = [Feld("effektiv", "Effektive Transferrate", effektiv, "MT/s", stellen=0, typisch=tuple(ddr)),
              Feld("kanal", "Je Kanal", je_kanal, "MB/s", stellen=0, typisch=tuple(kanal)),
              Feld("gesamt", "Gesamt", kanaele * je_kanal / 1000, "GB/s", stellen=1, typisch=(
                  (je_kanal / 1000, f"Du hast nur einen Kanal gerechnet; es sind {kanaele}."),
                  *((k * kanaele / 1000, h) for k, h in kanal)))]
    return Aufgabe(frage, felder, weg, toleranz=0.002, titel="Arbeitsspeicher")


def _pcie(rng):
    gen, lanes = rng.choice([2, 3, 4, 5]), rng.choice([4, 8, 16])
    gt, code = PCIE[gen]
    lane = pcie_lane(gen)
    frage = (f"In einen Server der {rng.choice(FIRMEN)} kommt eine Karte in einen **PCIe-{gen}.0-x{lanes}**-Steckplatz. PCIe {gen}.0 überträgt "
             f"je Lane {de(gt)} GT/s mit {'8b/10b' if code == 0.8 else '128b/130b'}-Codierung.\n\nWie hoch ist die Datenrate je Lane und "
             "für den ganzen Steckplatz, jeweils in einer Richtung? (GB/s, drei Nachkommastellen)")
    weg = schritte(f"Nutzanteil der Codierung: {'8 von 10 Bit' if code == 0.8 else '128 von 130 Bit'} = {de(code, 4)}",
                   f"Je Lane: {de(gt)} GT/s · {de(code, 4)} : 8 = **{de(lane, 3)} GB/s**",
                   f"x{lanes}: {lanes} · {de(lane, 3)} GB/s = **{de(lane * lanes, 3)} GB/s** (in jeder Richtung, PCIe ist vollduplex)")
    codierung = f"Du hast die Leitungscodierung vergessen; nur {'8 von 10' if code == 0.8 else '128 von 130'} Bit sind Nutzdaten."
    falsch = [(gt / 8, codierung), (gt * code, BIT_BYTE)]
    felder = [Feld("lane", "Je Lane", lane, "GB/s", stellen=3, typisch=tuple(falsch)),
              Feld("gesamt", f"x{lanes} gesamt", lane * lanes, "GB/s", stellen=3, typisch=(
                  (lane, f"Das ist eine Lane; der Steckplatz hat {lanes}."),
                  (lane * lanes * 2, "Gefragt ist eine Richtung; PCIe überträgt in beiden Richtungen gleichzeitig."),
                  *((w * lanes, h) for w, h in falsch)))]
    return Aufgabe(frage, felder, weg, toleranz=0.002, titel="PCIe-Lanes")


def _ssd(rng):
    groesse, gen = rng.choice([20, 50, 120, 250, 500]), rng.choice([3, 4])
    nvme = pcie_lane(gen) * 4 * 1000  # MB/s, x4 wie bei M.2
    t_sata, t_nvme = groesse * 1000 / SATA_MB, groesse * 1000 / nvme
    frage = (f"Die {rng.choice(FIRMEN)} kopiert eine Datensicherung von **{groesse} GB** (1 GB = 1.000 MB). Rechnen Sie mit dem Maximum der "
             f"Schnittstelle: SATA III (6 Gbit/s, 8b/10b) gegen eine NVMe-SSD an **PCIe {gen}.0 x4**.\n\nWie lange dauert das Lesen jeweils "
             "in Sekunden, und wie viel mal schneller ist NVMe? (eine Nachkommastelle)")
    weg = schritte(f"SATA III: 6.000 Mbit/s · 8/10 : 8 = {de(SATA_MB)} MB/s → {de(groesse * 1000)} MB : {de(SATA_MB)} = **{de(t_sata, 1)} s**",
                   f"NVMe: {de(pcie_lane(gen), 3)} GB/s je Lane · 4 = {de(nvme, 0)} MB/s → {de(groesse * 1000)} MB : {de(nvme, 0)} = "
                   f"**{de(t_nvme, 1)} s**",
                   f"Faktor: {de(t_sata, 1)} : {de(t_nvme, 1)} ≈ **{de(t_sata / t_nvme, 1)}** (echte SSDs liegen darunter, die Schnittstelle "
                   "ist die Obergrenze)")
    felder = [Feld("sata", "SATA III", t_sata, "s", stellen=1,
                   typisch=((groesse * 1000 / 750, "SATA III verliert durch die 8b/10b-Codierung 20 %: 600 MB/s, nicht 750."),)),
              Feld("nvme", f"NVMe PCIe {gen}.0 x4", t_nvme, "s", stellen=1,
                   typisch=((t_nvme * 4, "Das ist eine Lane; die M.2-SSD nutzt vier."),)),
              Feld("faktor", "NVMe ist schneller um den Faktor", t_sata / t_nvme, stellen=1,
                   typisch=((t_nvme / t_sata, "Du hast den Faktor falsch herum gebildet: lange Zeit durch kurze."),))]
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="SATA gegen NVMe")
