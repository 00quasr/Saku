"""Recht & Verträge rund um den Kundenauftrag: Vertragsarten, Angebot und Annahme, Gewährleistung und Garantie, Mängelrechte,
Zahlungsverzug und Softwarelizenzen. Prüfungsstoff nach BGB (Rechtsstand 2026), keine Rechtsberatung; alle Szenarien erfunden.
Fristen nach §§ 187, 188 BGB wie in wiso: Beginn am Tag nach dem Ereignis, Ende am Tag mit derselben Zahl (fehlt er, am Monatsletzten).
Was sich ändert (der Basiszinssatz), steht als Annahme in der Aufgabe."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, de, euro, schritte
from saku.lernen.rechnen.wiso import kurz, lang, plus_monate

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "vertragsart": """- **Kaufvertrag** (§ 433 BGB): eine fertige Sache gegen Geld; der Verkäufer übergibt und übereignet sie frei von Sach- und Rechtsmängeln, der Käufer zahlt und nimmt sie ab
- **Werkvertrag** (§ 631): geschuldet ist ein **Erfolg**, das fertige Werk (Reparatur, Einrichtung, Website); der Besteller zahlt und nimmt das Werk ab (§ 640)
- **Dienstvertrag** (§ 611): geschuldet ist nur die **Tätigkeit**, kein Ergebnis (Schulung, Beratung, Mitarbeit nach Stunden); der Arbeitsvertrag ist ein Sonderfall (§ 611a)
- **Werklieferungsvertrag** (§ 650 Abs. 1): eine bewegliche Sache wird aus Material des Herstellers erst angefertigt und dann geliefert; es gilt Kaufrecht, bei Einzelanfertigungen ergänzt um einige Regeln des Werkvertrags
- **Mietvertrag** (§ 535): Gebrauch auf Zeit gegen Entgelt; der Vermieter hält die Sache gebrauchsfähig, der Mieter zahlt und gibt sie am Ende zurück (§ 546); ohne Entgelt wäre es Leihe (§ 598)
- **Leasingvertrag**: im BGB nicht eigens geregelt, im Kern Mietrecht; eine Leasinggesellschaft schafft die Sache an und überlässt sie für eine feste Grundmietzeit, die Leasingnehmerin trägt Wartung und Risiko, oft mit Kauf- oder Verlängerungsoption
- Prüffragen: Erfolg oder nur Tätigkeit geschuldet? Wird die Sache erst hergestellt, aus wessen Material? Für immer (Eigentum) oder auf Zeit (Gebrauch)?

*Beispiel:* Ein Notebook wird zum Festpreis repariert und muss danach wieder laufen → Werkvertrag; ein Trainer schult zwei Tage nach Tagessatz → Dienstvertrag""",
    "angebot": """- Ein Vertrag entsteht aus zwei übereinstimmenden Willenserklärungen: **Antrag** (Angebot) und **Annahme**; wirksam werden sie mit dem Zugang beim anderen (§ 130 BGB), nicht mit dem Absenden
- Ein Angebot bindet (§ 145), außer die Bindung ist ausgeschlossen („freibleibend“, „unverbindlich“); Kataloge, Prospekte und Webshops sind nur eine Aufforderung, selbst ein Angebot abzugeben: dann ist erst die Bestellung der Antrag, die Auftragsbestätigung oder die Lieferung die Annahme
- Annahmefrist: unter Anwesenden und am Telefon nur sofort (§ 147 Abs. 1), unter Abwesenden bis zu dem Zeitpunkt, zu dem man die Antwort unter regelmäßigen Umständen erwarten darf (§ 147 Abs. 2), mit gesetzter Frist bis zu deren Ende (§ 148); danach erlischt das Angebot (§ 146)
- Verspätete Annahme = neuer Antrag (§ 150 Abs. 1); Annahme mit Änderungen = Ablehnung und neuer Antrag (§ 150 Abs. 2); ein Vertrag entsteht erst, wenn der andere diesen neuen Antrag annimmt
- Schweigen ist grundsätzlich keine Annahme, auch wenn der Antrag das behauptet
- Bestellt die Kundin rechtzeitig und unverändert auf ein bindendes Angebot, ist der Vertrag damit geschlossen; eine Auftragsbestätigung bestätigt ihn nur noch

*Beispiel:* Angebot gültig bis 14.05., Bestellung geht am 16.05. zu → neuer Antrag; erst die Auftragsbestätigung des Lieferers schließt den Vertrag""",
    "gewaehrleistung": """- **Gewährleistung** (Mängelansprüche, §§ 434 ff. BGB): gesetzlich, gegen den Verkäufer, für Mängel, die schon bei der Übergabe (Gefahrübergang) vorlagen
- Frist (§ 438 Abs. 1 Nr. 3, Abs. 2): **2 Jahre ab Ablieferung**, nicht ab Kaufvertrag oder Rechnung; Ende am Tag mit derselben Zahl zwei Jahre später (§§ 187, 188), nicht erst zum Jahresende wie die regelmäßige Verjährung (§ 199)
- Abweichende Vereinbarungen: gegenüber Verbrauchern kein Ausschluss (§ 476 Abs. 1); neue Sachen nicht unter 2 Jahre, gebrauchte nicht unter 1 Jahr, und das nur mit eigenem Hinweis vor dem Kauf und ausdrücklicher, gesonderter Vereinbarung (§ 476 Abs. 2); zwischen Unternehmern lässt sich die Frist einzeln vereinbart verkürzen und bei gebrauchten Sachen die Gewährleistung ausschließen (Grenze: Arglist, § 444)
- **Beweislastumkehr** beim Verbrauchsgüterkauf (ein Unternehmer verkauft einem Verbraucher, § 474): zeigt sich ein Mangel **innerhalb eines Jahres** nach der Übergabe, wird vermutet, dass er schon da war; der Verkäufer müsste das Gegenteil beweisen (§ 477). Danach und zwischen Unternehmern beweist der Käufer
- **Garantie** (§ 443): freiwilliges Versprechen von Hersteller oder Händler; Dauer, Beginn und Umfang laut Garantieerklärung, zusätzlich zur Gewährleistung, die sie nicht verkürzt
- Zwischen Kaufleuten muss der Käufer die Ware unverzüglich prüfen und Mängel unverzüglich rügen (§ 377 HGB); in den Aufgaben wird ein Mangel immer sofort gemeldet
- Fällt das Ende einer Frist, in der etwas zu erklären oder zu leisten ist, auf einen Samstag, Sonntag oder Feiertag, endet sie am nächsten Werktag (§ 193); solche Tage meiden die Aufgaben

*Beispiel:* Kaufvertrag 18.01.2027, Ablieferung 25.01.2027 → Gewährleistung bis 25.01.2029; 3 Jahre Herstellergarantie ab Kaufdatum → bis 18.01.2030""",
    "maengel": """- Mangelarten: **Sachmangel** (§ 434: die Sache weicht von der vereinbarten oder üblichen Beschaffenheit ab, auch von Werbeaussagen des Herstellers), **Rechtsmangel** (§ 435: ein Dritter hat Rechte an der Sache, etwa ein Urheber- oder Patentrecht), **Falschlieferung** (eine andere Sache, steht dem Sachmangel gleich, § 434 Abs. 5), **Zuweniglieferung** (die Menge gehört zur vereinbarten Beschaffenheit, § 434 Abs. 2 Satz 2; der Rest ist nachzuliefern), **Montagemangel** (der Verkäufer montiert unsachgemäß oder seine Montageanleitung ist fehlerhaft, § 434 Abs. 4)
- Rechte des Käufers (§ 437): **zuerst Nacherfüllung** (§ 439); der Käufer wählt zwischen Nachbesserung (Reparatur) und Ersatzlieferung, der Verkäufer trägt die Kosten und darf nur eine unverhältnismäßig teure Art verweigern (§ 439 Abs. 4)
- Erst wenn die Nacherfüllung scheitert (angemessene Frist ergebnislos abgelaufen, zweiter Nachbesserungsversuch fehlgeschlagen nach § 440, ernsthaft verweigert): **Rücktritt** (§ 323) oder **Minderung** (§ 441), dazu Schadensersatz, wenn der Verkäufer den Mangel zu vertreten hat (§§ 280, 281)
- Bei einem unerheblichen Mangel ist der Rücktritt ausgeschlossen (§ 323 Abs. 5 Satz 2), die Minderung nicht (§ 441 Abs. 1 Satz 2); ein behebbarer Mangel ist in der Regel unerheblich, wenn ihn zu beseitigen höchstens 5 % des Kaufpreises kostet (Rechtsprechung des BGH)
- Minderung (§ 441 Abs. 3): **geminderter Preis = Kaufpreis · Wert mit Mangel : Wert ohne Mangel**; zu viel Gezahltes erstattet der Verkäufer (§ 441 Abs. 4)
- Nach Ablauf der Gewährleistungsfrist (2 Jahre ab Ablieferung) kann sich der Verkäufer auf Verjährung berufen; dann sind auch Rücktritt und Minderung unwirksam (§ 438 Abs. 4 und 5, § 218)
- Beim Werkvertrag wählt dagegen der Unternehmer, ob er nachbessert oder neu herstellt (§ 635 Abs. 1); dazu kommt die Selbstvornahme (§ 637)

*Beispiel:* Kaufpreis 1.200 €, Wert ohne Mangel 1.500 €, mit Mangel 1.000 € → 1.200 · 1.000 : 1.500 = 800 €, erstattet werden 400 € (nicht 1.200 − 500 = 700 €)""",
    "verzug": """- Verzug (§ 286 BGB): die fällige Zahlung bleibt trotz **Mahnung** aus (Abs. 1, Verzug mit dem Zugang der Mahnung); ohne Mahnung, wenn der Zahlungstermin **im Vertrag** nach dem Kalender bestimmt ist (Abs. 2 Nr. 1, Verzug ab dem Tag danach; ein Datum nur auf der Rechnung reicht dafür nicht)
- **30-Tage-Regel** (Abs. 3): spätestens 30 Tage nach Fälligkeit und Zugang der Rechnung; gegenüber Verbrauchern nur, wenn die Rechnung **besonders darauf hinweist**; eine Mahnung vorher wirkt früher
- Frist nach §§ 187, 188: Zugang am 1. März → die 30 Tage enden am 31. März → Verzug ab 1. April; fällt das Fristende auf einen Samstag, Sonntag oder Feiertag, endet sie am nächsten Werktag (§ 193)
- Verzugszinssatz (§ 288): **Basiszinssatz + 5 Prozentpunkte**, wenn ein Verbraucher beteiligt ist (Abs. 1); **+ 9 Prozentpunkte** zwischen Unternehmern (Abs. 2); der Basiszinssatz (§ 247) ändert sich zum 1. Januar und 1. Juli und steht in der Aufgabe
- Zwischen Unternehmern zusätzlich **40 € Pauschale** (§ 288 Abs. 5), nicht gegenüber Verbrauchern
- Zinsen = Betrag · Zinssatz · Tage : 365. Konvention hier: Zinstage vom ersten Verzugstag bis einschließlich zum Zahlungstag, taggenau, das Jahr mit 365 Tagen, am Ende auf Cent gerundet (Zinsrechner und Gerichte zählen teils anders); nach einer Mahnung laufen die Zinsen ab dem Tag nach ihrem Zugang
- *Typische Fehler:* 5 und 9 Prozentpunkte verwechselt, mit 360 statt 365 Tagen gerechnet, Verzug schon am Termin statt am Tag danach, die Pauschale auch gegenüber Verbrauchern

*Beispiel:* 2.000 € zwischen Unternehmern, Basiszinssatz 1,27 %, 30 Zinstage: 10,27 % → 2.000 · 0,1027 · 30 : 365 = 16,88 € und 40 € Pauschale""",
    "lizenz": """- **OEM-Lizenz**: zusammen mit neuer Hardware verkauft, günstig, laut Lizenzbedingungen an das Gerät gebunden
- **Einzelplatzlizenz**: eine Installation auf einem Arbeitsplatz; **Volumenlizenz**: viele Lizenzen auf einmal, Mengenrabatt, zentrale Verwaltung, oft ein gemeinsamer Schlüssel
- **Abonnement** (Subscription, SaaS): Gebühr je Monat oder Jahr und Benutzer, Updates inklusive, mit der Kündigung endet die Nutzung; SaaS läuft beim Anbieter (im Browser)
- **Freeware**: kostenlos nutzbar (manchmal nur privat), Quellcode geschlossen, Verändern und Weiterverkaufen verboten; **Open Source**: Quellcode offen, Nutzen, Ändern und Weitergeben erlaubt, nach den Bedingungen der Lizenz
- **Copyleft (GNU GPL)**: wer veränderten Code weitergibt, muss ihn wieder unter der GPL und mit Quellcode weitergeben; interne Nutzung ohne Weitergabe löst das nicht aus; Geld für die Weitergabe zu verlangen ist erlaubt. Die AGPL verlangt den Quellcode auch, wenn andere ein verändertes Programm nur über ein Netzwerk nutzen
- **Permissiv (MIT, BSD)**: Einbau in eigene Produkte mit geschlossenem Quellcode erlaubt; Pflicht ist, den Urheber- und Lizenzhinweis beizulegen; die 3-Klausel-BSD verbietet, ohne Erlaubnis mit den Namen der Urheber zu werben
- Gebrauchte Software: eine dauerhaft gegen Einmalzahlung gekaufte Lizenz darf weiterverkauft werden, wenn die eigene Kopie unbrauchbar gemacht wird (Erschöpfung, § 69c Nr. 3 UrhG, EuGH „UsedSoft“ 2012)
- Kostenvergleich: Kauf = Lizenzpreis · Benutzer + Wartung je Jahr · Jahre; Abo = Preis je Benutzer und Monat · Benutzer · 12 · Jahre

*Beispiel:* 10 Benutzer, Kauf 400 € je Lizenz und 20 % Wartung im Jahr, 3 Jahre: 4.000 + 3 · 800 = 6.400 €; Abo 15 € im Monat: 10 · 15 · 36 = 5.400 € → das Abo ist günstiger""",
}

JA_NEIN = ["Ja", "Nein"]

# (Monat, Tag) gesetzlicher Feiertage mit festem Datum, auch der nur in einzelnen Ländern
FEIERTAGE = {(1, 1), (1, 6), (3, 8), (5, 1), (8, 8), (8, 15), (9, 20), (10, 3), (10, 31), (11, 1), (12, 25), (12, 26)}


def werktag(d: date) -> bool:
    """Kein Samstag, Sonntag oder Feiertag, in keinem Bundesland: dann verschiebt § 193 BGB kein Fristende.
    shortcut: statt Ostern zu berechnen, fällt die ganze Spanne der beweglichen Feiertage weg (Karfreitag frühestens am 20.03.,
    Fronleichnam spätestens am 24.06.) und der Buß- und Bettag (16. bis 22.11.); genauer erst, wenn Fristen in diesen Wochen enden sollen."""
    return (d.weekday() < 5 and (d.month, d.day) not in FEIERTAGE and not (3, 20) <= (d.month, d.day) <= (6, 24)
            and not (d.month == 11 and 16 <= d.day <= 22))


def _wochentag(d: date) -> date:
    """Der Tag selbst oder der Montag danach: Erklärungen gehen in den Aufgaben an Wochentagen zu (bei Firmen zählt sonst erst der
    nächste Geschäftstag als Zugang)."""
    return d + timedelta(days=7 - d.weekday() if d.weekday() >= 5 else 0)


def _tag(rng) -> date:
    return _wochentag(date(rng.randint(2026, 2028), 1, 1) + timedelta(days=rng.randrange(365)))


def _jahre(n: int) -> str:
    return "1 Jahr" if n == 1 else f"{n} Jahre"


# --- Vertragsarten ------------------------------------------------------------------------

VERTRAEGE = {  # Vertragsart: Fundstelle, woran man sie erkennt
    "Kaufvertrag": ("§ 433 BGB", "eine fertige Sache wird gegen Geld übergeben und übereignet"),
    "Werkvertrag": ("§ 631 BGB", "geschuldet ist ein Erfolg, das fertige und funktionierende Ergebnis, das abgenommen wird (§ 640)"),
    "Dienstvertrag": ("§ 611 BGB", "geschuldet ist nur die Tätigkeit, kein bestimmtes Ergebnis; bezahlt wird die Zeit"),
    "Werklieferungsvertrag": ("§ 650 Abs. 1 BGB", "eine bewegliche Sache wird aus Material des Herstellers erst angefertigt und dann geliefert; "
                                           "es gilt Kaufrecht"),
    "Mietvertrag": ("§ 535 BGB", "eine Sache wird auf Zeit gegen Entgelt zum Gebrauch überlassen; sie bleibt Eigentum des Vermieters, "
                                 "der sie in Ordnung hält"),
    "Leasingvertrag": ("im BGB nicht eigens geregelt, im Kern Mietrecht", "eine Leasing- oder Finanzierungsgesellschaft schafft die "
                       "Sache an und überlässt sie für eine feste Grundmietzeit; Wartung und Risiko trägt die Leasingnehmerin"),
}
# nur eindeutige Fälle; die Tests suchen die Merkmale (Festpreis, nach Stunden, aus eigenem Material …) in den Texten
SITUATIONEN = {
    "Kaufvertrag": [
        "Sie bestellt bei einem Händler 25 Monitore eines Standardmodells aus dem Katalog; sie werden geliefert und bezahlt.",
        "Sie kauft im Elektronikmarkt zehn Netzwerkkabel und einen Switch, bezahlt an der Kasse und nimmt alles mit.",
        "Sie erwirbt von einem Händler drei gebrauchte Server, die er auf Lager hat.",
        "Sie bestellt im Webshop eines Herstellers 40 Tastaturen aus dem Standardsortiment.",
    ],
    "Werkvertrag": [
        "Ein Systemhaus repariert eines ihrer Notebooks zum Festpreis: neues Display, danach muss das Gerät wieder einwandfrei laufen.",
        "Ein Dienstleister richtet in ihren Räumen mit ihren vorhandenen Geräten ein WLAN ein, zum Festpreis und mit Abnahme nach "
        "einem Funktionstest.",
        "Eine Agentur erstellt für sie eine Website nach Pflichtenheft; bezahlt wird nach der Abnahme der fertigen Seite.",
        "Ein Dienstleister überträgt alle ihre Postfächer auf einen neuen Mailserver; bezahlt wird, wenn die Übernahme vollständig "
        "und fehlerfrei abgeschlossen ist.",
    ],
    "Dienstvertrag": [
        "Ein IT-Trainer führt für ihre Beschäftigten eine zweitägige Schulung zur Tabellenkalkulation durch, bezahlt nach Tagessatz.",
        "Ein externer Berater unterstützt sie bei der Auswahl einer neuen Software, abgerechnet nach Stunden; ein bestimmtes Ergebnis "
        "schuldet er nicht.",
        "Ein freiberuflicher Entwickler arbeitet drei Monate in ihrem Team mit, abgerechnet nach Stunden, ohne dass ein bestimmtes "
        "Ergebnis vereinbart ist.",
        "Ein Dienstleister besetzt für sie die Hotline für Anwenderfragen, 20 Stunden im Monat zum Stundensatz.",
    ],
    "Werklieferungsvertrag": [
        "Ein Systemhaus baut aus eigenen Komponenten einen PC nach ihren Vorgaben zusammen und liefert ihn.",
        "Ein Hersteller fertigt für sie aus eigenem Material 500 Platinen nach ihrem Schaltplan und liefert sie.",
        "Ein Metallbauer fertigt aus eigenem Material einen Serverschrank in Sondermaßen für ihren Serverraum und liefert ihn.",
        "Ein Lieferant konfektioniert aus eigenem Kabel 60 Patchkabel in einer Sonderlänge für sie und liefert sie.",
    ],
    "Mietvertrag": [
        "Sie nimmt für eine Messe gegen eine Tagesgebühr drei Beamer bei einem Verleih; nach vier Tagen gehen sie zurück.",
        "Sie nutzt für eine Schulungswoche gegen Entgelt zwölf Notebooks eines Verleihers und gibt sie danach zurück; um defekte "
        "Geräte kümmert sich der Verleiher.",
        "Sie nutzt gegen eine monatliche Gebühr einen Multifunktionsdrucker; der Anbieter bleibt Eigentümer, repariert ihn und der "
        "Vertrag ist monatlich kündbar.",
    ],
    "Leasingvertrag": [
        "Eine Finanzierungsgesellschaft kauft 50 Notebooks beim Hersteller und überlässt sie ihr für eine feste Grundmietzeit von "
        "36 Monaten; Wartung und Risiko des Untergangs trägt die Nutzerin, am Ende darf sie die Geräte kaufen.",
        "Sie nutzt eine Telefonanlage, die eine Finanzierungsgesellschaft eigens für sie angeschafft hat: 48 Monate fest, nicht "
        "vorzeitig kündbar, Instandhaltung und Versicherung zahlt die Nutzerin.",
    ],
}
# Vertrag: (wie die Anbieterin leistet, Rolle der Anbieterin, Rolle der Kundin, [(Pflicht, 0 = Anbieterin, 1 = Kundin, Fundstelle)])
PFLICHTEN = {
    "Kaufvertrag": ("verkauft der {k} 20 Notebooks", "Verkäufer", "Käufer", [
        ("Die Notebooks übergeben", 0, "§ 433 Abs. 1 Satz 1 BGB"),
        ("Das Eigentum an den Notebooks verschaffen", 0, "§ 433 Abs. 1 Satz 1 BGB"),
        ("Die Notebooks frei von Sach- und Rechtsmängeln liefern", 0, "§ 433 Abs. 1 Satz 2 BGB"),
        ("Den vereinbarten Kaufpreis zahlen", 1, "§ 433 Abs. 2 BGB"),
        ("Die gelieferten Notebooks abnehmen", 1, "§ 433 Abs. 2 BGB")]),
    "Werkvertrag": ("richtet für die {k} zum Festpreis ein Netzwerk ein", "Unternehmer", "Besteller", [
        ("Das Netzwerk wie vereinbart einrichten", 0, "§ 631 Abs. 1 BGB"),
        ("Das Werk frei von Sach- und Rechtsmängeln verschaffen", 0, "§ 633 Abs. 1 BGB"),
        ("Die vereinbarte Vergütung zahlen", 1, "§ 631 Abs. 1 BGB"),
        ("Das vertragsgemäß eingerichtete Netzwerk abnehmen", 1, "§ 640 Abs. 1 BGB")]),
    "Mietvertrag": ("vermietet der {k} für drei Monate fünf Beamer", "Vermieter", "Mieter", [
        ("Den Gebrauch der Beamer während der Mietzeit gewähren", 0, "§ 535 Abs. 1 Satz 1 BGB"),
        ("Die Beamer gebrauchsfähig überlassen und während der Mietzeit so erhalten", 0, "§ 535 Abs. 1 Satz 2 BGB"),
        ("Die vereinbarte Miete zahlen", 1, "§ 535 Abs. 2 BGB"),
        ("Die Beamer nach dem Ende der Mietzeit zurückgeben", 1, "§ 546 Abs. 1 BGB")]),
}


@art("vertragsart", "Vertragsarten", "Recht & Verträge",
     "Kauf, Werk, Dienst, Werklieferung, Miete oder Leasing? Und wer schuldet was im Vertrag?",
     ("Vertragsart", "Werkvertrag", "Dienstvertrag", "Werklieferung", "Mietvertrag"), formeln=FORMELN["vertragsart"])
def vertragsart(rng):
    return rng.choice([_welcher_vertrag, _welcher_vertrag, _pflichten])(rng)


def _welcher_vertrag(rng):
    firma = rng.choice(FIRMEN)
    faelle = [(a, rng.choice(SITUATIONEN[a])) for a in rng.sample(list(SITUATIONEN), 3)]
    frage = (f"Die {firma} schließt in einem Monat mehrere Verträge:\n\n"
             + "\n".join(f"{i}. {text}" for i, (_, text) in enumerate(faelle, start=1))
             + "\n\nWelche Vertragsart liegt jeweils vor?")
    felder = [Feld(f"v{i}", f"Vertrag {i}", a, typ="text", optionen=list(VERTRAEGE)) for i, (a, _) in enumerate(faelle, start=1)]
    weg = schritte(*(f"Vertrag {i}: **{a}** ({VERTRAEGE[a][0]}), {VERTRAEGE[a][1]}" for i, (a, _) in enumerate(faelle, start=1)))
    return Aufgabe(frage, felder, weg, titel="Welcher Vertrag?")


def _pflichten(rng):
    vertrag = rng.choice(list(PFLICHTEN))
    leistung, rolle_a, rolle_k, pflichten = PFLICHTEN[vertrag]
    anbieterin, kundin = rng.sample(FIRMEN, 2)
    pflichten = rng.sample(pflichten, 4)
    optionen = [f"{anbieterin} ({rolle_a})", f"{kundin} ({rolle_k})"]
    frage = (f"Die {anbieterin} {leistung.format(k=kundin)} ({vertrag}).\n\n"
             "Wer schuldet nach dem Gesetz jeweils die folgende Leistung?")
    felder = [Feld(f"p{i}", text, optionen[wer], typ="text", optionen=optionen) for i, (text, wer, _) in enumerate(pflichten, start=1)]
    weg = schritte(*(f"{text}: **{optionen[wer]}** ({fundstelle})" for text, wer, fundstelle in pflichten),
                   f"Leistung und Gegenleistung: der {rolle_a} erbringt die Leistung, die den {vertrag} ausmacht, der {rolle_k} zahlt "
                   f"dafür und {'gibt die Sache am Ende zurück' if vertrag == 'Mietvertrag' else 'nimmt ab'}")
    return Aufgabe(frage, felder, weg, titel="Wer schuldet was?")


# --- Angebot und Annahme ------------------------------------------------------------------

ANTRAG = ["Angebot des Lieferers", "Bestellung der Kundin", "Auftragsbestätigung des Lieferers"]
ANNAHME = ["Bestellung der Kundin", "Auftragsbestätigung des Lieferers", "Lieferung der Ware", "Keine Annahme"]
WAREN_ANGEBOT = [("30 Notebooks", 890), ("12 Monitore", 240), ("8 Switches", 520), ("3 Server", 5600), ("25 Dockingstationen", 160),
                 ("40 Headsets", 75)]
# Fall: Titel
FAELLE_ANGEBOT = {"rechtzeitig": "Rechtzeitige Annahme", "freibleibend": "Freibleibendes Angebot", "webshop": "Bestellung im Webshop",
                  "verspaetet": "Verspätete Annahme", "geaendert": "Geänderte Annahme", "telefon": "Angebot am Telefon",
                  "schweigen": "Schweigen auf ein Angebot"}


@art("angebot", "Angebot und Annahme", "Recht & Verträge",
     "Antrag, Annahme, Annahmefrist und § 150 BGB: Ist ein Vertrag zustande gekommen?",
     ("Angebot und Annahme", "Antrag und Annahme", "Vertragsschluss", "Vertragsabschluss", "Willenserklärung", "Annahmefrist",
      "Auftragsbestätigung"), formeln=FORMELN["angebot"])
def angebot(rng):
    lieferer, kundin = rng.sample(FIRMEN, 2)
    ware, preis = rng.choice(WAREN_ANGEBOT)
    while True:
        tag = _tag(rng)
        bis = tag + timedelta(days=rng.choice([7, 10, 14, 21]))
        if tag.weekday() < 5 and werktag(bis):
            break
    fall = rng.choice(list(FAELLE_ANGEBOT))
    angebot_ = f"Am {lang(tag)} schickt die {lieferer} der {kundin} per E-Mail ein Angebot über {ware} zu je {euro(preis)} netto"
    nach = rng.choice([t for i in range(1, (bis - tag).days) if (t := tag + timedelta(days=i)).weekday() < 5])  # vor dem Fristende
    ja = rng.random() < 0.5  # nimmt der Lieferer einen neuen Antrag der Kundin an?

    def antwort(am: date) -> tuple[str, str]:
        """Antwort des Lieferers auf einen neuen Antrag der Kundin, und was daraus folgt."""
        if ja:
            return (f"Die {lieferer} ist einverstanden und schickt am {kurz(am)} eine Auftragsbestätigung.",
                    "Die Auftragsbestätigung nimmt den neuen Antrag an → **Vertrag: Ja**")
        return (f"Die {lieferer} antwortet am {kurz(am)}, zu diesen Bedingungen liefere sie nicht.",
                f"Die {lieferer} lehnt den neuen Antrag ab → **keine Annahme**, **kein Vertrag**")
    neu = (1, 1 if ja else 3, ja)  # die Kundin stellt den Antrag; Annahme durch Auftragsbestätigung oder keine
    if fall == "rechtzeitig":
        text = (f"{angebot_}, gültig bis {kurz(bis)}. Am {lang(nach)} geht bei der {lieferer} die Bestellung der {kundin} ein, genau zu "
                f"den Bedingungen des Angebots. Am {kurz(_wochentag(nach + timedelta(days=1)))} schickt die {lieferer} eine Auftragsbestätigung.")
        loesung = (0, 0, True)
        weg = [f"Das Angebot bindet (§ 145 BGB) und ist bis {kurz(bis)} annehmbar (§ 148) → es ist der **Antrag**",
               f"Die Bestellung geht am {kurz(nach)} zu, rechtzeitig und ohne Änderungen → sie ist die **Annahme**",
               "Der Vertrag ist mit ihrem Zugang geschlossen → **Ja**; die Auftragsbestätigung bestätigt ihn nur noch"]
    elif fall == "freibleibend":
        lieferung = rng.random() < 0.5
        text = (f"{angebot_}, mit dem Vermerk „{rng.choice(['freibleibend', 'unverbindlich'])}“. Am {lang(nach)} bestellt die {kundin} "
                "zu diesen Bedingungen. "
                + (f"Ohne weitere Erklärung liefert die {lieferer} die Ware am {kurz(_wochentag(nach + timedelta(days=3)))}." if lieferung else
                   f"Am {kurz(_wochentag(nach + timedelta(days=1)))} schickt die {lieferer} eine Auftragsbestätigung ohne Änderungen."))
        loesung = (1, 2 if lieferung else 1, True)
        weg = ["Der Vermerk schließt die Bindung aus (§ 145 BGB): das Schreiben ist nur eine Aufforderung, selbst ein Angebot abzugeben",
               f"Erst die Bestellung vom {kurz(nach)} ist der **Antrag**",
               ("Die Lieferung nimmt ihn durch schlüssiges Handeln an" if lieferung else "Die Auftragsbestätigung nimmt ihn an")
               + " → **Vertrag: Ja**"]
    elif fall == "webshop":
        text = (f"Die {kundin} bestellt am {lang(tag)} im Webshop der {lieferer} {ware} zu je {euro(preis)} netto. Sofort kommt eine "
                "automatische E-Mail: „Vielen Dank, Ihre Bestellung ist bei uns eingegangen. Diese E-Mail ist noch keine Annahme Ihres "
                f"Angebots.“ Weitere Nachrichten der {lieferer} gibt es bisher nicht.")
        loesung = (1, 3, False)
        weg = ["Die Artikel im Webshop sind nur eine Aufforderung, ein Angebot abzugeben; die Bestellung ist der **Antrag**",
               "Die automatische Eingangsbestätigung (im Online-Handel Pflicht, § 312i Abs. 1 Satz 1 Nr. 3 BGB) sagt ausdrücklich, dass "
               "sie nicht annimmt → **keine Annahme**",
               "**Noch kein Vertrag**; er entsteht erst mit einer Auftragsbestätigung oder dem Versand der Ware"]
    elif fall == "verspaetet":
        spaet = _wochentag(bis + timedelta(days=rng.randint(2, 12)))
        satz, schluss = antwort(_wochentag(spaet + timedelta(days=2)))
        text = (f"{angebot_}, gültig bis {kurz(bis)}. Die {kundin} bestellt zu den Bedingungen des Angebots, die Bestellung geht aber erst "
                f"am {lang(spaet)} per E-Mail ein. {satz}")
        loesung = neu
        weg = [f"Das Angebot war nur bis {kurz(bis)} annehmbar (§ 148 BGB); danach ist es erloschen (§ 146)",
               f"Die Bestellung vom {kurz(spaet)} ist verspätet und gilt als **neuer Antrag** (§ 150 Abs. 1)", schluss]
    elif fall == "geaendert":
        aenderung = rng.choice(["verlangt aber 5 % Rabatt", "verlangt aber 3 % Skonto",
                                f"will aber nur {euro(round(preis * 0.9))} je Stück zahlen"])
        satz, schluss = antwort(_wochentag(nach + timedelta(days=2)))
        text = f"{angebot_}, gültig bis {kurz(bis)}. Am {lang(nach)} geht die Bestellung der {kundin} ein; sie {aenderung}. {satz}"
        loesung = neu
        weg = [f"Die Bestellung kommt rechtzeitig, ändert aber das Angebot (sie {aenderung})",
               "Eine Annahme unter Änderungen gilt als Ablehnung, verbunden mit einem **neuen Antrag** (§ 150 Abs. 2 BGB)", schluss]
    elif fall == "telefon":
        zurueck = _wochentag(tag + timedelta(days=1))
        satz, schluss = antwort(zurueck)
        text = (f"Am {lang(tag)} bietet ein Vertriebsmitarbeiter der {lieferer} der Einkäuferin der {kundin} am Telefon {ware} zu je "
                f"{euro(preis)} netto an. Sie will es sich überlegen, ruft am {lang(zurueck)} zurück und bestellt zu genau diesen "
                f"Bedingungen. {satz}")
        loesung = neu
        weg = ["Ein Angebot am Telefon gilt als Angebot unter Anwesenden: es kann nur **sofort** angenommen werden (§ 147 Abs. 1 BGB); "
               "mit dem Ende des Gesprächs ist es erloschen (§ 146)",
               f"Die Bestellung vom {kurz(zurueck)} ist eine verspätete Annahme, also ein **neuer Antrag** (§ 150 Abs. 1)", schluss]
    else:
        text = (f"Am {lang(tag)} schickt die {lieferer} der {kundin} unaufgefordert ein Angebot über {ware} zu je {euro(preis)} netto, "
                f"mit dem Satz: „Hören wir bis zum {kurz(bis)} nichts von Ihnen, gilt der Auftrag als erteilt.“ Die {kundin} reagiert "
                "nicht.")
        loesung = (0, 3, False)
        weg = ["Das Schreiben ist der **Antrag**",
               "Schweigen ist grundsätzlich keine Annahme, und der Antragende kann das nicht einseitig festlegen → **keine Annahme**",
               "**Kein Vertrag**"]
    antrag, annahme, vertrag = loesung
    frage = (f"Lieferer ist die {lieferer}, Kundin die {kundin}.\n\n{text}\n\nWelche Erklärung ist der Antrag im Sinne des BGB, welche "
             "die Annahme, und ist ein Vertrag zustande gekommen?")
    felder = [Feld("antrag", "Antrag", ANTRAG[antrag], typ="text", optionen=ANTRAG),
              Feld("annahme", "Annahme", ANNAHME[annahme], typ="text", optionen=ANNAHME),
              Feld("vertrag", "Ist ein Vertrag zustande gekommen?", JA_NEIN[0 if vertrag else 1], typ="text", optionen=JA_NEIN)]
    return Aufgabe(frage, felder, schritte(*weg), titel=FAELLE_ANGEBOT[fall])


# --- Gewährleistung und Garantie ----------------------------------------------------------

WAREN_G = [("Notebook", "n"), ("Monitor", "m"), ("Multifunktionsdrucker", "m"), ("Tablet", "n"), ("Beamer", "m"), ("NAS-System", "n")]
FEHLER_G = ["fällt das Netzteil aus", "fällt die Hauptplatine aus", "bekommt das Display einen Streifen", "versagt der Lüfter",
            "lässt sich das Gerät nicht mehr einschalten"]
ANSPRUECHE = ["Gewährleistung und Garantie", "Nur Gewährleistung", "Nur Garantie", "Kein Anspruch"]
BEWEIS = ["Der Verkäufer: er muss beweisen, dass der Mangel noch nicht vorlag", "Der Käufer: er muss beweisen, dass der Mangel schon vorlag"]
FRISTEN_G = ["2 Jahre ab Ablieferung", "1 Jahr ab Ablieferung", "Keine Gewährleistung"]
# gebraucht, an einen Verbraucher, was vereinbart ist ({f}: der Verkäufer ohne Artikel), wirksam?, Monate Gewährleistung, warum
VEREINBARUNGEN = [
    (False, True, "In den AGB der {f} steht: „Die Gewährleistung beträgt ein Jahr.“", False, 24,
     "Gegenüber Verbrauchern lässt sich die Frist bei neuen Sachen nicht unter 2 Jahre verkürzen (§ 476 Abs. 2 BGB)"),
    (False, True, "In den AGB der {f} steht: „Jede Gewährleistung ist ausgeschlossen.“", False, 24,
     "Auf einen Ausschluss kann sich der Unternehmer gegenüber Verbrauchern nicht berufen (§ 476 Abs. 1 BGB)"),
    (True, True, "Vor dem Kauf hat die {f} die Kundin eigens auf eine kürzere Frist hingewiesen, und im Kaufvertrag ist ausdrücklich und "
     "gesondert vereinbart: Mängelansprüche verjähren nach einem Jahr.", True, 12,
     "Bei gebrauchten Sachen darf die Frist auf 1 Jahr sinken, wenn der Verbraucher vor dem Kauf eigens darauf hingewiesen wurde und "
     "die Verkürzung ausdrücklich und gesondert vereinbart ist (§ 476 Abs. 2 BGB)"),
    (True, True, "Klein gedruckt in den AGB der {f} steht: „Bei Gebrauchtgeräten beträgt die Gewährleistung ein Jahr.“ Eigens darauf "
     "hingewiesen oder gesondert vereinbart wurde das nicht.", False, 24,
     "Die Verkürzung bei gebrauchten Sachen wirkt gegenüber Verbrauchern nur mit eigenem Hinweis und ausdrücklicher, gesonderter "
     "Vereinbarung (§ 476 Abs. 2 Satz 2 BGB); eine AGB-Klausel allein reicht nicht"),
    (True, True, "Im Kaufvertrag steht: „Gekauft wie gesehen, unter Ausschluss jeder Gewährleistung.“", False, 24,
     "Auch bei gebrauchten Sachen kein Ausschluss gegenüber Verbrauchern (§ 476 Abs. 1 BGB), höchstens die Verkürzung auf 1 Jahr "
     "unter den Voraussetzungen des § 476 Abs. 2"),
    (True, False, "Im Kaufvertrag ist einzeln ausgehandelt: „Gekauft wie besichtigt, unter Ausschluss jeder Gewährleistung.“ Mängel "
     "kennt die {f} nicht.", True, 0,
     "Zwischen Unternehmern gilt § 476 nicht: bei gebrauchten Sachen darf die Gewährleistung ausgeschlossen werden; Grenze sind "
     "arglistig verschwiegene Mängel und eine Garantie (§ 444 BGB)"),
    (True, False, "Im Kaufvertrag ist einzeln ausgehandelt: Mängelansprüche verjähren ein Jahr nach der Ablieferung.", True, 12,
     "Zwischen Unternehmern gilt § 476 nicht; die einzeln ausgehandelte Verkürzung ist wirksam"),
    (False, False, "Im Kaufvertrag ist einzeln ausgehandelt: Mängelansprüche verjähren ein Jahr nach der Ablieferung.", True, 12,
     "Zwischen Unternehmern gilt § 476 nicht; die einzeln ausgehandelte Verkürzung ist auch bei neuen Sachen wirksam"),
]


def ware(name: str, genus: str, zustand: str = "") -> str:
    """Akkusativ mit Artikel: „ein neues Notebook“, „einen gebrauchten Monitor“, „ein Tablet“."""
    endung = "es" if genus == "n" else "en"
    return f"{'ein' if genus == 'n' else 'einen'} {zustand + endung + ' ' if zustand else ''}{name}"


@art("gewaehrleistung", "Gewährleistung und Garantie", "Recht & Verträge",
     "Fristende ab Ablieferung (§ 438 BGB), Garantie, Beweislastumkehr (§ 477) und abweichende Vereinbarungen (§ 476)",
     ("Gewährleistung", "Garantie", "Beweislast", "Mängelhaftung"), formeln=FORMELN["gewaehrleistung"])
def gewaehrleistung(rng):
    return rng.choice([_garantie, _garantie, _beweislast, _vereinbarung])(rng)


def _garantie(rng):
    ziel = rng.choice(ANSPRUECHE)
    while True:
        kauf = _tag(rng)
        ablieferung = _wochentag(kauf + timedelta(days=rng.randint(3, 21)))
        jahre = {"Nur Gewährleistung": 1, "Nur Garantie": rng.choice([3, 5])}.get(ziel, rng.choice([1, 3, 5]))
        ende, garantie = plus_monate(ablieferung, 24), plus_monate(kauf, 12 * jahre)
        fehler = ablieferung + timedelta(days=rng.randint(40, 365 * jahre + 400))
        drin = (fehler <= ende, fehler <= garantie)
        # beide Enden klar entfernt, damit die Frage nicht an einem Tag hängt
        if werktag(ende) and werktag(garantie) and min(abs((fehler - ende).days), abs((fehler - garantie).days)) >= 20 \
                and ANSPRUECHE[{(True, True): 0, (True, False): 1, (False, True): 2, (False, False): 3}[drin]] == ziel:
            break
    firma, (name, genus) = rng.choice(FIRMEN), rng.choice(WAREN_G)
    frage = (f"Die {firma} kauft am **{lang(kauf)}** bei einem Fachhändler {ware(name, genus, 'neu')} für ihr Büro; Kaufvertrag und "
             f"Rechnung tragen dieses Datum. Geliefert wird am **{lang(ablieferung)}**. Der Hersteller gibt **{_jahre(jahre)} Garantie "
             f"ab Kaufdatum** auf Material- und Verarbeitungsfehler.\n\nAm **{lang(fehler)}** {rng.choice(FEHLER_G)}; es ist ein "
             f"Produktionsfehler, den das Gerät schon bei der Lieferung hatte. Die {firma} meldet ihn sofort.\n\nBis wann läuft die "
             "gesetzliche Gewährleistung, bis wann die Garantie, und worauf kann sich die Firma jetzt stützen? (Datum als TT.MM.JJJJ)")
    felder = [Feld("ende", "Ende der Gewährleistung", kurz(ende), typ="datum"),
              Feld("garantie", "Ende der Garantie", kurz(garantie), typ="datum"),
              Feld("anspruch", "Worauf kann sie sich stützen?", ziel, typ="text", optionen=ANSPRUECHE)]
    weg = schritte(f"Gewährleistung bei neuen Sachen: 2 Jahre ab der **Ablieferung** (§ 438 Abs. 1 Nr. 3, Abs. 2 BGB), nicht ab dem "
                   f"Kaufvertrag: {kurz(ablieferung)} + 2 Jahre = **{kurz(ende)}** (§§ 187, 188)",
                   f"Garantie: freiwillig (§ 443 BGB), Beginn und Dauer laut Garantieerklärung: {kurz(kauf)} + {_jahre(jahre)} = "
                   f"**{kurz(garantie)}**",
                   f"Fehler am {kurz(fehler)}: die Gewährleistung {'läuft noch' if drin[0] else 'ist abgelaufen'}, die Garantie "
                   f"{'läuft noch' if drin[1] else 'ist abgelaufen'} → **{ziel}**"
                   + ("; die Gewährleistung richtet sich gegen den Händler, die Garantie gegen den Hersteller" if ziel == ANSPRUECHE[0]
                      else ""))
    return Aufgabe(frage, felder, weg, titel="Gewährleistung oder Garantie?")


def _beweislast(rng):
    verbraucher, erstes_jahr = rng.random() < 0.6, rng.random() < 0.5
    while True:
        ablieferung = _tag(rng)
        vermutung, ende = plus_monate(ablieferung, 12), plus_monate(ablieferung, 24)
        if werktag(ende):
            break
    fehler = ablieferung + timedelta(days=rng.randint(30, 340) if erstes_jahr else rng.randint(390, 700))
    firma, (name, genus) = rng.choice(FIRMEN), rng.choice(WAREN_G)
    andere = rng.choice([f for f in FIRMEN if f != firma])
    an, kaeufer = ("einer Privatkundin", "die Kundin") if verbraucher else (f"der {andere} für deren Büro", f"die {andere}")
    frage = (f"Die {firma} verkauft {an} {ware(name, genus, 'neu')}; die Übergabe ist am **{lang(ablieferung)}**. Am "
             f"**{lang(fehler)}** {rng.choice(FEHLER_G)}, und {kaeufer} meldet den Mangel sofort. Die {firma} meint, das Gerät sei bei "
             "der Übergabe in Ordnung gewesen.\n\nLiegt ein Verbrauchsgüterkauf vor? Wer muss beweisen, ob der Mangel schon bei der "
             "Übergabe vorlag, und bis wann läuft die Gewährleistung? (Datum als TT.MM.JJJJ)")
    verkaeufer_beweist = verbraucher and fehler <= vermutung
    felder = [Feld("vgk", "Verbrauchsgüterkauf?", JA_NEIN[0 if verbraucher else 1], typ="text", optionen=JA_NEIN),
              Feld("beweis", "Wer muss beweisen?", BEWEIS[0 if verkaeufer_beweist else 1], typ="text", optionen=BEWEIS),
              Feld("ende", "Ende der Gewährleistung", kurz(ende), typ="datum")]
    if verbraucher:
        schritt = (f"Ein Unternehmer verkauft einer Verbraucherin: **Verbrauchsgüterkauf** (§ 474 BGB). Zeigt sich ein Mangel innerhalb "
                   f"eines Jahres nach der Übergabe, also bis {kurz(vermutung)}, wird vermutet, dass er schon da war (§ 477)")
        beweis = (f"Der Mangel zeigt sich am {kurz(fehler)}, " + ("innerhalb des Jahres → die **Vermutung greift**: der Verkäufer müsste "
                  "beweisen, dass das Gerät bei der Übergabe in Ordnung war" if verkaeufer_beweist else "nach dem ersten Jahr → keine "
                  "Vermutung mehr: **die Käuferin** muss beweisen, dass der Mangel schon bei der Übergabe vorlag"))
    else:
        schritt = "Beide sind Unternehmer: **kein Verbrauchsgüterkauf**, die Vermutung des § 477 BGB gilt nicht"
        beweis = ("Also beweist die **Käuferin**, dass der Mangel schon bei der Lieferung vorlag, gleich wann er sich zeigt; zwischen "
                  "Kaufleuten muss sie ihn außerdem unverzüglich rügen (§ 377 HGB)")
    weg = schritte(schritt, beweis, f"Gewährleistung: 2 Jahre ab Ablieferung (§ 438 Abs. 1 Nr. 3, Abs. 2): **{kurz(ende)}**, für "
                                    "Verbraucher wie für Unternehmer")
    return Aufgabe(frage, felder, weg, titel="Beweislast")


def _vereinbarung(rng):
    gebraucht, verbraucher, text, wirksam, monate, warum = rng.choice(VEREINBARUNGEN)
    firma, (name, genus) = rng.choice(FIRMEN), rng.choice(WAREN_G)
    an = "einer Privatkundin" if verbraucher else f"der {rng.choice([f for f in FIRMEN if f != firma])} für den eigenen Betrieb"
    frage = (f"Die {firma} verkauft {an} {ware(name, genus, 'gebraucht' if gebraucht else 'neu')}. "
             f"{text.format(f=firma)}\n\n"
             "Ist die Vereinbarung wirksam, und wie lange haftet der Verkäufer für Mängel?")
    frist = FRISTEN_G[{24: 0, 12: 1, 0: 2}[monate]]
    felder = [Feld("wirksam", "Ist die Vereinbarung wirksam?", JA_NEIN[0 if wirksam else 1], typ="text", optionen=JA_NEIN),
              Feld("frist", "Gewährleistung", frist, typ="text", optionen=FRISTEN_G)]
    weg = schritte(f"{'Verbrauchsgüterkauf (§ 474 BGB): ein Unternehmer verkauft einer Verbraucherin' if verbraucher else 'Kauf zwischen Unternehmern'}, "
                   f"{'gebrauchte' if gebraucht else 'neue'} Sache",
                   f"{warum} → wirksam: **{JA_NEIN[0 if wirksam else 1]}**",
                   f"Damit gilt: **{frist}**" + ("" if wirksam or monate != 24 else " (die gesetzliche Frist, § 438 Abs. 1 Nr. 3)"))
    return Aufgabe(frage, felder, weg, titel="Abweichende Vereinbarung")


# --- Mängelrechte -------------------------------------------------------------------------

MANGELARTEN = ["Sachmangel", "Rechtsmangel", "Falschlieferung", "Zuweniglieferung", "Montagemangel"]
MAENGEL = {  # Mangelart: (warum, Fälle)
    "Sachmangel": ("die Sache weicht von der vereinbarten oder üblichen Beschaffenheit ab (§ 434 Abs. 1 bis 3 BGB)", [
        "Bei drei der 20 gelieferten Notebooks flackert das Display.",
        "Der neue Server startet nach dem Auspacken nicht.",
        "Der Akku der neuen Tablets hält zwei Stunden; die Werbung des Herstellers verspricht zehn.",
        "Der gelieferte Drucker zieht das Papier schief ein und verursacht ständig Staus."]),
    "Rechtsmangel": ("ein Dritter macht Rechte an der Sache geltend, sie lässt sich nicht ungestört nutzen (§ 435 BGB)", [
        "Ein Softwarehaus weist nach, dass die mitverkaufte Verwaltungssoftware sein Urheberrecht verletzt, und untersagt ihr die Nutzung.",
        "Ein Wettbewerber des Herstellers hat ein Patent auf die gelieferten Kartenlesegeräte und verbietet ihr, sie zu benutzen."]),
    "Falschlieferung": ("eine andere als die bestellte Sache; steht einem Sachmangel gleich (§ 434 Abs. 5 BGB)", [
        "Bestellt waren 27-Zoll-Monitore, geliefert werden 24-Zoll-Monitore.",
        "Bestellt war schwarzer Toner, geliefert wird gelber.",
        "Statt der bestellten Laserdrucker kommen Tintenstrahldrucker."]),
    "Zuweniglieferung": ("zu geringe Menge; die Menge gehört zur vereinbarten Beschaffenheit (§ 434 Abs. 2 Satz 2 BGB), der Rest ist "
                         "nachzuliefern", [
        "Bestellt und berechnet sind 30 Mäuse, im Karton sind nur 25.",
        "Statt der bestellten und berechneten 10 Dockingstationen kommen 8.",
        "Von 50 bestellten Patchkabeln kommen 40 an."]),
    "Montagemangel": ("der Verkäufer hat unsachgemäß montiert oder seine Montageanleitung ist fehlerhaft (§ 434 Abs. 4 BGB)", [
        "Der Händler montiert die gekauften Monitorhalterungen selbst; weil er zu kurze Schrauben nimmt, löst sich eine Halterung.",
        "Nach der fehlerhaften mitgelieferten Montageanleitung bauen ihre Mitarbeiter den gekauften Serverschrank auf; die Türen "
        "schließen nicht.",
        "Der Verkäufer baut die gekaufte Grafikkarte ein, setzt sie aber nicht richtig in den Steckplatz; der Rechner stürzt ab."]),
}
RECHTE = ["Zuerst Nacherfüllung", "Rücktritt oder Minderung", "Keine Mängelrechte mehr"]
WAHL = ["Ersatz liefern, wie die Käuferin es verlangt", "Reparieren, weil er das lieber will"]
# was geschehen ist, Index in RECHTE, warum
STUFEN = [
    ("Sie hat den Mangel gerade entdeckt und dem Händler sofort gemeldet. Sie möchte ein neues Gerät, der Händler würde lieber "
     "reparieren; beides kostet ihn etwa gleich viel.", 0, ""),
    ("Sie hat Ersatzlieferung verlangt und dafür eine angemessene Frist von zwei Wochen gesetzt; die Frist ist ergebnislos "
     "abgelaufen.", 1, "Die Frist zur Nacherfüllung ist ergebnislos abgelaufen (§ 437 Nr. 2, § 323 Abs. 1 BGB)"),
    ("Der Händler hat das Gerät zweimal repariert, beide Versuche sind fehlgeschlagen.", 1,
     "Nach dem zweiten erfolglosen Versuch gilt die Nachbesserung als fehlgeschlagen (§ 440 Satz 2 BGB); eine weitere Frist ist nicht "
     "nötig"),
    ("Der Händler lehnt jede Reparatur und jeden Austausch ernsthaft und endgültig ab.", 1,
     "Verweigert der Verkäufer die Nacherfüllung ernsthaft und endgültig, ist keine Frist nötig (§ 323 Abs. 2 Nr. 1, § 440 Satz 1 BGB)"),
    ("Der Mangel zeigt sich erst zwei Jahre und vier Monate nach der Lieferung; der Händler beruft sich auf Verjährung.", 2,
     "Mängelansprüche bei neuen Sachen verjähren 2 Jahre nach der Ablieferung (§ 438 Abs. 1 Nr. 3 BGB); beruft sich der Händler "
     "darauf, sind auch Rücktritt und Minderung unwirksam (§ 438 Abs. 4 und 5, § 218)"),
]
KLEINE_MAENGEL = ["Eine Abdeckklappe am Gehäuse klemmt", "Ein Standfuß wackelt", "Eine Taste der mitgelieferten Fernbedienung hakt"]
GROSSE_MAENGEL = ["Das Gerät startet immer wieder von selbst neu", "Das Display fällt immer wieder aus",
                  "Das Gerät überhitzt und schaltet sich ab"]
WERT_MAENGEL = ["Das Display hat einen dauerhaften hellen Fleck", "Der Lüfter ist dauerhaft laut", "Zwei USB-Anschlüsse funktionieren nicht"]


def cent(x: Decimal) -> Decimal:
    """Auf Cent runden wie in der Prüfung (kaufmännisch)."""
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


def minderung(preis, ohne, mit) -> Decimal:
    """§ 441 Abs. 3 BGB: geminderter Preis = Kaufpreis · Wert mit Mangel : Wert ohne Mangel, auf Cent."""
    return cent(Decimal(preis) * Decimal(mit) / Decimal(ohne))


@art("maengel", "Mängelrechte", "Recht & Verträge",
     "Mangelart erkennen, Nacherfüllung vor Rücktritt und Minderung, Minderung berechnen (§§ 434 bis 441 BGB)",
     ("Mängelrecht", "Mängelrüge", "Mängelanspr", "Mangelart", "Sachmangel", "Sachmängel", "Rechtsmangel", "Nacherfüllung",
      "Mangelhafte Lieferung", "Leistungsstörung"), formeln=FORMELN["maengel"])
def maengel(rng):
    return rng.choice([_mangelart, _reihenfolge, _reihenfolge, _minderung])(rng)


def _mangelart(rng):
    firma = rng.choice(FIRMEN)
    faelle = [(a, rng.choice(MAENGEL[a][1])) for a in rng.sample(MANGELARTEN, 3)]
    frage = (f"Bei der {firma} kommen mehrere Lieferungen an, und es gibt Ärger:\n\n"
             + "\n".join(f"{i}. {text}" for i, (_, text) in enumerate(faelle, start=1))
             + "\n\nUm welche Mangelart handelt es sich jeweils?")
    felder = [Feld(f"m{i}", f"Fall {i}", a, typ="text", optionen=MANGELARTEN) for i, (a, _) in enumerate(faelle, start=1)]
    weg = schritte(*(f"Fall {i}: **{a}**, {MAENGEL[a][0]}" for i, (a, _) in enumerate(faelle, start=1)))
    return Aufgabe(frage, felder, weg, titel="Mangelart erkennen")


def _reihenfolge(rng):
    stufe = rng.randrange(len(STUFEN))
    geschehen, recht, warum = STUFEN[stufe]
    firma, (name, genus) = rng.choice(FIRMEN), rng.choice(WAREN_G)
    preis = rng.choice([450, 890, 1200, 1490, 2400, 3600])
    erheblich = rng.random() < 0.6
    prozent = Decimal(str(rng.choice([15, 20, 30, 40] if erheblich else [1, 1.5, 2])))
    kosten = cent(preis * prozent / 100)
    mangel = rng.choice(GROSSE_MAENGEL if erheblich else KLEINE_MAENGEL)
    frage = (f"Die {firma} hat bei einem Händler {ware(name, genus, 'neu')} für **{euro(preis)}** gekauft. {mangel}; den Mangel zu "
             f"beseitigen kostet etwa **{euro(kosten)}**. {geschehen}\n\nWelche Mängelrechte hat sie jetzt? Darf sie vom Vertrag "
             "zurücktreten, und darf sie den Kaufpreis mindern?" + (" Was muss der Händler tun?" if stufe == 0 else ""))
    ruecktritt, mindern = recht == 1 and erheblich, recht == 1
    felder = [Feld("recht", "Mängelrechte jetzt", RECHTE[recht], typ="text", optionen=RECHTE),
              Feld("ruecktritt", "Rücktritt möglich?", JA_NEIN[0 if ruecktritt else 1], typ="text", optionen=JA_NEIN),
              Feld("minderung", "Minderung möglich?", JA_NEIN[0 if mindern else 1], typ="text", optionen=JA_NEIN)]
    if stufe == 0:
        felder.append(Feld("wahl", "Der Händler muss", WAHL[0], typ="text", optionen=WAHL))
        weg = ["Zuerst hat der Verkäufer Gelegenheit zur Nacherfüllung (§ 437 Nr. 1, § 439 BGB) → **Zuerst Nacherfüllung**",
               "Rücktritt und Minderung setzen voraus, dass die Nacherfüllung gescheitert ist → beides **Nein**",
               "Zwischen Nachbesserung und Ersatzlieferung wählt die Käuferin (§ 439 Abs. 1); der Händler darf die gewählte Art nur "
               "verweigern, wenn sie unverhältnismäßig teuer ist (§ 439 Abs. 4), hier nicht → **Ersatz liefern**"]
    elif recht == 1:
        weg = [f"{warum} → **Rücktritt oder Minderung**, hat der Händler den Mangel zu vertreten, dazu Schadensersatz (§§ 280, 281)",
               f"Erheblich? {euro(kosten)} von {euro(preis)} sind {de(float(prozent))} % des Kaufpreises → "
               + ("mehr als 5 %, erheblich → Rücktritt: **Ja**" if erheblich else
                  "höchstens 5 %, unerheblich: der Rücktritt ist ausgeschlossen (§ 323 Abs. 5 Satz 2) → **Nein**"),
               "Mindern darf sie auch bei einem unerheblichen Mangel (§ 441 Abs. 1 Satz 2) → **Ja**"]
    else:
        weg = [f"{warum} → **Keine Mängelrechte mehr**", "Rücktritt und Minderung: **Nein**"]
    return Aufgabe(frage, felder, schritte(*weg), titel="Reihenfolge der Mängelrechte")


def _minderung(rng):
    while True:
        ohne = rng.choice([800, 1000, 1200, 1500, 2000, 2400, 3000, 3600])
        mit = ohne * rng.choice([60, 70, 75, 80, 85, 90]) // 100
        preis = round(ohne * rng.choice([0.8, 0.85, 0.9, 1.1, 1.2]) / 10) * 10
        if preis != ohne:
            break
    firma, (name, genus) = rng.choice(FIRMEN), rng.choice(WAREN_G)
    gemindert = minderung(preis, ohne, mit)
    frage = (f"Die {firma} hat bei einem Händler {ware(name, genus, 'neu')} für **{euro(preis)}** gekauft und bezahlt. "
             f"{rng.choice(WERT_MAENGEL)}; zwei Reparaturversuche sind fehlgeschlagen. Die {firma} behält das Gerät und mindert den "
             f"Kaufpreis. Ein Gutachter schätzt: ohne den Mangel wäre es **{euro(ohne)}** wert, mit dem Mangel **{euro(mit)}**.\n\n"
             "Berechnen Sie den geminderten Kaufpreis und den Betrag, den der Händler erstatten muss (auf Cent).")
    felder = [Feld("preis", "Geminderter Kaufpreis", float(gemindert), "€"), Feld("erstattung", "Erstattung", float(preis - gemindert), "€")]
    weg = schritte("Minderung (§ 441 Abs. 3 BGB): der Kaufpreis sinkt im selben Verhältnis wie der Wert; vorher muss die Nacherfüllung "
                   "gescheitert sein, hier nach zwei Versuchen (§ 440 Satz 2)",
                   f"Geminderter Preis = {de(preis)} · {de(mit)} : {de(ohne)} = **{euro(gemindert)}**",
                   f"Erstattung (§ 441 Abs. 4): {euro(preis)} − {euro(gemindert)} = **{euro(preis - gemindert)}**",
                   f"Nicht einfach die Wertdifferenz abziehen: {euro(preis)} − {euro(ohne - mit)} = {euro(preis - ohne + mit)} wäre falsch, "
                   f"weil sie {'günstiger' if preis < ohne else 'teurer'} gekauft hat, als das Gerät ohne Mangel wert ist")
    return Aufgabe(frage, felder, weg, titel="Minderung berechnen")


# --- Zahlungsverzug -----------------------------------------------------------------------

GRUENDE = ["Mahnung (§ 286 Abs. 1)", "Vereinbarter Zahlungstermin (§ 286 Abs. 2 Nr. 1)", "30 Tage nach Rechnungszugang (§ 286 Abs. 3)"]
BASISZINS = [-0.88, 1.27, 1.62, 2.27, 3.12, 3.37, 3.62]  # Prozent, Größenordnungen der letzten Jahre; die Aufgabe nennt ihn als Annahme
LEISTUNGEN = ["zwölf Monitore", "einen Server", "die Einrichtung eines WLANs", "zwanzig Headsets", "eine Schulung", "einen Drucker"]


def verzugszinsen(betrag, satz, tage: int) -> Decimal:
    """Betrag · Zinssatz in % · Tage : 365, auf Cent (Konvention im Merkblatt)."""
    return cent(Decimal(betrag) * Decimal(satz) / 100 * tage / 365)


def _schuldner(rng, firma: str, verbraucher: bool) -> tuple[str, str]:
    """(an wen, wer): „einem Privatkunden“, „der Kunde“ bzw. „der Muster AG“, „die Muster AG“."""
    if verbraucher:
        return "einem Privatkunden", "der Kunde"
    andere = rng.choice([f for f in FIRMEN if f != firma])
    return f"der {andere}", f"die {andere}"


@art("verzug", "Zahlungsverzug", "Recht & Verträge",
     "Verzugsbeginn nach § 286 BGB (Mahnung, Termin, 30 Tage), Verzugszinsen und Pauschale nach § 288 tagesgenau",
     ("Zahlungsverzug", "Verzugszins", "Verzugsbeginn", "Mahnung", "Mahnwesen", "Basiszins", "Leistungsstörung"),
     formeln=FORMELN["verzug"])
def verzug(rng):
    return rng.choice([_verzugsbeginn, _verzugszinsen])(rng)


DREISSIG = "Verzug beginnt erst am Tag nach den 30 Tagen; der Tag des Zugangs zählt nicht mit."


def _verzugsbeginn(rng):
    fall = rng.choice(["termin", "termin", "unternehmer", "hinweis", "mahnung", "frueh"])
    verbraucher = fall in ("hinweis", "mahnung") or fall == "termin" and rng.random() < 0.5
    firma = rng.choice(FIRMEN)
    an, wer = _schuldner(rng, firma, verbraucher)
    while True:
        zugang = _tag(rng)
        frist, termin = zugang + timedelta(days=30), zugang + timedelta(days=rng.choice([10, 14, 21, 28]))
        mahnung = _wochentag(zugang + timedelta(days=rng.randint(8, 20) if fall == "frueh" else rng.randint(40, 60)))
        if werktag(termin if fall == "termin" else frist):
            break
    ab = {"termin": termin + timedelta(days=1), "unternehmer": frist + timedelta(days=1), "hinweis": frist + timedelta(days=1),
          "mahnung": mahnung, "frueh": mahnung}[fall]
    if fall == "mahnung" and rng.random() < 0.6:  # nach den 30 Tagen, aber vor der Mahnung: ohne Hinweis noch kein Verzug
        stichtag = zugang + timedelta(days=rng.randint(33, (mahnung - zugang).days - 3))
    else:
        stichtag = ab + timedelta(days=rng.choice([-1, 1]) * rng.randint(3, 12))
        if stichtag <= zugang:
            stichtag = ab + timedelta(days=rng.randint(3, 12))
    text = (f"Die {firma} stellt {an} **{euro(rng.randrange(300, 9000, 10))}** für {rng.choice(LEISTUNGEN)} in Rechnung; die Rechnung "
            f"geht am **{lang(zugang)}** zu.")
    if fall == "termin":
        text += f" Im Vertrag ist vereinbart: Zahlung bis spätestens **{kurz(termin)}**."
    else:
        text += " Ein Zahlungsziel ist nicht vereinbart, der Betrag ist sofort fällig."
    text += {"termin": "", "unternehmer": rng.choice(["", " Einen Hinweis auf die Folgen verspäteter Zahlung enthält die Rechnung nicht."]),
             "hinweis": " Die Rechnung weist ausdrücklich darauf hin, dass er 30 Tage nach Zugang ohne Mahnung in Verzug kommt.",
             "mahnung": " Einen Hinweis auf die Folgen verspäteter Zahlung enthält die Rechnung nicht. Am "
                        f"**{lang(mahnung)}** geht dem Kunden eine Mahnung zu.",
             "frueh": f" Schon am **{lang(mahnung)}** geht {an} eine Mahnung zu."}[fall]
    frage = (f"{text} Gezahlt ist bis heute nicht.\n\nWodurch kommt {wer} in Verzug, ab welchem Tag, und war {wer} am "
             f"**{lang(stichtag)}** schon in Verzug? (Datum als TT.MM.JJJJ)")
    grund = {"termin": 1, "unternehmer": 2, "hinweis": 2, "mahnung": 0, "frueh": 0}[fall]
    typisch = {"termin": [(termin, "Am vereinbarten Termin darf noch gezahlt werden; Verzug beginnt am Tag danach.")],
               "unternehmer": [(frist, DREISSIG)], "hinweis": [(frist, DREISSIG)],
               "mahnung": [(frist + timedelta(days=1), "Gegenüber einem Verbraucher gilt die 30-Tage-Regel nur mit Hinweis in der "
                                                       "Rechnung.")],
               "frueh": [(frist + timedelta(days=1), "Die Mahnung wirkt früher; die 30 Tage gelten nur „spätestens“.")]}[fall]
    felder = [Feld("grund", "Verzug durch", GRUENDE[grund], typ="text", optionen=GRUENDE),
              Feld("ab", "Verzug ab", kurz(ab), typ="datum", typisch=tuple((kurz(d), h) for d, h in typisch)),
              Feld("stichtag", f"Am {kurz(stichtag)} in Verzug?", JA_NEIN[0 if stichtag >= ab else 1], typ="text", optionen=JA_NEIN)]
    dreissig = [f"Fristbeginn am Tag nach dem Zugang: {kurz(zugang)} + 30 Tage = {kurz(frist)} (§§ 187, 188 BGB), ein Werktag",
                f"Verzug ab dem Tag danach: **{kurz(ab)}**"]
    weg = {"termin": [f"Der Zahlungstermin {kurz(termin)} ist im Vertrag nach dem Kalender bestimmt: Verzug ohne Mahnung (§ 286 Abs. 2 "
                      f"Nr. 1 BGB){', auch gegenüber Verbrauchern' if verbraucher else ''}",
                      f"Verzug ab dem Tag nach dem Termin: **{kurz(ab)}**"],
           "unternehmer": ["Kein Termin, keine Mahnung: § 286 Abs. 3 BGB, spätestens 30 Tage nach Fälligkeit und Zugang der Rechnung; "
                           "zwischen Unternehmern auch ohne Hinweis in der Rechnung", *dreissig],
           "hinweis": ["Kein Termin, keine Mahnung: § 286 Abs. 3 BGB, spätestens 30 Tage nach Fälligkeit und Zugang der Rechnung; "
                       "gegenüber dem Verbraucher nur, weil die Rechnung darauf hinweist", *dreissig],
           "mahnung": ["§ 286 Abs. 3 BGB greift nicht: der Kunde ist Verbraucher, und die Rechnung enthält keinen Hinweis",
                       f"Erst die Mahnung nach Fälligkeit begründet den Verzug, mit ihrem Zugang (§ 286 Abs. 1): **{kurz(ab)}**"],
           "frueh": ["Die 30-Tage-Regel gilt nur „spätestens“ (§ 286 Abs. 3 BGB); eine Mahnung nach Fälligkeit wirkt früher",
                     f"Verzug mit dem Zugang der Mahnung (§ 286 Abs. 1): **{kurz(ab)}**, nicht erst am {kurz(frist + timedelta(days=1))}"],
           }[fall]
    weg.append(f"Am {kurz(stichtag)}: " + ("**Ja**, in Verzug" if stichtag >= ab else "**Nein**, noch nicht in Verzug"))
    return Aufgabe(frage, felder, schritte(*weg), titel="Verzugsbeginn")


def _verzugszinsen(rng):
    unternehmer, termin = rng.random() < 0.55, rng.random() < 0.4
    while True:  # der ganze Zeitraum in einem Halbjahr: der Basiszinssatz ändert sich zum 1. Januar und 1. Juli
        zugang = _tag(rng)
        letzter = zugang + timedelta(days=rng.choice([10, 14, 21, 28]) if termin else 30)
        erster, zahlung = letzter + timedelta(days=1), letzter + timedelta(days=rng.randint(10, 110))
        if werktag(letzter) and zahlung.weekday() < 5 and (erster.year, erster.month < 7) == (zahlung.year, zahlung.month < 7):
            break
    firma = rng.choice(FIRMEN)
    an, _ = _schuldner(rng, firma, not unternehmer)
    betrag = Decimal(rng.randrange(400, 24000)) + Decimal(rng.choice([0, 50, 90, 99])) / 100
    basis = Decimal(str(rng.choice(BASISZINS)))
    satz = basis + (9 if unternehmer else 5)
    tage = (zahlung - erster).days + 1
    zinsen, pauschale = verzugszinsen(betrag, satz, tage), Decimal(40 if unternehmer else 0)
    if termin:
        bedingung = f"Im Vertrag ist vereinbart: Zahlung bis spätestens {kurz(letzter)}."
    else:
        bedingung = "Ein Zahlungsziel ist nicht vereinbart, der Betrag ist sofort fällig" + (
            "." if unternehmer else ", und die Rechnung weist auf den Verzug 30 Tage nach Zugang hin.")
    frage = (f"Die {firma} stellt {an} **{euro(betrag)}** für {rng.choice(LEISTUNGEN)} in Rechnung; die Rechnung geht am "
             f"{lang(zugang)} zu. {bedingung} Gemahnt wird nicht; das Geld geht erst am **{lang(zahlung)}** ein. Nehmen Sie für den "
             f"ganzen Zeitraum einen Basiszinssatz von **{de(float(basis))} %** an.\n\nBerechnen Sie den Verzugszinssatz, die Zinstage, "
             "die Verzugszinsen und die Pauschale nach § 288 BGB. Zinstage zählen vom ersten Verzugstag bis einschließlich zum "
             "Zahlungstag, taggenau mit 365 Tagen im Jahr; runden Sie auf Cent.")
    punkte = ("Ohne Verbraucher sind es 9 Prozentpunkte über dem Basiszinssatz, nicht 5." if unternehmer else
              "Ist ein Verbraucher beteiligt, sind es nur 5 Prozentpunkte über dem Basiszinssatz, nicht 9.")
    pauschale_falsch = ((0.0, "Ist der Schuldner kein Verbraucher, kommen 40 € Pauschale dazu (§ 288 Abs. 5).") if unternehmer else
                        (40.0, "Die Pauschale von 40 € gibt es nur, wenn der Schuldner kein Verbraucher ist."))
    andere = basis + (5 if unternehmer else 9)
    falsch_satz = [(andere, punkte), (satz - basis, "Du hast den Basiszinssatz vergessen; der Verzugszins liegt um die Prozentpunkte darüber.")]
    felder = [Feld("satz", "Verzugszinssatz", float(satz), "%", typisch=tuple((float(x), h) for x, h in falsch_satz)),
              Feld("tage", "Zinstage", tage, "Tage", stellen=0, typisch=(
                  (tage - 1, "Du hast einen Tag zu wenig; erster Verzugstag und Zahlungstag zählen beide mit."),
                  (tage + 1, "Du hast ab dem letzten Tag der Frist gezählt; Verzug beginnt erst am Tag danach."))),
              Feld("zinsen", "Verzugszinsen", float(zinsen), "€", typisch=(
                  (float(cent(Decimal(betrag) * satz / 100 * tage / 360)), "Du hast mit 360 Tagen gerechnet; hier zählt das Jahr 365 Tage."),
                  *((float(verzugszinsen(betrag, x, tage)), h) for x, h in falsch_satz))),
              Feld("pauschale", "Pauschale", float(pauschale), "€", typisch=(pauschale_falsch,))]
    weg = schritte(
        (f"Zahlungstermin {kurz(letzter)} im Vertrag vereinbart (§ 286 Abs. 2 Nr. 1 BGB)" if termin else
         f"§ 286 Abs. 3 BGB: {kurz(zugang)} + 30 Tage = {kurz(letzter)}" + ("" if unternehmer else ", gegenüber dem Verbraucher "
                                                                             "wegen des Hinweises in der Rechnung"))
        + f" → erster Verzugstag **{kurz(erster)}**",
        f"Zinssatz nach § 288 Abs. {2 if unternehmer else 1} BGB: {de(float(basis))} % + {9 if unternehmer else 5} Prozentpunkte = "
        f"**{de(float(satz))} %** ({'kein Verbraucher beteiligt' if unternehmer else 'ein Verbraucher ist beteiligt'})",
        f"Zinstage: vom {kurz(erster)} bis einschließlich {kurz(zahlung)} = **{tage} Tage**",
        f"Zinsen: {euro(betrag)} · {de(float(satz))} % · {tage} : 365 = **{euro(zinsen)}**",
        "Pauschale (§ 288 Abs. 5): " + ("**40,00 €**, der Schuldner ist kein Verbraucher" if unternehmer else
                                        "**0,00 €**, die Pauschale gibt es nur gegenüber Unternehmern"))
    return Aufgabe(frage, felder, weg, toleranz=0.001, titel="Verzugszinsen")


# --- Softwarelizenzen ---------------------------------------------------------------------

LIZENZEN = ["OEM-Lizenz", "Einzelplatzlizenz", "Volumenlizenz", "Abonnement (Subscription)", "Freeware", "Open-Source-Lizenz"]
LIZENZ_FAELLE = {  # Lizenz: (woran man sie erkennt, Fälle)
    "OEM-Lizenz": ("mit neuer Hardware verkauft, günstig, an das Gerät gebunden", [
        "Sie kauft 30 neue Büro-PCs; das Betriebssystem ist vorinstalliert, die Lizenz war im Gerätepreis enthalten und ist laut "
        "Lizenzbedingungen an diese Geräte gebunden.",
        "Zu den neuen Notebooks gehört eine Bürosoftware, die der Hersteller nur zusammen mit dem Gerät und günstiger als im Handel "
        "abgibt."]),
    "Einzelplatzlizenz": ("eine Lizenz für genau einen Arbeitsplatz", [
        "Eine Grafikerin braucht ein Bildbearbeitungsprogramm nur auf ihrem Arbeitsplatzrechner; es wird einmal bezahlt und darf auf "
        "genau einem Rechner dauerhaft genutzt werden.",
        "Für den einzigen CAD-Arbeitsplatz wird das Programm einmal gekauft, für genau diesen Rechner und unbefristet."]),
    "Volumenlizenz": ("viele Lizenzen auf einmal, mit Mengenrabatt und zentraler Verwaltung", [
        "Sie stattet 400 Arbeitsplätze mit derselben Bürosoftware aus, bekommt Mengenrabatt und einen gemeinsamen Lizenzschlüssel und "
        "verteilt die Installation zentral.",
        "Für alle 250 Beschäftigten wird derselbe Virenschutz auf einen Schlag lizenziert und über eine zentrale Konsole verwaltet."]),
    "Abonnement (Subscription)": ("Gebühr je Monat oder Jahr, Updates inklusive, die Nutzung endet mit der Kündigung", [
        "Sie zahlt je Benutzer und Monat für ein Projektmanagement-Werkzeug im Browser; Updates sind inbegriffen, nach der Kündigung "
        "endet die Nutzung.",
        "Die Bürosoftware wird jährlich je Benutzer bezahlt und ist immer auf dem neuesten Stand; zahlt sie nicht weiter, lässt sie "
        "sich nicht mehr nutzen."]),
    "Freeware": ("kostenlos nutzbar, aber der Quellcode ist geschlossen, Ändern und Weiterverkaufen sind verboten", [
        "Ein Packprogramm darf laut Lizenz kostenlos genutzt werden, auch im Betrieb; der Quellcode ist nicht veröffentlicht, Ändern "
        "und Weiterverkaufen sind verboten.",
        "Ein kostenloser PDF-Betrachter darf beliebig installiert werden; der Quellcode bleibt beim Hersteller, Veränderungen sind "
        "untersagt."]),
    "Open-Source-Lizenz": ("der Quellcode ist offen, Nutzen, Ändern und Weitergeben sind erlaubt, nach den Lizenzbedingungen", [
        "Ein Webserver ist kostenlos, sein Quellcode öffentlich; sie darf ihn verändern und weitergeben, wenn sie die "
        "Lizenzbedingungen einhält.",
        "Für die Lagerverwaltung nutzt sie ein Programm, dessen Quellcode jeder einsehen, verändern und weitergeben darf."]),
}
# Handlung (nach „Sie“), erlaubt?, warum
ERLAUBT = [
    ("verändert eine Bibliothek unter der GNU GPL, baut sie in ihr Produkt ein und verkauft es an Kunden, ohne den Quellcode "
     "herauszugeben.", False, "Copyleft: wer veränderten GPL-Code weitergibt, muss das Ganze wieder unter der GPL und mit Quellcode "
     "weitergeben"),
    ("verändert ein Programm unter der GNU GPL und nutzt die geänderte Fassung nur intern, ohne sie weiterzugeben.", True,
     "Die Pflichten der GPL greifen erst bei der Weitergabe; intern ändern und nutzen ist frei"),
    ("verkauft ein unverändertes Programm unter der GNU GPL auf USB-Sticks gegen Geld und legt Lizenztext und Quellcode bei.", True,
     "Die GPL erlaubt, für die Weitergabe Geld zu verlangen; die Käufer bekommen dieselben Rechte"),
    ("baut eine Bibliothek unter der MIT-Lizenz in ihr Produkt ein, verkauft es ohne Quellcode und legt den Urheber- und "
     "Lizenzhinweis bei.", True, "Permissive Lizenz ohne Copyleft: Pflicht ist nur der Urheber- und Lizenzhinweis"),
    ("baut eine Bibliothek unter der MIT-Lizenz in ihr Produkt ein und entfernt dabei den Urheber- und Lizenzhinweis.", False,
     "Die MIT-Lizenz verlangt, den Urheber- und Lizenzhinweis in allen Kopien beizubehalten"),
    ("baut Code unter der BSD-Lizenz in ein Produkt mit geschlossenem Quellcode ein und behält den Lizenzhinweis bei.", True,
     "Permissiv: Weitergabe auch ohne Quellcode erlaubt, wenn der Hinweis bleibt"),
    ("wirbt für ihr Produkt, das Code unter der 3-Klausel-BSD-Lizenz enthält, ohne Erlaubnis mit den Namen der ursprünglichen "
     "Entwickler.", False, "Die dritte Klausel verbietet, ohne schriftliche Erlaubnis mit den Namen der Urheber zu werben"),
    ("nimmt ein Freeware-Programm auseinander, verändert es und verkauft es unter eigenem Namen.", False,
     "Freeware ist nur kostenlos nutzbar; Ändern und Weiterverkaufen erlaubt sie nicht, die Rechte bleiben beim Urheber"),
    ("setzt im Betrieb ein Freeware-Programm ein, das laut Lizenz nur für die private Nutzung kostenlos ist.", False,
     "Die Lizenz erlaubt nur die private Nutzung; im Betrieb braucht sie eine gewerbliche Lizenz"),
    ("installiert eine Einzelplatzlizenz, die laut Lizenzbedingungen für genau einen Rechner gilt, auf drei Rechnern gleichzeitig.",
     False, "Jede weitere Installation braucht eine eigene Lizenz"),
    ("nutzt ein Software-Abonnement weiter, nachdem sie es gekündigt hat und nicht mehr zahlt.", False,
     "Das Abonnement räumt die Nutzung nur für die bezahlte Laufzeit ein"),
    ("verkauft eine unbefristet gegen Einmalzahlung gekaufte Einzelplatzlizenz weiter und löscht ihre eigene Installation.", True,
     "Erschöpfung (§ 69c Nr. 3 UrhG, EuGH „UsedSoft“): eine auf Dauer verkaufte Kopie darf weiterverkauft werden, wenn die eigene "
     "unbrauchbar ist"),
]
KAUF, ABO = "Kauf mit Wartung", "Abonnement"


@art("lizenz", "Softwarelizenzen", "Recht & Verträge",
     "OEM, Einzelplatz, Volumen, Abo, Freeware, Open Source; was erlauben GPL und MIT? Kauf oder Abo über mehrere Jahre",
     ("Lizenz", "Open Source", "Open-Source", "Copyleft", "Freeware", "Urheberrecht"), formeln=FORMELN["lizenz"])
def lizenz(rng):
    return rng.choice([_lizenzmodell, _erlaubt, _lizenzkosten])(rng)


def _lizenzmodell(rng):
    firma = rng.choice(FIRMEN)
    faelle = [(a, rng.choice(LIZENZ_FAELLE[a][1])) for a in rng.sample(LIZENZEN, 3)]
    frage = (f"Die {firma} ordnet ihre Software:\n\n" + "\n".join(f"{i}. {text}" for i, (_, text) in enumerate(faelle, start=1))
             + "\n\nWelches Lizenzmodell liegt jeweils vor?")
    felder = [Feld(f"l{i}", f"Fall {i}", a, typ="text", optionen=LIZENZEN) for i, (a, _) in enumerate(faelle, start=1)]
    weg = schritte(*(f"Fall {i}: **{a}**, {LIZENZ_FAELLE[a][0]}" for i, (a, _) in enumerate(faelle, start=1)))
    return Aufgabe(frage, felder, weg, titel="Passendes Lizenzmodell")


def _erlaubt(rng):
    firma = rng.choice(FIRMEN)
    faelle = rng.sample(ERLAUBT, 3)
    frage = (f"Die Entwicklungsabteilung der {firma} fragt, was sie darf:\n\n"
             + "\n".join(f"{i}. Sie {text}" for i, (text, _, _) in enumerate(faelle, start=1)) + "\n\nIst das jeweils erlaubt?")
    felder = [Feld(f"e{i}", f"Fall {i} erlaubt?", JA_NEIN[0 if ok else 1], typ="text", optionen=JA_NEIN)
              for i, (_, ok, _) in enumerate(faelle, start=1)]
    weg = schritte(*(f"Fall {i}: **{JA_NEIN[0 if ok else 1]}**. {warum}" for i, (_, ok, warum) in enumerate(faelle, start=1)))
    return Aufgabe(frage, felder, weg, titel="Was erlaubt die Lizenz?")


def _lizenzkosten(rng):
    while True:
        nutzer, preis = rng.choice([5, 8, 10, 12, 15, 20, 25, 30, 40, 50]), rng.choice([180, 240, 300, 360, 450, 480, 600, 720])
        wartung, abo, jahre = rng.choice([15, 18, 20, 22, 25]), rng.choice([8, 10, 12, 15, 18, 20, 24, 30]), rng.choice([3, 4, 5])
        ab_zweitem = rng.random() < 0.4  # im ersten Jahr sind Updates im Kaufpreis enthalten
        lizenzen = Decimal(nutzer * preis)
        je_jahr = lizenzen * wartung / 100
        w_jahre = jahre - 1 if ab_zweitem else jahre
        kauf, miete = lizenzen + je_jahr * w_jahre, Decimal(nutzer * abo * 12 * jahre)
        if abs(kauf - miete) >= Decimal("0.03") * min(kauf, miete):  # klar unterscheidbar
            break
    guenstiger = KAUF if kauf < miete else ABO
    frage = (f"Die {rng.choice(FIRMEN)} braucht eine Software für **{nutzer} Benutzer**, voraussichtlich **{jahre} Jahre** lang. "
             f"Zwei Angebote liegen vor:\n\n- **Kauf:** {euro(preis)} je Lizenz einmalig, dazu ein Wartungsvertrag (Updates und "
             f"Support) für {wartung} % des Lizenzpreises im Jahr"
             + (", ab dem zweiten Jahr; im ersten Jahr sind Updates inklusive" if ab_zweitem else "")
             + f"\n- **Abonnement:** {euro(abo)} je Benutzer und Monat, Updates und Support inklusive\n\nBerechnen Sie die Kosten "
             f"beider Angebote über die {jahre} Jahre (netto, ohne Zinsen) und geben Sie das günstigere an.")
    felder = [Feld("kauf", "Kauf mit Wartung, gesamt", float(kauf), "€"), Feld("abo", "Abonnement, gesamt", float(miete), "€"),
              Feld("guenstiger", "Günstiger", guenstiger, typ="text", optionen=[KAUF, ABO])]
    weg = schritte(f"Lizenzen: {nutzer} · {euro(preis)} = {euro(lizenzen)}",
                   f"Wartung: {euro(lizenzen)} · {wartung} % = {euro(je_jahr)} im Jahr, {w_jahre} Jahre"
                   + (" (das erste ist inklusive)" if ab_zweitem else "") + f" → {euro(je_jahr * w_jahre)}",
                   f"Kauf gesamt: {euro(lizenzen)} + {euro(je_jahr * w_jahre)} = **{euro(kauf)}**",
                   f"Abonnement: {nutzer} · {euro(abo)} · 12 · {jahre} = **{euro(miete)}**",
                   f"Günstiger: **{guenstiger}**, um {euro(abs(kauf - miete))}; die gekaufte Version darf man danach weiter nutzen, "
                   "das Abo endet mit der Kündigung")
    return Aufgabe(frage, felder, weg, toleranz=0.001, titel="Lizenzkosten vergleichen")
