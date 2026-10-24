"""Stichpunkt-Abgleich für Freitext-Antworten in Üben: kostenlos und ohne KI.
Die Musterlösung wird in erwartete Punkte zerlegt; ein Punkt gilt als erkannt, wenn genug seiner bedeutsamen Wörter in der
eigenen Antwort vorkommen. Nur eine Hilfe: bewertet wird weiter mit 1, 2, 3 von Hand."""

import math
import re

from saku.lernen import operatoren
from saku.lernen.karten import ergebnis_aus_punkten

HOECHSTENS = 10  # Punkte je Musterlösung; mehr sind meist Beispiele derselben Sache
STAMM = 5  # gleicher Anfang ab so vielen Zeichen …
STAMM_ANTEIL = 0.7  # … der mindestens 70 % des längeren Worts ausmacht: „verschlüsselt“ ↔ „Verschlüsselung“, nicht „Daten“ ↔ „Datenbank“
# Erkannt ab der Hälfte der bedeutsamen Wörter, aber nie mehr als drei verlangt: ein langer Lösungssatz soll nicht an einer
# Stichpunkt-Antwort scheitern, die nur die Kernbegriffe nennt. Ein getroffener Fachbegriff (VPN, IPv6, TCP/IP) reicht allein.
ANTEIL, HOECHSTENS_NOETIG = 0.5, 3

STOPPWOERTER = set("""
aber alle allem allen aller alles als also am an andere anderem anderen anderer anderes auch auf aus bei beim bereits bin bis bist
bzw da dabei dadurch dafuer daher damit dann darauf darf das dass dazu dein dem den denen denn der deren des dessen deshalb die dies
diese diesem diesen dieser dieses doch dort du durch eben eher eigene eigenen ein eine einem einen einer eines einige einzelne er es
etc etwa euer falls fuer gegen gegenueber ggf gibt gilt hat hatte hatten haben hier hin ich ihr ihre ihren im in indem ins ist ja je
jede jedem jeden jeder jedes jeweils kann kein keine keinen koennen koennte man mehr mehrere mit mittels moeglich moegliche moeglichen
muss muessen nach neben nicht noch nur ob oder ohne sehr sein seine seinen sich sie sind so sodass soll sollen sollte sowie sowohl
ueber um und uns unter usw viel viele vom von vor waehrend wann war waren was weil welche welchen welcher welches wenn wer werden wie
wird wir wo wobei wurde wurden z zu zum zur zwischen beispiel beispiele beispielsweise antwort antworten loesung loesungen punkt
punkte richtig falsch hinweis
""".split())
FLOSKEL = re.compile(r"^(lösungshinweis(e)?|lösungsvorschlag|musterlösung|lösung|hinweis|beispiele?|z\.\s*b\.|u\.\s*a\.|"
                     r"mögliche (antworten|lösungen|nennungen)|erwartungshorizont|antwort(en)?)\s*:?$", re.I)
ZAHLWOERTER = {"zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8}
# Operatoren, bei denen eine Zahl vor dem Substantiv die Anzahl der erwarteten Punkte meint (nicht bei Berechnen: „für zwei Jahre“)
AUFZAEHLEND = {"nennen", "angeben", "identifizieren", "beschreiben", "unterscheiden", "erklaeren", "erlaeutern", "begruenden"}
# Wort mit Punkt, Bindestrich oder Schrägstrich im Inneren (802.1X, Client-Server, TCP/IP), Zahl mit Dezimalkomma (7,4)
WORT = re.compile(r"[A-Za-zÄÖÜäöüß0-9](?:[A-Za-zÄÖÜäöüß0-9]|[./\-](?=[A-Za-zÄÖÜäöüß0-9])|(?<=\d),(?=\d))*")


def normal(wort: str) -> str:
    return wort.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def fachbegriff(wort: str) -> bool:
    """Abkürzung (zwei Großbuchstaben), Zahl ab zwei Zeichen (7,4 oder 802.1X, nicht „3“) oder Kompositum mit - oder /."""
    return sum(c.isupper() for c in wort) >= 2 or (any(c.isdigit() for c in wort) and len(wort) >= 2) or "-" in wort or "/" in wort


def bedeutsam(text: str) -> list[str]:
    """Wörter, die etwas aussagen, im Original (ohne Stoppwörter; kurze nur als Abkürzung oder mit Ziffer)."""
    return [w for w in WORT.findall(text) if normal(w) not in STOPPWOERTER and (len(w) >= 3 or fachbegriff(w))]


def _klar(text: str) -> str:
    """Markdown ohne Bilder, Links, Hervorhebungen, Überschriften und Punkteangaben wie „(je 1 Punkt)“."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text or "")
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\*\*|__|`+|<br\s*/?>", " ", text)
    text = re.sub(r"\(\s*(?:je\s*)?\d+(?:[,.]\d+)?\s*(?:punkte?|p\.)\s*\)", "", text, flags=re.I)
    return re.sub(r"^\s*#+\s*", "", text, flags=re.M)


def zerlegen(loesung: str) -> list[str]:
    """Erwartete Punkte: Aufzählung, sonst Tabellenzeilen (ohne Kopf), sonst Sätze; Floskeln und Einleitungen fallen weg."""
    zeilen = [z.strip() for z in _klar(loesung).splitlines() if z.strip()]
    aufzaehlung = [m[1] for z in zeilen if (m := re.match(r"^(?:[-*•–]|\d+[.)]|[a-z][.)])\s+(.+)$", z))]
    tabelle = [z for z in zeilen if z.startswith("|") and not re.fullmatch(r"[|:\-\s]+", z)]
    if len(aufzaehlung) >= 2:
        punkte = aufzaehlung
    elif len(tabelle) >= 2:  # erste Zeile ist der Kopf
        punkte = [" – ".join(c.strip() for c in z.strip("|").split("|") if c.strip()) for z in tabelle[1:]]
    else:
        text = " ".join(z for z in zeilen if not FLOSKEL.match(z))
        text = re.sub(r"\b([A-Za-z])\.\s+([A-Za-z])\.", r"\1.\2.", text)  # „z. B.“, „d. h.“, „u. a.“ ohne Leerzeichen
        # Satzende nach zwei Buchstaben oder Ziffern („Netze.“, „WAN.“), nicht nach einer Abkürzung wie „z.B.“
        punkte = re.split(r"(?<=[A-Za-zÄÖÜäöüß0-9)]{2}[.!?;])(?<![A-Za-z]\.[A-Za-z]\.)\s+(?=[A-ZÄÖÜ0-9])", text)
    raus = []
    for p in punkte:
        p = re.sub(r"^(?:z\.\s*b\.|beispiele?|u\.\s*a\.|etwa)\s*:?\s*", "", p.strip(), flags=re.I).strip()
        if p and not FLOSKEL.match(p) and not p.endswith(":") and bedeutsam(p):
            raus.append(p)
    return raus[:HOECHSTENS]


def verlangte_anzahl(aufgabe: str) -> int | None:
    """„Nennen Sie zwei Vorteile und drei Nachteile“ → 5: Zahl vor einem Substantiv in den Sätzen mit Operator."""
    summe = 0
    for satz in re.split(r"(?<=[.!?])\s+", aufgabe or ""):
        if not {o["schluessel"] for o in operatoren.erkennen(satz)} & AUFZAEHLEND:
            continue
        for zahl in re.findall(r"\b((?i:zwei|drei|vier|fünf|sechs|sieben|acht)|[2-8])\s+(?:[a-zäöüß]+e[nrs]?\s+)?[A-ZÄÖÜ]\w+", satz):
            summe += ZAHLWOERTER.get(zahl.lower(), 0) or int(zahl)
    return summe or None


def _gleich(a: str, b: str) -> bool:
    if a == b:
        return True
    gemeinsam = len(next((a[:i] for i in range(min(len(a), len(b)), 0, -1) if a[:i] == b[:i]), ""))
    return gemeinsam >= STAMM and gemeinsam >= STAMM_ANTEIL * max(len(a), len(b))


def _teile(wort: str) -> list[str]:
    return [t for t in re.split(r"[-/]", wort) if len(t) >= 2]


def _vorkommt(wort: str, menge: set[str]) -> bool:
    """Kommt das Wort (normalisiert) in der Menge vor, auch über den Stamm oder bei Komposita über die Teile
    (alle bis auf einen, mindestens zwei: „Client und Server“ trifft „Client-Server-Modell“, TCP/IP braucht beide)?"""
    if any(_gleich(wort, m) for m in menge):
        return True
    teile = _teile(wort)
    if len(teile) < 2:
        return False
    getroffen = sum(any(_gleich(t, m) for m in menge) for t in teile)
    return wort.replace("-", "").replace("/", "") in menge or getroffen >= max(2, len(teile) - 1)


def _menge(text: str) -> set[str]:
    """Normalisierte Wörter eines Texts samt den Teilen ihrer Komposita (für den Vergleich)."""
    menge = set()
    for w in WORT.findall(text or ""):
        n = normal(w).rstrip(".")
        menge |= {n, n.replace("-", "").replace("/", ""), *_teile(n)}
    return menge


def abgleichen(antwort: str, loesung: str, aufgabe: str = "") -> dict | None:
    """Punkte der Musterlösung mit erkannt ja/nein, getroffenen Wörtern und Textteilen zum Hervorheben; dazu erkannt,
    ziel (bei „Nennen Sie zwei …“ die verlangte Anzahl), anteil und vorschlag 1/2/3. None ohne Antwort oder ohne Punkte."""
    if not (antwort or "").strip():
        return None
    in_aufgabe, in_antwort = _menge(aufgabe), _menge(antwort)
    verlangt, erwartet = verlangte_anzahl(aufgabe), zerlegen(loesung)
    if verlangt and len(erwartet) < verlangt:  # „Anweisungsüberdeckung, Zweigüberdeckung.“ sind zwei Punkte in einem Satz
        erwartet = [t.strip(" .") for p in erwartet for t in re.split(r"[,;]|\bund\b|\bsowie\b", p) if bedeutsam(t)][:HOECHSTENS]
    punkte = []
    def eigene(text: str) -> list[str]:  # Wörter aus der Aufgabenstellung verraten nichts: abschreiben bringt den Punkt nicht
        return [w for w in dict.fromkeys(bedeutsam(text)) if not _vorkommt(normal(w).rstrip("."), in_aufgabe)]
    for text in erwartet:
        # Klammern sind meist Zusätze („verschlüsselt (Vertraulichkeit)“): sie zählen als Treffer, aber nicht als verlangt
        woerter = eigene(re.sub(r"\([^)]*\)", " ", text)) or eigene(text)
        zusatz = [w for w in eigene(" ".join(re.findall(r"\(([^)]*)\)", text))) if w not in woerter]
        if not woerter:
            continue
        treffer = [w for w in woerter + zusatz if _vorkommt(normal(w).rstrip("."), in_antwort)]
        noetig = max(1, min(math.ceil(ANTEIL * len(woerter)), HOECHSTENS_NOETIG))
        erkannt = len(treffer) >= noetig or any(fachbegriff(w) for w in treffer)
        punkte.append({"text": text, "woerter": woerter, "treffer": treffer, "erkannt": erkannt, "teile": _hervorheben(text, treffer)})
    if not punkte:
        return None
    erkannt = sum(p["erkannt"] for p in punkte)
    ziel = min(verlangt, len(punkte)) if verlangt else len(punkte)
    gezaehlt = min(erkannt, ziel)
    return {"punkte": punkte, "erkannt": gezaehlt, "ziel": ziel, "verlangt": verlangt, "anteil": gezaehlt / ziel,
            "vorschlag": ergebnis_aus_punkten(gezaehlt, ziel)}


def _hervorheben(text: str, treffer: list[str]) -> list[tuple[str, bool]]:
    """Text in Stücke (Stück, getroffen?) für <mark> in der Anzeige."""
    if not treffer:
        return [(text, False)]
    muster = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in sorted(treffer, key=len, reverse=True)) + r")\b")
    teile, pos = [], 0
    for m in muster.finditer(text):
        teile += [(text[pos:m.start()], False), (m.group(), True)]
        pos = m.end()
    return [t for t in teile + [(text[pos:], False)] if t[0]]


def fuer_teilaufgabe(t: dict, eigene: str | None) -> dict | None:
    """Abgleich für eine Freitext-Teilaufgabe (Üben, Simulation, Mini-Test), dazu ein Punktevorschlag anteilig auf halbe
    Punkte. Bewusst nicht in antwort.vorschlag: dessen Punkte werden vorbelegt, bei Freitext vergibt sie der Nutzer.
    None bei anklickbaren und anderen festen Formaten, ohne eigene Antwort oder ohne zerlegbare Lösung."""
    if t["antwort"] and t["antwort"]["art"] != "frei":
        return None
    a = abgleichen(eigene or "", t["loesung_inhalt"] or t["loesung_text"] or "", t["inhalt"] or t["text"] or "")
    if a and t["punkte"]:
        a["punkte_vorschlag"] = round(t["punkte"] * a["anteil"] * 2) / 2
    return a
