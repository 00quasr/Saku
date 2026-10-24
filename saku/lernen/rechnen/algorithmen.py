"""Algorithmen: Sortieren, binäre Suche, Hashing, binärer Suchbaum, Stack und Queue.
Jede Lösung entsteht durch echtes Ausführen des Verfahrens; der Rechenweg zeigt jeden Zwischenstand."""

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, schritte, tabelle

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "sortieren": """- Bubblesort: benachbarte Werte vergleichen und tauschen, wenn links > rechts; nach Durchlauf k stehen die k größten Werte hinten
- Selectionsort: im unsortierten Rest das Minimum suchen und mit der ersten Stelle des Rests tauschen; nach Durchlauf k sind die ersten k Stellen fertig
- Insertionsort: den nächsten Wert in den sortierten Anfang einfügen, Größere rücken nach rechts; nach Durchlauf k sind die ersten k + 1 Werte sortiert
- Vertauschungen Bubblesort = Anzahl der Paare, die falsch herum stehen; ein Array mit n Werten braucht höchstens n − 1 Durchläufe

*Beispiel:* Bubblesort [5, 1, 4, 2], Durchlauf 1: [1, 4, 2, 5] mit 3 Vertauschungen""",
    "binaersuche": """- Voraussetzung: das Array ist sortiert
- links ← 0, rechts ← n − 1; solange links ≤ rechts: mitte ← (links + rechts) DIV 2
- Wert gefunden → fertig; Wert an der Mitte zu klein → links ← mitte + 1; zu groß → rechts ← mitte − 1
- Höchstens ⌊log₂ n⌋ + 1 Vergleiche (bei 15 Werten 4)

*Beispiel:* [3, 8, 12, 17, 21, 30, 42], gesucht 30: mitte 3 (17, zu klein), mitte 5 (30, gefunden) → 2 Vergleiche""",
    "hashing": """- Hashfunktion h(k) = k MOD m, m = Größe der Tabelle (Indizes 0 bis m − 1)
- Kollision (Platz belegt): lineares Sondieren, den nächsten Index probieren: (i + 1) MOD m, nach dem letzten Index geht es bei 0 weiter
- Suchen läuft genauso: ab h(k) weiter, bis der Schlüssel oder ein leerer Platz kommt
- Belegungsfaktor = Anzahl Schlüssel : m

*Beispiel:* m = 7, Schlüssel 15, 22: 15 MOD 7 = 1 → Index 1; 22 MOD 7 = 1 belegt → Index 2""",
    "baum": """- Binärer Suchbaum: links stehen kleinere, rechts größere Schlüssel; Einfügen von der Wurzel aus nach links oder rechts bis zu einem freien Platz
- Preorder: Wurzel, links, rechts · Inorder: links, Wurzel, rechts (ergibt die sortierte Folge) · Postorder: links, rechts, Wurzel
- Höhe hier als Anzahl der Ebenen: nur die Wurzel hat Höhe 1

*Beispiel:* Einfügen 50, 30, 70, 20: Preorder 50, 30, 20, 70 · Inorder 20, 30, 50, 70 · Postorder 20, 30, 70, 50 · Höhe 3""",
    "stapel": """- Stack (Stapel, LIFO): push legt oben auf, pop nimmt das oberste Element (zuletzt hinein, zuerst heraus)
- Queue (Warteschlange, FIFO): enqueue stellt hinten an, dequeue nimmt das vorderste Element (zuerst hinein, zuerst heraus)
- Für jede Operation den Inhalt notieren; ausgegeben wird, was pop bzw. dequeue zurückgibt

*Beispiel:* push 3, push 5, pop, push 7 → Stack von unten nach oben [3, 7], Ausgabe 5""",
}

THEMEN = {
    "sortieren": ("Sortier", "Bubblesort", "Selectionsort", "Insertionsort"),
    "binaersuche": ("Suchalgorithm", "Binäre Suche", "Binärsuche"),
    "hashing": ("Hashtabelle", "Hashing", "Assoziativ"),
    "baum": ("Bäume", "Binärbaum", "Suchbaum", "Baumstruktur"),
    "stapel": ("Stack", "Queue", "Stapel", "Warteschlange", "Datenstruktur"),
}


def _liste(werte) -> str:
    return ", ".join(map(str, werte))


def _array_zeile(name: str, werte: list, label: str) -> list:
    """Eine Tabellenzeile mit je einem Eingabefeld pro Index."""
    return [Feld(f"{name}{i}", f"{label}, Index {i}", w, stellen=0) for i, w in enumerate(werte)]


# --- Sortieren --------------------------------------------------------------

def bubblesort(werte: list) -> list[tuple[list, int]]:
    """(Array nach dem Durchlauf, Vertauschungen im Durchlauf) für jeden Durchlauf."""
    a, raus = list(werte), []
    for i in range(len(a) - 1):
        getauscht = 0
        for j in range(len(a) - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                getauscht += 1
        raus.append((list(a), getauscht))
    return raus


def selectionsort(werte: list) -> list[tuple[list, int]]:
    a, raus = list(werte), []
    for i in range(len(a) - 1):
        k = min(range(i, len(a)), key=a.__getitem__)
        if k != i:
            a[i], a[k] = a[k], a[i]
        raus.append((list(a), int(k != i)))
    return raus


def insertionsort(werte: list) -> list[tuple[list, int]]:
    """Zweiter Wert: wie viele Werte nach rechts gerückt sind."""
    a, raus = list(werte), []
    for i in range(1, len(a)):
        x, j = a[i], i - 1
        while j >= 0 and a[j] > x:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = x
        raus.append((list(a), i - 1 - j))
    return raus


VERFAHREN = {"Bubblesort": bubblesort, "Selectionsort": selectionsort, "Insertionsort": insertionsort}


@art("sortieren", "Sortieren", "Algorithmen", "Bubblesort, Selectionsort, Insertionsort: das Array nach jedem Durchlauf",
     THEMEN["sortieren"], formeln=FORMELN["sortieren"])
def sortieren(rng):
    werte = rng.sample(range(1, 100), rng.randint(6, 9))
    name = rng.choice(list(VERFAHREN))
    verlauf = VERFAHREN[name](werte)
    zaehlt = {"Bubblesort": "Vertauschungen", "Selectionsort": "Vertauschungen", "Insertionsort": "verschobene Werte"}[name]
    weg = (f"{name}, aufsteigend:\n\n"
           + tabelle(["Durchlauf", "Array danach", zaehlt], [["Start", _liste(werte), ""]] +
                     [[n, _liste(a), z] for n, (a, z) in enumerate(verlauf, start=1)])
           + "\n\n" + FORMELN["sortieren"].split("\n")[list(VERFAHREN).index(name)].removeprefix("- "))
    frage = f"Ein Programm der {rng.choice(FIRMEN)} sortiert das Array\n\n`[{_liste(werte)}]`\n\naufsteigend mit **{name}**."
    if name != "Insertionsort" and rng.random() < 0.35:
        konvention = " Beim Selectionsort zählt ein Tausch nur, wenn das Minimum nicht schon vorn steht." if name == "Selectionsort" else ""
        frage += f"\n\nWie viele Vertauschungen führt das Verfahren insgesamt durch, bis das Array sortiert ist?{konvention}"
        return Aufgabe(frage, [Feld("tausch", "Vertauschungen insgesamt", sum(z for _, z in verlauf), stellen=0)], weg,
                       titel=f"{name}: Vertauschungen")
    k = rng.randint(1, min(3, len(verlauf) - 1))
    nach = verlauf[k - 1][0]
    zeile = _array_zeile("i", nach, f"nach Durchlauf {k}")
    frage += f"\n\nWie sieht das Array nach dem **{k}. Durchlauf** aus?"
    return Aufgabe(frage, zeile, weg, titel=f"{name}: nach Durchlauf {k}",
                   tabelle=[["Index", *map(str, range(len(nach)))], [f"nach {k}.", *zeile]])


# --- Binäre Suche ------------------------------------------------------------

def binaere_suche(werte: list, gesucht: int) -> list[tuple[int, int, int, str]]:
    """(links, rechts, mitte, Entscheidung) je Vergleich."""
    links, rechts, raus = 0, len(werte) - 1, []
    while links <= rechts:
        mitte = (links + rechts) // 2
        if werte[mitte] == gesucht:
            raus.append((links, rechts, mitte, "gefunden"))
            break
        if werte[mitte] < gesucht:
            raus.append((links, rechts, mitte, f"{werte[mitte]} < {gesucht} → links ← {mitte + 1}"))
            links = mitte + 1
        else:
            raus.append((links, rechts, mitte, f"{werte[mitte]} > {gesucht} → rechts ← {mitte - 1}"))
            rechts = mitte - 1
    return raus


@art("binaersuche", "Binäre Suche", "Algorithmen", "Welche Elemente werden verglichen, wie viele Vergleiche?",
     THEMEN["binaersuche"], formeln=FORMELN["binaersuche"])
def binaersuche(rng):
    werte = sorted(rng.sample(range(2, 100), rng.randint(9, 15)))
    vorhanden = rng.random() < 0.7
    gesucht = rng.choice(werte) if vorhanden else rng.choice([x for x in range(1, 101) if x not in werte])
    verlauf = binaere_suche(werte, gesucht)
    verglichen = [werte[m] for _, _, m, _ in verlauf]
    frage = (f"Die Artikelnummern im Lager der {rng.choice(FIRMEN)} liegen sortiert in einem Array (Index ab 0):\n\n"
             f"`[{_liste(werte)}]`\n\nGesucht wird **{gesucht}** mit binärer Suche: links ← 0, rechts ← {len(werte) - 1}, "
             "mitte ← (links + rechts) DIV 2.\n\nWelche Werte werden nacheinander mit dem gesuchten Wert verglichen, und wie viele "
             "Vergleiche sind es?")
    weg = (tabelle(["Vergleich", "links", "rechts", "mitte", "Wert an mitte", "Entscheidung"],
                   [[n, l, r, m, werte[m], e] for n, (l, r, m, e) in enumerate(verlauf, start=1)])
           + ("" if vorhanden else f"\n\nDanach ist links > rechts: **{gesucht}** steht nicht im Array."))
    felder = [Feld("werte", "Verglichene Werte", _liste(verglichen), typ="liste"),
              Feld("anzahl", "Anzahl Vergleiche", len(verglichen), stellen=0)]
    return Aufgabe(frage, felder, weg, titel="Gefunden" if vorhanden else "Nicht gefunden")


# --- Hashing -------------------------------------------------------------------

def einfuegen(schluessel: list, m: int) -> tuple[list, list[tuple[int, list[int]]]]:
    """Tabelle nach linearem Sondieren und je Schlüssel die probierten Indizes."""
    tabelle_, wege = [None] * m, []
    for k in schluessel:
        i, probiert = k % m, []
        while tabelle_[i] is not None:
            probiert.append(i)
            i = (i + 1) % m
        tabelle_[i] = k
        wege.append((k, probiert + [i]))
    return tabelle_, wege


@art("hashing", "Hashing", "Algorithmen", "h(k) = k MOD m mit linearem Sondieren: wo landet welcher Schlüssel?",
     THEMEN["hashing"], formeln=FORMELN["hashing"])
def hashing(rng):
    while True:
        m = rng.choice([7, 10, 11])
        schluessel = rng.sample(range(10, 100), rng.randint(5, min(7, m - 2)))
        belegung, wege = einfuegen(schluessel, m)
        if sum(len(p) > 1 for _, p in wege) >= 2:  # mindestens zwei Kollisionen, sonst gibt es nichts zu sondieren
            break
    frage = (f"Die {rng.choice(FIRMEN)} speichert Kundennummern in einer Hashtabelle mit **m = {m}** Plätzen (Index 0 bis {m - 1}). "
             f"Hashfunktion h(k) = k MOD {m}, bei Kollision lineares Sondieren (nächster Index, nach {m - 1} folgt 0).\n\n"
             f"Eingefügt werden nacheinander: **{_liste(schluessel)}**")
    weg = schritte(*(f"{k} MOD {m} = {p[0]}" + ("" if len(p) == 1 else " belegt → " + " → ".join(map(str, p[1:])))
                     + f" → Index **{p[-1]}**" for k, p in wege))
    weg += "\n\n" + tabelle(["Index", *map(str, range(m))], [["Schlüssel", *("–" if w is None else w for w in belegung)]])
    if rng.random() < 0.5:
        zeile = [Feld(f"i{i}", f"Index {i}", "" if w is None else w, typ="text" if w is None else "zahl", stellen=0)
                 for i, w in enumerate(belegung)]
        frage += "\n\nTragen Sie die Belegung der Tabelle nach allen Einfügungen ein (freie Plätze leer lassen)."
        return Aufgabe(frage, zeile, weg, titel="Belegung der Tabelle",
                       tabelle=[["Index", *map(str, range(m))], ["Schlüssel", *zeile]])
    k, pfad = max(wege, key=lambda w: (len(w[1]), w[0]))
    frage += f"\n\nAn welchem Index steht der Schlüssel **{k}**, und wie viele Plätze werden beim Einfügen von {k} probiert?"
    felder = [Feld("index", f"Index von {k}", pfad[-1], stellen=0), Feld("probiert", "Probierte Plätze", len(pfad), stellen=0)]
    return Aufgabe(frage, felder, weg, titel="Index eines Schlüssels")


# --- Binärer Suchbaum ---------------------------------------------------------------

def suchbaum(schluessel: list) -> dict:
    """Knoten als dict {wert, links, rechts}."""
    wurzel = None
    for k in schluessel:
        neu = {"wert": k, "links": None, "rechts": None}
        if wurzel is None:
            wurzel = neu
            continue
        knoten = wurzel
        while True:
            seite = "links" if k < knoten["wert"] else "rechts"
            if knoten[seite] is None:
                knoten[seite] = neu
                break
            knoten = knoten[seite]
    return wurzel


def durchlauf(k, art_: str) -> list:
    if k is None:
        return []
    l, r = durchlauf(k["links"], art_), durchlauf(k["rechts"], art_)
    return {"pre": [k["wert"], *l, *r], "in": [*l, k["wert"], *r], "post": [*l, *r, k["wert"]]}[art_]


def hoehe(k) -> int:
    return 0 if k is None else 1 + max(hoehe(k["links"]), hoehe(k["rechts"]))


def zeichnen(k, praefix: str = "", seite: str = "") -> list[str]:
    """Eingerückte Darstellung: L/R vor jedem Kind."""
    if k is None:
        return []
    zeilen_ = [f"{praefix}{seite}{k['wert']}"]
    kinder = [(s, k[n]) for s, n in (("L: ", "links"), ("R: ", "rechts")) if k[n]]
    for i, (s, kind) in enumerate(kinder):
        letztes = i == len(kinder) - 1
        weiter = praefix + ("    " if not seite else ("    " if seite.startswith("└") else "│   "))
        zeilen_ += zeichnen(kind, weiter if seite else "", ("└─ " if letztes else "├─ ") + s)
    return zeilen_


ORDNUNGEN = {"pre": "Preorder", "in": "Inorder", "post": "Postorder"}


@art("baum", "Binärer Suchbaum", "Algorithmen", "Einfügen, Preorder, Inorder, Postorder und Höhe",
     THEMEN["baum"], formeln=FORMELN["baum"])
def baum(rng):
    while True:
        schluessel = rng.sample(range(10, 100), rng.randint(7, 9))
        wurzel = suchbaum(schluessel)
        if 3 <= hoehe(wurzel) <= 5:
            break
    gefragt = rng.sample(list(ORDNUNGEN), 2)
    frage = (f"Die {rng.choice(FIRMEN)} legt Produktnummern in einem binären Suchbaum ab (kleinere links, größere rechts). "
             f"Eingefügt werden nacheinander:\n\n**{_liste(schluessel)}**\n\n"
             f"Geben Sie die Ausgabe der Durchläufe {ORDNUNGEN[gefragt[0]]} und {ORDNUNGEN[gefragt[1]]} an sowie die Höhe des Baums "
             "(Anzahl der Ebenen, nur die Wurzel hat Höhe 1).")
    weg = ("Der Baum nach allen Einfügungen:\n\n```\n" + "\n".join(zeichnen(wurzel)) + "\n```\n\n"
           + schritte(*(f"{ORDNUNGEN[o]}: **{_liste(durchlauf(wurzel, o))}**" for o in ORDNUNGEN),
                      f"Höhe: längster Weg von der Wurzel bis zu einem Blatt hat **{hoehe(wurzel)} Ebenen**"))
    felder = [Feld(o, ORDNUNGEN[o], _liste(durchlauf(wurzel, o)), typ="liste") for o in gefragt]
    felder.append(Feld("hoehe", "Höhe (Ebenen)", hoehe(wurzel), stellen=0))
    return Aufgabe(frage, felder, weg, titel=" und ".join(ORDNUNGEN[o] for o in gefragt))


# --- Stack und Queue ---------------------------------------------------------------

@art("stapel", "Stack und Queue", "Algorithmen", "push/pop und enqueue/dequeue: was wird ausgegeben, was bleibt?",
     THEMEN["stapel"], formeln=FORMELN["stapel"])
def stapel(rng):
    stack = rng.random() < 0.5
    rein, raus_ = ("push", "pop") if stack else ("enqueue", "dequeue")
    inhalt, ausgabe, ops, zeilen_ = [], [], [], []
    werte = iter(rng.sample(range(1, 50), 12))
    for _ in range(rng.randint(8, 11)):
        if inhalt and (len(inhalt) >= 4 or rng.random() < 0.4):
            wert = inhalt.pop() if stack else inhalt.pop(0)
            ausgabe.append(wert)
            ops.append(f"{raus_}()")
            zeilen_.append([len(ops), f"{raus_}()", f"[{_liste(inhalt)}]", wert])
        else:
            wert = next(werte)
            inhalt.append(wert)
            ops.append(f"{rein}({wert})")
            zeilen_.append([len(ops), f"{rein}({wert})", f"[{_liste(inhalt)}]", ""])
    if not inhalt:  # am Ende soll etwas übrig sein, sonst ist die zweite Frage leer
        inhalt.append(next(werte))
        ops.append(f"{rein}({inhalt[-1]})")
        zeilen_.append([len(ops), ops[-1], f"[{_liste(inhalt)}]", ""])
    richtung = "von unten nach oben" if stack else "von vorn nach hinten"
    name = "Stack (Stapel, LIFO)" if stack else "Queue (Warteschlange, FIFO)"
    frage = (f"Ein Druckdienst der {rng.choice(FIRMEN)} verwaltet Aufträge in einer **{name}**, die anfangs leer ist. "
             f"Ausgeführt werden nacheinander:\n\n`{'; '.join(ops)}`\n\nWelche Werte geben die {raus_}-Aufrufe der Reihe nach "
             f"zurück, und was steht am Ende in der Datenstruktur ({richtung})?")
    weg = tabelle(["Schritt", "Operation", f"Inhalt danach ({richtung})", "Ausgabe"], zeilen_)
    felder = [Feld("ausgabe", f"Ausgabe der {raus_}-Aufrufe", _liste(ausgabe), typ="liste"),
              Feld("inhalt", f"Inhalt am Ende ({richtung})", _liste(inhalt), typ="liste")]
    return Aufgabe(frage, felder, weg, titel="Stack" if stack else "Queue")
