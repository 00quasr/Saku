"""UML lesen: Zustands-, Klassen-, Use-Case- und Sequenzdiagramme aus erfundenen Modellen, gezeichnet als SVG (svg.py).
Jedes Modell ist ein kleines Datenstück; dasselbe Stück wird gezeichnet, als Text beschrieben (aria-label) und für die Lösung
ausgewertet. Alle Systeme, Klassen und Abläufe sind erfunden."""

import itertools
import math

from markupsafe import Markup

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, schritte, tabelle
from saku.lernen.rechnen.programmieren import OPS
from saku.lernen.rechnen.svg import ZEILE, Bild, breite

# Notation und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Lösungsweg
FORMELN = {
    "zustand": """- Zustand: abgerundeter Kasten; Startzustand: ausgefüllter Kreis ● mit Pfeil auf den ersten Zustand, Endzustand ◉
- Übergang: Pfeil mit `ereignis [wächter] / verhalten`; er schaltet, wenn das Ereignis eintritt **und** der Wächter gilt, danach läuft das Verhalten
- Ein Ereignis, zu dem der aktuelle Zustand keinen Übergang hat oder dessen Wächter nicht gilt, verfällt: der Zustand bleibt
- Selbstübergang: Pfeil vom Zustand auf sich selbst, der Zustand wird verlassen und wieder betreten (etwa um zu zählen)
- Nachspielen in einer Tabelle: Ereignis, Zustand vorher, schaltender Übergang, Zustand danach, Zähler

*Beispiel:* „Abgemeldet“ mit `passwortFalsch [fehler < 2] / fehler ← fehler + 1` auf sich selbst und `passwortFalsch [fehler = 2]` nach „Gesperrt“: dreimal falsch → gesperrt, ein `passwortRichtig` danach verfällt""",
    "klassen": """- Klasse: Kasten mit dem Namen oben, darunter Attribute `name: Typ`, darunter Methoden `name(parameter): Rückgabetyp`
- Sichtbarkeit: `+` public (alle), `-` private (nur die Klasse selbst), `#` protected (die Klasse und ihre Unterklassen), `~` package (nur Klassen im selben Paket)
- Abstrakte Klasse: Name kursiv oder `{abstract}`, von ihr gibt es keine Objekte; abstrakte Methoden kursiv, Unterklassen überschreiben sie. Interface: `«interface»` über dem Namen, nur Methoden
- Assoziation: Linie; die Multiplizität am **anderen** Ende sagt, mit wie vielen Objekten der dortigen Klasse ein Objekt verbunden ist: `1` genau eins, `0..1` höchstens eins, `*` oder `0..*` beliebig viele, `1..*` mindestens eins, `0..5` bis fünf; die Rolle am Ende nennt die Verbindung aus Sicht der anderen Klasse
- Aggregation: leere Raute ◇ am Ganzen, die Teile bestehen ohne das Ganze weiter; Komposition: gefüllte Raute ◆ am Ganzen, jedes Teil gehört zu genau einem Ganzen und wird mit ihm gelöscht
- Generalisierung (Vererbung): durchgezogene Linie mit leerem Dreieck an der Oberklasse; Realisierung eines Interfaces: gestrichelt mit leerem Dreieck
- Ein Objekt der Unterklasse hat alle Attribute der Oberklasse, auch die privaten (direkt zugreifen darf es nur auf `+`, `#` und, im selben Paket, `~`); eine überschriebene Methode gibt es einmal

*Beispiel:* `Kunde 1 —— 0..* Mietvertrag`: ein Kunde hat beliebig viele Mietverträge (auch keinen), jeder Mietvertrag gehört zu genau einem Kunden""",
    "usecase": """- Systemgrenze: Rechteck mit dem Namen des Systems, darin die Anwendungsfälle als Ellipsen; die Akteure (Strichmännchen) stehen außerhalb
- Linie zwischen Akteur und Anwendungsfall: der Akteur nutzt ihn
- `«include»`: gestrichelter Pfeil vom Basisfall zum eingebundenen Fall; der eingebundene läuft **jedes Mal** mit (Pflicht)
- `«extend»`: gestrichelter Pfeil vom erweiternden Fall zum Basisfall; die Erweiterung läuft nur **unter einer Bedingung** (optional)
- Merkhilfe: «include» zeigt auf das, was immer dazugehört, «extend» auf das, was erweitert wird
- Generalisierung von Akteuren: Linie mit leerem Dreieck zum allgemeinen Akteur; der spezielle darf alles, was der allgemeine darf, nicht umgekehrt

*Beispiel:* „Bestellung aufgeben“ «include» „Anmelden“ (jede Bestellung verlangt die Anmeldung); „Gutschein einlösen“ «extend» „Bestellung aufgeben“ (nur wenn ein Gutschein vorliegt)""",
    "sequenz": """- Lebenslinie: Kasten mit `:Klasse` (oder `name:Klasse`), darunter eine gestrichelte Linie; die Zeit läuft von oben nach unten
- Synchrone Nachricht: durchgezogene Linie mit **gefüllter** Spitze, der Sender wartet, bis die Antwort kommt
- Asynchrone Nachricht: durchgezogene Linie mit **offener** Spitze, der Sender arbeitet sofort weiter und erwartet keine Antwort
- Antwort (Rückgabe): **gestrichelte** Linie mit offener Spitze zurück zum Aufrufer, beschriftet mit dem Rückgabewert
- Jede Antwort gehört zum letzten noch offenen synchronen Aufruf in der Gegenrichtung
- Aktivierungsbalken (schmale Rechtecke auf der Lebenslinie) zeigen, wann ein Objekt arbeitet; sie dürfen fehlen

*Beispiel:* `:Browser` ruft `anmelden(name, passwort)` synchron beim `:Webserver` auf, der fragt synchron `pruefe(name, hash)` bei der `:Datenbank`, Antwort `gueltig`, dann Antwort `sitzung` an den Browser""",
}


def _liste(teile: list[str]) -> str:
    return teile[0] if len(teile) == 1 else ", ".join(teile[:-1]) + " und " + teile[-1]


# --- Zustandsdiagramm ------------------------------------------------------------------------------
# Ein Automat: Zustände mit Platz im Raster (Zeile, Spalte), der erste ist der Startzustand; Übergänge
# (von, Ereignis, Wächter, nach, Wirkung). Wächter und Wirkung betreffen den Zähler des Automaten, der bei 0 beginnt:
# Wächter (Vergleich, Zahl), Wirkung "+1" oder "0". Übergänge laufen nur zwischen Zuständen derselben Zeile oder Spalte (dazwischen
# frei), Selbstübergänge stehen in der obersten oder untersten Zeile: so kreuzt keine Linie einen Kasten.

def _konto(rng):
    n = rng.choice([3, 4, 5])
    return {"name": "Benutzerkonto", "zaehler": "fehler",
            "text": f"die Anmeldung eines Kundenportals: nach {n} falschen Passwörtern in Folge wird das Konto gesperrt, nur ein "
                    "Administrator kann es entsperren",
            "zustaende": {"Abgemeldet": (0, 0), "Angemeldet": (0, 1), "Gesperrt": (1, 0)},
            "uebergaenge": [("Abgemeldet", "passwortRichtig", None, "Angemeldet", "0"),
                            ("Abgemeldet", "passwortFalsch", ("<", n - 1), "Abgemeldet", "+1"),
                            ("Abgemeldet", "passwortFalsch", ("=", n - 1), "Gesperrt", None),
                            ("Angemeldet", "abmelden", None, "Abgemeldet", None),
                            ("Gesperrt", "entsperren", None, "Abgemeldet", "0")]}


def _fahrkarte(rng):
    p = rng.choice([2, 3, 4])
    return {"name": "Fahrkartenautomat", "zaehler": "muenzen",
            "text": f"die Steuerung eines Fahrkartenautomaten: eine Fahrkarte kostet {p} Münzen zu 1 €, der Automat zählt mit",
            "zustaende": {"Bereit": (0, 1), "Wartung": (0, 0), "Bezahlen": (0, 2), "Drucken": (1, 2), "Entnahme": (1, 1)},
            "uebergaenge": [("Bereit", "fahrkarteWählen", None, "Bezahlen", "0"),
                            ("Bezahlen", "münze", ("<", p - 1), "Bezahlen", "+1"),
                            ("Bezahlen", "münze", ("=", p - 1), "Drucken", None),
                            ("Bezahlen", "abbrechen", None, "Bereit", None),
                            ("Drucken", "druckFertig", None, "Entnahme", None),
                            ("Entnahme", "fahrkarteEntnommen", None, "Bereit", None),
                            ("Bereit", "störung", None, "Wartung", None),
                            ("Wartung", "repariert", None, "Bereit", None)]}


def _bestellung(rng):
    return {"name": "Bestellung", "zaehler": "", "text": "die Bestellabwicklung eines Onlineshops",
            "zustaende": {"Neu": (0, 0), "Bezahlt": (0, 1), "Versendet": (0, 2), "Zugestellt": (0, 3),
                          "Storniert": (1, 0), "Erstattung": (1, 1), "Retoure": (1, 3)},
            "uebergaenge": [("Neu", "bezahlen", None, "Bezahlt", None), ("Bezahlt", "versenden", None, "Versendet", None),
                            ("Versendet", "zustellen", None, "Zugestellt", None), ("Neu", "stornieren", None, "Storniert", None),
                            ("Bezahlt", "stornieren", None, "Erstattung", None), ("Erstattung", "erstatten", None, "Storniert", None),
                            ("Zugestellt", "zurücksenden", None, "Retoure", None),
                            ("Retoure", "wareEingetroffen", None, "Erstattung", None)]}


def _druckauftrag(rng):
    return {"name": "Druckauftrag", "zaehler": "", "text": "die Warteschlange eines Netzwerkdruckers",
            "zustaende": {"Wartend": (0, 0), "Druckend": (0, 1), "Fertig": (0, 2), "Abgebrochen": (1, 0), "Angehalten": (1, 1)},
            "uebergaenge": [("Wartend", "starten", None, "Druckend", None), ("Druckend", "letzteSeite", None, "Fertig", None),
                            ("Druckend", "papierLeer", None, "Angehalten", None),
                            ("Angehalten", "papierNachgelegt", None, "Druckend", None),
                            ("Wartend", "abbrechen", None, "Abgebrochen", None),
                            ("Angehalten", "abbrechen", None, "Abgebrochen", None)]}


def _paket(rng):
    m = rng.choice([2, 3])
    return {"name": "Paketsendung", "zaehler": "versuche",
            "text": f"die Sendungsverfolgung eines Paketdienstes: nach {m} vergeblichen Zustellversuchen kommt das Paket in die Filiale",
            "zustaende": {"Angekündigt": (0, 0), "Unterwegs": (0, 1), "In Zustellung": (0, 2), "Zugestellt": (0, 3),
                          "Rücksendung": (1, 1), "In der Filiale": (1, 2), "Abgeholt": (1, 3)},
            "uebergaenge": [("Angekündigt", "eingeliefert", None, "Unterwegs", None),
                            ("Unterwegs", "imZustellbezirk", None, "In Zustellung", None),
                            ("In Zustellung", "angenommen", None, "Zugestellt", None),
                            ("In Zustellung", "nichtAngetroffen", ("<", m - 1), "In Zustellung", "+1"),
                            ("In Zustellung", "nichtAngetroffen", ("=", m - 1), "In der Filiale", None),
                            ("In der Filiale", "abgeholt", None, "Abgeholt", None),
                            ("In der Filiale", "fristAbgelaufen", None, "Rücksendung", None)]}


def _support(rng):
    return {"name": "Support-Ticket", "zaehler": "", "text": "das Ticketsystem ihres IT-Supports",
            "zustaende": {"Neu": (0, 0), "In Bearbeitung": (0, 1), "Gelöst": (0, 2), "Geschlossen": (0, 3),
                          "Abgelehnt": (1, 0), "Wartet auf Kunde": (1, 1)},
            "uebergaenge": [("Neu", "zuweisen", None, "In Bearbeitung", None), ("Neu", "ablehnen", None, "Abgelehnt", None),
                            ("In Bearbeitung", "rückfrage", None, "Wartet auf Kunde", None),
                            ("Wartet auf Kunde", "antwort", None, "In Bearbeitung", None),
                            ("In Bearbeitung", "lösen", None, "Gelöst", None), ("Gelöst", "wiedereröffnen", None, "In Bearbeitung", None),
                            ("Gelöst", "bestätigen", None, "Geschlossen", None)]}


AUTOMATEN = [_konto, _fahrkarte, _bestellung, _druckauftrag, _paket, _support]
Z_HOEHE, Z_ZEILE, Z_LUECKE, VERSATZ = 34, 64, 60, 7  # Höhe eines Zustands, Abstand der Zeilen, kleinste Spaltenlücke, zwei Pfeile


def _schild(u, zaehler: str) -> list[str]:
    """Beschriftung eines Übergangs: `ereignis [wächter]`, darunter `/ verhalten`."""
    _, ereignis, waechter, _, wirkung = u
    kopf = ereignis + (f" [{zaehler} {waechter[0]} {waechter[1]}]" if waechter else "")
    if not wirkung:
        return [kopf]
    return [kopf, f"/ {zaehler} ← {zaehler} + 1" if wirkung == "+1" else f"/ {zaehler} ← 0"]


def zustandsdiagramm(a: dict) -> Markup:
    """Zustände im Raster, Übergänge als Pfeile (zwei zwischen denselben Zuständen nebeneinander), Selbstübergänge als Schlaufe
    oben bzw. unten, der Startknoten links vom Startzustand oder darüber. Die Spalten rücken so weit auseinander, dass alle
    Beschriftungen passen."""
    pos, z = a["zustaende"], a["zaehler"]
    gruppen = {}  # (von, nach) → Zeilen der Beschriftung: mehrere Übergänge mit derselben Richtung teilen sich einen Pfeil
    for u in a["uebergaenge"]:
        gruppen.setdefault((u[0], u[3]), []).extend(_schild(u, z))
    spalten, zeilen = max(s for _, s in pos.values()) + 1, max(r for r, _ in pos.values()) + 1
    b = {n: breite(n) + 28 for n in pos}
    sb = [max(b[n] for n, (_, s) in pos.items() if s == sp) for sp in range(spalten)]
    luecke = [Z_LUECKE] * (spalten - 1)
    start = next(iter(pos))
    # waagrechte Pfeile: die längste Zeile passt zwischen die Kästen
    for (von, nach), text in gruppen.items():
        (r1, s1), (r2, s2) = pos[von], pos[nach]
        if von != nach and r1 == r2:
            links, rechts = sorted((s1, s2))
            fehlt = max(map(breite, text)) + 36 - sum(luecke[links:rechts]) - sum(sb[links + 1:rechts])
            luecke[rechts - 1] += max(fehlt, 0)
    # Beschriftungen neben senkrechten Pfeilen und über Schlaufen: je Spalte und Band (zwischen den Zeilen, oben, unten),
    # wie weit sie links und rechts der Mitte reichen; Nachbarspalten rücken auseinander, bis nichts aneinanderstößt
    weit = [{} for _ in range(spalten)]

    def reicht(s, band, links, rechts):
        alt = weit[s].get(band, (0, 0))
        weit[s][band] = max(alt[0], links), max(alt[1], rechts)
    for (von, nach), text in gruppen.items():
        (r1, s1), (r2, s2) = pos[von], pos[nach]
        w = max(map(breite, text))
        if von == nach:
            reicht(s1, "oben" if r1 == 0 else "unten", max(w / 2, 16), max(w / 2, 16))
        elif s1 == s2:
            gepaart, runter = (nach, von) in gruppen, r2 > r1
            for band in range(min(r1, r2), max(r1, r2)):
                if gepaart and runter:
                    reicht(s1, band, VERSATZ + 6 + w, VERSATZ)
                else:
                    reicht(s1, band, VERSATZ, VERSATZ + 6 + w)
    if pos[start][1] > 0:
        reicht(pos[start][1], "oben", 10, 10)
    for s in range(spalten - 1):
        abstand = max((weit[s][band][1] + weit[s + 1][band][0] + 14 for band in weit[s] if band in weit[s + 1]), default=0)
        luecke[s] += max(abstand - (sb[s] / 2 + luecke[s] + sb[s + 1] / 2), 0)
    cx = [sb[0] / 2]
    for s in range(1, spalten):
        cx.append(cx[-1] + sb[s - 1] / 2 + luecke[s - 1] + sb[s] / 2)
    oben = [r * (Z_HOEHE + Z_ZEILE) for r in range(zeilen)]

    bild = Bild()
    for n, (r, s) in pos.items():
        bild.kasten(cx[s] - b[n] / 2, oben[r], b[n], Z_HOEHE, rund=12)
        bild.text(cx[s], oben[r] + Z_HOEHE / 2 + 4, n, "middle")
    r, s = pos[start]
    if s == 0:
        x = cx[0] - b[start] / 2
        bild.kreis(x - 34, oben[r] + Z_HOEHE / 2, 7, voll=True)
        bild.pfeil([(x - 27, oben[r] + Z_HOEHE / 2), (x, oben[r] + Z_HOEHE / 2)])
    else:
        bild.kreis(cx[s], oben[r] - 36, 7, voll=True)
        bild.pfeil([(cx[s], oben[r] - 29), (cx[s], oben[r])])
    for (von, nach), text in gruppen.items():
        (r1, s1), (r2, s2) = pos[von], pos[nach]
        gepaart, hoch = (nach, von) in gruppen and von != nach, (len(text) - 1) * ZEILE
        if von == nach:
            x = cx[s1]
            if r1 == 0:
                y = oben[r1]
                bild.pfeil([(x - 12, y), (x - 12, y - 24), (x + 12, y - 24), (x + 12, y)])
                bild.beschriftung([(x, y - 31 - hoch, "middle")], text)
            else:
                y = oben[r1] + Z_HOEHE
                bild.pfeil([(x - 12, y), (x - 12, y + 24), (x + 12, y + 24), (x + 12, y)])
                bild.beschriftung([(x, y + 41, "middle")], text)
        elif r1 == r2:
            rechts = s2 > s1
            y = oben[r1] + Z_HOEHE / 2 + ((-VERSATZ if rechts else VERSATZ) if gepaart else 0)
            xa, xb = (cx[s1] + b[von] / 2, cx[s2] - b[nach] / 2) if rechts else (cx[s1] - b[von] / 2, cx[s2] + b[nach] / 2)
            bild.pfeil([(xa, y), (xb, y)])
            ueber, unter = ((xa + xb) / 2, y - 5 - hoch, "middle"), ((xa + xb) / 2, y + 15, "middle")
            bild.beschriftung([unter, ueber] if gepaart and not rechts else [ueber, unter], text)
        else:
            runter = r2 > r1
            x = cx[s1] + ((-VERSATZ if runter else VERSATZ) if gepaart else 0)
            ya, yb = (oben[r1] + Z_HOEHE, oben[r2]) if runter else (oben[r1], oben[r2] + Z_HOEHE)
            bild.pfeil([(x, ya), (x, yb)])
            y = (ya + yb) / 2 + 4 - hoch / 2
            links, rechts = (x - 6, y, "end"), (x + 6, y, "start")
            bild.beschriftung([links, rechts] if gepaart and runter else [rechts, links], text)
    zaehler = f" Der Zähler {z} beginnt bei 0." if z else ""
    uebergaenge = "; ".join(f"von „{u[0]}“ nach „{u[3]}“ bei {' '.join(_schild(u, z))}" for u in a["uebergaenge"])
    return bild.svg("uml-zustand", f"Zustandsdiagramm {a['name']}. Startzustand „{start}“.{zaehler} Übergänge: {uebergaenge}")


def nachspielen(a: dict, folge: list[str], zustand: str | None = None) -> list[tuple]:
    """Ereignis für Ereignis: (Ereignis, Zustand vorher, schaltender Übergang oder None, Zustand danach, Zähler danach)."""
    zustand, zaehler, raus = zustand or next(iter(a["zustaende"])), 0, []
    for e in folge:
        u = next((u for u in a["uebergaenge"] if u[0] == zustand and u[1] == e and (not u[2] or OPS[u[2][0]](zaehler, u[2][1]))), None)
        vorher = zustand
        if u:
            zustand, zaehler = u[3], zaehler + 1 if u[4] == "+1" else 0 if u[4] == "0" else zaehler
        raus.append((e, vorher, u, zustand, zaehler))
    return raus


def _folge(rng, a: dict, laenge: int) -> list[str]:
    """Zufällige Ereignisfolge ab dem Start: meist ein Ereignis, das gerade schaltet, manchmal eines, das verfällt. In einen
    Zustand ohne Ausgang (Storniert, Abgebrochen …) führt sie erst am Ende, sonst verfiele der Rest."""
    alle, folge = sorted({u[1] for u in a["uebergaenge"]}), []
    ende = {z for z in a["zustaende"] if not any(u[0] == z for u in a["uebergaenge"])}
    for i in range(laenge):
        zustand, zaehler = nachspielen(a, folge)[-1][3:] if folge else (next(iter(a["zustaende"])), 0)
        moeglich = sorted({u[1] for u in a["uebergaenge"] if u[0] == zustand and (not u[2] or OPS[u[2][0]](zaehler, u[2][1]))})
        if i < laenge - 2:
            moeglich = [e for e in moeglich if nachspielen(a, [*folge, e])[-1][3] not in ende] or moeglich
        folge.append(rng.choice(moeglich) if moeglich and rng.random() < 0.8 else rng.choice(alle))
    return folge


def _spur(a: dict, folge: list[str]) -> str:
    """Nachgespielt als Tabelle."""
    z = a["zaehler"]
    kopf = ["Nr.", "Ereignis", "Zustand vorher", "Übergang", "Zustand danach"] + ([z] if z else [])
    zeilen = []
    for i, (e, vorher, u, nachher, zaehler) in enumerate(nachspielen(a, folge), start=1):
        if u:
            uebergang = " ".join(_schild(u, z))
        elif any(x[0] == vorher and x[1] == e for x in a["uebergaenge"]):
            uebergang = "verfällt (kein Wächter gilt)"
        else:
            uebergang = "verfällt (kein Übergang)"
        zeilen.append([i, f"`{e}`", vorher, uebergang, f"**{nachher}**"] + ([zaehler] if z else []))
    return tabelle(kopf, zeilen)


@art("zustand", "Zustandsdiagramm", "UML", "Zustandsautomaten nachspielen: Ereignisse, Wächter, Zähler, verfallende Ereignisse",
     ("Zustandsdiagramm", "Zustandsautomat", "Zustandsübergang", "Zustandsübergänge"), formeln=FORMELN["zustand"])
def zustand(rng):
    a = rng.choice(AUTOMATEN)(rng)
    z, start, firma = a["zaehler"], next(iter(a["zustaende"])), rng.choice(FIRMEN)
    namen = sorted(a["zustaende"])
    einleitung = (f"Die {firma} entwickelt {a['text']}. Das Zustandsdiagramm unten zeigt das Verhalten"
                  + (f", der Zähler `{z}` beginnt bei 0" if z else "") + ". Ein Ereignis, zu dem kein Übergang passt, verfällt.\n\n")
    if rng.random() < 0.6:
        folge = _folge(rng, a, rng.randint(5, 8))
        ende = nachspielen(a, folge)[-1]
        frage = (einleitung + f"Ereignisfolge ab dem Startzustand: `{', '.join(folge)}`\n\n"
                 "In welchem Zustand ist das System nach dieser Folge?" + (f" Welchen Wert hat `{z}` dann?" if z else ""))
        felder = [Feld("zustand", "Zustand am Ende", ende[3], typ="text", optionen=namen)]
        if z:
            felder.append(Feld("zaehler", f"{z} am Ende", ende[4], stellen=0))
        weg = f"Vom Startzustand „{start}“ aus Ereignis für Ereignis nachspielen:\n\n{_spur(a, folge)}\n\nAm Ende: **{ende[3]}**" + \
            (f", `{z}` = **{ende[4]}**" if z else "") + "."
        return Aufgabe(frage, felder, weg, titel="Ereignisfolge nachspielen", struktogramm=zustandsdiagramm(a))
    # welche Folge führt zum Ziel? Eine richtige, die übrigen enden woanders
    while True:
        richtig = _folge(rng, a, rng.randint(3, 5))
        ziel = nachspielen(a, richtig)[-1][3]
        if ziel == start:
            continue
        falsche = []
        for _ in range(300):
            kandidat = list(richtig)
            if rng.random() < 0.5:
                i, j = rng.sample(range(len(kandidat)), 2)
                kandidat[i], kandidat[j] = kandidat[j], kandidat[i]
            else:
                kandidat[rng.randrange(len(kandidat))] = rng.choice(sorted({u[1] for u in a["uebergaenge"]}))
            if nachspielen(a, kandidat)[-1][3] != ziel and kandidat not in falsche:
                falsche.append(kandidat)
            if len(falsche) == 3:
                break
        if len(falsche) >= 2:
            break
    folgen = [richtig, *falsche]
    rng.shuffle(folgen)
    buchstaben = "ABCD"[:len(folgen)]
    frage = (einleitung + f"Welche Ereignisfolge führt vom Startzustand „{start}“ in den Zustand **„{ziel}“**?\n\n"
             + "\n".join(f"- {b}: `{', '.join(f)}`" for b, f in zip(buchstaben, folgen)))
    weg = "\n".join(f"- {b}: endet in **{nachspielen(a, f)[-1][3]}**" + (" ✓" if f == richtig else "") for b, f in zip(buchstaben, folgen))
    weg += f"\n\nDie richtige Folge nachgespielt:\n\n{_spur(a, richtig)}"
    return Aufgabe(frage, [Feld("folge", "Ereignisfolge", buchstaben[folgen.index(richtig)], typ="text", optionen=list(buchstaben))],
                   weg, titel="Ereignisfolge finden", struktogramm=zustandsdiagramm(a))


# --- Klassendiagramm -------------------------------------------------------------------------------
# Ein Fachmodell: Klassen mit Attributen und Methoden; kette: die obere Zeile von links nach rechts, je zwei Nachbarn verbunden
# (a, b, mögliche Arten, Multiplizitäten am Ende von a und von b, Rollen); bei Aggregation und Komposition ist a das Ganze.
# Die Oberklasse (abstrakt oder Interface) steht in der Kette, ihre Unterklassen darunter; eine gleichnamige Methode der
# Unterklasse überschreibt die der Oberklasse, dort ist sie abstrakt.

MODELLE = [
    {"thema": "die Software einer Autovermietung", "kette": ["Kunde", "Mietvertrag", "Fahrzeug"], "ober": ("Fahrzeug", "abstract"),
     "unter": ["PKW", "Transporter"],
     "klassen": {"Kunde": (["kundenNr: int", "name: String", "geburtsdatum: Date"], ["mieten(f: Fahrzeug, tage: int): Mietvertrag"]),
                 "Mietvertrag": (["vertragsNr: int", "beginn: Date", "tage: int"], ["gesamtpreis(): double"]),
                 "Fahrzeug": (["kennzeichen: String", "tagespreis: double", "kilometerstand: int"],
                              ["berechnePreis(tage: int): double", "tanken(liter: double): void"]),
                 "PKW": (["sitzplaetze: int"], ["berechnePreis(tage: int): double"]),
                 "Transporter": (["ladevolumen: double", "maxZuladung: int"], ["berechnePreis(tage: int): double"])},
     "verbindungen": [("Kunde", "Mietvertrag", ("assoziation", "komposition"), ("1",), ("0..*", "1..*"), ("mieter", "vertraege")),
                      ("Mietvertrag", "Fahrzeug", ("assoziation",), ("0..*", "0..1"), ("1",), ("", "fahrzeug"))]},
    {"thema": "einen Onlineshop", "kette": ["Bestellung", "Bestellposition", "Artikel"], "ober": ("Artikel", "abstract"),
     "unter": ["Buch", "Elektrogeraet"],
     "klassen": {"Bestellung": (["bestellNr: int", "datum: Date", "status: String"], ["summe(): double", "stornieren(): void"]),
                 "Bestellposition": (["menge: int", "einzelpreis: double"], ["gesamt(): double"]),
                 "Artikel": (["artikelNr: int", "bezeichnung: String", "nettopreis: double"], ["bruttopreis(): double", "bestand(): int"]),
                 "Buch": (["isbn: String", "autor: String"], ["bruttopreis(): double"]),
                 "Elektrogeraet": (["garantieMonate: int"], ["bruttopreis(): double"])},
     "verbindungen": [("Bestellung", "Bestellposition", ("komposition", "aggregation"), ("1",), ("1..*",), ("bestellung", "positionen")),
                      ("Bestellposition", "Artikel", ("assoziation",), ("0..*",), ("1",), ("", "artikel"))]},
    {"thema": "das Buchungssystem eines Hotels", "kette": ["Hotel", "Zimmer", "Buchung"], "ober": ("Zimmer", "abstract"),
     "unter": ["Einzelzimmer", "Suite"],
     "klassen": {"Hotel": (["name: String", "sterne: int"], ["freieZimmer(von: Date, bis: Date): int"]),
                 "Zimmer": (["nummer: int", "etage: int", "preisProNacht: double"], ["maxGaeste(): int", "reinigen(): void"]),
                 "Einzelzimmer": (["schreibtisch: boolean"], ["maxGaeste(): int"]),
                 "Suite": (["raeume: int", "whirlpool: boolean"], ["maxGaeste(): int"]),
                 "Buchung": (["anreise: Date", "abreise: Date"], ["naechte(): int"])},
     "verbindungen": [("Hotel", "Zimmer", ("komposition", "aggregation"), ("1", "0..1"), ("1..*",), ("hotel", "zimmer")),
                      ("Zimmer", "Buchung", ("assoziation",), ("1", "1..*"), ("0..*",), ("zimmer", "buchungen"))]},
    {"thema": "die Ausleihe einer Stadtbibliothek", "kette": ["Mitglied", "Ausleihe", "Medium"], "ober": ("Medium", "abstract"),
     "unter": ["Buch", "DVD"],
     "klassen": {"Mitglied": (["mitgliedsNr: int", "name: String"], ["ausleihen(m: Medium): Ausleihe"]),
                 "Ausleihe": (["ausgeliehenAm: Date", "rueckgabeBis: Date"], ["verlaengern(): boolean"]),
                 "Medium": (["inventarNr: int", "titel: String", "jahr: int"], ["leihfristTage(): int", "reservieren(): void"]),
                 "Buch": (["isbn: String", "seiten: int"], ["leihfristTage(): int"]),
                 "DVD": (["laufzeitMin: int", "fsk: int"], ["leihfristTage(): int"])},
     "verbindungen": [("Mitglied", "Ausleihe", ("assoziation", "komposition"), ("1",), ("0..5", "0..3", "0..10"), ("entleiher", "ausleihen")),
                      ("Ausleihe", "Medium", ("assoziation",), ("0..*", "0..1"), ("1",), ("", "medium"))]},
    {"thema": "eine Projektverwaltung", "kette": ["Arbeitspaket", "Projekt", "Mitarbeiter"], "ober": ("Mitarbeiter", "abstract"),
     "unter": ["Festangestellter", "Freelancer"],
     "klassen": {"Arbeitspaket": (["bezeichnung: String", "aufwandStunden: int"], ["abschliessen(): void"]),
                 "Projekt": (["projektNr: int", "titel: String", "budget: double"], ["fortschritt(): double"]),
                 "Mitarbeiter": (["personalNr: int", "name: String", "stundensatz: double"],
                                 ["kosten(stunden: int): double", "einplanen(p: Projekt): void"]),
                 "Festangestellter": (["gehalt: double", "urlaubstage: int"], ["kosten(stunden: int): double"]),
                 "Freelancer": (["firma: String"], ["kosten(stunden: int): double"])},
     "verbindungen": [("Projekt", "Arbeitspaket", ("komposition",), ("1",), ("1..*",), ("projekt", "pakete")),
                      ("Projekt", "Mitarbeiter", ("aggregation", "assoziation"), ("0..*", "1..*"), ("1..*",), ("projekte", "team"))]},
    {"thema": "den Bezahlvorgang eines Onlineshops", "kette": ["Kunde", "Bestellung", "Zahlungsart"],
     "ober": ("Zahlungsart", "interface"), "unter": ["Kreditkarte", "Lastschrift"],
     "klassen": {"Kunde": (["kundenNr: int", "email: String"], ["bestellen(): Bestellung"]),
                 "Bestellung": (["bestellNr: int", "betrag: double"], ["bezahlen(): boolean"]),
                 "Zahlungsart": ([], ["autorisieren(betrag: double): boolean", "gebuehr(betrag: double): double"]),
                 "Kreditkarte": (["kartenNr: String", "gueltigBis: Date"],
                                 ["autorisieren(betrag: double): boolean", "gebuehr(betrag: double): double"]),
                 "Lastschrift": (["iban: String", "mandatsRef: String"],
                                 ["autorisieren(betrag: double): boolean", "gebuehr(betrag: double): double"])},
     "verbindungen": [("Kunde", "Bestellung", ("assoziation", "komposition"), ("1",), ("0..*",), ("kunde", "bestellungen")),
                      ("Bestellung", "Zahlungsart", ("assoziation",), ("0..*",), ("1",), ("", "zahlungsart"))]},
    {"thema": "die Haustechnik eines Bürogebäudes", "kette": ["Gebaeude", "Raum", "Sensor"], "ober": ("Sensor", "interface"),
     "unter": ["Temperatursensor", "Rauchmelder"],
     "klassen": {"Gebaeude": (["adresse: String", "baujahr: int"], ["alarmAusloesen(): void"]),
                 "Raum": (["nummer: String", "flaeche: double"], ["lueften(): void"]),
                 "Sensor": ([], ["messen(): double", "istDefekt(): boolean"]),
                 "Temperatursensor": (["einheit: String"], ["messen(): double", "istDefekt(): boolean"]),
                 "Rauchmelder": (["batterie: int"], ["messen(): double", "istDefekt(): boolean", "testen(): void"])},
     "verbindungen": [("Gebaeude", "Raum", ("komposition",), ("1",), ("1..*",), ("gebaeude", "raeume")),
                      ("Raum", "Sensor", ("aggregation", "assoziation"), ("0..1",), ("0..*", "1..*"), ("raum", "sensoren"))]},
]
BEZIEHUNGEN = {"assoziation": "Assoziation", "aggregation": "Aggregation", "komposition": "Komposition",
               "vererbung": "Generalisierung (Vererbung)", "realisierung": "Realisierung (Interface)"}
SICHTBARKEIT = {"+": "public", "-": "private", "#": "protected", "~": "package"}


def _methode(text: str) -> str:
    return text.split("(")[0]


def _modell(rng) -> dict:
    """Ein Fachmodell mit gezogenen Arten, Multiplizitäten und Sichtbarkeiten; manchmal fehlt eine Unterklasse (dann vier Klassen).
    klassen: Name → (Art: "", "abstract" oder "interface"; Attribute als (Sichtbarkeit, Text); Methoden als (Text, abstrakt))."""
    v = rng.choice(MODELLE)
    ober, art_ = v["ober"]
    unter = [u for u in v["unter"] if rng.random() < 0.8] or [rng.choice(v["unter"])]
    verbindungen = []
    for a, b, arten, ma, mb, (ra, rb) in v["verbindungen"]:
        art_v = rng.choice(arten)
        verbindungen.append((a, b, art_v, "1" if art_v == "komposition" else rng.choice(ma), rng.choice(mb), ra, rb))
    klassen = {}
    for name in [*v["kette"], *unter]:
        attribute, methoden = v["klassen"][name]
        if name == ober:  # genau ein Attribut dürfen Unterklassen direkt sehen (+ oder #), die übrigen nicht (- oder ~ im fremden Paket)
            offen = rng.randrange(len(attribute)) if attribute else -1
            sicht = [rng.choice("+#") if i == offen else rng.choice("--~") for i in range(len(attribute))]
            ueberschrieben = {_methode(m) for u in unter for m in v["klassen"][u][1]}
            klassen[name] = (art_, list(zip(sicht, attribute)), [(m, art_ == "interface" or _methode(m) in ueberschrieben) for m in methoden])
        else:
            klassen[name] = ("", [("-", x) for x in attribute], [(m, False) for m in methoden])
    return {"thema": v["thema"], "kette": v["kette"], "ober": ober, "unter": unter, "klassen": klassen, "verbindungen": verbindungen}


def _vielheit(m: str) -> tuple[int, int | None]:
    """Multiplizität als (mindestens, höchstens), None = beliebig viele."""
    if m == "*":
        return 0, None
    unten, _, oben = m.partition("..")
    return int(unten), None if oben == "*" else int(oben or unten)


def _klassenkasten(bild: Bild, x: float, y: float, name: str, k: tuple, b: float):
    """Drei Fächer übereinander (Name, Attribute, Methoden); ein Interface ohne Attributfach."""
    art_, attribute, methoden = k
    kopf = ["«interface»", name] if art_ == "interface" else [name, "{abstract}"] if art_ == "abstract" else [name]
    faecher = [(kopf, "kopf")] + ([] if art_ == "interface" else [([f"{s} {a}" for s, a in attribute], "")]) + \
        [([f"+ {m}" for m, _ in methoden], "methoden")]
    for zeilen, fach in faecher:
        h = max(len(zeilen), 0) * ZEILE + 8 if zeilen else 10
        bild.kasten(x, y, b, h)
        for i, zeile in enumerate(zeilen):
            if fach == "kopf":
                klasse = "uml-fett" + (" uml-kursiv" if art_ == "abstract" else "") if zeile == name else ""
                bild.text(x + b / 2, y + 16 + i * ZEILE, zeile, "middle", klasse)
            else:
                abstrakt = fach == "methoden" and methoden[i][1]
                bild.text(x + 8, y + 16 + i * ZEILE, zeile, klasse="uml-kursiv" if abstrakt else "")
        y += h


def _kastenmass(k: tuple, name: str) -> tuple[float, float]:
    art_, attribute, methoden = k
    texte = [name, "«interface»" if art_ == "interface" else "{abstract}"] + [f"{s} {a}" for s, a in attribute] + [f"+ {m}" for m, _ in methoden]
    faecher = [2 if art_ else 1] + ([] if art_ == "interface" else [len(attribute)]) + [len(methoden)]
    return max(max(map(breite, texte)) + 16, 96), sum(n * ZEILE + 8 if n else 10 for n in faecher)


def klassendiagramm(m: dict) -> Markup:
    """Die Kette in der oberen Zeile, Nachbarn waagrecht verbunden (Multiplizität über, Rolle unter der Linie, Raute am Ganzen);
    die Unterklassen darunter, mittig unter der Oberklasse, als Baum mit einem Dreieck an der Oberklasse."""
    klassen, bild = m["klassen"], Bild()
    mass = {n: _kastenmass(k, n) for n, k in klassen.items()}
    verbindung = {frozenset(v[:2]): v for v in m["verbindungen"]}
    x, links = 0.0, {}
    for i, n in enumerate(m["kette"]):
        if i:  # Lücke zur vorigen Klasse: Platz für beide Enden der Verbindung
            a, b, art_, ma, mb, ra, rb = verbindung[frozenset((m["kette"][i - 1], n))]
            enden = [(ma, ra, art_ in ("aggregation", "komposition")), (mb, rb, False)]
            if a == n:
                enden.reverse()
            x += sum(max(breite(mu), breite(r)) + (26 if raute else 0) for mu, r, raute in enden) + 30
        links[n] = x
        x += mass[n][0]
    hoehe0 = max(mass[n][1] for n in m["kette"])
    for n in m["kette"]:
        _klassenkasten(bild, links[n], 0, n, klassen[n], mass[n][0])
    for vorher, n in zip(m["kette"], m["kette"][1:]):
        a, b, art_, ma, mb, ra, rb = verbindung[frozenset((vorher, n))]
        y = min(mass[vorher][1], mass[n][1]) / 2
        xl, xr = links[vorher] + mass[vorher][0], links[n]
        ganzes = {"aggregation": "raute", "komposition": "raute-voll"}.get(art_, "")
        if a == vorher:  # das Ganze links: Raute am Anfang der Linie
            bild.pfeil([(xl, y), (xr, y)], form="", anfang=ganzes)
        else:
            bild.pfeil([(xl, y), (xr, y)], form=ganzes)
        for mu, r, rechts, raute in ((ma, ra, a != vorher, bool(ganzes)), (mb, rb, b != vorher, False)):
            versatz = 6 + (22 if raute else 0)
            x, anker = (xr - versatz, "end") if rechts else (xl + versatz, "start")
            bild.beschriftung([(x, y - 5, anker)], [mu])
            if r:
                bild.beschriftung([(x, y + 15, anker)], [r])
    ober, unter = m["ober"], m["unter"]
    real = klassen[ober][0] == "interface"
    breiten = [mass[u][0] for u in unter]
    mitte, gesamt = links[ober] + mass[ober][0] / 2, sum(breiten) + 40 * (len(unter) - 1)
    # mittig unter der Oberklasse, aber nicht rechts über die Kette hinaus: sonst wird das ganze Bild breiter und kleiner
    x, oben, bus = max(min(mitte - gesamt / 2, links[m["kette"][-1]] + mass[m["kette"][-1]][0] - gesamt), 0), hoehe0 + 70, hoehe0 + 35
    xs = []
    for u, b in zip(unter, breiten):
        _klassenkasten(bild, x, oben, u, klassen[u], b)
        xs.append(x + b / 2)
        bild.linie([(x + b / 2, oben), (x + b / 2, bus)], gestrichelt=real)
        x += b + 40
    if min(xs) < max(xs) or xs[0] != mitte:
        bild.linie([(min(*xs, mitte), bus), (max(*xs, mitte), bus)], gestrichelt=real)
    bild.pfeil([(mitte, bus), (mitte, mass[ober][1])], form="dreieck", gestrichelt=real)
    return bild.svg("uml-klassen", _klassentext(m))


def _klassentext(m: dict) -> str:
    """Textfassung: Klassen mit Fächern, dann die Beziehungen mit Multiplizitäten und Rollen."""
    teile = []
    for n, (art_, attribute, methoden) in m["klassen"].items():
        art_text = {"abstract": "Abstrakte Klasse", "interface": "Interface"}.get(art_, "Klasse")
        attr = "; ".join(f"{s} {a}" for s, a in attribute) or "keine"
        meth = "; ".join(f"+ {t}" + (" (abstrakt)" if ab else "") for t, ab in methoden)
        teile.append(f"{art_text} {n}. Attribute: {attr}. Methoden: {meth}.")
    bez = []
    for a, b, art_, ma, mb, ra, rb in m["verbindungen"]:
        ende_a, ende_b = f"{a} ({ma}{', Rolle ' + ra if ra else ''})", f"{b} ({mb}{', Rolle ' + rb if rb else ''})"
        if art_ == "assoziation":
            bez.append(f"Assoziation zwischen {ende_a} und {ende_b}")
        else:
            bez.append(f"{BEZIEHUNGEN[art_]}: Ganzes {ende_a}, Teil {ende_b}")
    verb = "realisiert" if m["klassen"][m["ober"]][0] == "interface" else "erbt von"
    bez += [f"{u} {verb} {m['ober']}" for u in m["unter"]]
    return f"Klassendiagramm. {' '.join(teile)} Beziehungen: {'; '.join(bez)}."


def _anzahl_text(n: int | None) -> str:
    return "beliebig viele" if n is None else str(n)


def _vielheit_feld(name: str, label: str, n: int | None) -> Feld:
    """Obergrenze immer als Textfeld: eine Zahl oder „beliebig viele“ (auch *, n …); verschiedene Feldarten verrieten die Antwort."""
    if n is None:
        return Feld(name, label, "beliebig viele", typ="text", auch=("*", "n", "beliebig", "unbegrenzt", "unendlich", "∞", "viele"))
    return Feld(name, label, str(n), typ="text")


@art("klassen", "Klassendiagramm", "UML", "Klassendiagramme lesen: Multiplizitäten, Beziehungen, Vererbung, Sichtbarkeit",
     ("Klassendiagramm", "Objektorient", "Klassen und Objekte", "mit UML", "UML-Diagramm"), formeln=FORMELN["klassen"])
def klassen(rng):
    m = _modell(rng)
    k, ober, firma = m["klassen"], m["ober"], rng.choice(FIRMEN)
    abstrakt = k[ober][0] == "abstract"
    teile = [v for v in m["verbindungen"] if v[2] in ("aggregation", "komposition")]
    varianten = ["multiplizitaet", "beziehung", "vererbung"] + (["sichtbarkeit"] if abstrakt else []) + (["ganzes"] if teile else [])
    variante = rng.choice(varianten)
    einleitung = f"Die {firma} entwickelt {m['thema']}. Das Klassendiagramm unten zeigt einen Ausschnitt des Fachmodells.\n\n"
    bild = {"struktogramm": klassendiagramm(m)}
    if variante == "multiplizitaet":
        a, b, art_, ma, mb, *_ = rng.choice(m["verbindungen"])
        (amin, amax), (bmin, bmax) = _vielheit(ma), _vielheit(mb)
        frage = einleitung + (f"Lesen Sie die Verbindung zwischen **{a}** und **{b}** ab: Mit wie vielen Objekten der anderen Klasse "
                              "ist ein Objekt mindestens und höchstens verbunden? (Ohne Obergrenze: „beliebig viele“.)")
        felder = [Feld("ab_min", f"Ein {a}: mindestens … {b}", bmin, stellen=0), _vielheit_feld("ab_max", f"Ein {a}: höchstens … {b}", bmax),
                  Feld("ba_min", f"Ein {b}: mindestens … {a}", amin, stellen=0), _vielheit_feld("ba_max", f"Ein {b}: höchstens … {a}", amax)]
        weg = (f"Die Multiplizität steht am Ende der Klasse, die gezählt wird, also am **anderen** Ende der Linie.\n\n"
               f"1. Am Ende von {b} steht `{mb}`: ein Objekt von {a} ist mit mindestens {bmin} und höchstens {_anzahl_text(bmax)} "
               f"Objekten von {b} verbunden.\n"
               f"2. Am Ende von {a} steht `{ma}`: ein Objekt von {b} ist mit mindestens {amin} und höchstens {_anzahl_text(amax)} "
               f"Objekten von {a} verbunden.")
        return Aufgabe(frage, felder, weg, titel="Multiplizitäten", **bild)
    if variante == "beziehung":
        u = rng.choice(m["unter"])
        paare = [(a, b, art_) for a, b, art_, *_ in m["verbindungen"]] + [(u, ober, "vererbung" if abstrakt else "realisierung")]
        frage = einleitung + "Welche Beziehung zeigt das Diagramm jeweils zwischen den beiden Klassen?"
        optionen = list(BEZIEHUNGEN.values())
        felder = [Feld(f"b{i}", f"{a} – {b}", BEZIEHUNGEN[art_], typ="text", optionen=optionen) for i, (a, b, art_) in enumerate(paare)]
        zeichen = {"assoziation": "eine einfache Linie ohne Raute und Dreieck", "aggregation": "eine leere Raute am Ganzen ({a})",
                   "komposition": "eine gefüllte Raute am Ganzen ({a})", "vererbung": "ein leeres Dreieck an der Oberklasse ({b})",
                   "realisierung": "eine gestrichelte Linie mit leerem Dreieck am Interface ({b})"}
        weg = "\n".join(f"{i}. {a} – {b}: {zeichen[art_].format(a=a, b=b)} → **{BEZIEHUNGEN[art_]}**"
                        for i, (a, b, art_) in enumerate(paare, start=1))
        return Aufgabe(frage, felder, weg, titel="Beziehungen", **bild)
    if variante == "vererbung":
        u = rng.choice(m["unter"])
        attr = len(k[u][1]) + len(k[ober][1])
        methoden = sorted({_methode(t) for t, _ in k[u][2]} | {_methode(t) for t, _ in k[ober][2]})
        doppelt = sorted({_methode(t) for t, _ in k[u][2]} & {_methode(t) for t, _ in k[ober][2]})
        frage = einleitung + (f"a) Wie viele Attribute hat ein Objekt der Klasse **{u}**, geerbte mitgezählt?\n\n"
                              f"b) Wie viele verschiedene Methoden lassen sich auf einem Objekt von {u} aufrufen? Eine überschriebene "
                              "oder implementierte Methode zählt einmal.\n\nc) Von welcher Klasse (oder welchem Interface) lassen "
                              "sich keine Objekte erzeugen?")
        felder = [Feld("attribute", f"Attribute eines {u}-Objekts", attr, stellen=0),
                  Feld("methoden", f"Methoden eines {u}-Objekts", len(methoden), stellen=0),
                  Feld("abstrakt", "Keine Objekte von", ober, typ="text", optionen=sorted(k))]
        erbt = "erbt von" if abstrakt else "realisiert das Interface"
        weg = schritte(
            f"{u} {erbt} {ober}" + (f" und bekommt dessen {len(k[ober][1])} Attribute dazu, auch die privaten: "
                                     f"{len(k[u][1])} + {len(k[ober][1])} = **{attr}**" if abstrakt else
                                     f"; ein Interface hat keine Attribute, es bleiben die eigenen: **{attr}**"),
            f"Methoden: {', '.join(f'`{x}()`' for x in methoden)} = **{len(methoden)}**"
            + (f"; {', '.join(f'`{x}()`' for x in doppelt)} {'überschreibt' if abstrakt else 'implementiert'} {u}, "
               "das zählt nur einmal" if doppelt else ""),
            f"{ober} ist " + ("abstrakt (Name kursiv, `{abstract}`)" if abstrakt else "ein Interface (`«interface»`)")
            + f": davon gibt es keine Objekte, nur von den Unterklassen → **{ober}**")
        return Aufgabe(frage, felder, weg, titel="Vererbung", **bild)
    if variante == "sichtbarkeit":
        u = rng.choice(m["unter"])
        attribute = k[ober][1]
        offen = next(a for s, a in attribute if s in "+#")
        andere = rng.choice([(s, a) for s, a in attribute if a != offen])
        frage = einleitung + (f"Die Unterklassen liegen in einem anderen Paket als {ober}.\n\na) Auf welches Attribut von {ober} darf "
                              f"eine Methode der Klasse **{u}** direkt zugreifen?\n\nb) Welche Sichtbarkeit hat das Attribut "
                              f"`{andere[1].split(':')[0]}`?")
        felder = [Feld("zugriff", "Direkt zugreifbar", offen.split(":")[0], typ="text", optionen=[a.split(":")[0] for _, a in attribute]),
                  Feld("sicht", f"Sichtbarkeit von {andere[1].split(':')[0]}", SICHTBARKEIT[andere[0]], typ="text",
                       optionen=list(SICHTBARKEIT.values()))]
        weg = "\n".join(f"- `{s} {a}`: {SICHTBARKEIT[s]} → " + ("darf {u} direkt nutzen" if s in "+#" else
                        "nur die Klasse selbst" if s == "-" else "nur im selben Paket, {u} liegt in einem anderen").format(u=u)
                        for s, a in attribute)
        weg += f"\n\nDirekt zugreifen darf {u} also nur auf **{offen.split(':')[0]}**; `{andere[1].split(':')[0]}` ist **{SICHTBARKEIT[andere[0]]}**."
        return Aufgabe(frage, felder, weg, titel="Sichtbarkeit", **bild)
    g, t, art_, mg, *_ = rng.choice(teile)
    gmin, gmax = _vielheit(mg)
    komposition = art_ == "komposition"
    frage = einleitung + (f"Zwischen **{g}** und **{t}** besteht eine Teil-Ganzes-Beziehung.\n\na) Was passiert mit den zugehörigen "
                          f"Objekten von {t}, wenn ein Objekt von {g} gelöscht wird?\n\nb) Kann ein Objekt von {t} zu mehreren "
                          f"Objekten von {g} gleichzeitig gehören?\n\nc) Kann ein Objekt von {t} ohne ein Objekt von {g} bestehen?")
    felder = [Feld("loeschen", f"{t} beim Löschen von {g}", "werden mitgelöscht" if komposition else "bleiben bestehen", typ="text",
                   optionen=["werden mitgelöscht", "bleiben bestehen"]),
              Feld("mehrere", f"Ein {t} in mehreren {g}?", "Ja" if gmax is None or gmax > 1 else "Nein", typ="text", optionen=["Ja", "Nein"]),
              Feld("ohne", f"Ein {t} ohne {g}?", "Ja" if gmin == 0 else "Nein", typ="text", optionen=["Ja", "Nein"])]
    weg = schritte(
        f"Die Raute sitzt an {g}, sie ist " + ("gefüllt: **Komposition**, die Teile leben nur mit dem Ganzen und werden **mitgelöscht**"
                                                if komposition else "leer: **Aggregation**, die Teile **bleiben bestehen**"),
        f"Am Ende von {g} steht `{mg}`: ein {t} gehört zu höchstens {_anzahl_text(gmax)} {g} → "
        + ("**Ja**, zu mehreren" if gmax is None or gmax > 1 else "**Nein**"),
        f"Mindestens {gmin} → " + ("**Ja**, ein Teil kann ohne Ganzes bestehen" if gmin == 0 else "**Nein**, jedes Teil braucht sein Ganzes"))
    return Aufgabe(frage, felder, weg, titel="Ganzes und Teil", **bild)


# --- Use-Case-Diagramm -----------------------------------------------------------------------------
# Ein System: Akteure (Name, allgemeiner Akteur oder None), die Anwendungsfälle der linken Spalte mit den Akteuren, die sie
# nutzen; include (Basis, eingebundener Fall, Anforderung), extend (Erweiterung, Basis, Anforderung). Eingebundene und
# erweiternde Fälle stehen in der rechten Spalte. Der allgemeine Akteur steht vor dem speziellen.

SYSTEME = [
    {"system": "Webshop", "thema": "einen Webshop", "akteure": [("Gast", None), ("Kunde", "Gast"), ("Mitarbeiter", None)],
     "faelle": [("Artikel suchen", ["Gast"]), ("Bestellung aufgeben", ["Kunde"]), ("Bewertung schreiben", ["Kunde"]),
                ("Artikel pflegen", ["Mitarbeiter"])],
     "include": [("Bestellung aufgeben", "Anmelden", "Wer eine Bestellung aufgibt, muss sich dabei jedes Mal anmelden."),
                 ("Bewertung schreiben", "Anmelden", "Vor jeder Bewertung meldet sich der Kunde an."),
                 ("Artikel pflegen", "Anmelden", "Mitarbeiter melden sich immer an, bevor sie Artikel pflegen.")],
     "extend": [("Gutschein einlösen", "Bestellung aufgeben", "Beim Bestellen kann ein Gutschein eingelöst werden, falls der Kunde einen hat."),
                ("Filter setzen", "Artikel suchen", "Bei der Suche lassen sich auf Wunsch Filter setzen.")]},
    {"system": "Bibliothekssystem", "thema": "das System einer Stadtbibliothek",
     "akteure": [("Besucher", None), ("Mitglied", "Besucher"), ("Bibliothekar", None)],
     "faelle": [("Katalog durchsuchen", ["Besucher"]), ("Medium ausleihen", ["Mitglied"]), ("Medium verlängern", ["Mitglied"]),
                ("Mahnung erstellen", ["Bibliothekar"])],
     "include": [("Medium ausleihen", "Ausweis prüfen", "Bei jeder Ausleihe wird der Ausweis des Mitglieds geprüft."),
                 ("Medium verlängern", "Ausweis prüfen", "Auch vor jeder Verlängerung wird der Ausweis geprüft."),
                 ("Mahnung erstellen", "Gebühr berechnen", "Zu jeder Mahnung wird die Mahngebühr berechnet.")],
     "extend": [("Medium vormerken", "Katalog durchsuchen", "Ist ein gefundenes Medium verliehen, kann es bei der Suche vorgemerkt werden."),
                ("Gebühr bezahlen", "Medium verlängern", "Ist die Leihfrist schon überschritten, wird beim Verlängern zusätzlich eine Gebühr bezahlt.")]},
    {"system": "Kinoportal", "thema": "das Ticketportal eines Kinos",
     "akteure": [("Besucher", None), ("Kunde", "Besucher"), ("Kassenkraft", None)],
     "faelle": [("Programm ansehen", ["Besucher"]), ("Ticket buchen", ["Kunde"]), ("Buchung stornieren", ["Kunde"]),
                ("Ticket verkaufen", ["Kassenkraft"])],
     "include": [("Ticket buchen", "Bezahlen", "Jede Buchung wird sofort bezahlt."),
                 ("Ticket verkaufen", "Bezahlen", "Auch an der Kasse wird jedes Ticket gleich bezahlt."),
                 ("Buchung stornieren", "Buchung suchen", "Zum Stornieren wird immer zuerst die Buchung gesucht.")],
     "extend": [("Sitzplatz wählen", "Ticket buchen", "Beim Buchen kann der Kunde auf Wunsch einen bestimmten Sitzplatz wählen."),
                ("Trailer ansehen", "Programm ansehen", "Im Programm lässt sich zu einem Film optional der Trailer abspielen.")]},
    {"system": "Lernplattform", "thema": "eine Lernplattform für Weiterbildungen",
     "akteure": [("Gast", None), ("Teilnehmer", "Gast"), ("Dozent", None)],
     "faelle": [("Kurse ansehen", ["Gast"]), ("Kurs belegen", ["Teilnehmer"]), ("Test ablegen", ["Teilnehmer"]), ("Kurs anlegen", ["Dozent"])],
     "include": [("Kurs belegen", "Anmelden", "Zum Belegen eines Kurses ist jedes Mal eine Anmeldung nötig."),
                 ("Test ablegen", "Ergebnis speichern", "Nach jedem Test wird das Ergebnis gespeichert."),
                 ("Kurs anlegen", "Material hochladen", "Zu jedem neuen Kurs lädt der Dozent das Kursmaterial hoch.")],
     "extend": [("Warteliste beitreten", "Kurs belegen", "Ist ein Kurs voll, kommt der Teilnehmer beim Belegen auf die Warteliste."),
                ("Zertifikat laden", "Test ablegen", "Wer einen Test besteht, kann danach ein Zertifikat herunterladen.")]},
    {"system": "Werkstattportal", "thema": "das Kundenportal einer Kfz-Werkstatt",
     "akteure": [("Kunde", None), ("Stammkunde", "Kunde"), ("Werkstattmeister", None)],
     "faelle": [("Termin buchen", ["Kunde"]), ("Rechnung ansehen", ["Kunde"]), ("Wartungshistorie ansehen", ["Stammkunde"]),
                ("Auftrag annehmen", ["Werkstattmeister"])],
     "include": [("Termin buchen", "Fahrzeug angeben", "Bei jeder Terminbuchung wird das Fahrzeug angegeben."),
                 ("Auftrag annehmen", "Kosten schätzen", "Zu jedem angenommenen Auftrag schätzt der Meister die Kosten.")],
     "extend": [("Ersatzwagen reservieren", "Termin buchen", "Bei der Terminbuchung kann bei Bedarf ein Ersatzwagen reserviert werden."),
                ("Rechnung herunterladen", "Rechnung ansehen", "Eine angesehene Rechnung lässt sich auf Wunsch als PDF herunterladen.")]},
]
U_RY, U_ABSTAND, U_SPALTE, U_AKTEUR = 20, 26, 150, 96  # halbe Höhe einer Ellipse, Abstand darunter, Spaltenlücke, Akteurabstand


def _rand(cx: float, cy: float, rx: float, ry: float, px: float, py: float) -> tuple[float, float]:
    """Der Punkt am Rand der Ellipse in Richtung (px, py)."""
    dx, dy = px - cx, py - cy
    t = 1 / math.hypot(dx / rx, dy / ry)
    return cx + dx * t, cy + dy * t


def _rechte_spalte(s: dict) -> dict[str, int]:
    """Zeile je eingebundenem und erweiterndem Fall: so, dass sich möglichst wenige «include»- und «extend»-Pfeile kreuzen, dann
    möglichst waagrecht. Alle Belegungen werden durchprobiert, es sind nur wenige Fälle."""
    reihe = [f for f, _ in s["faelle"]]
    paare = [(reihe.index(b), t) for b, t, _ in s["include"]] + [(reihe.index(b), e) for e, b, _ in s["extend"]]
    rechts = sorted({f for _, f in paare})

    def kosten(zeilen):
        z = dict(zip(rechts, zeilen))
        kreuzungen = sum(1 for (i, f), (j, g) in itertools.combinations(paare, 2) if (i - j) * (z[f] - z[g]) < 0)
        return kreuzungen * 1000 + sum(abs(i - z[f]) for i, f in paare), zeilen
    return dict(zip(rechts, min(kosten(p) for p in itertools.permutations(range(len(reihe) + 1), len(rechts)))[1]))


def _nutzt(s: dict, akteur: str) -> list[str]:
    """Anwendungsfälle des Akteurs, die vom allgemeinen Akteur geerbten mitgezählt."""
    eltern = dict(s["akteure"])[akteur]
    return [f for f, wer in s["faelle"] if akteur in wer] + (_nutzt(s, eltern) if eltern else [])


def usecasediagramm(s: dict, ohne: tuple = ()) -> Markup:
    """Systemgrenze mit zwei Spalten Ellipsen (links die Fälle der Akteure, rechts eingebundene und erweiternde), Akteure links
    davor, der spezielle unter dem allgemeinen. ohne: (von, nach) der «include»- und «extend»-Pfeile, die fehlen sollen."""
    links, rechts = [f for f, _ in s["faelle"]], _rechte_spalte(s)
    rx = {f: breite(f) / 2 + 22 for f in [*links, *rechts]}
    y = {f: i * (2 * U_RY + U_ABSTAND) + U_RY for i, f in enumerate(links)} | \
        {f: i * (2 * U_RY + U_ABSTAND) + U_RY for f, i in rechts.items()}
    x_rechts = max(2 * rx[f] for f in links) + U_SPALTE
    cx = {f: rx[f] for f in links} | {f: x_rechts + rx[f] for f in rechts}
    bild = Bild()
    unten, ende = max(y.values()) + U_RY + 20, max(cx[f] + rx[f] for f in cx) + 24
    bild.kasten(-24, -48, ende + 24, unten + 48, klasse=" uml-rahmen")
    bild.text(-14, -26, s["system"], klasse="uml-fett")
    for f in cx:
        bild.ellipse(cx[f], y[f], rx[f], U_RY)
        bild.text(cx[f], y[f] + 4, f, "middle")
    ax, oben, letzte = -24 - 110, {}, -math.inf
    for name, _ in s["akteure"]:
        ys = [y[f] for f, wer in s["faelle"] if name in wer]
        oben[name] = letzte = max(sum(ys) / len(ys) - 23, letzte + U_AKTEUR)
    for name, eltern in s["akteure"]:
        bild.strichmann(ax, oben[name])
        bild.text(ax, oben[name] + 60, name, "middle")
        if eltern:
            bild.pfeil([(ax, oben[name] - 2), (ax, oben[eltern] + 66)], form="dreieck")
    for f, wer in s["faelle"]:
        for name in wer:
            start = (ax + 16, oben[name] + 20)
            bild.linie([start, _rand(cx[f], y[f], rx[f], U_RY, *start)])
    pfeile = [(b, t, "«include»") for b, t, _ in s["include"]] + [(e, b, "«extend»") for e, b, _ in s["extend"]]
    pfeile.sort(key=lambda p: y[p[0]] != y[p[1]])  # waagrechte zuerst: ihre Beschriftung steht dann sicher über der eigenen Linie
    for von, nach, text in pfeile:
        if (von, nach) in ohne:
            continue
        a, b = _rand(cx[von], y[von], rx[von], U_RY, cx[nach], y[nach]), _rand(cx[nach], y[nach], rx[nach], U_RY, cx[von], y[von])
        bild.pfeil([a, b], gestrichelt=True)
        bild.an_linie(a, b, [text])
    akteure = "; ".join(n + (f" (erbt von {e})" if e else "") for n, e in s["akteure"])
    verbindungen = [f"{n} nutzt „{f}“" for f, wer in s["faelle"] for n in wer] + \
        [f"„{von}“ {text} „{nach}“" for von, nach, text in pfeile if (von, nach) not in ohne]
    return bild.svg("uml-usecase", f"Use-Case-Diagramm, System {s['system']}. Akteure: {akteure}. Anwendungsfälle: "
                                   f"{', '.join(f'„{f}“' for f in cx)}. Verbindungen: {'; '.join(verbindungen)}.")


@art("usecase", "Use-Case-Diagramm", "UML", "Anwendungsfälle lesen und modellieren: «include» oder «extend», Akteure mit Generalisierung",
     ("Use-Case", "Use Case", "Anwendungsfall", "Anwendungsfälle"), formeln=FORMELN["usecase"])
def usecase(rng):
    s = rng.choice(SYSTEME)
    firma = rng.choice(FIRMEN)
    einleitung = f"Die {firma} plant {s['thema']}. Das Use-Case-Diagramm unten zeigt den Stand der Analyse.\n\n"
    variante = rng.choice(["anforderung", "akteure", "lesen"])
    inc, ext = rng.choice(s["include"]), rng.choice(s["extend"])
    if variante == "anforderung":  # zwei Beziehungen fehlen im Bild, die Anforderungen beschreiben sie
        paare = [(inc[0], inc[1], "«include»", inc[2]), (ext[1], ext[0], "«extend»", ext[2])]  # (Basis, anderer Fall, …)
        rng.shuffle(paare)
        bild = usecasediagramm(s, ohne=((inc[0], inc[1]), (ext[0], ext[1])))
        frage = einleitung + "Zwei Anforderungen fehlen noch im Diagramm:\n\n" + "\n".join(
            f"{i}. {p[3]}" for i, p in enumerate(paare, start=1)) + "\n\nWie werden sie im Diagramm ergänzt?"
        felder, weg = [], []
        for i, (basis, anderer, text, satz) in enumerate(paare, start=1):
            felder += [Feld(f"b{i}", f"{i}. Beziehung", text, typ="text", optionen=["«include»", "«extend»"]),
                       Feld(f"z{i}", f"{i}. Pfeil zeigt auf", anderer if text == "«include»" else basis, typ="text",
                            optionen=sorted([basis, anderer]))]
            weg.append(f"„{satz}“ – " + (f"„{anderer}“ gehört **jedes Mal** zu „{basis}“: **«include»**, der Pfeil zeigt vom Basisfall "
                                         f"auf den eingebundenen Fall „{anderer}“." if text == "«include»" else
                                         f"„{anderer}“ kommt nur **unter einer Bedingung** dazu: **«extend»**, der Pfeil zeigt von der "
                                         f"Erweiterung auf den erweiterten Fall „{basis}“."))
        return Aufgabe(frage, felder, schritte(*weg), titel="include oder extend", struktogramm=bild)
    bild = usecasediagramm(s)
    if variante == "akteure":
        kind, eltern = next((n, e) for n, e in s["akteure"] if e)
        eigene, geerbte = [f for f, wer in s["faelle"] if kind in wer], _nutzt(s, eltern)
        nur_kind, nur_eltern = rng.choice(eigene), rng.choice(geerbte)
        fragen = [("kind", f"Darf {kind} „{nur_eltern}“ nutzen?", "Ja"), ("eltern", f"Darf {eltern} „{nur_kind}“ nutzen?", "Nein")]
        rng.shuffle(fragen)
        frage = einleitung + (f"a) Wie viele Anwendungsfälle darf der Akteur **{kind}** nutzen, die über die Generalisierung geerbten "
                              "mitgezählt? Fälle, die nur über «include» oder «extend» erreicht werden, zählen nicht.\n\n"
                              + "\n\n".join(f"{b}) {f[1]}" for b, f in zip("bc", fragen)))
        felder = [Feld("anzahl", f"Anwendungsfälle von {kind}", len(eigene) + len(geerbte), stellen=0)] + \
            [Feld(n, text, l, typ="text", optionen=["Ja", "Nein"]) for n, text, l in fragen]
        weg = schritte(f"{kind} ist direkt mit {_liste([f'„{f}“' for f in eigene])} verbunden ({len(eigene)})",
                       f"Das Dreieck zeigt auf {eltern}: {kind} ist ein spezieller {eltern} und erbt {_liste([f'„{f}“' for f in geerbte])} "
                       f"({len(geerbte)}), zusammen **{len(eigene) + len(geerbte)}**",
                       f"{kind} darf „{nur_eltern}“ nutzen (**Ja**, geerbt); {eltern} darf „{nur_kind}“ nicht (**Nein**): "
                       "geerbt wird nur vom allgemeinen zum speziellen Akteur")
        return Aufgabe(frage, felder, weg, titel="Akteure und Generalisierung", struktogramm=bild)
    fragen = [("inc", f"Läuft „{inc[1]}“ bei jedem „{inc[0]}“ mit?", "Ja"), ("ext", f"Läuft „{ext[0]}“ bei jedem „{ext[1]}“ mit?", "Nein")]
    rng.shuffle(fragen)
    alle = sorted([f for f, _ in s["faelle"]] + list(_rechte_spalte(s)))
    frage = einleitung + "\n\n".join(f"{b}) {f[1]}" for b, f in zip("ab", fragen)) + \
        f"\n\nc) Welchen Anwendungsfall erweitert „{ext[0]}“?"
    felder = [Feld(n, text, l, typ="text", optionen=["Ja", "Nein"]) for n, text, l in fragen] + \
        [Feld("basis", f"„{ext[0]}“ erweitert", ext[1], typ="text", optionen=alle)]
    weg = schritte(f"„{inc[0]}“ «include» „{inc[1]}“: der eingebundene Fall läuft **jedes Mal** mit → **Ja**",
                   f"„{ext[0]}“ «extend» „{ext[1]}“: die Erweiterung läuft nur unter einer Bedingung → **Nein**",
                   f"Der «extend»-Pfeil zeigt von der Erweiterung auf den erweiterten Fall: **{ext[1]}**")
    return Aufgabe(frage, felder, weg, titel="Beziehungen lesen", struktogramm=bild)


# --- Sequenzdiagramm -------------------------------------------------------------------------------
# Ein Ablauf: Teilnehmer (Lebenslinien) von links nach rechts, Nachrichten von oben nach unten als (von, an, Text, Art) mit
# Art sync (durchgezogen, gefüllte Spitze), async (durchgezogen, offene Spitze) oder antwort (gestrichelt, offene Spitze).

ABLAEUFE = [
    {"thema": "die Anmeldung an einem Kundenportal", "teilnehmer": [":Browser", ":Webserver", ":Datenbank", ":Protokoll"],
     "nachrichten": [(":Browser", ":Webserver", "anmelden(name, passwort)", "sync"),
                     (":Webserver", ":Datenbank", "pruefe(name, hash)", "sync"), (":Datenbank", ":Webserver", "gueltig", "antwort"),
                     (":Webserver", ":Protokoll", "schreibe(anmeldung)", "async"), (":Webserver", ":Browser", "sitzung", "antwort")]},
    {"thema": "den Bestellvorgang eines Onlineshops", "teilnehmer": [":Kunde", ":Shop", ":Lager", ":Zahlung", ":Versand"],
     "nachrichten": [(":Kunde", ":Shop", "bestellen(artikel)", "sync"), (":Shop", ":Lager", "reservieren(artikel)", "sync"),
                     (":Lager", ":Shop", "reserviert", "antwort"), (":Shop", ":Zahlung", "abbuchen(betrag)", "sync"),
                     (":Zahlung", ":Shop", "bestaetigt", "antwort"), (":Shop", ":Versand", "beauftragen(paket)", "async"),
                     (":Shop", ":Kunde", "bestellNr", "antwort")]},
    {"thema": "die Software eines Geldautomaten", "teilnehmer": [":Kunde", ":Automat", ":Bank"],
     "nachrichten": [(":Kunde", ":Automat", "karteEinstecken()", "async"), (":Kunde", ":Automat", "pinEingeben(pin)", "async"),
                     (":Automat", ":Bank", "pruefePin(karte, pin)", "sync"), (":Bank", ":Automat", "gueltig", "antwort"),
                     (":Kunde", ":Automat", "betragWaehlen(betrag)", "async"), (":Automat", ":Bank", "abheben(konto, betrag)", "sync"),
                     (":Bank", ":Automat", "freigabe", "antwort"), (":Automat", ":Kunde", "geldAusgeben(betrag)", "async")]},
    {"thema": "die Ticketbuchung eines Kinos", "teilnehmer": [":App", ":Buchung", ":Saalplan", ":Mail"],
     "nachrichten": [(":App", ":Buchung", "buchen(film, platz)", "sync"), (":Buchung", ":Saalplan", "sperren(platz)", "sync"),
                     (":Saalplan", ":Buchung", "gesperrt", "antwort"), (":Buchung", ":Mail", "sendeTicket(adresse)", "async"),
                     (":Buchung", ":App", "ticket", "antwort")]},
    {"thema": "den Druck aus einer Anwendung", "teilnehmer": [":Anwendung", ":Druckdienst", ":Drucker"],
     "nachrichten": [(":Anwendung", ":Druckdienst", "drucken(dokument)", "async"), (":Druckdienst", ":Drucker", "sendeDaten(seiten)", "sync"),
                     (":Drucker", ":Druckdienst", "fertig", "antwort"), (":Druckdienst", ":Anwendung", "auftragErledigt()", "async")]},
]
NACHRICHT = {"sync": "synchron", "async": "asynchron", "antwort": "Antwort"}
S_KOPF, S_ZEILE = 30, 36  # Höhe der Kästen oben, Abstand der Nachrichten


def sequenzdiagramm(ablauf: dict) -> Markup:
    """Lebenslinien mit Kasten und gestrichelter Linie, Nachrichten als waagrechte Pfeile; die Beschriftung steht über dem Pfeil
    gleich neben dem Sender, die Lücke dorthin ist so breit, dass sie keine Lebenslinie kreuzt."""
    t = ablauf["teilnehmer"]
    b = [breite(n) + 20 for n in t]
    luecke = [b[i] / 2 + b[i + 1] / 2 + 30 for i in range(len(t) - 1)]
    for von, an, text, _ in ablauf["nachrichten"]:
        i, j = t.index(von), t.index(an)
        k = i if j > i else i - 1  # die Lücke neben dem Sender in Richtung Empfänger
        luecke[k] = max(luecke[k], breite(text) + 24)
    x = [b[0] / 2]
    for g in luecke:
        x.append(x[-1] + g)
    unten = S_KOPF + S_ZEILE * (len(ablauf["nachrichten"]) + 1)
    bild = Bild()
    for n, xi, bi in zip(t, x, b):
        bild.kasten(xi - bi / 2, 0, bi, S_KOPF)
        bild.text(xi, S_KOPF / 2 + 4, n, "middle")
        bild.linie([(xi, S_KOPF), (xi, unten)], gestrichelt=True)
    for nr, (von, an, text, art_) in enumerate(ablauf["nachrichten"], start=1):
        xa, xb, y = x[t.index(von)], x[t.index(an)], S_KOPF + S_ZEILE * nr
        bild.pfeil([(xa, y), (xb, y)], form="voll" if art_ == "sync" else "offen", gestrichelt=art_ == "antwort")
        bild.beschriftung([(xa + 8, y - 5, "start") if xb > xa else (xa - 8, y - 5, "end")], [text])
    nachrichten = "; ".join(f"{nr}. {NACHRICHT[a]} von {v} an {n}: {txt}" for nr, (v, n, txt, a) in enumerate(ablauf["nachrichten"], start=1))
    return bild.svg("uml-sequenz", f"Sequenzdiagramm mit den Lebenslinien {', '.join(t)}. Nachrichten von oben nach unten: {nachrichten}.")


def _aufruf(ablauf: dict, antwort: int) -> int:
    """Index des synchronen Aufrufs, zu dem die Antwort gehört: der letzte noch offene in der Gegenrichtung."""
    offen = []
    for i, (von, an, _, art_) in enumerate(ablauf["nachrichten"][:antwort + 1]):
        if art_ == "sync":
            offen.append(i)
        elif art_ == "antwort":
            treffer = next(k for k in reversed(offen) if ablauf["nachrichten"][k][:2] == (an, von))
            offen.remove(treffer)
            if i == antwort:
                return treffer
    raise ValueError("keine Antwort")


@art("sequenz", "Sequenzdiagramm", "UML", "Sequenzdiagramme lesen: synchron, asynchron, Antworten und Reihenfolge",
     ("Sequenzdiagramm",), formeln=FORMELN["sequenz"])
def sequenz(rng):
    ablauf = rng.choice(ABLAEUFE)
    n, t = ablauf["nachrichten"], ablauf["teilnehmer"]
    einleitung = (f"Die {rng.choice(FIRMEN)} dokumentiert {ablauf['thema']}. Das Sequenzdiagramm unten zeigt den Ablauf.\n\n")
    bild = sequenzdiagramm(ablauf)
    if rng.random() < 0.5:
        gefragt = sorted(rng.sample(range(len(n)), 2))
        warten = rng.choice([i for i, m in enumerate(n) if m[3] != "antwort"])
        frage = einleitung + "a) Um welche Art von Nachricht handelt es sich jeweils?\n\n" + \
            f"b) Wartet {n[warten][0]} nach dem Senden von `{n[warten][2]}` auf eine Antwort?"
        felder = [Feld(f"art{i}", f"„{n[i][2]}“", NACHRICHT[n[i][3]], typ="text", optionen=list(NACHRICHT.values())) for i in gefragt] + \
            [Feld("warten", f"{n[warten][0]} wartet?", "Ja" if n[warten][3] == "sync" else "Nein", typ="text", optionen=["Ja", "Nein"])]
        zeichen = {"sync": "durchgezogen mit gefüllter Spitze", "async": "durchgezogen mit offener Spitze", "antwort": "gestrichelt"}
        weg = schritte(*(f"`{n[i][2]}`: {zeichen[n[i][3]]} → **{NACHRICHT[n[i][3]]}**" for i in gefragt),
                       f"`{n[warten][2]}` ist {NACHRICHT[n[warten][3]]}: " + ("der Sender wartet auf die Antwort → **Ja**" if n[warten][3] == "sync"
                                                                             else "der Sender arbeitet sofort weiter → **Nein**"))
        return Aufgabe(frage, felder, weg, titel="Nachrichtenarten", struktogramm=bild)
    ziel = rng.choice(t[1:])
    antwort = rng.choice([i for i, m in enumerate(n) if m[3] == "antwort"])
    aufruf = _aufruf(ablauf, antwort)
    an_ziel = [m for m in n if m[1] == ziel]
    aufrufe = [m[2] for m in n if m[3] == "sync"]
    frage = einleitung + (f"a) Wie viele Nachrichten empfängt **{ziel}**, Antworten mitgezählt?\n\n"
                          f"b) Auf welchen Aufruf antwortet die Nachricht `{n[antwort][2]}`?")
    felder = [Feld("anzahl", f"Nachrichten an {ziel}", len(an_ziel), stellen=0),
              Feld("aufruf", f"„{n[antwort][2]}“ antwortet auf", n[aufruf][2], typ="text", optionen=aufrufe)]
    weg = schritte(f"Pfeile, die bei {ziel} ankommen: " + (", ".join(f"`{m[2]}`" for m in an_ziel) or "keine") + f" → **{len(an_ziel)}**",
                   f"`{n[antwort][2]}` geht gestrichelt von {n[antwort][0]} an {n[antwort][1]}; der letzte noch offene synchrone Aufruf "
                   f"von {n[antwort][1]} an {n[antwort][0]} davor ist **{n[aufruf][2]}**")
    return Aufgabe(frage, felder, weg, titel="Ablauf", struktogramm=bild)
