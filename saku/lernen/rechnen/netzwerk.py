"""Netzwerk: Subnetting (IPv4), Übertragungszeiten, IPv6, Routing, Standardports und das OSI- und TCP/IP-Modell."""

import ipaddress
import math

from saku.lernen.rechnen.basis import ABTEILUNGEN, BYTE, FAKTOR, FIRMEN, Aufgabe, Feld, art, de, hoch, schritte, tabelle

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "subnetz": """- Präfix /p: p Einsen in der Maske, 32 − p Hostbits
- Hosts je Netz = 2^(32 − p) − 2 (Netz-ID und Broadcast sind nicht nutzbar)
- Maskenwerte im Oktett: 128, 192, 224, 240, 248, 252, 254, 255
- Blockgröße = 256 − Maskenwert im angebrochenen Oktett
- Netz-ID: Oktett auf ein Vielfaches der Blockgröße abrunden, dahinter 0; Broadcast: nächste Netz-ID − 1, dahinter 255
- n gleich große Subnetze: log₂ n Bits leihen → neues Präfix p + log₂ n; k. Subnetz = Netz-ID + (k − 1) · Blockgröße

*Beispiel:* 192.168.1.77/26 → Maske 255.255.255.192, Block 256 − 192 = 64, Netz-ID 192.168.1.64, Broadcast 192.168.1.127, 2⁶ − 2 = 62 Hosts""",
    "uebertragung": """- Dauer = Datenmenge in Bit : Datenrate in Bit/s
- 1 Byte = 8 Bit; Datenraten sind dezimal: 1 Mbit/s = 10⁶ Bit/s, 1 Gbit/s = 1.000 Mbit/s
- Dateigrößen in MiB oder GiB erst in Byte umrechnen (· 1.024² bzw. · 1.024³)
- Overhead p %: nutzbare Datenrate = Datenrate · (1 − p : 100)
- Nötige Datenrate = Datenmenge : Zeit, mit Overhead geteilt durch (1 − p : 100)

*Beispiel:* 650 MB über 25 Mbit/s: 650 · 8 = 5.200 Mbit; 5.200 : 25 = 208 s ≈ 3,47 min""",
    "ipv6": """- 128 Bit in 8 Blöcken zu je 4 Hexadezimalziffern (16 Bit)
- Kürzen: führende Nullen je Block weglassen; die längste Folge von Nullblöcken (bei Gleichstand die erste) einmal durch `::` ersetzen
- Ausschreiben: `::` steht für so viele Nullblöcke, dass es 8 Blöcke werden; jeden Block auf 4 Ziffern auffüllen
- Anzahl /64-Netze in einem Präfix /p = 2^(64 − p)

*Beispiel:* `2001:0db8:0000:0000:0000:00ff:0000:0001` → `2001:db8::ff:0:1`; ein /48 enthält 2¹⁶ = 65.536 /64-Netze""",
    "vlsm": """- VLSM: Subnetze unterschiedlicher Größe aus einem Netz, die größte zuerst, lückenlos ab dem Netzanfang
- Blockgröße je Abteilung: kleinste Zweierpotenz ≥ Hosts + 2 (Netz-ID und Broadcast), Präfix = 32 − log₂ Blockgröße
- Das nächste Subnetz beginnt direkt nach dem Broadcast des vorigen; so liegt jedes Netz auf einer Grenze seiner Größe
- Broadcast = Netz-ID + Blockgröße − 1

*Beispiel:* 192.168.10.0/24, Vertrieb 50 Hosts → 64er-Block /26: .0 bis .63; Lager 20 Hosts → 32er-Block /27: .64 bis .95""",
    "routing": """- Ein Eintrag passt, wenn die ersten p Bit (Präfix) der Zieladresse mit der Netzadresse übereinstimmen
- Passen mehrere, gewinnt der längste Präfix (Longest Prefix Match), egal in welcher Reihenfolge die Einträge stehen
- 0.0.0.0/0 (Default-Route) passt immer und greift nur, wenn sonst nichts passt
- Prüfen im angebrochenen Oktett: Zielwert auf ein Vielfaches der Blockgröße abrunden und mit der Netzadresse vergleichen

*Beispiel:* Ziel 10.20.30.200, Einträge 10.20.0.0/16 und 10.20.30.128/25: 200 liegt im Block 128 bis 255 → /25 gewinnt""",
    "eui64": """- Modifiziertes EUI-64: MAC-Adresse (48 Bit) in der Mitte teilen, FF:FE einfügen → 64 Bit Interface-ID
- Im ersten Byte das 7. Bit von links (Universal/Local, Wert 2) umdrehen: 00 → 02, 02 → 00, 0C → 0E
- Adresse = /64-Präfix + Interface-ID; Link-Local: fe80::/64 + Interface-ID
- Zum Schluss kürzen: führende Nullen je Block weg, die längste Nullfolge einmal durch :: ersetzen

*Beispiel:* MAC 00:1A:2B:3C:4D:5E → 02:1A:2B:FF:FE:3C:4D:5E → Interface-ID 21a:2bff:fe3c:4d5e, Link-Local fe80::21a:2bff:fe3c:4d5e"""
}


# private Bereiche (RFC 1918): Start, Präfix
PRIVAT = [(0x0A000000, 8), (0xAC100000, 12), (0xC0A80000, 16)]


def _ip(x: int) -> str:
    return str(ipaddress.IPv4Address(x))


def _maske(p: int) -> int:
    return (0xFFFFFFFF << (32 - p)) & 0xFFFFFFFF


def _bits(x: int) -> str:
    b = f"{x:032b}"
    return ".".join(b[i:i + 8] for i in range(0, 32, 8))


def _netz(rng, p: int) -> int:
    """Netz-ID eines zufälligen privaten Netzes mit Präfix p."""
    start, bereich = rng.choice([b for b in PRIVAT if b[1] <= p])
    return (start + rng.randrange(2 ** (32 - bereich))) & _maske(p)


def _oktett(x: int, i: int) -> int:
    return (x >> (24 - 8 * i)) & 0xFF


def _maske_erklaert(p: int) -> str:
    """„/21 → 8 + 8 + 5 Einsen → 255.255.248.0“ mit dem angebrochenen Oktett als Summe der Stellenwerte."""
    voll, rest = divmod(p, 8)
    teile = ["8"] * voll + ([str(rest)] if rest else [])
    zeile = f"/{p} = {' + '.join(teile)} Einsen → `{_bits(_maske(p))}` = **{_ip(_maske(p))}**"
    if rest:
        werte = [128 >> i for i in range(rest)]
        zeile += f" (im {voll + 1}. Oktett: {' + '.join(map(str, werte))} = {sum(werte)})"
    return zeile


@art("subnetz", "Subnetting", "Netzwerk", "IPv4: Netz-ID, Broadcast, Hosts, Maske ↔ Präfix, Netze teilen",
     ("Subnet", "IPv4", "IP-Adressierung", "IP-Konfiguration", "Netzmaske", "CIDR"),
     formeln=FORMELN["subnetz"])
def subnetz(rng):
    return rng.choice([_host_infos, _maske_praefix, _teilen, _mindest_hosts])(rng)


def _host_infos(rng):
    p = rng.choice([p for p in range(17, 31) if p % 8])  # bei /24 oder /16 gäbe es nichts zu rechnen
    netz = _netz(rng, p)
    ip = netz + rng.randrange(1, 2 ** (32 - p) - 1)
    broadcast = netz | (~_maske(p) & 0xFFFFFFFF)
    i = (p - 1) // 8  # das Oktett, in dem die Maske endet
    block = 256 - _oktett(_maske(p), i)
    wert = _oktett(ip, i)
    hostbits = 32 - p
    hinten = "" if i == 3 else ", dahinter alles 0"
    weg = [
        _maske_erklaert(p),
        f"Blockgröße im {i + 1}. Oktett: 256 − {_oktett(_maske(p), i)} = **{block}**",
        f"Netz-ID: {wert} : {block} = {wert // block} Rest {wert % block} → {wert // block} · {block} = {wert // block * block}"
        f"{hinten} → **{_ip(netz)}**",
        f"Broadcast: {wert // block * block} + {block} − 1 = {wert // block * block + block - 1}"
        f"{'' if i == 3 else ', dahinter alles 255'} → **{_ip(broadcast)}**",
        f"Erster Host = Netz-ID + 1 → **{_ip(netz + 1)}**, letzter Host = Broadcast − 1 → **{_ip(broadcast - 1)}**",
        f"Hosts: 32 − {p} = {hostbits} Hostbits → 2{hoch(hostbits)} − 2 = **{de(2 ** hostbits - 2)}** "
        "(Netz-ID und Broadcast sind nicht nutzbar)",
    ]
    firma, abteilung = rng.choice(FIRMEN), rng.choice(ABTEILUNGEN)
    if rng.random() < 0.5:
        frage = (f"Die {firma} richtet in der Abteilung {abteilung} einen neuen Client ein. Er erhält die IP-Adresse "
                 f"`{_ip(ip)}/{p}`.\n\nErmitteln Sie die Subnetzmaske, die Netz-ID, die Broadcast-Adresse und die Anzahl "
                 "der nutzbaren Host-Adressen in diesem Netz.")
        felder = [Feld("maske", "Subnetzmaske", _ip(_maske(p)), typ="ip"), Feld("netz", "Netz-ID", _ip(netz), typ="ip"),
                  Feld("broadcast", "Broadcast-Adresse", _ip(broadcast), typ="ip"),
                  Feld("hosts", "Nutzbare Hosts", 2 ** hostbits - 2, stellen=0)]
        return Aufgabe(frage, felder, schritte(*weg), titel="Netz-ID und Broadcast")
    frage = (f"Ein Drucker der {firma} ({abteilung}) ist so konfiguriert:\n\n"
             f"- IP-Adresse: `{_ip(ip)}`\n- Subnetzmaske: `{_ip(_maske(p))}`\n\n"
             "Geben Sie die Präfixlänge, die Netz-ID sowie die erste und die letzte nutzbare Host-Adresse des Netzes an.")
    felder = [Feld("praefix", "Präfixlänge", p, einheit="Bit", stellen=0), Feld("netz", "Netz-ID", _ip(netz), typ="ip"),
              Feld("erster", "Erster Host", _ip(netz + 1), typ="ip"), Feld("letzter", "Letzter Host", _ip(broadcast - 1), typ="ip")]
    weg[0] = f"Maske binär: `{_bits(_maske(p))}` → {p} Einsen → **/{p}**"
    return Aufgabe(frage, felder, schritte(*weg[:5]), titel="Erster und letzter Host")


def _maske_praefix(rng):
    p = rng.randint(8, 30)
    hostbits = 32 - p
    hosts = Feld("hosts", "Nutzbare Hosts", 2 ** hostbits - 2, stellen=0)
    host_weg = f"Hosts: 32 − {p} = {hostbits} Hostbits → 2{hoch(hostbits)} − 2 = **{de(2 ** hostbits - 2)}**"
    if rng.random() < 0.5:
        frage = (f"In der Netzwerkdokumentation der {rng.choice(FIRMEN)} ist ein Netz mit dem Präfix `/{p}` angegeben.\n\n"
                 "Geben Sie die Subnetzmaske in Punktschreibweise an und berechnen Sie die Anzahl der nutzbaren Host-Adressen.")
        return Aufgabe(frage, [Feld("maske", "Subnetzmaske", _ip(_maske(p)), typ="ip"), hosts],
                       schritte(_maske_erklaert(p), host_weg), titel="Präfix → Maske")
    maske = _ip(_maske(p))
    einsen = [f"{o} = {bin(o).count('1')}" for o in map(int, maske.split(".")) if o]
    frage = (f"Im Datenblatt eines Routers der {rng.choice(FIRMEN)} steht die Subnetzmaske `{maske}`.\n\n"
             "Geben Sie die Maske in CIDR-Schreibweise (Präfixlänge) an und berechnen Sie die Anzahl der nutzbaren Host-Adressen.")
    weg = [f"Binär: `{_bits(_maske(p))}`", f"Einsen je Oktett: {', '.join(einsen)} → zusammen **/{p}**", host_weg]
    return Aufgabe(frage, [Feld("praefix", "Präfixlänge", p, einheit="Bit", stellen=0), hosts], schritte(*weg),
                   titel="Maske → Präfix")


def _teilen(rng):
    p0 = rng.randint(16, 26)
    bits = rng.randint(1, min(6, 30 - p0))
    n, p = 2 ** bits, p0 + bits
    netz = _netz(rng, p0)
    block = 2 ** (32 - p)
    k = rng.randint(2, min(n, 8))
    zeilen = [[i, _ip(netz + (i - 1) * block), _ip(netz + i * block - 1)] for i in range(1, k + 1)]
    frage = (f"Die {rng.choice(FIRMEN)} verwendet das Netz `{_ip(netz)}/{p0}`. Es soll in **{n} gleich große Subnetze** "
             f"aufgeteilt werden, eines je Abteilung.\n\nErmitteln Sie das neue Präfix, die Anzahl der nutzbaren Hosts je Subnetz "
             f"sowie Netz-ID und Broadcast-Adresse des **{k}. Subnetzes**.")
    felder = [Feld("praefix", "Neues Präfix", p, einheit="Bit", stellen=0),
              Feld("hosts", "Hosts je Subnetz", block - 2, stellen=0),
              Feld("netz", f"Netz-ID des {k}. Subnetzes", zeilen[-1][1], typ="ip"),
              Feld("broadcast", f"Broadcast des {k}. Subnetzes", zeilen[-1][2], typ="ip")]
    weg = schritte(
        f"{n} Subnetze = 2{hoch(bits)} → {bits} Bit vom Hostanteil leihen → /{p0} + {bits} = **/{p}**",
        f"Hostbits: 32 − {p} = {32 - p} → 2{hoch(32 - p)} − 2 = **{de(block - 2)}** Hosts je Subnetz",
        f"Blockgröße: 2{hoch(32 - p)} = {de(block)} Adressen; das k. Subnetz beginnt bei Netz-ID + (k − 1) · {de(block)}",
    )
    return Aufgabe(frage, felder, weg + "\n\n" + tabelle(["Subnetz", "Netz-ID", "Broadcast"], zeilen), titel="Netz teilen")


def _mindest_hosts(rng):
    while True:
        p0 = rng.randint(16, 24)
        bedarf = rng.choice([10, 12, 20, 25, 28, 30, 40, 50, 55, 60, 100, 120, 200, 250, 300, 500, 1000])
        hostbits = math.ceil(math.log2(bedarf + 2))
        p = 32 - hostbits
        if p0 < p <= 30:
            break
    netz = _netz(rng, p0)
    frage = (f"Die {rng.choice(FIRMEN)} hat das Netz `{_ip(netz)}/{p0}`. Es soll in gleich große Subnetze aufgeteilt werden, "
             f"von denen jedes **mindestens {bedarf} Hosts** aufnehmen kann. Die Subnetze sollen so klein wie möglich sein.\n\n"
             "Ermitteln Sie das Präfix der Subnetze, die Anzahl der nutzbaren Hosts je Subnetz und die Anzahl der Subnetze.")
    felder = [Feld("praefix", "Präfix der Subnetze", p, einheit="Bit", stellen=0),
              Feld("hosts", "Hosts je Subnetz", 2 ** hostbits - 2, stellen=0),
              Feld("anzahl", "Anzahl Subnetze", 2 ** (p - p0), stellen=0)]
    kleiner = f"2{hoch(hostbits - 1)} − 2 = {de(2 ** (hostbits - 1) - 2)} reicht nicht, " if hostbits > 2 else ""
    weg = schritte(
        f"Kleinste Hostbit-Zahl b mit 2ᵇ − 2 ≥ {bedarf}: {kleiner}2{hoch(hostbits)} − 2 = {de(2 ** hostbits - 2)} reicht → b = {hostbits}",
        f"Präfix: 32 − {hostbits} = **/{p}**, also **{de(2 ** hostbits - 2)}** Hosts je Subnetz",
        f"Geliehene Bits: {p} − {p0} = {p - p0} → 2{hoch(p - p0)} = **{de(2 ** (p - p0))}** Subnetze",
    )
    return Aufgabe(frage, felder, weg, titel="Subnetze nach Hostbedarf")


# --- Übertragungszeit -------------------------------------------------------

DATEIEN = {
    "ein ISO-Abbild": [(4.7, "GB"), (8.5, "GB"), (650, "MB"), (700, "MiB"), (4.4, "GiB")],
    "eine Datensicherung": [(120, "GB"), (250, "GB"), (500, "GiB"), (1.5, "TB"), (2, "TB"), (80, "GiB")],
    "ein Schulungsvideo": [(700, "MiB"), (850, "MB"), (1.2, "GB"), (2.4, "GiB")],
    "ein Software-Update": [(80, "MB"), (350, "MiB"), (512, "MB"), (1.8, "GB")],
}
RATEN = [16, 25, 40, 50, 100, 250, 500, 1000]


def _datei(rng) -> tuple[str, float, str]:
    name = rng.choice(list(DATEIEN))
    return name, *rng.choice(DATEIEN[name])


def _rate(r: float) -> str:
    return f"{de(r / 1000)} Gbit/s" if r >= 1000 else f"{de(r)} Mbit/s"


@art("uebertragung", "Übertragungszeit", "Netzwerk", "Datenmenge und Datenrate: Bit vs. Byte, MB vs. MiB, Overhead",
     ("Übertragungszeit", "Übertragungsdauer", "Downloadzeit", "Backupdauer", "Restoredauer"), formeln=FORMELN["uebertragung"])
def uebertragung(rng):
    return rng.choice([_dauer, _noetige_rate, _menge_in_zeit])(rng)


def _overhead(rng) -> int:
    return rng.choice([0, 0, 5, 8, 10, 12, 15, 20])


def _dauer(rng):
    while True:  # nicht wochenlang: 2 TB über 16 Mbit/s rechnet niemand
        name, wert, einheit = _datei(rng)
        rate, overhead = rng.choice(RATEN), _overhead(rng)
        byte = wert * BYTE[einheit]
        mbit = byte * 8 / 10 ** 6
        netto = rate * (1 - overhead / 100)
        sekunden = mbit / netto
        if 10 <= sekunden <= 48 * 3600:
            break
    satz = f" Durch Protokoll-Overhead stehen nur **{100 - overhead} %** der Datenrate für Nutzdaten zur Verfügung." if overhead else ""
    frage = (f"Die {rng.choice(FIRMEN)} überträgt {name} mit **{de(wert)} {einheit}** über eine Leitung mit "
             f"**{_rate(rate)}**.{satz}\n\nBerechnen Sie die Datenmenge in Mbit und die Übertragungsdauer in Sekunden und in "
             "Minuten. Runden Sie auf zwei Nachkommastellen. (1 Mbit = 10⁶ Bit)")
    felder = [Feld("mbit", "Datenmenge", mbit, "Mbit"), Feld("sekunden", "Dauer", sekunden, "s"),
              Feld("minuten", "Dauer", sekunden / 60, "min")]
    weg = [f"In Byte: {de(wert)} {einheit} = {de(wert)} · {FAKTOR[einheit]} Byte = {de(byte, 0)} Byte",
           f"In Bit: · 8 = {de(byte * 8, 0)} Bit = **{de(mbit)} Mbit**"]
    if rate >= 1000:
        weg.append(f"Datenrate: {_rate(rate)} = {de(rate)} Mbit/s")
    if overhead:
        weg.append(f"Nutzbare Datenrate: {de(rate)} Mbit/s · {de((100 - overhead) / 100)} = {de(netto)} Mbit/s")
    weg += [f"Dauer = Datenmenge : Datenrate = {de(mbit)} Mbit : {de(netto)} Mbit/s = **{de(sekunden)} s**",
            f"In Minuten: {de(sekunden)} s : 60 = **{de(sekunden / 60)} min**"]
    return Aufgabe(frage, felder, schritte(*weg), toleranz=0.005, titel="Übertragungsdauer")


def _noetige_rate(rng):
    while True:
        name, wert, einheit = _datei(rng)
        minuten, overhead = rng.choice([10, 15, 30, 45, 60, 90, 120, 180, 240]), _overhead(rng)
        mbit = wert * BYTE[einheit] * 8 / 10 ** 6
        netto = mbit / (minuten * 60)
        brutto = netto / (1 - overhead / 100)
        if 1 <= brutto <= 1000:  # mehr als 1 Gbit/s hat kaum eine Firma
            break
    zeit = f"{minuten} Minuten" if minuten < 60 else "1 Stunde" if minuten == 60 else f"{de(minuten / 60)} Stunden"
    satz = f" Planen Sie ein, dass **{overhead} %** der Datenrate für Protokoll-Overhead verloren gehen." if overhead else ""
    frage = (f"Die {rng.choice(FIRMEN)} will {name} mit **{de(wert)} {einheit}** in höchstens **{zeit}** übertragen.{satz}\n\n"
             "Berechnen Sie die Datenmenge in Mbit und die mindestens nötige Datenrate der Leitung in Mbit/s (zwei Nachkommastellen).")
    felder = [Feld("mbit", "Datenmenge", mbit, "Mbit"), Feld("rate", "Nötige Datenrate", brutto, "Mbit/s")]
    weg = [f"Datenmenge: {de(wert)} · {FAKTOR[einheit]} Byte · 8 = **{de(mbit)} Mbit**",
           f"Zeit: {zeit} = {de(minuten * 60)} s",
           f"Nutzdatenrate = {de(mbit)} Mbit : {de(minuten * 60)} s = **{de(netto)} Mbit/s**"]
    if overhead:
        weg.append(f"Mit Overhead: nur {100 - overhead} % kommen an → {de(netto)} : {de((100 - overhead) / 100)} = **{de(brutto)} Mbit/s**")
    return Aufgabe(frage, felder, schritte(*weg), toleranz=0.005, titel="Nötige Datenrate")


def _menge_in_zeit(rng):
    rate, minuten = rng.choice(RATEN), rng.choice([5, 10, 15, 20, 30, 45, 60, 90, 120])
    byte = rate * 10 ** 6 * minuten * 60 / 8
    frage = (f"Ein Server der {rng.choice(FIRMEN)} ist mit **{_rate(rate)}** angebunden. Die Leitung wird **{minuten} Minuten** "
             "lang voll ausgelastet.\n\nWie viele Daten werden in dieser Zeit übertragen? Geben Sie das Ergebnis in GB und in GiB an "
             "(zwei Nachkommastellen).")
    felder = [Feld("gb", "Datenmenge", byte / 10 ** 9, "GB"), Feld("gib", "Datenmenge", byte / 2 ** 30, "GiB")]
    weg = schritte(
        f"Zeit: {minuten} min = {de(minuten * 60)} s",
        f"Bit: {de(rate)} · 10⁶ Bit/s · {de(minuten * 60)} s = {de(rate * 10 ** 6 * minuten * 60, 0)} Bit",
        f"Byte: : 8 = {de(byte, 0)} Byte",
        f"GB: : 10⁹ = **{de(byte / 10 ** 9)} GB**",
        f"GiB: : 1.024³ = : {de(2 ** 30)} = **{de(byte / 2 ** 30)} GiB**",
    )
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="Datenmenge in einer Zeit")


# --- IPv6 -------------------------------------------------------------------

def _ipv6(rng) -> ipaddress.IPv6Address:
    """2001:db8::/32 (Dokumentation) mit Nullblöcken, mindestens einer Folge aus zwei oder mehr."""
    while True:
        bloecke = [0x2001, 0x0DB8] + [0 if rng.random() < 0.45 else rng.choice([rng.randrange(1, 16), rng.randrange(16, 256),
                                     rng.randrange(256, 4096), rng.randrange(4096, 65536)]) for _ in range(6)]
        if any(bloecke[i] == bloecke[i + 1] == 0 for i in range(2, 7)) and any(bloecke[2:]):
            return ipaddress.IPv6Address(":".join(f"{b:04x}" for b in bloecke))


@art("ipv6", "IPv6", "Netzwerk", "Adressen kürzen und ausschreiben, /64-Netze in einem Präfix zählen", ("IPv6",), formeln=FORMELN["ipv6"])
def ipv6(rng):
    return rng.choice([_kuerzen, _ausschreiben, _netze])(rng)


def _ohne_nullen(adresse: ipaddress.IPv6Address) -> str:
    return ":".join(f"{int(b, 16):x}" for b in adresse.exploded.split(":"))


def _kuerzen(rng):
    adresse = _ipv6(rng)
    frage = (f"Ein Server der {rng.choice(FIRMEN)} hat die IPv6-Adresse\n\n`{adresse.exploded}`\n\n"
             "Geben Sie die Adresse in der kürzest möglichen Schreibweise an.")
    weg = schritte(f"Führende Nullen in jedem Block weglassen: `{_ohne_nullen(adresse)}`",
                   "Die längste Folge von Nullblöcken (bei Gleichstand die erste) einmal durch `::` ersetzen; "
                   "ein einzelner Nullblock bleibt `0`",
                   f"Ergebnis: **`{adresse.compressed}`**")
    return Aufgabe(frage, [Feld("kurz", "Kurzform", adresse.compressed, typ="text")], weg, titel="Adresse kürzen")


def _ausschreiben(rng):
    adresse = _ipv6(rng)
    fehlend = 8 - len([b for b in adresse.compressed.split(":") if b])
    frage = (f"In einer Firewall-Regel der {rng.choice(FIRMEN)} steht die Adresse `{adresse.compressed}`.\n\n"
             "Schreiben Sie die Adresse vollständig aus (8 Blöcke mit je 4 Hexadezimalziffern).")
    weg = schritte(f"`::` steht für die fehlenden Blöcke: 8 − {8 - fehlend} vorhandene = {fehlend} Nullblöcke",
                   "Jeden Block mit führenden Nullen auf 4 Ziffern auffüllen",
                   f"Ergebnis: **`{adresse.exploded}`**")
    return Aufgabe(frage, [Feld("lang", "Vollständige Adresse", adresse.exploded, typ="text")], weg, titel="Adresse ausschreiben")


def _netze(rng):
    p = rng.choice([32, 40, 44, 48, 52, 56, 60])
    netz = ipaddress.IPv6Network((int(_ipv6(rng)) >> (128 - p) << (128 - p), p))
    bits = 64 - p
    frage = (f"Der Provider weist der {rng.choice(FIRMEN)} das Präfix `{netz}` zu. Intern sollen ausschließlich /64-Netze "
             "verwendet werden.\n\nWie viele Bits stehen für die Subnetz-ID zur Verfügung, und wie viele /64-Netze lassen sich bilden?")
    felder = [Feld("bits", "Bits für Subnetze", bits, "Bit", stellen=0), Feld("anzahl", "Anzahl /64-Netze", 2 ** bits, stellen=0)]
    weg = schritte(f"Subnetz-ID: 64 − {p} = **{bits} Bit**", f"Anzahl: 2{hoch(bits)} = **{de(2 ** bits)}** Netze")
    return Aufgabe(frage, felder, weg, titel="/64-Netze zählen")


# --- VLSM -----------------------------------------------------------------------------

ABTEILUNGS_NAMEN = ["Vertrieb", "Entwicklung", "Lager", "Verwaltung", "Support", "Marketing", "Produktion", "Gäste-WLAN", "Server"]


@art("vlsm", "VLSM", "Netzwerk", "Ein Netz nach Hostbedarf aufteilen: größte zuerst, lückenlos, je Abteilung Netz-ID, Präfix, Broadcast",
     ("VLSM", "IP-Adresskonzept", "Adressplan"), formeln=FORMELN["vlsm"])
def vlsm(rng):
    while True:
        p0 = rng.choice([22, 23, 24])
        anzahl = rng.randint(3, 5)
        bits = rng.sample(range(3, 32 - p0), min(anzahl, 32 - p0 - 3))  # verschiedene Blockgrößen: „größte zuerst“ ist eindeutig
        bloecke = sorted((2 ** b for b in bits), reverse=True)
        if len(bloecke) >= 3 and sum(bloecke) <= 2 ** (32 - p0):
            break
    netz = _netz(rng, p0)
    namen = rng.sample(ABTEILUNGS_NAMEN, len(bloecke))
    # Hostbedarf: passt in den Block, aber nicht in den nächstkleineren
    bedarf = {n: rng.randint(b // 2 - 1, b - 2) for n, b in zip(namen, bloecke)}
    start, plan = netz, {}
    for n, b in zip(namen, bloecke):
        plan[n] = (start, 32 - b.bit_length() + 1, start + b - 1, b)
        start += b
    reihenfolge = rng.sample(namen, len(namen))  # in der Frage gemischt; die Sortierung gehört zur Aufgabe
    frage = (f"Die {rng.choice(FIRMEN)} hat das Netz `{_ip(netz)}/{p0}` und teilt es mit VLSM auf die Abteilungen auf:\n\n"
             + "\n".join(f"- {n}: {bedarf[n]} Hosts" for n in reihenfolge)
             + "\n\nVergeben Sie die Subnetze nach Größe, das größte zuerst, lückenlos ab dem Netzanfang, jeweils so klein wie möglich. "
             "Tragen Sie je Abteilung Netz-ID, Präfix und Broadcast-Adresse ein.")
    zellen = [[Feld(f"{i}_netz", f"{n}: Netz-ID", _ip(plan[n][0]), typ="ip"), Feld(f"{i}_praefix", f"{n}: Präfix", plan[n][1], stellen=0),
               Feld(f"{i}_bc", f"{n}: Broadcast", _ip(plan[n][2]), typ="ip")] for i, n in enumerate(reihenfolge)]
    zeilen = [[n, bedarf[n], f"{bedarf[n]} + 2 → {b} = 2{hoch(b.bit_length() - 1)}", f"/{p}", _ip(s), _ip(e)]
              for n, (s, p, e, b) in sorted(plan.items(), key=lambda x: -x[1][3])]
    weg = (schritte("Blockgröße je Abteilung: kleinste Zweierpotenz ≥ Hosts + 2, Präfix = 32 − Hostbits",
                    "Nach Blockgröße sortieren, die größte zuerst, und lückenlos ab der Netz-ID vergeben",
                    "Broadcast = Netz-ID + Blockgröße − 1, das nächste Netz beginnt eine Adresse danach")
           + "\n\n" + tabelle(["Abteilung", "Hosts", "Block", "Präfix", "Netz-ID", "Broadcast"], zeilen)
           + (f"\n\nFrei bleibt ab {_ip(start)} bis {_ip(netz + 2 ** (32 - p0) - 1)}." if start < netz + 2 ** (32 - p0) else ""))
    return Aufgabe(frage, [f for zeile in zellen for f in zeile], weg, titel=f"VLSM aus einem /{p0}",
                   tabelle=[["Abteilung", "Netz-ID", "Präfix", "Broadcast"], *([n, *z] for n, z in zip(reihenfolge, zellen))])


# --- Routing ----------------------------------------------------------------------------

def _praefix_bits(x: int, p: int) -> str:
    """Die ersten p Bit, in Oktetten mit Punkt getrennt."""
    bits = f"{x:032b}"[:p]
    return ".".join(bits[i:i + 8] for i in range(0, len(bits), 8)) or "–"


@art("routing", "Routing-Tabelle", "Netzwerk", "Welcher Eintrag greift? Longest Prefix Match mit überlappenden Präfixen und Default-Route",
     ("Routing", "Router", "Gateway"), formeln=FORMELN["routing"])
def routing(rng):
    while True:
        p1 = rng.choice([8, 12, 16])
        p2 = rng.choice([q for q in (16, 20, 22, 24) if q > p1])
        p3 = rng.choice([q for q in (24, 25, 26, 27, 28) if q > p2])
        n1 = _netz(rng, p1)
        n2 = (n1 + rng.randrange(2 ** (32 - p1))) & _maske(p2)
        n3 = (n2 + rng.randrange(2 ** (32 - p2))) & _maske(p3)
        anders = _netz(rng, rng.choice([16, 24]))
        if not (anders & _maske(p1)) == n1 and n3 != n2:
            break
    eintraege = [(n1, p1), (n2, p2), (n3, p3), (anders, 24 if anders & 0xFF == 0 else 16), (0, 0)]
    eintraege[3] = (anders & _maske(eintraege[3][1]), eintraege[3][1])
    hops = rng.sample(["R1", "R2", "R3", "R4", "R5", "R6"], len(eintraege))
    tabelle_ = list(zip(eintraege, hops))
    rng.shuffle(tabelle_)  # die Reihenfolge der Einträge spielt keine Rolle
    def treffer(ziel):
        return max(((n, p, h) for (n, p), h in tabelle_ if (ziel & _maske(p) if p else 0) == n), key=lambda t: t[1])
    ziele = [n3 + rng.randrange(1, 2 ** (32 - p3) - 1),  # im längsten Präfix
             next(z for z in iter(lambda: n2 + rng.randrange(2 ** (32 - p2)), None) if (z & _maske(p3)) != n3),  # mittlerer
             next(z for z in iter(lambda: rng.choice([0x08080808, 0x01010101, 0xC6336401, 0xCB007105, 0x5DB8D822]) + rng.randrange(200), None)
                  if treffer(z)[1] == 0)]  # nur die Default-Route
    rng.shuffle(ziele)
    def name(n, p):
        return "0.0.0.0/0 (Default)" if p == 0 else f"{_ip(n)}/{p}"
    nach_eintrag = rng.random() < 0.4  # statt des Next Hops: welcher Eintrag greift
    frage = (f"Der Router der {rng.choice(FIRMEN)} hat diese Routing-Tabelle:\n\n"
             + tabelle(["Ziel", "Next Hop"], [[name(n, p), h] for (n, p), h in tabelle_])
             + ("\n\nWelcher Eintrag der Tabelle greift für diese Ziele?" if nach_eintrag else
                "\n\nÜber welchen Next Hop leitet er Pakete an diese Ziele weiter?")
             + "\n\n" + "\n".join(f"- `{_ip(z)}`" for z in ziele))
    weg, felder = [], []
    for i, z in enumerate(ziele):
        n, p, h = treffer(z)
        zeilen = [[f"{_ip(en)}/{ep}" if ep else "0.0.0.0/0", _praefix_bits(en, ep), _praefix_bits(z, ep),
                   "✓" if (z & _maske(ep) if ep else 0) == en else "✕"] for (en, ep), _ in sorted(tabelle_, key=lambda t: -t[0][1])]
        weg.append(f"**{_ip(z)}** = `{_bits(z)}`\n\n" + tabelle(["Eintrag", "Netz-Bits", "Ziel-Bits", "passt"], zeilen)
                   + f"\n\nLängster passender Präfix: /{p} → **{h}**")
        if nach_eintrag:
            felder.append(Feld(f"ziel{i}", f"Eintrag für {_ip(z)}", name(n, p), typ="text",
                               optionen=[name(en, ep) for (en, ep), _ in sorted(tabelle_, key=lambda t: -t[0][1])]))
        else:
            felder.append(Feld(f"ziel{i}", f"Next Hop für {_ip(z)}", h, typ="text", optionen=sorted(hops)))
    return Aufgabe(frage, felder, "\n\n".join(weg), titel="Welcher Eintrag greift?" if nach_eintrag else "Next Hop bestimmen")


# --- EUI-64 -----------------------------------------------------------------------------

def eui64(mac: int) -> int:
    """Modifiziertes EUI-64 (RFC 4291, Anhang A): FFFE in die Mitte, das U/L-Bit (7. Bit des ersten Bytes) umdrehen."""
    return ((mac >> 24) << 40 | 0xFFFE << 24 | (mac & 0xFFFFFF)) ^ (0x02 << 56)


def _mac_text(mac: int, trenner: str) -> str:
    return trenner.join(f"{(mac >> (8 * i)) & 0xFF:02X}" for i in range(5, -1, -1))


@art("eui64", "IPv6 mit EUI-64", "Netzwerk", "Interface-ID aus der MAC-Adresse, globale und Link-Local-Adresse",
     ("EUI-64", "SLAAC", "Autokonfiguration", "Interface-ID"), formeln=FORMELN["eui64"])
def eui_64(rng):
    erstes = rng.choice([0x00, 0x00, 0x02, 0x08, 0x0C, 0x3C, 0xA4, 0xF0])  # Unicast (letztes Bit 0), mal mit gesetztem U/L-Bit
    mac = erstes << 40 | rng.randrange(1 << 40)
    iid = eui64(mac)
    praefix = int(_ipv6(rng)) >> 64 << 64
    netz = ipaddress.IPv6Network((praefix, 64))
    global_ = ipaddress.IPv6Address(praefix | iid)
    link = ipaddress.IPv6Address(0xFE80 << 112 | iid)
    iid_text = ":".join(f"{(iid >> (16 * i)) & 0xFFFF:x}" for i in range(3, -1, -1))
    mitte = _mac_text(mac >> 24, ":")[-8:] + ":FF:FE:" + _mac_text(mac & 0xFFFFFF, ":")[-8:]
    if rng.random() < 0.35:  # rückwärts: aus der Adresse die MAC
        frage = (f"Im Log eines Switches der {rng.choice(FIRMEN)} taucht die Link-Local-Adresse `{link.compressed}` auf. Sie wurde nach "
                 "dem modifizierten EUI-64-Verfahren gebildet.\n\nWelche MAC-Adresse hat das Gerät? (Format AA:BB:CC:DD:EE:FF)")
        weg = schritte(f"Interface-ID ausschreiben: {':'.join(f'{(iid >> (16 * i)) & 0xFFFF:04x}' for i in range(3, -1, -1))}",
                       f"FF:FE in der Mitte entfernen: {_mac_text(iid >> 40 & 0xFFFFFF, ':')[-8:]} | {_mac_text(iid & 0xFFFFFF, ':')[-8:]}",
                       f"Erstes Byte {erstes ^ 2:02X} = `{erstes ^ 2:08b}` → 7. Bit zurückdrehen → `{erstes:08b}` = {erstes:02X}",
                       f"MAC: **{_mac_text(mac, ':')}**")
        return Aufgabe(frage, [Feld("mac", "MAC-Adresse", _mac_text(mac, ":"), typ="pfad")], weg, titel="EUI-64 rückwärts: MAC")
    frage = (f"Ein Client der {rng.choice(FIRMEN)} mit der MAC-Adresse **{_mac_text(mac, rng.choice([':', '-']))}** bildet seine "
             f"IPv6-Adressen per SLAAC nach dem modifizierten EUI-64-Verfahren. Der Router kündigt das Präfix `{netz}` an.\n\n"
             "Geben Sie die Interface-ID, die globale Adresse und die Link-Local-Adresse an (gekürzt).")
    weg = schritte(f"MAC teilen und FF:FE einfügen: {mitte}",
                   f"Erstes Byte {erstes:02X} = `{erstes:08b}` → 7. Bit umdrehen → `{erstes ^ 2:08b}` = {erstes ^ 2:02X}",
                   f"Interface-ID: **{iid_text}**",
                   f"Global: Präfix {':'.join(f'{(praefix >> (16 * (7 - i))) & 0xFFFF:x}' for i in range(4))} + Interface-ID, "
                   f"gekürzt → **{global_.compressed}**",
                   f"Link-Local: fe80:: + Interface-ID → **{link.compressed}**")
    felder = [Feld("iid", "Interface-ID", iid_text, typ="ipv6"), Feld("global", "Globale Adresse", global_.compressed, typ="ipv6"),
              Feld("link", "Link-Local-Adresse", link.compressed, typ="ipv6")]
    return Aufgabe(frage, felder, weg, titel="EUI-64")


# --- Ports und Protokolle ---------------------------------------------------------------

# Kurzname, Port, Transport, von Anfang an verschlüsselt, Name in der Frage, wofür, weitere richtige Namen (IANA-Standardports).
# Transport nur als „TCP“ oder „UDP“ und Verschlüsselung nur als True/False gefragt; ein Text heißt: nicht eindeutig, nur zum Lesen
PORTS = [
    ("FTP", 20, "TCP", False, "FTP-Daten (aktiver Modus)", "Dateiübertragung, Daten", ("FTP-Daten", "FTP-Data")),
    ("FTP", 21, "TCP", False, "FTP-Steuerverbindung", "Dateiübertragung, Befehle", ("FTP-Steuerung", "FTP-Control")),
    ("SSH", 22, "TCP", True, "SSH", "verschlüsselte Fernwartung und Dateiübertragung", ("SFTP", "SCP")),
    ("Telnet", 23, "TCP", False, "Telnet", "unverschlüsselte Fernwartung, veraltet", ()),
    ("SMTP", 25, "TCP", False, "SMTP zwischen Mailservern", "E-Mail-Transport zwischen Mailservern", ()),
    ("DNS", 53, "UDP und TCP", False, "DNS", "Namensauflösung; TCP für Zonentransfers und große Antworten", ()),
    ("DHCP", 67, "UDP", False, "DHCP-Server", "IP-Adressen vergeben, Server", ("BOOTP", "DHCP-Server")),
    ("DHCP", 68, "UDP", False, "DHCP-Client", "IP-Adressen vergeben, Client", ("BOOTP", "DHCP-Client")),
    ("TFTP", 69, "UDP", False, "TFTP", "einfache Dateiübertragung, z. B. PXE-Boot", ()),
    ("HTTP", 80, "TCP", False, "HTTP", "Webseiten", ()),
    ("POP3", 110, "TCP", False, "POP3", "E-Mails abholen", ("POP",)),
    ("NTP", 123, "UDP", False, "NTP", "Uhrzeit synchronisieren", ()),
    ("IMAP", 143, "TCP", False, "IMAP", "E-Mails auf dem Server verwalten", ("IMAP4",)),
    ("SNMP", 161, "UDP", "nur SNMPv3, wenn eingestellt", "SNMP (Abfragen)", "Netzwerkgeräte überwachen", ()),
    ("LDAP", 389, "TCP", False, "LDAP", "Verzeichnisdienst, z. B. Active Directory", ()),
    ("HTTPS", 443, "TCP (HTTP/3: UDP)", True, "HTTPS", "Webseiten über TLS", ("HTTP über TLS",)),
    ("SMB", 445, "TCP", "ab SMB 3 möglich", "SMB", "Datei- und Druckerfreigaben unter Windows", ("CIFS",)),
    ("SMTPS", 465, "TCP", True, "SMTPS (implizites TLS)", "E-Mail einliefern mit implizitem TLS",
     ("Submissions", "SMTP über TLS")),
    ("Syslog", 514, "UDP", False, "Syslog", "Protokollmeldungen an einen Logserver", ()),
    ("SMTP", 587, "TCP", False, "SMTP-Submission (STARTTLS)", "E-Mail vom Mailprogramm einliefern, meist mit STARTTLS",
     ("Submission", "SMTP-Submission")),
    ("LDAPS", 636, "TCP", True, "LDAPS", "Verzeichnisdienst über TLS", ("LDAP über TLS",)),
    ("IMAPS", 993, "TCP", True, "IMAPS", "E-Mails auf dem Server verwalten, über TLS", ("IMAP über TLS",)),
    ("POP3S", 995, "TCP", True, "POP3S", "E-Mails abholen über TLS", ("POP3 über TLS",)),
    ("RDP", 3389, "TCP und UDP", "ja, nach kurzer Aushandlung (meist TLS)", "RDP", "Remotedesktop unter Windows", ()),
]


def _ja_nein(wert) -> str:
    return wert if isinstance(wert, str) else "Ja" if wert else "Nein"


def _port_zeilen(auswahl) -> list[list]:
    return [[port, f"**{kurz}**" + (f" (auch {', '.join(auch)})" if auch else ""), transport, _ja_nein(verschluesselt), wofuer]
            for kurz, port, transport, verschluesselt, _, wofuer, auch in sorted(auswahl, key=lambda p: p[1])]


PORT_KOPF = ["Port", "Protokoll", "Transport", "von Anfang an verschlüsselt", "wofür"]
FORMELN["ports"] = tabelle(PORT_KOPF, _port_zeilen(PORTS)) + """

- Die IANA vergibt die Well-known Ports 0 bis 1.023 und registriert weitere bis 49.151 (z. B. RDP 3389); Server lauschen dort, Clients nehmen einen freien hohen Port
- TCP: verbindungsorientiert und gesichert (Drei-Wege-Handshake, Bestätigungen); UDP: verbindungslos, schnell, ohne Bestätigung
- Von Anfang an verschlüsselt: SSH und die Dienste mit S am Ende (HTTPS, SMTPS, IMAPS, POP3S, LDAPS: implizites TLS)
- STARTTLS (SMTP 25 und 587, IMAP 143, POP3 110, LDAP 389, FTP 21) beginnt unverschlüsselt und schaltet erst danach um: zählt hier als nein

*Beispiel:* Webserver mit HTTPS → TCP 443 freigeben; ein Mailprogramm holt per IMAPS (TCP 993) ab und liefert per SMTP-Submission (TCP 587, STARTTLS) ein"""


@art("ports", "Ports und Protokolle", "Netzwerk", "Standardports nach IANA: Port ↔ Protokoll, TCP oder UDP, von Anfang an verschlüsselt?",
     ("Portnummer", "Port-Nummer", "Well-known", "Firewall", "Netzwerkdienst"), formeln=FORMELN["ports"])
def ports(rng):
    return rng.choice([_port_zu_protokoll, _protokoll_zu_port, _steckbrief])(rng)


def _port_zu_protokoll(rng):
    auswahl = sorted(rng.sample(PORTS, 4), key=lambda p: p[1])
    frage = (f"In den Firewall-Regeln der {rng.choice(FIRMEN)} tauchen diese Ports auf:\n\n" + "\n".join(f"- `{p[1]}`" for p in auswahl)
             + "\n\nWelches Protokoll gehört jeweils zu diesem Standardport? (Kurzname wie HTTP)")
    felder = [Feld(f"p{port}", f"Port {port}", kurz, typ="text", auch=auch) for kurz, port, *_, auch in auswahl]
    return Aufgabe(frage, felder, tabelle(PORT_KOPF, _port_zeilen(auswahl)), titel="Port → Protokoll")


def _protokoll_zu_port(rng):
    auswahl = rng.sample(PORTS, 4)
    frage = (f"Für neue Firewall-Regeln der {rng.choice(FIRMEN)} brauchen Sie die Standardports (nach IANA) dieser Dienste:\n\n"
             + "\n".join(f"- {p[4]}" for p in auswahl) + "\n\nGeben Sie jeweils die Portnummer an.")
    felder = [Feld(f"p{port}", name, port, stellen=0) for _, port, _, _, name, *_ in auswahl]
    return Aufgabe(frage, felder, tabelle(PORT_KOPF, _port_zeilen(auswahl)), titel="Protokoll → Port")


def _steckbrief(rng):
    auswahl = rng.sample([p for p in PORTS if p[2] in ("TCP", "UDP") or isinstance(p[3], bool)], 3)
    frage = (f"Die {rng.choice(FIRMEN)} dokumentiert die Dienste eines neuen Servers: " + ", ".join(p[4] for p in auswahl)
             + ".\n\nErgänzen Sie für jeden Dienst den Standardport, das Transportprotokoll und ob die Verbindung von Anfang an "
             "verschlüsselt ist (STARTTLS zählt nicht).")
    felder = []
    for _, port, transport, verschluesselt, name, *_ in auswahl:
        felder.append(Feld(f"p{port}", f"{name}: Port", port, stellen=0))
        if transport in ("TCP", "UDP"):
            felder.append(Feld(f"t{port}", f"{name}: TCP oder UDP?", transport, typ="text", optionen=["TCP", "UDP"]))
        if isinstance(verschluesselt, bool):
            felder.append(Feld(f"v{port}", f"{name}: verschlüsselt?", _ja_nein(verschluesselt), typ="text",
                               optionen=["Ja", "Nein"]))
    return Aufgabe(frage, felder, tabelle(PORT_KOPF, _port_zeilen(auswahl)), titel="Steckbrief der Dienste")


# --- OSI- und TCP/IP-Modell -------------------------------------------------------------

OSI = ["Bitübertragungsschicht", "Sicherungsschicht", "Vermittlungsschicht", "Transportschicht", "Sitzungsschicht", "Darstellungsschicht",
       "Anwendungsschicht"]
TCP_IP = ["Netzzugangsschicht", "Internetschicht", "Transportschicht", "Anwendungsschicht"]
ZU_TCP_IP = {1: 0, 2: 0, 3: 1, 4: 2, 5: 3, 6: 3, 7: 3}
# Begriff, OSI-Schicht, warum; nur eindeutige Zuordnungen (kein ARP, kein TLS, keine Firewall, kein Access Point)
ELEMENTE = [
    ("Hub", 1, "verteilt Signale an alle Anschlüsse, ohne Adressen auszuwerten"), ("Repeater", 1, "verstärkt und erneuert das Signal"),
    ("Twisted-Pair-Kabel", 1, "Übertragungsmedium"), ("Glasfaserkabel", 1, "Übertragungsmedium"),
    ("Bit", 1, "Dateneinheit der Bitübertragungsschicht"),
    ("Switch", 2, "leitet Frames anhand der MAC-Adresse weiter"), ("Bridge", 2, "verbindet Netzsegmente anhand der MAC-Adressen"),
    ("MAC-Adresse", 2, "physische Adresse der Netzwerkkarte"), ("Frame (Rahmen)", 2, "Dateneinheit der Sicherungsschicht"),
    ("PPP", 2, "Protokoll für Punkt-zu-Punkt-Verbindungen"),
    ("Router", 3, "leitet Pakete anhand der IP-Adresse zwischen Netzen weiter"), ("IP", 3, "logische Adressierung und Wegewahl"),
    ("ICMP", 3, "Fehler- und Diagnosemeldungen zu IP, z. B. ping"), ("IP-Adresse", 3, "logische Adresse eines Hosts"),
    ("Paket", 3, "Dateneinheit der Vermittlungsschicht"),
    ("TCP", 4, "verbindungsorientierter Transport zwischen Ports"), ("UDP", 4, "verbindungsloser Transport zwischen Ports"),
    ("Portnummer", 4, "adressiert den Dienst auf dem Host"), ("Segment", 4, "Dateneinheit von TCP"),
    ("HTTP", 7, "Anwendungsprotokoll für Webseiten"), ("DNS", 7, "Anwendungsprotokoll für die Namensauflösung"),
    ("SMTP", 7, "Anwendungsprotokoll für den E-Mail-Versand"), ("FTP", 7, "Anwendungsprotokoll für Dateiübertragung"),
    ("DHCP", 7, "Anwendungsprotokoll für die Adressvergabe (über UDP)"),
]
FORMELN["osi"] = tabelle(["Nr.", "OSI-Schicht", "englisch", "TCP/IP-Modell", "Beispiele", "Dateneinheit"], [
    [7, "Anwendungsschicht", "Application", "Anwendung", "HTTP, DNS, SMTP, FTP, DHCP", "Daten"],
    [6, "Darstellungsschicht", "Presentation", "Anwendung", "Kodierung, Kompression", "Daten"],
    [5, "Sitzungsschicht", "Session", "Anwendung", "Sitzungen auf- und abbauen", "Daten"],
    [4, "Transportschicht", "Transport", "Transport", "TCP, UDP, Portnummern", "Segment"],
    [3, "Vermittlungsschicht", "Network", "Internet", "IP, ICMP, IP-Adressen, Router", "Paket"],
    [2, "Sicherungsschicht", "Data Link", "Netzzugang", "MAC-Adressen, Switch, Bridge, PPP", "Frame (Rahmen)"],
    [1, "Bitübertragungsschicht", "Physical", "Netzzugang", "Kabel, Stecker, Hub, Repeater", "Bit"],
]) + """

- Merksatz von 7 nach 1: **A**lle **d**eutschen **S**tudenten **t**rinken **v**erschiedene **S**orten **B**ier
- Vermittlungsschicht heißt auch Netzwerkschicht, Sitzungsschicht auch Kommunikationssteuerungsschicht
- TCP/IP-Modell mit vier Schichten: Netzzugang (OSI 1 und 2), Internet (3), Transport (4), Anwendung (5 bis 7)

*Beispiel:* Ein Switch arbeitet mit Frames und MAC-Adressen → Schicht 2 (TCP/IP: Netzzugang); ein Router mit Paketen und IP-Adressen → Schicht 3 (Internet)"""


@art("osi", "OSI- und TCP/IP-Modell", "Netzwerk", "Geräte, Protokolle, Adressen und Dateneinheiten der richtigen Schicht zuordnen",
     ("OSI-", "ISO/OSI", "Schichtenmodell", "TCP/IP-Modell", "Kopplungselement"), formeln=FORMELN["osi"])
def osi(rng):
    return rng.choice([_schicht_nummer, _schicht_namen])(rng)


def _osi_weg(auswahl) -> str:
    return tabelle(["Begriff", "OSI-Schicht", "TCP/IP-Modell", "warum"],
                   [[name, f"**{n}** {OSI[n - 1]}", TCP_IP[ZU_TCP_IP[n]], warum] for name, n, warum in auswahl])


def _schicht_nummer(rng):
    auswahl = rng.sample(ELEMENTE, 5)
    frage = (f"Für eine Schulung der Auszubildenden ordnet die {rng.choice(FIRMEN)} Netzwerkbegriffe dem OSI-Referenzmodell zu:\n\n"
             + "\n".join(f"- {name}" for name, *_ in auswahl) + "\n\nGeben Sie zu jedem Begriff die Nummer der Schicht an (1 bis 7).")
    felder = [Feld(f"e{i}", name, n, stellen=0) for i, (name, n, _) in enumerate(auswahl)]
    return Aufgabe(frage, felder, _osi_weg(auswahl), titel="OSI-Schicht zuordnen")


def _schicht_namen(rng):
    auswahl = rng.sample(ELEMENTE, 3)
    frage = (f"In der Netzwerkdokumentation der {rng.choice(FIRMEN)} kommen vor: " + ", ".join(name for name, *_ in auswahl)
             + ".\n\nNennen Sie für jeden Begriff die Schicht im OSI-Modell und im TCP/IP-Modell (vier Schichten).")
    felder = []
    for i, (name, n, _) in enumerate(auswahl):
        felder += [Feld(f"o{i}", f"{name}: OSI-Schicht", OSI[n - 1], typ="text", optionen=OSI),
                   Feld(f"t{i}", f"{name}: TCP/IP-Schicht", TCP_IP[ZU_TCP_IP[n]], typ="text", optionen=TCP_IP)]
    return Aufgabe(frage, felder, _osi_weg(auswahl), titel="Schichten benennen")
