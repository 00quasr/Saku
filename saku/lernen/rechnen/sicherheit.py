"""IT-Sicherheit: Passwortstärke, Schlüsselanzahl, Schutzbedarf (BSI-Standard 200-2), Risikobewertung, Prüfziffern und DSGVO in
Zahlen (Art. 33 und 83). Alle Szenarien sind erfunden."""

import math
from datetime import datetime, timedelta
from fractions import Fraction

from saku.lernen.rechnen.basis import ABTEILUNGEN, FIRMEN, Aufgabe, Feld, art, de, euro, hoch, schritte, tabelle
from saku.lernen.rechnen.wiso import WOCHENTAGE, kurz, lang

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "passwort": """- Zeichenvorrat N: Kleinbuchstaben 26, Großbuchstaben 26 (ohne Umlaute und ß), Ziffern 10, Sonderzeichen so viele, wie erlaubt sind
- Kombinationen bei genau L Zeichen: N^L; jedes Zeichen mehr multipliziert sie mit N
- Brute Force: im schlimmsten Fall alle Kombinationen, im Mittel die Hälfte (Konvention: das Passwort liegt zufällig irgendwo in der Reihe)
- Dauer = Kombinationen : Versuche pro Sekunde; hier 1 Jahr = 365 Tage = 31.536.000 s
- Entropie = L · log₂ N Bit (log₂ N = ln N : ln 2), gilt nur für zufällig gewählte Zeichen; echte Wörter fallen viel schneller (Wörterbuchangriff)
- Mindestlänge für E Bit: E : log₂ N, immer aufrunden; ein Bit mehr verdoppelt die Kombinationen, Länge schlägt Zeichenvielfalt

*Beispiel:* 8 Zeichen aus a–z, A–Z, 0–9: N = 62, 62⁸ ≈ 2,18 · 10¹⁴; bei 10⁹ Versuchen pro Sekunde höchstens 218.340 s ≈ 60,65 Stunden, im Mittel 30,33 Stunden; Entropie 8 · 5,95 = 47,63 Bit""",
    "schluessel": """- Symmetrisch: jedes Paar teilt einen geheimen Schlüssel → n · (n − 1) : 2 Schlüssel
- Asymmetrisch: jeder Teilnehmer hat ein Schlüsselpaar → n Paare = 2n Schlüssel (n öffentliche, n private)
- k neue Teilnehmer: symmetrisch kommen k · n + k · (k − 1) : 2 Schlüssel hinzu (jeder Neue mit allen Bisherigen, die Neuen untereinander), asymmetrisch 2k
- Verschlüsseln mit dem **öffentlichen Schlüssel des Empfängers**, entschlüsseln mit seinem **privaten**
- Signieren (den Hashwert der Nachricht) mit dem **privaten Schlüssel des Absenders**, prüfen mit seinem **öffentlichen**
- Hybrid: den Text symmetrisch mit einem zufälligen Sitzungsschlüssel (schnell), den Sitzungsschlüssel asymmetrisch mit dem öffentlichen Schlüssel des Empfängers

*Beispiel:* 10 Teilnehmer: symmetrisch 10 · 9 : 2 = 45 Schlüssel, asymmetrisch 2 · 10 = 20 Schlüssel""",
    "schutzbedarf": """- Grundwerte: **Vertraulichkeit** (nur Befugte erhalten Kenntnis), **Integrität** (Daten sind korrekt und unverändert), **Verfügbarkeit** (nutzbar, wenn sie gebraucht werden)
- Schutzbedarfskategorien (BSI-Standard 200-2): normal (Schaden begrenzt und überschaubar), hoch (beträchtlich), sehr hoch (existenziell bedrohlich, katastrophal)
- Vererbung: Geschäftsprozesse und Anwendungen → IT-Systeme → Räume und Gebäude, je Grundwert getrennt
- Maximumprinzip: ein IT-System übernimmt je Grundwert den höchsten Schutzbedarf der Anwendungen, die darauf laufen; ein Raum den höchsten der Systeme darin
- Kumulationseffekt: viele Anwendungen oder Systeme an einer Stelle, deren Schäden sich summieren → Schutzbedarf kann **höher** sein als das Maximum
- Verteilungseffekt: Anwendung redundant auf mehreren Systemen oder nur unwichtige Teile auf diesem → Schutzbedarf kann **niedriger** sein (meist Verfügbarkeit); beide Effekte begründet man im Einzelfall

*Beispiel:* Server mit Lohnbuchhaltung (hoch, hoch, normal) und Intranet-Wiki (normal, normal, normal) → hoch, hoch, normal""",
    "risiko": """- Risiko (erwarteter Schaden pro Jahr) = Eintrittshäufigkeit pro Jahr · Schaden je Fall
- Häufigkeit: „einmal in n Jahren“ = 1 : n, „p % Wahrscheinlichkeit im Jahr“ = p : 100, „k-mal im Jahr“ = k
- Rangfolge: nach dem Risiko sortieren, das größte zuerst behandeln
- Maßnahme lohnt sich, wenn der vermiedene Schaden pro Jahr (Risiko vorher − Risiko nachher) größer ist als ihre Kosten pro Jahr; einmalige Kosten auf die Nutzungsdauer verteilen
- Risikomatrix: Risikowert = Stufe der Eintrittswahrscheinlichkeit · Stufe der Schadenshöhe; die Grenzen der Risikoklassen legt jede Firma selbst fest (sie stehen in der Aufgabe)

*Beispiel:* Ausfall einmal in 4 Jahren mit 20.000 € Schaden: 0,25 · 20.000 € = 5.000 € pro Jahr; eine Maßnahme für 3.000 € im Jahr, die das auf 2.500 € halbiert, spart nur 2.500 € → lohnt sich nicht""",
    "pruefziffer": """- Gerade Parität: das Paritätsbit macht die Anzahl der Einsen (mit Paritätsbit) gerade; ungerade Parität: ungerade
- Die Paritätsprüfung erkennt jede ungerade Anzahl gekippter Bits; zwei gekippte Bits bleiben unbemerkt, korrigieren kann sie nichts
- EAN-13 und ISBN-13 (eine EAN mit 978 oder 979 vorn): die ersten 12 Ziffern von links abwechselnd mit 1 und 3 gewichten und addieren
- Prüfziffer = (10 − Summe mod 10) mod 10, also die Ergänzung bis zum nächsten Zehner (bei glatter Summe 0)
- Kontrolle: alle 13 Ziffern gewichtet (die 13. mit 1) ergeben ein Vielfaches von 10; eine einzelne falsche Ziffer fällt immer auf
- XOR bitweise: gleiche Bits → 0, verschiedene → 1; Klartext ⊕ Schlüssel = Geheimtext, Geheimtext ⊕ Schlüssel = Klartext

*Beispiel:* EAN 401234567890?: 4 + 0 + 1 + 6 + 3 + 12 + 5 + 18 + 7 + 24 + 9 + 0 = 89 → 90 − 89 = 1 → 4012345678901""",
    "dsgvo": """- Art. 83 Abs. 4 DSGVO, Pflichten von Verantwortlichen und Auftragsverarbeitern (Art. 8, 11, 25 bis 39, 42, 43, z. B. Art. 28 Auftragsverarbeitung, Art. 30 Verzeichnis, Art. 32 Sicherheit, Art. 33 Meldung, Art. 37 Datenschutzbeauftragter): bis 10 Mio. € oder 2 % des weltweiten Jahresumsatzes
- Art. 83 Abs. 5, Grundsätze und Rechtmäßigkeit (Art. 5, 6, 7, 9), Rechte der Betroffenen (Art. 12 bis 22), Übermittlung in Drittländer (Art. 44 bis 49): bis 20 Mio. € oder 4 %
- Umsatz: der gesamte weltweite Jahresumsatz des vorangegangenen Geschäftsjahrs; bei Unternehmen gilt der **höhere** der beiden Beträge als Obergrenze, die Geldbuße selbst legt die Behörde im Einzelfall fest
- Art. 33: eine Verletzung des Schutzes personenbezogener Daten der Aufsichtsbehörde unverzüglich und möglichst binnen **72 Stunden** melden, **nachdem sie bekannt wurde** (nicht ab dem Vorfall); entfällt nur, wenn voraussichtlich kein Risiko für die Betroffenen besteht
- Gerechnet wird hier wie üblich: Zeitpunkt der Kenntnis + 72 Stunden = gleiche Uhrzeit drei Tage später; Wochenenden und Feiertage zählen mit

*Beispiel:* Umsatz 750 Mio. €, Verstoß gegen Art. 33: 2 % = 15 Mio. € > 10 Mio. € → bis 15 Mio. €; Kenntnis Freitag 14:20 Uhr → Meldung bis Montag 14:20 Uhr""",
}


def _aufzaehlung(teile: list[str]) -> str:
    return teile[0] if len(teile) == 1 else ", ".join(teile[:-1]) + " und " + teile[-1]


def _zehner(x: float) -> str:
    """2,18 · 10¹⁴"""
    mantisse, exponent = f"{x:.2e}".split("e")
    return f"{de(float(mantisse))} · 10{hoch(int(exponent))}"


# --- Passwortstärke ---------------------------------------------------------------------

KLASSEN = {"klein": ("Kleinbuchstaben (a–z)", 26), "gross": ("Großbuchstaben (A–Z)", 26), "ziffern": ("Ziffern (0–9)", 10)}
REGELN = [("ziffern",), ("klein",), ("klein", "ziffern"), ("klein", "gross"), ("klein", "gross", "ziffern"),
          ("klein", "gross", "ziffern", "sonder"), ("klein", "gross", "ziffern", "sonder")]
# Versuche pro Sekunde als Zehnerexponent, in Worten, wie
RATEN = [(3, "1.000", "über eine Anmeldeschnittstelle ohne Sperre"), (6, "1 Million (10⁶)", "offline gegen erbeutete Passwort-Hashes"),
         (9, "1 Milliarde (10⁹)", "offline mit einer Grafikkarte"), (10, "10 Milliarden (10¹⁰)", "offline mit mehreren Grafikkarten"),
         (11, "100 Milliarden (10¹¹)", "offline mit einem Grafikkarten-Cluster")]
JAHR = 365 * 86400
# Einheit, nach „in“, Sekunden, so steht der Teiler im Rechenweg
EINHEITEN = [("Jahre", "Jahren", JAHR, "31.536.000 (365 · 24 · 3.600)"), ("Tage", "Tagen", 86400, "86.400 (24 · 3.600)"),
             ("Stunden", "Stunden", 3600, "3.600"), ("Minuten", "Minuten", 60, "60")]


def _zeichen(rng) -> tuple[str, list[int]]:
    """Erlaubte Zeichen als Satzteil und die Anzahl je Zeichenklasse."""
    regel, sonder = rng.choice(REGELN), rng.choice([8, 10, 12, 16, 20, 32])
    teile = [KLASSEN[k] if k != "sonder" else (f"{sonder} erlaubten Sonderzeichen", sonder) for k in regel]
    return _aufzaehlung([t for t, _ in teile]), [n for _, n in teile]


def _umlaute(anzahl: list[int]) -> str:
    return " Umlaute und ß sind nicht erlaubt." if 26 in anzahl else ""


def _summe(anzahl: list[int]) -> str:
    return f"{' + '.join(map(str, anzahl))} = {sum(anzahl)}" if len(anzahl) > 1 else str(anzahl[0])


def _vorrat_weg(anzahl: list[int]) -> str:
    return f"Zeichenvorrat: {' + '.join(map(str, anzahl))} = **{sum(anzahl)}**" if len(anzahl) > 1 else f"Zeichenvorrat: **{anzahl[0]}**"


@art("passwort", "Passwortstärke", "IT-Sicherheit", "Zeichenvorrat, Kombinationen, Brute-Force-Dauer und Entropie; zwei Passwortregeln vergleichen",
     ("Passw", "Kennw", "Brute-Force", "Brute Force", "Entropie"), formeln=FORMELN["passwort"])  # auch Passwörter, Kennwörter
def passwort(rng):
    return rng.choice([_brute_force, _brute_force, _entropie, _regeln])(rng)


def _brute_force(rng):
    while True:  # Kombinationen bis 2⁵³: als Gleitkommazahl noch exakt; Dauer zwischen zwei Minuten und 100.000 Jahren
        text, anzahl = _zeichen(rng)
        n, laenge = sum(anzahl), rng.randint(4, 12)
        exponent, rate, wie = rng.choice(RATEN)
        kombinationen = n ** laenge
        sekunden = kombinationen / 10 ** exponent
        if (laenge >= 6 or n == 10) and kombinationen <= 2 ** 53 and 120 <= sekunden <= 10 ** 5 * JAHR:
            break
    einheit, in_einheit, faktor, faktor_text = next(e for e in EINHEITEN if sekunden >= 2 * e[2])
    dauer = sekunden / faktor
    frage = (f"Die Passwortrichtlinie der {rng.choice(FIRMEN)} verlangt Passwörter aus genau **{laenge} Zeichen**; erlaubt sind {text}.{_umlaute(anzahl)} "
             f"Ein Angreifer probiert {wie} **{rate} Passwörter pro Sekunde**.\n\nBerechnen Sie den Zeichenvorrat, die Anzahl der "
             f"möglichen Passwörter (als Potenz wie 10^4 oder ausgeschrieben) und die Dauer des Brute-Force-Angriffs in {in_einheit} im "
             "schlimmsten Fall und im Mittel (zwei Nachkommastellen; 1 Jahr = 365 Tage).")
    felder = [Feld("vorrat", "Zeichenvorrat", n, "Zeichen", stellen=0), Feld("kombinationen", "Mögliche Passwörter", kombinationen, stellen=0),
              Feld("max", "Dauer im schlimmsten Fall", dauer, einheit), Feld("mittel", "Dauer im Mittel", dauer / 2, einheit)]
    weg = [_vorrat_weg(anzahl),
           f"Kombinationen bei {laenge} Zeichen: {n}{hoch(laenge)} = **{de(kombinationen, 0)}** ≈ {_zehner(kombinationen)}",
           f"Schlimmster Fall, alle Kombinationen: {de(kombinationen, 0)} : 10{hoch(exponent)} pro Sekunde = {de(sekunden)} s",
           f"In {in_einheit}: {de(sekunden)} s : {faktor_text} = **{de(dauer)} {einheit}**",
           f"Im Mittel (Konvention: gefunden nach der Hälfte aller Kombinationen): {de(dauer)} : 2 = **{de(dauer / 2)} {einheit}**"]
    return Aufgabe(frage, felder, schritte(*weg), toleranz=0.005, titel="Brute-Force-Dauer")


def _entropie(rng):
    while True:  # Ziel : log₂ N nicht knapp über oder unter einer ganzen Zahl, sonst kippt die Mindestlänge mit gerundetem log₂
        text, anzahl = _zeichen(rng)
        n, laenge, ziel = sum(anzahl), rng.randint(6, 14), rng.choice([64, 72, 80, 90, 100, 128])
        je = math.log2(n)
        if n > 10 and laenge * je < ziel and 0.05 < ziel / je % 1 < 0.95:
            break
    mindest = math.ceil(ziel / je)
    frage = (f"Ein Passwortmanager der {rng.choice(FIRMEN)} erzeugt zufällige Passwörter aus {text}.{_umlaute(anzahl)} Bisher sind sie **{laenge} Zeichen** "
             f"lang; künftig sollen sie mindestens **{ziel} Bit** Entropie haben.\n\nBerechnen Sie den Zeichenvorrat, die Entropie je "
             "Zeichen und die des bisherigen Passworts in Bit (zwei Nachkommastellen) sowie die nötige Mindestlänge.")
    felder = [Feld("vorrat", "Zeichenvorrat", n, "Zeichen", stellen=0), Feld("je", "Entropie je Zeichen", je, "Bit"),
              Feld("bisher", "Entropie bisher", laenge * je, "Bit"), Feld("mindest", "Mindestlänge", mindest, "Zeichen", stellen=0)]
    weg = schritte(_vorrat_weg(anzahl),
                   f"Entropie je Zeichen: log₂ {n} = ln {n} : ln 2 = **{de(je)} Bit**",
                   f"Bisher: {laenge} · {de(je, 4)} = **{de(laenge * je)} Bit**, weniger als {ziel} Bit",
                   f"Mindestlänge: {ziel} : {de(je, 4)} = {de(ziel / je)} → aufrunden → **{mindest} Zeichen** "
                   f"({mindest} · {de(je, 4)} = {de(mindest * je)} Bit, mit {mindest - 1} Zeichen nur {de((mindest - 1) * je)} Bit)")
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="Entropie und Mindestlänge")


def _regeln(rng):
    while True:  # Regel A hat mehr Zeichenarten, Regel B ist länger: welche gewinnt?
        (text_a, anz_a), (text_b, anz_b) = _zeichen(rng), _zeichen(rng)
        la, lb = rng.randint(6, 10), rng.randint(9, 16)
        ea, eb = la * math.log2(sum(anz_a)), lb * math.log2(sum(anz_b))
        if sum(anz_a) > sum(anz_b) and la < lb and abs(ea - eb) >= 2:
            break
    staerker, mehr = ("Regel A", ea - eb) if ea > eb else ("Regel B", eb - ea)
    frage = (f"Die {rng.choice(FIRMEN)} vergleicht zwei Regeln für zufällig erzeugte Passwörter:\n\n"
             f"- **Regel A:** {la} Zeichen aus {text_a}\n- **Regel B:** {lb} Zeichen aus {text_b}\n\n"
             "Umlaute und ß sind nicht erlaubt. Berechnen Sie die Entropie beider Regeln in Bit (zwei Nachkommastellen) und geben Sie an, "
             "welche Regel stärker ist.")
    felder = [Feld("a", "Entropie Regel A", ea, "Bit"), Feld("b", "Entropie Regel B", eb, "Bit"),
              Feld("staerker", "Stärkere Regel", staerker, typ="text", optionen=["Regel A", "Regel B"])]
    faktor = 2 ** mehr
    weg = schritte(f"Regel A: N = {_summe(anz_a)} → {la} · log₂ {sum(anz_a)} = {la} · "
                   f"{de(math.log2(sum(anz_a)), 4)} = **{de(ea)} Bit**",
                   f"Regel B: N = {_summe(anz_b)} → {lb} · log₂ {sum(anz_b)} = {lb} · "
                   f"{de(math.log2(sum(anz_b)), 4)} = **{de(eb)} Bit**",
                   f"**{staerker}** hat {de(mehr)} Bit mehr, also 2^{de(mehr)} ≈ {_zehner(faktor) if faktor >= 10 ** 6 else de(faktor, 0 if faktor >= 100 else 1)}-mal "
                   "so viele Kombinationen" + (": die Länge schlägt die Zeichenvielfalt" if staerker == "Regel B" else ""))
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="Passwortregeln vergleichen")


# --- Schlüsselanzahl und welcher Schlüssel ------------------------------------------------

SCHLUESSEL = ["Öffentlicher Schlüssel des Absenders", "Privater Schlüssel des Absenders", "Öffentlicher Schlüssel des Empfängers",
              "Privater Schlüssel des Empfängers", "Symmetrischer Sitzungsschlüssel"]
# Schritt, Index in SCHLUESSEL, warum
SIGNIEREN = [("Nachricht signieren (ihren Hashwert)", 1, "nur der Absender besitzt seinen privaten Schlüssel; das belegt Herkunft und Unversehrtheit"),
             ("Signatur prüfen", 0, "den öffentlichen Schlüssel des Absenders kennt jeder, er passt nur zu dessen privatem")]
ASYMMETRISCH = [("Nachricht verschlüsseln", 2, "lesen soll nur der Empfänger, und nur er hat den passenden privaten Schlüssel"),
                ("Nachricht entschlüsseln", 3, "der private Schlüssel des Empfängers passt zum öffentlichen, mit dem verschlüsselt wurde"),
                *SIGNIEREN]
HYBRID = [("Nachrichtentext verschlüsseln", 4, "der große Text geht symmetrisch, das ist schnell"),
          ("Sitzungsschlüssel verschlüsseln", 2, "nur der Empfänger soll den Sitzungsschlüssel auspacken können"),
          ("Sitzungsschlüssel entschlüsseln", 3, "der private Schlüssel des Empfängers öffnet, was mit seinem öffentlichen verschlüsselt wurde"),
          ("Nachrichtentext entschlüsseln", 4, "symmetrisch: derselbe Sitzungsschlüssel ver- und entschlüsselt"),
          *SIGNIEREN]


TEAMS = [a for a in ABTEILUNGEN if a != "Geschäftsleitung"]  # „die Abteilung Geschäftsleitung“ klingt schief


def _symmetrisch(n: int) -> int:
    return n * (n - 1) // 2


@art("schluessel", "Schlüssel und Verschlüsselung", "IT-Sicherheit",
     "Schlüsselanzahl symmetrisch n · (n − 1) : 2 und asymmetrisch 2n; welcher Schlüssel verschlüsselt, signiert, prüft?",
     ("Verschlüsselung", "Kryptografie", "Kryptographie", "Kryptologie", "Schlüsselverteilung", "Schlüsselaustausch", "Public Key",
      "Public-Key"), formeln=FORMELN["schluessel"])
def schluessel(rng):
    return rng.choice([_zaehlen, _neue, _welcher, _welcher])(rng)


def _zaehlen(rng):
    n = rng.randint(4, 60)
    frage = (f"In der Abteilung {rng.choice(TEAMS)} der {rng.choice(FIRMEN)} arbeiten **{n} Personen**. Jede soll mit jeder anderen "
             "vertraulich kommunizieren können, ohne dass Dritte mitlesen.\n\nWie viele Schlüssel sind dafür mit einem symmetrischen "
             "Verfahren nötig, und wie viele Schlüssel (öffentliche und private zusammen) mit einem asymmetrischen?")
    felder = [Feld("symmetrisch", "Symmetrisch", _symmetrisch(n), "Schlüssel", stellen=0),
              Feld("asymmetrisch", "Asymmetrisch", 2 * n, "Schlüssel", stellen=0)]
    weg = schritte(f"Symmetrisch braucht jedes Paar einen eigenen geheimen Schlüssel: n · (n − 1) : 2 = {n} · {n - 1} : 2 = "
                   f"**{de(_symmetrisch(n))}**",
                   f"Asymmetrisch hat jede Person ein Schlüsselpaar: 2 · n = 2 · {n} = **{2 * n}** ({n} öffentliche und {n} private)")
    return Aufgabe(frage, felder, weg, titel="Schlüssel zählen")


def _neue(rng):
    n, k = rng.randint(3, 30), rng.randint(1, 6)
    neu = "kommt **ein neuer Standort** hinzu, der" if k == 1 else f"kommen **{k} neue Standorte** hinzu, die"
    frage = (f"Die {rng.choice(FIRMEN)} verbindet ihre **{n} Standorte** über verschlüsselte Tunnel, jeden mit jedem und mit einem "
             f"eigenen Schlüssel je Verbindung. Jetzt {neu} ebenso mit allen verbunden werden soll{'' if k == 1 else 'en'}.\n\n"
             "Wie viele Schlüssel kommen bei einem symmetrischen Verfahren hinzu, wie viele sind es danach insgesamt, und wie viele "
             "Schlüssel kommen bei einem asymmetrischen Verfahren (je Standort ein Schlüsselpaar) hinzu?")
    vorher, nachher = _symmetrisch(n), _symmetrisch(n + k)
    felder = [Feld("dazu", "Symmetrisch hinzu", nachher - vorher, "Schlüssel", stellen=0),
              Feld("gesamt", "Symmetrisch insgesamt", nachher, "Schlüssel", stellen=0),
              Feld("asymmetrisch", "Asymmetrisch hinzu", 2 * k, "Schlüssel", stellen=0)]
    weg = schritte(f"Vorher symmetrisch: {n} · {n - 1} : 2 = {de(vorher)}",
                   f"Nachher: {n + k} · {n + k - 1} : 2 = **{de(nachher)}**",
                   f"Hinzu: {de(nachher)} − {de(vorher)} = **{de(nachher - vorher)}** (Probe: jeder Neue mit allen {n} Bisherigen, "
                   f"die Neuen untereinander: {k} · {n} + {k} · {k - 1} : 2 = {de(k * n + _symmetrisch(k))})",
                   f"Asymmetrisch: jeder neue Standort bringt ein Schlüsselpaar mit: 2 · {k} = **{2 * k}**")
    return Aufgabe(frage, felder, weg, titel="Neue Teilnehmer")


def _welcher(rng):
    hybrid = rng.random() < 0.5
    schritte_ = sorted(rng.sample(HYBRID if hybrid else ASYMMETRISCH, 4 if hybrid else 3), key=(HYBRID if hybrid else ASYMMETRISCH).index)
    absender, empfaenger = rng.sample(TEAMS, 2)
    verfahren = ("Weil ein großer Anhang dabei ist, wird hybrid verschlüsselt: mit einem zufälligen symmetrischen Sitzungsschlüssel und "
                 "einem asymmetrischen Verfahren." if hybrid else "Verschlüsselt wird asymmetrisch.")
    frage = (f"Die Abteilung {absender} der {rng.choice(FIRMEN)} (Absender) schickt der Abteilung {empfaenger} (Empfänger) ein vertrauliches "
             f"Angebot per E-Mail. Beide haben ein Schlüsselpaar, und jede Seite kennt den öffentlichen Schlüssel der anderen. {verfahren} "
             "Außerdem wird die E-Mail digital signiert.\n\nWelcher Schlüssel wird für den jeweiligen Schritt verwendet?")
    optionen = SCHLUESSEL if hybrid else SCHLUESSEL[:4]
    felder = [Feld(f"s{i}", text, SCHLUESSEL[j], typ="text", optionen=optionen) for i, (text, j, _) in enumerate(schritte_)]
    weg = schritte(*(f"{text}: **{SCHLUESSEL[j]}**, {warum}" for text, j, warum in schritte_))
    return Aufgabe(frage, felder, weg, titel="Welcher Schlüssel?")


# --- Schutzbedarfsfeststellung (BSI-Standard 200-2) ---------------------------------------

STUFEN = ["normal", "hoch", "sehr hoch"]
GRUNDWERTE = ["Vertraulichkeit", "Integrität", "Verfügbarkeit"]
# Schutzbedarf der Anwendungen je Grundwert als Index in STUFEN: erfunden, aber plausibel
ANWENDUNGEN = {
    "Lohnbuchhaltung": (1, 1, 0), "Webshop": (1, 1, 1), "Intranet-Wiki": (0, 0, 0), "E-Mail": (1, 0, 1), "Warenwirtschaft": (0, 1, 1),
    "Konstruktionsdaten (CAD)": (2, 1, 0), "Zeiterfassung": (0, 1, 0), "Kundendatenbank (CRM)": (1, 0, 0),
    "Produktionssteuerung": (0, 2, 2), "Personalakten": (2, 1, 0), "Druckdienst": (0, 0, 0),
}
VORFAELLE = [
    ["Ein Praktikant kann im Netzlaufwerk die Gehaltsliste aller Beschäftigten öffnen.",
     "Eine E-Mail mit Kundendaten geht versehentlich an einen externen Verteiler.",
     "Ein Angreifer liest im offenen Gäste-WLAN unverschlüsselte Anmeldedaten mit.",
     "Ausgedruckte Personalakten bleiben über Nacht im Etagendrucker liegen.",
     "Ein Konkurrent kommt über einen ehemaligen Mitarbeiter an vertrauliche Konstruktionspläne."],
    ["Ein Angreifer ändert unbemerkt die Bankverbindung in einer ausgehenden Rechnung.",
     "Durch einen Programmfehler bucht die Warenwirtschaft Lagerabgänge doppelt.",
     "Ein Mitarbeiter ändert ohne Berechtigung die Preise im Webshop.",
     "Schadsoftware verfälscht Messwerte in der Produktionsdatenbank.",
     "Eine Kopie des Vertragsarchivs ist unbemerkt beschädigt, die Prüfsummen stimmen nicht mehr."],
    ["Der Webshop ist nach einem DDoS-Angriff sechs Stunden nicht erreichbar.",
     "Nach einem Festplattendefekt kann die Buchhaltung einen Tag lang nicht arbeiten.",
     "Wegen Bauarbeiten fällt der Internetanschluss des Standorts für zwei Tage aus.",
     "Der Serverraum steht nach einem Wasserschaden still, kein Dienst ist erreichbar.",
     "Der einzige Lizenzserver ist ausgefallen, niemand kann die CAD-Software starten."],
]
WARUM = ["Unbefugte erhalten Kenntnis von Informationen", "Daten sind verändert oder falsch und damit nicht mehr korrekt",
         "Daten oder Dienste stehen nicht zur Verfügung, wenn sie gebraucht werden"]


def _maximum(anwendungen) -> tuple[int, ...]:
    return tuple(max(ANWENDUNGEN[a][g] for a in anwendungen) for g in range(3))


def _max_text(anwendungen, g: int) -> str:
    werte = [STUFEN[ANWENDUNGEN[a][g]] for a in anwendungen]
    return f"max({', '.join(werte)}) = **{STUFEN[_maximum(anwendungen)[g]]}**" if len(werte) > 1 else f"**{werte[0]}**"


@art("schutzbedarf", "Schutzbedarf", "IT-Sicherheit",
     "BSI-Standard 200-2: Grundwerte erkennen, Schutzbedarf nach dem Maximumprinzip auf Server und Räume vererben",
     ("Schutzbedarf", "Grundschutz", "Schutzziel", "Informationssicherheit", "Sicherheitskonzept"), formeln=FORMELN["schutzbedarf"])
def schutzbedarf(rng):
    return rng.choice([_vererben, _vererben, _grundwert])(rng)


def _vererben(rng):
    while True:
        anwendungen = rng.sample(list(ANWENDUNGEN), 5)
        server = {"S1": [anwendungen[0]], "S2": [anwendungen[1]], "S3": [anwendungen[2]]}
        for a in anwendungen[3:]:
            server[rng.choice(list(server))].append(a)
        cluster = None  # eine Anwendung mit Verfügbarkeit ab hoch läuft redundant auf einem zweiten Server
        kandidaten = [(s, a) for s, liste in server.items() for a in liste if ANWENDUNGEN[a][2]]
        if kandidaten and rng.random() < 0.4:
            s, a = rng.choice(kandidaten)
            zweiter = rng.choice([t for t in server if t != s])
            server[zweiter].append(a)
            cluster = (a, sorted([s, zweiter]))
        raum = sorted(rng.sample(list(server), 2))  # stehen im Serverraum, der dritte im Technikraum
        ziel = rng.choice(raum)
        im_raum = list(dict.fromkeys(server[raum[0]] + server[raum[1]]))
        if _maximum(server[ziel]) != _maximum(im_raum):  # sonst lernt man am Raum nichts
            break
    technik = next(s for s in server if s not in raum)

    def laeuft_auf(a):
        auf = [s for s in server if a in server[s]]
        return f"{auf[0]} und {auf[1]} (Cluster)" if len(auf) > 1 else auf[0]
    zeilen = [[a, *(STUFEN[w] for w in ANWENDUNGEN[a]), laeuft_auf(a)] for a in anwendungen]
    frage = (f"Die {rng.choice(FIRMEN)} erstellt ein Sicherheitskonzept nach BSI-Standard 200-2. Der Schutzbedarf der Anwendungen ist "
             "festgestellt:\n\n" + tabelle(["Anwendung", *GRUNDWERTE, "läuft auf"], zeilen)
             + f"\n\nDie Server {raum[0]} und {raum[1]} stehen im Serverraum, {technik} im Technikraum.\n\n"
             f"Ermitteln Sie nach dem Maximumprinzip den Schutzbedarf des Servers **{ziel}** und des **Serverraums** für jeden Grundwert. "
             "Kumulations- und Verteilungseffekte bleiben hier außer Betracht.")
    sv, rv = _maximum(server[ziel]), _maximum(im_raum)
    felder = ([Feld(f"s{g}", f"{ziel}: {gw}", STUFEN[sv[g]], typ="text", optionen=STUFEN) for g, gw in enumerate(GRUNDWERTE)]
              + [Feld(f"r{g}", f"Serverraum: {gw}", STUFEN[rv[g]], typ="text", optionen=STUFEN) for g, gw in enumerate(GRUNDWERTE)])
    weg = (schritte(f"Auf {ziel} laufen: {', '.join(server[ziel])}",
                    f"Im Serverraum stehen {raum[0]} und {raum[1]} mit: {', '.join(im_raum)}",
                    "Maximumprinzip: je Grundwert übernimmt der Server den höchsten Schutzbedarf seiner Anwendungen, der Raum den "
                    "höchsten aller Anwendungen auf den Servern darin")
           + "\n\n" + tabelle(["Grundwert", ziel, "Serverraum"], [[gw, _max_text(server[ziel], g), _max_text(im_raum, g)]
                                                                 for g, gw in enumerate(GRUNDWERTE)]))
    if len(server[ziel]) > 1 and min(sv) < 2:
        weg += (f"\n\n**Kumulationseffekt:** Auf {ziel} laufen {len(server[ziel])} Anwendungen. Trifft ein Ausfall oder Angriff alle "
                "zugleich, kann der Gesamtschaden größer sein als bei jeder einzelnen; dann wäre der Schutzbedarf begründet höher "
                "anzusetzen als das Maximum.")
    if cluster and ziel in cluster[1] and all(ANWENDUNGEN[a][2] < ANWENDUNGEN[cluster[0]][2] for a in server[ziel] if a != cluster[0]):
        weg += (f"\n\n**Verteilungseffekt:** {cluster[0]} läuft redundant auf {cluster[1][0]} und {cluster[1][1]}. Fällt {ziel} aus, "
                f"übernimmt der andere Server; die Verfügbarkeit von {ziel} könnte deshalb begründet niedriger als „{STUFEN[sv[2]]}“ "
                "eingestuft werden.")
    return Aufgabe(frage, felder, weg, titel="Schutzbedarf vererben")


def _grundwert(rng):
    while True:
        vorfaelle = rng.sample([(g, text) for g, texte in enumerate(VORFAELLE) for text in texte], 4)
        if len({g for g, _ in vorfaelle}) >= 2:
            break
    frage = (f"Die Informationssicherheitsbeauftragte der {rng.choice(FIRMEN)} wertet Vorfälle aus:\n\n"
             + "\n".join(f"{i}. {text}" for i, (_, text) in enumerate(vorfaelle, start=1))
             + "\n\nWelcher Grundwert der Informationssicherheit ist jeweils in erster Linie verletzt?")
    felder = [Feld(f"v{i}", f"Vorfall {i}", GRUNDWERTE[g], typ="text", optionen=GRUNDWERTE) for i, (g, _) in enumerate(vorfaelle, start=1)]
    weg = schritte(*(f"{text} → **{GRUNDWERTE[g]}**: {WARUM[g]}" for g, text in vorfaelle))
    return Aufgabe(frage, felder, weg, titel="Grundwerte erkennen")


# --- Risikobewertung ----------------------------------------------------------------------

HAEUFIGKEITEN = [("einmal in 20 Jahren", Fraction(1, 20)), ("einmal in 10 Jahren", Fraction(1, 10)), ("einmal in 5 Jahren", Fraction(1, 5)),
                 ("einmal in 4 Jahren", Fraction(1, 4)), ("einmal in 2 Jahren", Fraction(1, 2)), ("einmal im Jahr", Fraction(1)),
                 ("zweimal im Jahr", Fraction(2)), ("viermal im Jahr", Fraction(4)), ("mit 2 % Wahrscheinlichkeit im Jahr", Fraction(2, 100)),
                 ("mit 5 % Wahrscheinlichkeit im Jahr", Fraction(5, 100)), ("mit 30 % Wahrscheinlichkeit im Jahr", Fraction(30, 100))]
SCHAEDEN = [1_500, 2_500, 4_000, 6_000, 8_000, 12_000, 20_000, 30_000, 45_000, 60_000, 90_000, 150_000, 250_000]  # Vielfache von 500: Cent-genau
# Bedrohung, Maßnahme, senkt sie die Häufigkeit (h) oder den Schaden je Fall (s)?
BEDROHUNGEN = [("Stromausfall im Serverraum", "eine USV mit automatischem Herunterfahren", "s"),
               ("Ransomware-Befall der Fileserver", "Offline-Backups mit regelmäßigem Wiederherstellungstest", "s"),
               ("Notebook-Diebstahl mit Kundendaten", "Festplattenverschlüsselung auf allen Notebooks", "s"),
               ("Phishing-Angriff mit Datenabfluss", "Schulungen und Zwei-Faktor-Anmeldung", "h"),
               ("DDoS-Angriff auf den Webshop", "einen DDoS-Schutzdienst des Providers", "h"),
               ("Festplattendefekt im NAS", "ein RAID 6 mit Ersatzplatte", "h"),
               ("Ausfall des Mailservers", "einen zweiten Mailserver im Cluster", "s"),
               ("Wasserschaden im Serverraum", "Wassermelder und einen erhöhten Doppelboden", "h"),
               ("Fehler beim Software-Update", "eine Testumgebung und das Vier-Augen-Prinzip", "h")]
W_STUFEN = ["selten", "möglich", "wahrscheinlich", "häufig"]
S_STUFEN = ["gering", "spürbar", "erheblich", "existenzbedrohend"]
KLASSEN_RISIKO = ["niedrig", "mittel", "hoch"]


def _anteil(h: Fraction) -> str:
    return de(float(h), 4)


@art("risiko", "Risikobewertung", "IT-Sicherheit",
     "Eintrittshäufigkeit · Schaden = Risiko pro Jahr, Rangfolge, Risikomatrix, lohnt sich die Maßnahme?",
     ("Risik", "Bedrohungsanalyse", "Schadenshöhe", "Eintrittswahrscheinlichkeit"), formeln=FORMELN["risiko"])
def risiko(rng):
    return rng.choice([_rangfolge, _massnahme, _matrix])(rng)


def _rangfolge(rng):
    while True:
        risiken = [(b, *rng.choice(HAEUFIGKEITEN), rng.choice(SCHAEDEN)) for b, _, _ in rng.sample(BEDROHUNGEN, 4)]
        werte = sorted(h * s for _, _, h, s in risiken)
        if all(b - a >= 50 for a, b in zip(werte, werte[1:])):  # eindeutige Rangfolge
            break
    buchstaben = "ABCD"
    frage = (f"Die {rng.choice(FIRMEN)} bewertet Risiken für ihre IT:\n\n"
             + tabelle(["Risiko", "Bedrohung", "Eintritt", "Schaden je Fall"], [[x, b, t, euro(s)] for x, (b, t, _, s) in zip(buchstaben, risiken)])
             + "\n\nBerechnen Sie für jedes Risiko den erwarteten Schaden pro Jahr und geben Sie die Rangfolge an, das höchste Risiko "
             "zuerst (Buchstaben, z. B. „A, B, C, D“).")
    rang = sorted(buchstaben, key=lambda x: -risiken[buchstaben.index(x)][2] * risiken[buchstaben.index(x)][3])
    felder = [Feld(x, f"Risiko {x}", float(h * s), "€/Jahr") for x, (_, _, h, s) in zip(buchstaben, risiken)]
    felder.append(Feld("rang", "Rangfolge", ", ".join(rang), typ="pfad"))
    weg = schritte(*(f"{x}: {t} = {_anteil(h)} pro Jahr → {_anteil(h)} · {euro(s)} = **{euro(h * s)}**"
                     for x, (_, t, h, s) in zip(buchstaben, risiken)),
                   "Rangfolge nach dem erwarteten Schaden: **" + " > ".join(rang) + "**")
    return Aufgabe(frage, felder, weg, titel="Risiko pro Jahr")


def _massnahme(rng):
    while True:
        bedrohung, massnahme, wirkung = rng.choice(BEDROHUNGEN)
        text1, h1 = rng.choice(HAEUFIGKEITEN[2:8])  # ab einmal in 5 Jahren: es gibt noch seltenere
        schaden = rng.choice(SCHAEDEN[3:])
        if wirkung == "h":
            text2, h2 = rng.choice([x for x in HAEUFIGKEITEN[:8] if x[1] < h1])  # „auf einmal in 10 Jahren“, nicht „auf mit 2 %“
            s2, effekt = schaden, f"senkt die Häufigkeit auf **{text2}**"
        else:
            s2 = rng.choice([s for s in SCHAEDEN if s < schaden])
            h2, effekt = h1, f"senkt den Schaden je Fall auf **{euro(s2)}**"
        jahre, laufend = rng.choice([3, 4, 5]), rng.choice([0, 0, 600, 1_200, 2_400])
        einmalig = jahre * rng.choice([500, 1_000, 1_500, 2_000, 3_000, 5_000, 8_000])
        vorher, nachher, kosten = h1 * schaden, h2 * s2, Fraction(einmalig, jahre) + laufend
        nutzen = vorher - nachher - kosten
        if abs(nutzen) >= 100:
            break
    lohnt = "Ja" if nutzen > 0 else "Nein"
    laufend_text = f" und laufend **{euro(laufend)} pro Jahr**" if laufend else ""
    frage = (f"Bei der {rng.choice(FIRMEN)} rechnet man {text1} mit einem **{bedrohung}**; der Schaden je Fall beträgt **{euro(schaden)}**.\n\n"
             f"Als Maßnahme schlägt die IT {massnahme} vor. Sie kostet einmalig **{euro(einmalig)}** bei einer Nutzungsdauer von "
             f"**{jahre} Jahren**{laufend_text} und {effekt}.\n\nBerechnen Sie das Risiko pro Jahr vor und nach der Maßnahme, die Kosten "
             "der Maßnahme pro Jahr und ihren Nutzen pro Jahr (vermiedener Schaden − Kosten). Lohnt sich die Maßnahme?")
    felder = [Feld("vorher", "Risiko vorher", float(vorher), "€/Jahr"), Feld("nachher", "Risiko nachher", float(nachher), "€/Jahr"),
              Feld("kosten", "Kosten der Maßnahme", float(kosten), "€/Jahr"), Feld("nutzen", "Nutzen", float(nutzen), "€/Jahr"),
              Feld("lohnt", "Lohnt sich die Maßnahme?", lohnt, typ="text", optionen=["Ja", "Nein"])]
    weg = schritte(f"Vorher: {text1} = {_anteil(h1)} pro Jahr → {_anteil(h1)} · {euro(schaden)} = **{euro(vorher)}**",
                   f"Nachher: {_anteil(h2)} · {euro(s2)} = **{euro(nachher)}**",
                   f"Vermiedener Schaden: {euro(vorher)} − {euro(nachher)} = {euro(vorher - nachher)} pro Jahr",
                   f"Kosten pro Jahr: {euro(einmalig)} : {jahre}" + (f" + {euro(laufend)}" if laufend else "") + f" = **{euro(kosten)}**",
                   f"Nutzen: {euro(vorher - nachher)} − {euro(kosten)} = **{euro(nutzen)}** → **{lohnt}**, die Maßnahme "
                   + ("spart mehr, als sie kostet" if nutzen > 0 else "kostet mehr, als sie an Schaden vermeidet"))
    return Aufgabe(frage, felder, weg, titel="Lohnt sich die Maßnahme?")


def _matrix(rng):
    grenzen = rng.choice([(3, 8), (4, 9), (2, 6)])  # bis dahin niedrig, bis dahin mittel, darüber hoch
    risiken = [(b, rng.randint(1, 4), rng.randint(1, 4)) for b, _, _ in rng.sample(BEDROHUNGEN, 3)]

    def klasse(wert):
        return KLASSEN_RISIKO[0 if wert <= grenzen[0] else 1 if wert <= grenzen[1] else 2]
    frage = (f"Die {rng.choice(FIRMEN)} bewertet Risiken mit einer 4 × 4-Matrix. Eintrittswahrscheinlichkeit: "
             + ", ".join(f"{i} = {w}" for i, w in enumerate(W_STUFEN, start=1)) + "; Schadenshöhe: "
             + ", ".join(f"{i} = {s}" for i, s in enumerate(S_STUFEN, start=1))
             + f". Risikowert = Wahrscheinlichkeit · Schadenshöhe; 1 bis {grenzen[0]}: niedrig, {grenzen[0] + 1} bis {grenzen[1]}: mittel, "
             f"ab {grenzen[1] + 1}: hoch.\n\n" + tabelle(["Bedrohung", "Eintrittswahrscheinlichkeit", "Schadenshöhe"],
                                                         [[b, W_STUFEN[w - 1], S_STUFEN[s - 1]] for b, w, s in risiken])
             + "\n\nBerechnen Sie für jede Bedrohung den Risikowert und ordnen Sie die Risikoklasse zu.")
    felder = []
    for i, (b, w, s) in enumerate(risiken):
        felder += [Feld(f"w{i}", f"{b}: Risikowert", w * s, stellen=0),
                   Feld(f"k{i}", f"{b}: Klasse", klasse(w * s), typ="text", optionen=KLASSEN_RISIKO)]
    weg = schritte(*(f"{b}: {W_STUFEN[w - 1]} = {w}, {S_STUFEN[s - 1]} = {s} → {w} · {s} = **{w * s}** → **{klasse(w * s)}**"
                     for b, w, s in risiken))
    return Aufgabe(frage, felder, weg, titel="Risikomatrix")


# --- Prüfziffern, Parität, XOR ------------------------------------------------------------

def gewichtet(ziffern: list[int]) -> int:
    """EAN-13: von links abwechselnd mal 1 und mal 3."""
    return sum(z * (3 if i % 2 else 1) for i, z in enumerate(ziffern))


def pruefziffer(ziffern: list[int]) -> int:
    return (10 - gewichtet(ziffern) % 10) % 10


@art("pruefziffer", "Prüfziffern und Parität", "IT-Sicherheit", "Paritätsbit, EAN-13- und ISBN-13-Prüfziffer, XOR bitweise",
     ("Prüfziffer", "Prüfsumme", "Paritä", "EAN-13", "ISBN", "Barcode", "Strichcode", "Fehlererkennung", "XOR"), formeln=FORMELN["pruefziffer"])
def pruefziffern(rng):
    return rng.choice([_paritaet, _ean, _ean, _xor])(rng)


def _einsen(wort: int) -> int:
    return bin(wort).count("1")


def _paritaet(rng):
    bits = rng.choice([7, 8])
    wort, daten = rng.randrange(1, 2 ** bits), rng.randrange(1, 2 ** bits)
    gesendet = daten << 1 | _einsen(daten) % 2  # Paritätsbit hinten, gerade Parität
    empfangen = gesendet
    gekippt = rng.choice([0, 1, 1, 2])
    for stelle in rng.sample(range(bits + 1), gekippt):
        empfangen ^= 1 << stelle
    gerade, fehler = _einsen(wort) % 2, _einsen(empfangen) % 2 == 1
    frage = (f"Zwei Steuerungen der {rng.choice(FIRMEN)} tauschen Datenwörter mit {bits} Bit und einem Paritätsbit aus.\n\n"
             f"1. Welches Paritätsbit gehört zum Datenwort `{wort:0{bits}b}` bei gerader und bei ungerader Parität?\n"
             f"2. Bei gerader Parität kommt `{empfangen:0{bits + 1}b}` an (Paritätsbit am Ende). Meldet die Paritätsprüfung einen Fehler?")
    felder = [Feld("gerade", "Paritätsbit, gerade Parität", gerade, stellen=0),
              Feld("ungerade", "Paritätsbit, ungerade Parität", 1 - gerade, stellen=0),
              Feld("fehler", "Meldet die Prüfung einen Fehler?", "Ja" if fehler else "Nein", typ="text", optionen=["Ja", "Nein"])]
    wirklich = {0: "Tatsächlich kam das Wort unverändert an.",
                1: f"Tatsächlich ist ein Bit gekippt (gesendet: `{gesendet:0{bits + 1}b}`).",
                2: f"Tatsächlich sind zwei Bits gekippt (gesendet: `{gesendet:0{bits + 1}b}`): Die Anzahl der Einsen bleibt gerade, "
                   "die Paritätsprüfung bemerkt das nicht."}[gekippt]
    weg = schritte(f"`{wort:0{bits}b}` enthält {_einsen(wort)} Einsen ({'un' if _einsen(wort) % 2 else ''}gerade)",
                   f"Gerade Parität: die Einsen samt Paritätsbit müssen gerade sein → Paritätsbit **{gerade}**",
                   f"Ungerade Parität: die Einsen samt Paritätsbit müssen ungerade sein → Paritätsbit **{1 - gerade}**",
                   f"Empfangen `{empfangen:0{bits + 1}b}`: {_einsen(empfangen)} Einsen, "
                   + ("ungerade → **Ja**, Fehler erkannt" if fehler else "gerade → **Nein**, die Prüfung meldet keinen Fehler"),
                   wirklich)
    return Aufgabe(frage, felder, weg, titel="Paritätsbit")


def _summe_text(ziffern: list[int]) -> str:
    return " + ".join(f"{z} · {3 if i % 2 else 1}" for i, z in enumerate(ziffern))


def _ean(rng):
    firma = rng.choice(FIRMEN)
    if rng.random() < 0.5:
        name, ziffern = "EAN-13", [4, rng.randint(0, 4)] + [rng.randrange(10) for _ in range(10)]
        anlass = f"Die {firma} vergibt für einen neuen Artikel eine EAN-13."
    else:
        name, ziffern = "ISBN-13", [9, 7, 8, 3] + [rng.randrange(10) for _ in range(8)]
        anlass = f"Die {firma} gibt ein Schulungshandbuch als Buch heraus und erhält eine ISBN-13."
    pz = pruefziffer(ziffern)
    if rng.random() < 0.5:
        frage = (f"{anlass} Die ersten zwölf Ziffern lauten `{''.join(map(str, ziffern))}`.\n\n"
                 "Berechnen Sie die gewichtete Summe der zwölf Ziffern und die Prüfziffer.")
        summe = gewichtet(ziffern)
        felder = [Feld("summe", "Gewichtete Summe", summe, stellen=0), Feld("pz", "Prüfziffer", pz, stellen=0)]
        weg = schritte("Gewichte von links abwechselnd 1 und 3", f"Summe: {_summe_text(ziffern)} = **{summe}**",
                       f"Prüfziffer: bis zum nächsten Zehner fehlen (10 − {summe} mod 10) mod 10 = (10 − {summe % 10}) mod 10 = **{pz}**",
                       f"Vollständig: {''.join(map(str, ziffern))}{pz}")
        return Aufgabe(frage, felder, weg, titel=f"{name}-Prüfziffer")
    nummer = ziffern + [pz]
    if rng.random() < 0.5:  # Tippfehler: eine Ziffer anders, das fällt bei EAN-13 immer auf
        stelle = rng.randrange(13)
        nummer[stelle] = rng.choice([z for z in range(10) if z != nummer[stelle]])
    summe = gewichtet(nummer)
    gueltig = summe % 10 == 0
    frage = (f"{anlass} In einer Liste steht die Nummer `{''.join(map(str, nummer))}`.\n\n"
             "Berechnen Sie die gewichtete Summe aller 13 Ziffern und prüfen Sie, ob die Nummer gültig ist.")
    felder = [Feld("summe", "Gewichtete Summe aller 13 Ziffern", summe, stellen=0),
              Feld("gueltig", "Ist die Nummer gültig?", "Ja" if gueltig else "Nein", typ="text", optionen=["Ja", "Nein"])]
    weg = schritte("Alle 13 Ziffern von links abwechselnd mit 1 und 3 gewichten, die Prüfziffer an 13. Stelle mit 1",
                   f"Summe: {_summe_text(nummer)} = **{summe}**",
                   f"{summe} ist {'ein' if gueltig else 'kein'} Vielfaches von 10 → **{'Ja' if gueltig else 'Nein'}**"
                   + ("" if gueltig else f"; richtig wäre die Prüfziffer {pruefziffer(nummer[:12])} zu den ersten zwölf Ziffern"))
    return Aufgabe(frage, felder, weg, titel=f"{name} prüfen")


def _bits(x: int) -> str:
    return f"{x >> 4:04b} {x & 15:04b}"


def _xor(rng):
    klar, schluessel_ = rng.randrange(256), rng.randrange(1, 256)
    geheim = klar ^ schluessel_
    firma = rng.choice(FIRMEN)
    if rng.random() < 0.5:
        frage = (f"Zwei Systeme der {firma} verschleiern ein Steuerbyte mit XOR. Klartext: `{_bits(klar)}`, Schlüssel: "
                 f"`{_bits(schluessel_)}`.\n\nBerechnen Sie den Geheimtext binär und hexadezimal.")
        zeilen, ergebnis, name = [["Klartext", klar], ["Schlüssel", schluessel_], ["Geheimtext", geheim]], geheim, "Geheimtext"
    else:
        frage = (f"Bei der {firma} kommt das mit XOR verschleierte Steuerbyte `{_bits(geheim)}` an. Der gemeinsame Schlüssel ist "
                 f"`{_bits(schluessel_)}`.\n\nWie lautet der Klartext binär und hexadezimal?")
        zeilen, ergebnis, name = [["Geheimtext", geheim], ["Schlüssel", schluessel_], ["Klartext", klar]], klar, "Klartext"
    felder = [Feld("binaer", f"{name} binär", f"{ergebnis:08b}", typ="binaer"), Feld("hex", f"{name} hexadezimal", f"{ergebnis:02X}", typ="hex")]
    weg = (schritte("XOR Bit für Bit: gleiche Bits ergeben 0, verschiedene 1",
                    f"{name}: **{_bits(ergebnis)}** = {ergebnis >> 4:X} | {ergebnis & 15:X} = **{ergebnis:02X}** hexadezimal",
                    "Probe: noch einmal XOR mit demselben Schlüssel ergibt wieder den Ausgangswert")
           + "\n\n" + tabelle(["", "Bits"], [[t, f"`{_bits(x)}`"] for t, x in zeilen]))
    return Aufgabe(frage, felder, weg, titel="XOR bitweise")


# --- DSGVO in Zahlen ----------------------------------------------------------------------

# Art. 83 Abs. 4 lit. a: Art. 8, 11, 25 bis 39, 42, 43; Abs. 5: Art. 5, 6, 7, 9 (lit. a), 12 bis 22 (lit. b), 44 bis 49 (lit. c)
PFLICHTEN = "Pflichten des Verantwortlichen (Art. 25 bis 39)"
GRUNDSAETZE = "Grundsätze und Rechtmäßigkeit der Verarbeitung (Art. 5, 6, 7, 9)"
VERSTOESSE = {
    4: [("hat eine meldepflichtige Datenpanne nicht an die Aufsichtsbehörde gemeldet (Art. 33 DSGVO)", PFLICHTEN),
        ("führt kein Verzeichnis von Verarbeitungstätigkeiten (Art. 30 DSGVO)", PFLICHTEN),
        ("hat für ihre Kundendatenbank keine angemessenen technischen und organisatorischen Maßnahmen getroffen (Art. 32 DSGVO)", PFLICHTEN),
        ("hat trotz Pflicht keinen Datenschutzbeauftragten benannt (Art. 37 DSGVO)", PFLICHTEN),
        ("lässt Personaldaten bei einem Dienstleister ohne Vertrag zur Auftragsverarbeitung verarbeiten (Art. 28 DSGVO)", PFLICHTEN),
        ("hat vor einer umfangreichen Videoüberwachung keine Datenschutz-Folgenabschätzung durchgeführt (Art. 35 DSGVO)", PFLICHTEN)],
    5: [("nutzt Kundendaten ohne Rechtsgrundlage für Werbung (Art. 6 DSGVO)", GRUNDSAETZE),
        ("beantwortet Auskunftsersuchen von Kunden nicht (Art. 15 DSGVO)", "Rechte der Betroffenen (Art. 12 bis 22)"),
        ("löscht Daten trotz berechtigten Löschantrags nicht (Art. 17 DSGVO)", "Rechte der Betroffenen (Art. 12 bis 22)"),
        ("übermittelt Beschäftigtendaten ohne geeignete Garantien in ein Drittland (Art. 44 DSGVO)",
         "Übermittlung in Drittländer (Art. 44 bis 49)"),
        ("bewahrt Bewerberdaten unbegrenzt auf, entgegen dem Grundsatz der Speicherbegrenzung (Art. 5 DSGVO)", GRUNDSAETZE),
        ("verarbeitet Gesundheitsdaten von Beschäftigten ohne Ausnahmetatbestand (Art. 9 DSGVO)", GRUNDSAETZE)],
}
UMSAETZE = [60, 150, 320, 480, 520, 750, 1_100, 2_400, 6_800]  # Mio. €; bei 500 Mio. € wären beide Beträge gleich
ABSAETZE = ["Art. 83 Abs. 4", "Art. 83 Abs. 5"]
DATENPANNEN = ["kopiert ein Angreifer Kundendaten aus dem Webshop", "geht eine Liste mit Gehaltsdaten per E-Mail an einen falschen Verteiler",
               "verliert ein Außendienstmitarbeiter einen unverschlüsselten USB-Stick mit Bewerberdaten",
               "verschlüsselt Ransomware den Fileserver mit den Personalakten"]


def _mio(x: float) -> str:
    return f"{de(x)} Mio. €" if x < 1000 else f"{de(x / 1000)} Mrd. € ({de(x)} Mio. €)"


@art("dsgvo", "DSGVO in Zahlen", "IT-Sicherheit", "Bußgeldrahmen nach Art. 83 und Meldefrist von 72 Stunden nach Art. 33",
     ("DSGVO", "Datenschutz-Grundverordnung", "Datenschutzverletzung", "Datenpanne", "Bußgeld"), formeln=FORMELN["dsgvo"])
def dsgvo(rng):
    return rng.choice([_bussgeld, _meldefrist])(rng)


def _bussgeld(rng):
    absatz, umsatz = rng.choice([4, 5]), rng.choice(UMSAETZE)
    fest, prozent = (10, 2) if absatz == 4 else (20, 4)
    anteil = umsatz * prozent / 100
    verstoss, gruppe = rng.choice(VERSTOESSE[absatz])
    frage = (f"Eine Aufsichtsbehörde stellt fest: Die {rng.choice(FIRMEN)} {verstoss}. Der weltweite Jahresumsatz des Unternehmens im "
             f"vorangegangenen Geschäftsjahr betrug **{_mio(umsatz)}**.\n\nNach welchem Absatz von Art. 83 DSGVO richtet sich der "
             "Bußgeldrahmen? Berechnen Sie den umsatzabhängigen Betrag und die Obergrenze des Bußgelds in Mio. €.")
    felder = [Feld("absatz", "Bußgeldrahmen nach", ABSAETZE[absatz - 4], typ="text", optionen=ABSAETZE),
              Feld("anteil", "Umsatzabhängiger Betrag", anteil, "Mio. €"), Feld("hoechst", "Obergrenze", max(fest, anteil), "Mio. €")]
    weg = schritte(f"Der Verstoß betrifft die {gruppe} → **{ABSAETZE[absatz - 4]}**: bis {fest} Mio. € oder {prozent} % des weltweiten "
                   "Jahresumsatzes, der höhere Betrag",
                   f"{prozent} % von {de(umsatz)} Mio. € = {de(umsatz)} · {de(prozent / 100)} = **{de(anteil)} Mio. €**",
                   f"Der höhere Betrag zählt: max({fest}; {de(anteil)}) = **{de(max(fest, anteil))} Mio. €**")
    return Aufgabe(frage, felder, weg, titel="Bußgeldrahmen")


def _meldefrist(rng):
    # nicht im März und Oktober: über die Zeitumstellung wären 72 Stunden nicht mehr dieselbe Uhrzeit drei Tage später
    kenntnis = datetime(rng.randint(2026, 2028), rng.choice([1, 2, 4, 5, 6, 7, 8, 9, 11, 12]), rng.randint(1, 28), rng.randint(7, 19),
                        rng.choice([5, 10, 15, 20, 25, 35, 40, 45, 50, 55]))
    vorfall = kenntnis - timedelta(hours=rng.randint(5, 60), minutes=rng.randint(1, 59))
    frist = kenntnis + timedelta(hours=72)
    firma = rng.choice(FIRMEN)
    frage = (f"Bei der {firma} {rng.choice(DATENPANNEN)}, und zwar am {lang(vorfall)} um {vorfall:%H:%M} Uhr. Bemerkt wird die Datenpanne "
             f"erst am **{lang(kenntnis)} um {kenntnis:%H:%M} Uhr**. Die Datenschutzbeauftragte stellt fest, dass ein Risiko für die "
             "Betroffenen besteht; die Verletzung ist also meldepflichtig.\n\nBis wann muss die Meldung an die Aufsichtsbehörde "
             "spätestens erfolgen (Art. 33 DSGVO)? Geben Sie Datum, Uhrzeit und Wochentag an.")
    felder = [Feld("datum", "Meldung spätestens am", kurz(frist), typ="datum"), Feld("uhrzeit", "Uhrzeit", f"{frist:%H:%M}", typ="liste"),
              Feld("tag", "Wochentag", WOCHENTAGE[frist.weekday()], typ="wochentage")]
    weg = schritte(f"Die Frist läuft ab der Kenntnis, nicht ab dem Vorfall: {lang(kenntnis)}, {kenntnis:%H:%M} Uhr",
                   "72 Stunden = 3 Tage, Wochenenden und Feiertage zählen mit",
                   f"{kurz(kenntnis)}, {kenntnis:%H:%M} Uhr + 72 Stunden = **{lang(frist)}, {frist:%H:%M} Uhr**",
                   "Melden muss die Firma unverzüglich; die 72 Stunden sind die Obergrenze, eine spätere Meldung ist zu begründen")
    return Aufgabe(frage, felder, weg, titel="Meldefrist nach Art. 33")
