"""WiSo: Kündigungsfristen (§ 622 BGB, § 22 BBiG) und Urlaubsanspruch (BUrlG, § 19 JArbSchG).
Fristen nach §§ 187, 188 BGB: Die Frist beginnt am Tag nach dem Zugang und endet mit dem Tag, der dem Zugangstag entspricht
(4 Wochen = 28 Tage später; n Monate später, fehlt der Tag im Monat, dann am Monatsletzten)."""

import calendar
import math
from datetime import date, timedelta

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, de, schritte

FORMELN = {
    "kuendigung": """- § 622 Abs. 1 BGB, Grundkündigungsfrist: 4 Wochen zum 15. oder zum Ende eines Kalendermonats; gilt für Arbeitnehmer immer
- § 622 Abs. 2 BGB, Kündigung durch den Arbeitgeber nach 2 / 5 / 8 / 10 / 12 / 15 / 20 Jahren Betriebszugehörigkeit (beim Zugang): 1 / 2 / 3 / 4 / 5 / 6 / 7 Monate zum Monatsende
- § 622 Abs. 3 BGB, vereinbarte Probezeit (höchstens 6 Monate): 2 Wochen, zu jedem Tag
- Fristbeginn am Tag nach dem Zugang (§ 187 BGB); 4 Wochen enden 28 Tage nach dem Zugang, n Monate am gleichen Tag n Monate später (§ 188 BGB); danach der nächste zulässige Termin
- Ausbildung (§ 22 BBiG): in der Probezeit (1 bis 4 Monate) jederzeit ohne Frist; danach Azubi mit 4 Wochen, wenn er die Ausbildung aufgibt oder wechselt; der Betrieb nur fristlos aus wichtigem Grund
- *Typische Fehler:* den Tag des Zugangs mitgezählt, nach den 4 Wochen nicht bis zum 15. oder Monatsende weitergezählt, die verlängerten Fristen auch bei Kündigung durch den Arbeitnehmer

*Beispiel:* Zugang 3. März, + 28 Tage = 31. März → Termin 31. März; Zugang 4. März, + 28 Tage = 1. April → Termin 15. April""",
    "urlaub": """- § 3 BUrlG: mindestens 24 Werktage im Jahr; Werktage sind Montag bis Samstag (6-Tage-Woche)
- Umrechnung: Urlaubstage = Werktage : 6 · Arbeitstage je Woche (24 Werktage = 20 Tage bei der 5-Tage-Woche)
- § 19 JArbSchG, Alter zu Beginn des Kalenderjahres: noch nicht 16 → 30, noch nicht 17 → 27, noch nicht 18 → 25 Werktage
- § 4 BUrlG: voller Anspruch erst nach 6 Monaten (Wartezeit); wer ab 2. Juli eintritt, erfüllt sie im Jahr nicht
- § 5 BUrlG: 1/12 je vollem Beschäftigungsmonat, wenn die Wartezeit im Jahr nicht erfüllt ist oder man in der ersten Jahreshälfte ausscheidet; wer nach erfüllter Wartezeit in der zweiten Hälfte ausscheidet, behält den vollen Urlaub
- § 5 Abs. 2 BUrlG: Bruchteile ab einem halben Tag werden auf volle Tage aufgerundet

*Beispiel:* 30 Tage Jahresurlaub, Eintritt 1. August: 5 volle Monate → 30 · 5 : 12 = 12,5 → 13 Tage""",
}

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
# § 622 Abs. 2 BGB: (Jahre Betriebszugehörigkeit, Monate Frist zum Monatsende)
STAFFEL = [(20, 7), (15, 6), (12, 5), (10, 4), (8, 3), (5, 2), (2, 1)]
FRISTEN = ["2 Wochen", "4 Wochen zum 15. oder Monatsende"] + [f"{n} {'Monat' if n == 1 else 'Monate'} zum Monatsende" for n in range(1, 8)]
FRISTEN_AUSBILDUNG = ["Ohne Frist, jederzeit", "4 Wochen", "4 Wochen zum 15. oder Monatsende", "Nur fristlos aus wichtigem Grund"]


def lang(d: date) -> str:
    return f"{WOCHENTAGE[d.weekday()]}, {d.day}. {MONATE[d.month - 1]} {d.year}"


def kurz(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def monatsende(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def plus_monate(d: date, n: int) -> date:
    """Gleicher Tag n Monate später; fehlt er, der Monatsletzte (§ 188 Abs. 3 BGB)."""
    m = d.month - 1 + n
    jahr, monat = d.year + m // 12, m % 12 + 1
    return date(jahr, monat, min(d.day, calendar.monthrange(jahr, monat)[1]))


def grundfrist(zugang: date) -> date:
    """§ 622 Abs. 1 BGB: 4 Wochen zum 15. oder zum Monatsende."""
    frueh = zugang + timedelta(days=28)
    return date(frueh.year, frueh.month, 15) if frueh.day <= 15 else monatsende(frueh)


def volle_jahre(von: date, bis: date) -> int:
    return bis.year - von.year - ((bis.month, bis.day) < (von.month, von.day))


def _zugang(rng) -> date:
    return date(rng.randint(2026, 2028), 1, 1) + timedelta(days=rng.randrange(365))


@art("kuendigung", "Kündigungsfristen", "WiSo", "Kündigungstermin nach § 622 BGB und § 22 BBiG, mit Kalenderlogik",
     ("Kündigung", "Ausbildungsvertrag", "Arbeitsrecht"), formeln=FORMELN["kuendigung"])
def kuendigung(rng):
    return rng.choice([_arbeitnehmer, _arbeitgeber, _arbeitgeber, _probezeit, _ausbildung])(rng)


# typische Fehler (Feld.typisch)
ZUGANG = "Du hast den Tag des Zugangs mitgezählt; die Frist beginnt erst am Tag danach (§ 187 BGB)."
NUR_ARBEITGEBER = "Die verlängerten Fristen aus § 622 Abs. 2 gelten nur, wenn der Arbeitgeber kündigt."
GRUNDFRIST = "Du hast die Grundfrist genommen; kündigt der Arbeitgeber, verlängert sie sich mit der Betriebszugehörigkeit."
PROBEZEIT = "In der Probezeit gilt die kürzere Frist von 2 Wochen, zu jedem Tag."


def _felder(frist: str, ende: date, optionen=FRISTEN, frist_typisch=(), ende_typisch=()) -> list[Feld]:
    """ende_typisch: (Datum, Hinweis) aus typischen Fehlern."""
    return [Feld("frist", "Kündigungsfrist", frist, typ="text", optionen=optionen, typisch=tuple(frist_typisch)),
            Feld("ende", "Ende des Arbeitsverhältnisses", kurz(ende), typ="datum", typisch=tuple((kurz(d), h) for d, h in ende_typisch))]


def _grund_typisch(zugang: date) -> list:
    """Ende nach § 622 Abs. 1: Zugang mitgezählt, oder nach den 4 Wochen nicht bis zum Termin weitergezählt."""
    return [(grundfrist(zugang - timedelta(days=1)), ZUGANG),
            (zugang + timedelta(days=28), "Nach den 4 Wochen geht es noch bis zum nächsten 15. oder Monatsende.")]


def _grund_weg(zugang: date, wer: str) -> list[str]:
    frueh = zugang + timedelta(days=28)
    ende = grundfrist(zugang)
    return [f"§ 622 Abs. 1 BGB: 4 Wochen zum 15. oder zum Monatsende ({wer})",
            f"Fristbeginn am Tag nach dem Zugang (§ 187 BGB); 4 Wochen = 28 Tage: {kurz(zugang)} + 28 Tage = {kurz(frueh)} (§ 188 BGB)",
            f"Nächster zulässiger Termin ab {kurz(frueh)}: {'der 15.' if ende.day == 15 else 'das Monatsende'} → **{kurz(ende)}**"]


def _eintritt(rng, zugang: date, jahre: float) -> date:
    """Eintritt so, dass beim Zugang gut erkennbar so viele volle Jahre bestehen (kein Jahrestag in der Nähe)."""
    return zugang - timedelta(days=int(jahre * 365.25) + rng.randint(190 if jahre == 0 else 40, 300))


def _arbeitnehmer(rng):
    zugang = _zugang(rng)
    eintritt = _eintritt(rng, zugang, rng.randint(1, 15))
    jahre = volle_jahre(eintritt, zugang)
    frage = (f"Eine Mitarbeiterin der {rng.choice(FIRMEN)} ist seit dem **{kurz(eintritt)}** dort beschäftigt. Sie kündigt selbst; "
             f"die Kündigung geht dem Arbeitgeber am **{lang(zugang)}** zu. Vertraglich ist nichts Abweichendes vereinbart.\n\n"
             "Welche Kündigungsfrist gilt, und an welchem Tag endet das Arbeitsverhältnis frühestens? (Datum als TT.MM.JJJJ)")
    weg = schritte(f"Kündigung durch die Arbeitnehmerin: die verlängerten Fristen aus § 622 Abs. 2 BGB gelten nur für den Arbeitgeber, "
                   f"die {jahre} Jahre Betriebszugehörigkeit spielen keine Rolle", *_grund_weg(zugang, "für Arbeitnehmer immer"))
    frist_typisch, ende_typisch = [], _grund_typisch(zugang)
    if laenger := next((m for j, m in STAFFEL if jahre >= j), 0):  # was gälte, wenn der Arbeitgeber kündigte
        frist_typisch.append((FRISTEN[1 + laenger], NUR_ARBEITGEBER))
        ende_typisch.append((monatsende(plus_monate(zugang, laenger)), NUR_ARBEITGEBER))
    return Aufgabe(frage, _felder(FRISTEN[1], grundfrist(zugang), frist_typisch=frist_typisch, ende_typisch=ende_typisch), weg,
                   titel="Kündigung durch den Arbeitnehmer")


def _arbeitgeber(rng):
    zugang = _zugang(rng)
    eintritt = _eintritt(rng, zugang, rng.choice([0, 1, 2, 3, 5, 6, 8, 9, 10, 12, 13, 15, 17, 20, 22]))
    jahre = volle_jahre(eintritt, zugang)
    frage = (f"Die {rng.choice(FIRMEN)} kündigt einem Mitarbeiter ordentlich. Er ist seit dem **{kurz(eintritt)}** im Betrieb, die "
             f"Probezeit ist lange vorbei. Die Kündigung geht ihm am **{lang(zugang)}** zu; Arbeits- und Tarifvertrag regeln nichts "
             "Abweichendes.\n\nWelche Kündigungsfrist gilt, und an welchem Tag endet das Arbeitsverhältnis frühestens? (Datum als TT.MM.JJJJ)")
    monate = next((m for j, m in STAFFEL if jahre >= j), 0)
    if not monate:
        weg = schritte(f"Betriebszugehörigkeit beim Zugang: {jahre} {'Jahr' if jahre == 1 else 'Jahre'} (seit {kurz(eintritt)}), "
                       "weniger als 2 Jahre", *_grund_weg(zugang, "Arbeitgeber, unter 2 Jahren Betriebszugehörigkeit"))
        return Aufgabe(frage, _felder(FRISTEN[1], grundfrist(zugang), ende_typisch=_grund_typisch(zugang)), weg,
                       titel="Kündigung durch den Arbeitgeber")
    fristende = plus_monate(zugang, monate)
    ende = monatsende(fristende)
    stufe = next(j for j, m in STAFFEL if m == monate)
    weg = schritte(f"Betriebszugehörigkeit beim Zugang: {jahre} Jahre (seit {kurz(eintritt)}) → mindestens {stufe} Jahre",
                   f"§ 622 Abs. 2 Satz 1 Nr. {monate} BGB: Kündigung durch den Arbeitgeber mit **{monate} "
                   f"{'Monat' if monate == 1 else 'Monaten'} zum Monatsende**",
                   f"Fristbeginn am Tag nach dem Zugang; {monate} {'Monat' if monate == 1 else 'Monate'} nach dem {kurz(zugang)} "
                   f"ist der {kurz(fristende)} (§ 188 BGB)",
                   f"Nächstes Monatsende ab {kurz(fristende)}: **{kurz(ende)}**")
    felder = _felder(FRISTEN[1 + monate], ende, frist_typisch=[(FRISTEN[1], GRUNDFRIST)], ende_typisch=[
        (grundfrist(zugang), GRUNDFRIST), (monatsende(plus_monate(zugang - timedelta(days=1), monate)), ZUGANG),
        (fristende, "Nach den Monaten geht es noch bis zum Monatsende.")])
    return Aufgabe(frage, felder, weg, titel="Kündigung durch den Arbeitgeber")


def _probezeit(rng):
    eintritt = date(rng.randint(2026, 2028), rng.randint(1, 12), rng.choice([1, 15]))
    probe = rng.choice([3, 6])
    zugang = eintritt + timedelta(days=rng.randint(10, probe * 30 - 15))
    wer = rng.choice(["Der Arbeitgeber kündigt der neuen Mitarbeiterin", "Der neue Mitarbeiter kündigt selbst"])
    ende = zugang + timedelta(days=14)
    frage = (f"Bei der {rng.choice(FIRMEN)} beginnt am **{kurz(eintritt)}** ein Arbeitsverhältnis mit einer vereinbarten Probezeit "
             f"von {probe} Monaten. {wer}; die Kündigung geht am **{lang(zugang)}** zu.\n\n"
             "Welche Kündigungsfrist gilt, und an welchem Tag endet das Arbeitsverhältnis frühestens? (Datum als TT.MM.JJJJ)")
    weg = schritte(f"Die Probezeit läuft bis {kurz(plus_monate(eintritt, probe) - timedelta(days=1))}, der Zugang liegt darin",
                   "§ 622 Abs. 3 BGB: in der Probezeit **2 Wochen**, nicht an den 15. oder das Monatsende gebunden (für beide Seiten)",
                   f"{kurz(zugang)} + 14 Tage = **{kurz(ende)}**")
    felder = _felder(FRISTEN[0], ende, frist_typisch=[(FRISTEN[1], PROBEZEIT)],
                     ende_typisch=[(grundfrist(zugang), PROBEZEIT), (ende - timedelta(days=1), ZUGANG)])
    return Aufgabe(frage, felder, weg, titel="Kündigung in der Probezeit")


def _ausbildung(rng):
    beginn = date(rng.randint(2026, 2028), rng.choice([8, 9]), 1)
    probe = rng.choice([1, 2, 3, 4])
    probe_ende = plus_monate(beginn, probe) - timedelta(days=1)
    fall = rng.choice(["probe", "azubi", "betrieb"])
    zugang = beginn + timedelta(days=rng.randint(3, probe * 30 - 5)) if fall == "probe" else \
        probe_ende + timedelta(days=rng.randint(20, 300))
    firma = rng.choice(FIRMEN)
    lage = f"Ein Auszubildender beginnt am **{kurz(beginn)}** seine Ausbildung bei der {firma}; vereinbart sind {probe} " \
           f"{'Monat' if probe == 1 else 'Monate'} Probezeit."
    if fall == "betrieb":
        frage = (f"{lage} Am **{lang(zugang)}** will der Betrieb das Ausbildungsverhältnis ordentlich beenden, weil die Leistungen "
                 "nicht stimmen.\n\nWie kann der Betrieb jetzt kündigen?")
        weg = schritte(f"Die Probezeit endete am {kurz(probe_ende)}, der {kurz(zugang)} liegt danach",
                       "§ 22 Abs. 2 BBiG: nach der Probezeit kann der Ausbildungsbetrieb nicht ordentlich kündigen, "
                       "**nur fristlos aus wichtigem Grund** (Nr. 1), schriftlich mit Angabe der Gründe (Abs. 3)",
                       "Schwache Leistungen allein sind in der Regel kein wichtiger Grund; erst Gespräche und Abmahnung")
        felder = [Feld("frist", "Kündigung durch den Betrieb", FRISTEN_AUSBILDUNG[3], typ="text", optionen=FRISTEN_AUSBILDUNG, typisch=(
            (FRISTEN_AUSBILDUNG[1], "Nach der Probezeit kann der Betrieb nicht mehr ordentlich kündigen, nur der Auszubildende."),
            (FRISTEN_AUSBILDUNG[2], "Das ist die Grundfrist aus dem Arbeitsrecht; im Ausbildungsverhältnis gilt § 22 BBiG.")))]
        return Aufgabe(frage, felder, weg, titel="Ausbildung: Kündigung durch den Betrieb")
    if fall == "probe":
        wer = rng.choice(["Der Betrieb kündigt", "Der Auszubildende kündigt"])
        frage = f"{lage} {wer} am **{lang(zugang)}**; die Kündigung geht am selben Tag zu."
        weg = schritte(f"Die Probezeit läuft bis {kurz(probe_ende)}, der Zugang liegt darin",
                       "§ 22 Abs. 1 BBiG: in der Probezeit jederzeit **ohne Kündigungsfrist** (für beide Seiten, schriftlich)",
                       f"Das Ausbildungsverhältnis endet mit dem Zugang: **{kurz(zugang)}**")
        frist, ende = FRISTEN_AUSBILDUNG[0], zugang
        typisch = [(zugang + timedelta(days=14), "Die 2 Wochen gelten in der Probezeit eines Arbeitsverhältnisses; in der "
                                                  "Ausbildung geht es ohne Frist (§ 22 Abs. 1 BBiG).")]
    else:
        frage = (f"{lage} Am **{lang(zugang)}** geht dem Betrieb seine Kündigung zu: Er will die Ausbildung aufgeben und "
                 "studieren.")
        ende = zugang + timedelta(days=28)
        weg = schritte(f"Die Probezeit endete am {kurz(probe_ende)}, der Zugang liegt danach",
                       "§ 22 Abs. 2 Nr. 2 BBiG: der Auszubildende kann mit **4 Wochen** kündigen, wenn er die Ausbildung aufgibt "
                       "oder sich für einen anderen Beruf ausbilden lassen will; nicht an den 15. oder das Monatsende gebunden",
                       f"{kurz(zugang)} + 28 Tage = **{kurz(ende)}**")
        frist = FRISTEN_AUSBILDUNG[1]
        typisch = [(grundfrist(zugang), "Der Auszubildende kündigt mit 4 Wochen ohne festen Termin, nicht zum 15. oder Monatsende."),
                   (ende - timedelta(days=1), ZUGANG)]
    frage += "\n\nWelche Kündigungsfrist gilt, und an welchem Tag endet das Ausbildungsverhältnis? (Datum als TT.MM.JJJJ)"
    felder = [Feld("frist", "Kündigungsfrist", frist, typ="text", optionen=FRISTEN_AUSBILDUNG),
              Feld("ende", "Ende des Ausbildungsverhältnisses", kurz(ende), typ="datum", typisch=tuple((kurz(d), h) for d, h in typisch))]
    return Aufgabe(frage, felder, weg, titel="Ausbildung: Kündigung")


# --- Urlaub -------------------------------------------------------------------

def volle_monate(von: date, bis: date) -> int:
    """Volle Beschäftigungsmonate von „von“ bis einschließlich „bis“ (von ist ein 1. oder 15.)."""
    n = 0
    while plus_monate(von, n + 1) - timedelta(days=1) <= bis:
        n += 1
    return n


def aufrunden(tage: float) -> float:
    """§ 5 Abs. 2 BUrlG: Bruchteile ab einem halben Tag auf volle Tage aufrunden."""
    return math.ceil(tage) if tage - math.floor(tage) >= 0.5 else tage


def jugend_werktage(geburt: date, jahr: int) -> tuple[int, int]:
    """(Alter zu Beginn des Kalenderjahres, Werktage nach § 19 JArbSchG bzw. 24 nach § 3 BUrlG)."""
    alter = volle_jahre(geburt, date(jahr, 1, 1))
    return alter, 30 if alter < 16 else 27 if alter < 17 else 25 if alter < 18 else 24


@art("urlaub", "Urlaubsanspruch", "WiSo", "BUrlG und JArbSchG: Werktage umrechnen, anteiliger Urlaub bei Ein- und Austritt",
     ("Urlaub", "Jugendarbeitsschutz", "Arbeitszeit"), formeln=FORMELN["urlaub"])
def urlaub(rng):
    return rng.choice([_umrechnung, _eintritt_im_jahr, _austritt])(rng)


def _umrechnung(rng):
    jahr, woche = rng.randint(2026, 2028), rng.choice([5, 5, 4])
    geburt = date(jahr - rng.choice([15, 16, 17, 19]) - 1, rng.randint(2, 11), rng.randint(1, 28))
    alter, werktage = jugend_werktage(geburt, jahr)
    tage = werktage * woche / 6
    regel = (f"§ 19 JArbSchG: zu Beginn des Jahres noch nicht {alter + 1} → **{werktage} Werktage**" if alter < 18
             else f"volljährig: § 3 BUrlG, mindestens **{werktage} Werktage**")
    frage = (f"Eine Auszubildende der {rng.choice(FIRMEN)} ist am **{kurz(geburt)}** geboren. Sie arbeitet an {woche} Tagen pro Woche; "
             f"vertraglich gilt nur der gesetzliche Mindesturlaub.\n\nWie viele Werktage Urlaub stehen ihr im Jahr {jahr} zu, und wie viele "
             f"Arbeitstage sind das bei ihrer {woche}-Tage-Woche? (zwei Nachkommastellen)")
    weg = schritte(f"Alter zu Beginn des Jahres {jahr} (1. Januar): {alter} Jahre", regel,
                   f"Werktage sind Montag bis Samstag; umrechnen: {werktage} : 6 · {woche} = **{de(tage)} Arbeitstage**")
    felder = [Feld("werktage", "Urlaub in Werktagen", werktage, stellen=0), Feld("tage", f"Urlaub bei {woche}-Tage-Woche", tage, "Tage")]
    return Aufgabe(frage, felder, weg, titel="Werktage umrechnen")


def _anteil(jahresurlaub: int, monate: int) -> float | None:
    tage = jahresurlaub * monate / 12
    rest = tage - math.floor(tage)
    return None if 0 < rest < 0.5 else aufrunden(tage)  # Reste unter einem halben Tag würden nicht gerundet: lieber vermeiden


OPTIONEN = ["Voller Jahresurlaub", "Anteilig, 1/12 je vollem Monat"]


def _eintritt_im_jahr(rng):
    while True:
        jahr, jahresurlaub = rng.randint(2026, 2028), rng.choice([20, 24, 25, 26, 28, 30])
        voll = rng.random() < 0.35
        eintritt = date(jahr, rng.randint(2, 6), 1) if voll else date(jahr, rng.randint(7, 11), rng.choice([1, 15]))
        if eintritt == date(jahr, 7, 1):
            eintritt = date(jahr, 7, 15)  # der 1. Juli ist der Grenzfall (Wartezeit endet am 31.12.), den sparen wir aus
        monate = volle_monate(eintritt, date(jahr, 12, 31))
        anspruch = jahresurlaub if voll else _anteil(jahresurlaub, monate)
        if anspruch is not None:
            break
    frage = (f"Ein neuer Mitarbeiter beginnt am **{kurz(eintritt)}** bei der {rng.choice(FIRMEN)}. Sein Vertrag sieht {jahresurlaub} "
             f"Arbeitstage Urlaub im Jahr vor.\n\nWie viel Urlaub steht ihm im Jahr {jahr} zu, und warum?")
    if voll:
        weg = schritte(f"Wartezeit (§ 4 BUrlG): 6 Monate ab {kurz(eintritt)}, erfüllt am "
                       f"{kurz(plus_monate(eintritt, 6) - timedelta(days=1))}, also noch im Jahr {jahr}",
                       f"Damit entsteht der **volle Jahresurlaub: {jahresurlaub} Tage**")
    else:
        weg = schritte(f"Wartezeit (§ 4 BUrlG): 6 Monate ab {kurz(eintritt)} sind erst im nächsten Jahr erfüllt",
                       f"§ 5 Abs. 1 a BUrlG: 1/12 je vollem Beschäftigungsmonat bis 31.12.: {monate} volle Monate",
                       f"{jahresurlaub} · {monate} : 12 = {de(jahresurlaub * monate / 12)}"
                       + (" → ab einem halben Tag aufrunden (§ 5 Abs. 2)" if anspruch != jahresurlaub * monate / 12 else "")
                       + f" → **{de(anspruch)} Tage**")
    felder = [Feld("anspruch", f"Urlaub {jahr}", anspruch, "Tage"),
              Feld("art", "Voll oder anteilig?", OPTIONEN[0 if voll else 1], typ="text", optionen=OPTIONEN)]
    return Aufgabe(frage, felder, weg, titel="Eintritt im Laufe des Jahres")


def _austritt(rng):
    while True:
        jahr, jahresurlaub = rng.randint(2026, 2028), rng.choice([20, 24, 25, 26, 28, 30])
        erste_haelfte = rng.random() < 0.65
        monat = rng.randint(2, 6) if erste_haelfte else rng.randint(7, 11)
        austritt = monatsende(date(jahr, monat, 1)) if rng.random() < 0.7 else date(jahr, monat, 15)
        monate = volle_monate(date(jahr, 1, 1), austritt)
        anspruch = _anteil(jahresurlaub, monate) if erste_haelfte else jahresurlaub
        if anspruch is not None:
            break
    frage = (f"Eine Mitarbeiterin ist seit mehreren Jahren bei der {rng.choice(FIRMEN)} und scheidet zum **{kurz(austritt)}** aus. "
             f"Ihr Vertrag sieht {jahresurlaub} Arbeitstage Urlaub im Jahr vor.\n\nWie viel Urlaub steht ihr im Jahr {jahr} zu?")
    if erste_haelfte:
        weg = schritte("Wartezeit längst erfüllt, aber Austritt in der ersten Jahreshälfte (bis 30.06.)",
                       f"§ 5 Abs. 1 c BUrlG: 1/12 je vollem Monat vom 01.01. bis {kurz(austritt)}: {monate} volle Monate",
                       f"{jahresurlaub} · {monate} : 12 = {de(jahresurlaub * monate / 12)}"
                       + (" → ab einem halben Tag aufrunden (§ 5 Abs. 2)" if anspruch != jahresurlaub * monate / 12 else "")
                       + f" → **{de(anspruch)} Tage**")
    else:
        weg = schritte("Wartezeit erfüllt und Austritt in der zweiten Jahreshälfte",
                       f"§ 5 Abs. 1 c BUrlG greift nicht: **voller Jahresurlaub, {jahresurlaub} Tage** (gesetzlich mindestens der "
                       "Mindesturlaub; vertraglicher Mehrurlaub kann anders geregelt sein, hier nicht)")
    felder = [Feld("anspruch", f"Urlaub {jahr}", anspruch, "Tage"),
              Feld("art", "Voll oder anteilig?", OPTIONEN[1 if erste_haelfte else 0], typ="text", optionen=OPTIONEN)]
    return Aufgabe(frage, felder, weg, titel="Austritt im Laufe des Jahres")
