"""Netzwerk: Subnetting (IPv4), Übertragungszeiten und IPv6."""

import ipaddress
import math

from saku.lernen.rechnen.basis import ABTEILUNGEN, BYTE, FAKTOR, FIRMEN, Aufgabe, Feld, art, de, hoch, schritte, tabelle

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
     ("Subnet", "IPv4", "IP-Adressierung", "IP-Adresskonzept", "IP-Konfiguration", "Netzmaske", "CIDR"))
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
     ("Übertragungszeit", "Übertragungsdauer", "Downloadzeit", "Backupdauer", "Restoredauer"))
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


@art("ipv6", "IPv6", "Netzwerk", "Adressen kürzen und ausschreiben, /64-Netze in einem Präfix zählen", ("IPv6",))
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
