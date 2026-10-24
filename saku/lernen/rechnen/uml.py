"""UML lesen: Zustands-, Klassen-, Use-Case- und Sequenzdiagramme aus erfundenen Modellen, gezeichnet als SVG (svg.py).
Jedes Modell ist ein kleines Datenstück; dasselbe Stück wird gezeichnet, als Text beschrieben (aria-label) und für die Lösung
ausgewertet. Alle Systeme, Klassen und Abläufe sind erfunden."""

from markupsafe import Markup

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, tabelle
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
    """Zufällige Ereignisfolge ab dem Start: meist ein Ereignis, das gerade schaltet, manchmal eines, das verfällt."""
    alle, folge = sorted({u[1] for u in a["uebergaenge"]}), []
    for _ in range(laenge):
        zustand, zaehler = nachspielen(a, folge)[-1][3:] if folge else (next(iter(a["zustaende"])), 0)
        moeglich = sorted({u[1] for u in a["uebergaenge"] if u[0] == zustand and (not u[2] or OPS[u[2][0]](zaehler, u[2][1]))})
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
     ("Zustandsdiagramm", "Zustandsautomat", "Zustandsübergang"), formeln=FORMELN["zustand"])
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
    optionen = [", ".join(f) for f in folgen]
    frage = (einleitung + f"Welche Ereignisfolge führt vom Startzustand „{start}“ in den Zustand **„{ziel}“**?")
    weg = "\n\n".join(f"`{o}` endet in **{nachspielen(a, f)[-1][3]}**" + (" ✓" if f == richtig else "") for o, f in zip(optionen, folgen))
    weg += f"\n\nDie richtige Folge nachgespielt:\n\n{_spur(a, richtig)}"
    return Aufgabe(frage, [Feld("folge", "Ereignisfolge", ", ".join(richtig), typ="text", optionen=optionen)], weg,
                   titel="Ereignisfolge finden", struktogramm=zustandsdiagramm(a))
