"""Wirtschaft: Handelskalkulation und Angebotsvergleich, Kauf/Leasing/Miete, Nutzwertanalyse."""

from decimal import ROUND_HALF_UP, Decimal

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, de, euro, schritte, tabelle

WAREN = [("Notebooks", [650, 850, 980, 1200, 1450]), ("Monitore", [180, 240, 320, 450]), ("Switches", [380, 520, 890, 1250]),
         ("Server", [2400, 3600, 4800, 5600]), ("Multifunktionsdrucker", [480, 760, 1150]), ("Dockingstationen", [120, 160, 220])]


def _cent(x: Decimal) -> Decimal:
    """Auf Cent runden wie in der Prüfung (kaufmännisch)."""
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


def _prozent(p: Decimal) -> str:
    return f"{de(float(p))} %"


@art("kalkulation", "Kalkulation", "Wirtschaft", "Bezugs- und Angebotskalkulation, Angebotsvergleich",
     ("Kalkulation", "Angebotsvergleich", "Bezugspreis"))
def kalkulation(rng):
    return rng.choice([_vorwaerts, _vorwaerts, _angebotsvergleich])(rng)


def _vorwaerts(rng):
    ware, preise = rng.choice(WAREN)
    lep = Decimal(rng.choice(preise))
    rabatt, skonto = Decimal(rng.choice([5, 10, 12, 15, 20, 25])), Decimal(rng.choice([2, 3]))
    bezug = Decimal(rng.choice([15, 20, 25, 30, 45, 60]))
    hk, gewinn = Decimal(rng.choice([20, 25, 30, 35, 40])), Decimal(rng.choice([8, 10, 12, 15, 20]))
    k_skonto, k_rabatt = Decimal(rng.choice([2, 3])), Decimal(rng.choice([5, 10, 15]))
    h = Decimal(100)

    r = _cent(lep * rabatt / h)
    zep = lep - r
    s = _cent(zep * skonto / h)
    bep = zep - s
    bzp = bep + bezug
    hkz = _cent(bzp * hk / h)
    sk = bzp + hkz
    g = _cent(sk * gewinn / h)
    bvp = sk + g
    zvp = _cent(bvp / (h - k_skonto) * h)  # Kundenskonto und -rabatt „im Hundert“: vom höheren Preis gerechnet
    lvp = _cent(zvp / (h - k_rabatt) * h)
    ust = _cent(lvp * Decimal(19) / h)
    zeilen = [
        ["Listeneinkaufspreis", "", euro(lep)], ["− Liefererrabatt", _prozent(rabatt), euro(r)],
        ["= Zieleinkaufspreis", "", euro(zep)], ["− Liefererskonto", _prozent(skonto), euro(s)],
        ["= Bareinkaufspreis", "", euro(bep)], ["+ Bezugskosten", "", euro(bezug)],
        ["**= Bezugspreis**", "", f"**{euro(bzp)}**"], ["+ Handlungskosten", _prozent(hk), euro(hkz)],
        ["**= Selbstkosten**", "", f"**{euro(sk)}**"], ["+ Gewinn", _prozent(gewinn), euro(g)],
        ["**= Barverkaufspreis**", "", f"**{euro(bvp)}**"], ["+ Kundenskonto", _prozent(k_skonto), euro(zvp - bvp)],
        ["= Zielverkaufspreis", "", euro(zvp)], ["+ Kundenrabatt", _prozent(k_rabatt), euro(lvp - zvp)],
        ["**= Listenverkaufspreis netto**", "", f"**{euro(lvp)}**"], ["+ Umsatzsteuer", "19 %", euro(ust)],
        ["**= Listenverkaufspreis brutto**", "", f"**{euro(lvp + ust)}**"],
    ]
    variante = rng.choice(["bezug", "selbstkosten", "angebot"])
    if variante == "bezug":
        zeilen = zeilen[:7]
        felder = [Feld("zep", "Zieleinkaufspreis", float(zep), "€"), Feld("bep", "Bareinkaufspreis", float(bep), "€"),
                  Feld("bzp", "Bezugspreis", float(bzp), "€")]
        auftrag = "Berechnen Sie mit einer Bezugskalkulation den Ziel- und den Bareinkaufspreis sowie den Bezugspreis je Stück."
        daten = (f"- Listeneinkaufspreis: {euro(lep)}\n- Liefererrabatt: {_prozent(rabatt)}\n- Liefererskonto: {_prozent(skonto)}\n"
                 f"- Bezugskosten (Fracht, Verpackung): {euro(bezug)}")
    else:
        daten = (f"- Listeneinkaufspreis: {euro(lep)}, Liefererrabatt {_prozent(rabatt)}, Liefererskonto {_prozent(skonto)}\n"
                 f"- Bezugskosten: {euro(bezug)}\n- Handlungskostenzuschlag: {_prozent(hk)}\n- Gewinnzuschlag: {_prozent(gewinn)}\n"
                 f"- Kundenskonto: {_prozent(k_skonto)}, Kundenrabatt: {_prozent(k_rabatt)}\n- Umsatzsteuer: 19 %")
        if variante == "selbstkosten":
            felder = [Feld("bzp", "Bezugspreis", float(bzp), "€"), Feld("sk", "Selbstkosten", float(sk), "€"),
                      Feld("bvp", "Barverkaufspreis", float(bvp), "€")]
            auftrag = "Berechnen Sie den Bezugspreis, die Selbstkosten und den Barverkaufspreis je Stück."
            zeilen = zeilen[:11]
        else:
            felder = [Feld("sk", "Selbstkosten", float(sk), "€"), Feld("lvp", "Listenverkaufspreis netto", float(lvp), "€"),
                      Feld("brutto", "Listenverkaufspreis brutto", float(lvp + ust), "€")]
            auftrag = "Erstellen Sie das Angebot: Berechnen Sie die Selbstkosten und den Listenverkaufspreis netto und brutto je Stück."
    frage = (f"Die {rng.choice(FIRMEN)} kauft {ware} ein und verkauft sie an Geschäftskunden weiter. Für die Kalkulation "
             f"gelten:\n\n{daten}\n\n{auftrag} Runden Sie jeden Schritt auf Cent.")
    weg = tabelle(["Schritt", "%", "Betrag"], zeilen)
    if variante != "bezug":
        weg += ("\n\nHandlungskosten rechnen vom Bezugspreis, der Gewinn von den Selbstkosten. Kundenskonto und Kundenrabatt "
                "werden **im Hundert** gerechnet, weil der Kunde sie vom höheren Preis abzieht: Zielverkaufspreis = "
                f"Barverkaufspreis : {de(float(h - k_skonto))} % · 100 %, Listenverkaufspreis = Zielverkaufspreis : "
                f"{de(float(h - k_rabatt))} % · 100 %.")
    return Aufgabe(frage, felder, weg, toleranz=0.001, titel={"bezug": "Bezugskalkulation", "selbstkosten": "Selbstkosten",
                                                              "angebot": "Angebotskalkulation"}[variante])


def _angebotsvergleich(rng):
    ware, preise = rng.choice(WAREN)
    menge, basis = rng.choice([5, 8, 10, 12, 15, 20, 25]), rng.choice(preise)
    while True:
        angebote = []
        for name in "ABC":
            stueck = Decimal(round(basis * rng.uniform(0.9, 1.15)))
            rabatt, skonto = Decimal(rng.choice([0, 5, 8, 10, 12, 15])), Decimal(rng.choice([0, 2, 3]))
            fracht = Decimal(rng.choice([0, 0, 25, 40, 60, 85]))
            listen = stueck * menge
            r = _cent(listen * rabatt / 100)
            s = _cent((listen - r) * skonto / 100)
            angebote.append((name, stueck, rabatt, skonto, fracht, listen, r, s, listen - r - s + fracht))
        bezugspreise = sorted(a[-1] for a in angebote)
        if bezugspreise[1] - bezugspreise[0] >= 1:
            break
    bester = min(angebote, key=lambda a: a[-1])[0]
    zeilen = [[f"Angebot {a[0]}", f"{euro(a[1])} · {menge} = {euro(a[5])}", f"− {euro(a[6])} ({_prozent(a[2])})",
               f"− {euro(a[7])} ({_prozent(a[3])})", f"+ {euro(a[4])}", f"**{euro(a[8])}**"] for a in angebote]
    liste = "\n".join(f"- **Angebot {a[0]}:** {euro(a[1])} je Stück, "
                      + (f"Rabatt {_prozent(a[2])}, " if a[2] else "kein Rabatt, ")
                      + (f"Skonto {_prozent(a[3])}, " if a[3] else "kein Skonto, ")
                      + (f"Versand {euro(a[4])}" if a[4] else "frei Haus") for a in angebote)
    frage = (f"Die {rng.choice(FIRMEN)} braucht **{menge} {ware}** und hat drei Angebote eingeholt:\n\n{liste}\n\n"
             "Führen Sie einen quantitativen Angebotsvergleich durch: Berechnen Sie den Bezugspreis jedes Angebots für die gesamte "
             "Menge (Skonto wird genutzt) und geben Sie das günstigste Angebot an.")
    weg = (tabelle(["", "Listenpreis", "Rabatt", "Skonto", "Bezugskosten", "Bezugspreis"], zeilen)
           + f"\n\nRabatt vom Listenpreis, Skonto vom Zieleinkaufspreis (nach Rabatt), dann Bezugskosten dazu. "
           f"Am günstigsten: **Angebot {bester}**.")
    felder = [Feld(f"angebot_{a[0].lower()}", f"Bezugspreis Angebot {a[0]}", float(a[8]), "€") for a in angebote]
    felder.append(Feld("bester", "Günstigstes Angebot", bester, typ="text", optionen=list("ABC")))
    return Aufgabe(frage, felder, weg, toleranz=0.001, titel="Angebotsvergleich")


# --- Kauf, Leasing, Miete ----------------------------------------------------

GERAETE = ["einen Multifunktionsdrucker", "einen Server", "eine Firewall-Appliance", "ein Kopiersystem", "eine Telefonanlage"]


def _modelle(rng):
    """Kauf (Preis, Wartung je Monat), Leasing (Sonderzahlung, Rate), Miete (Rate) mit glatten Beträgen."""
    kauf = rng.choice([2400, 3600, 4800, 6000, 7200, 9000, 12000])
    wartung = round(kauf * rng.uniform(0.004, 0.01) / 5) * 5
    sonder = rng.choice([0, 250, 500, 1000])
    leasing = round(kauf * rng.uniform(0.026, 0.034) / 5) * 5
    miete = round(kauf * rng.uniform(0.035, 0.05) / 5) * 5
    return kauf, wartung, sonder, leasing, miete


@art("vergleich", "Kauf, Leasing, Miete", "Wirtschaft", "Gesamtkosten über die Laufzeit und ab wann sich der Kauf lohnt",
     ("Leasing", "Miete", "Kostenarten", "Kostenvergleich", "Wirtschaftlichkeit", "Amortisation"))
def vergleich(rng):
    return rng.choice([_gesamtkosten, _ab_wann])(rng)


def _angebote_text(kauf, wartung, sonder, leasing, miete) -> str:
    return (f"- **Kauf:** {euro(kauf)}, dazu Wartungsvertrag {euro(wartung)} im Monat\n"
            f"- **Leasing:** {f'Sonderzahlung {euro(sonder)}, dann ' if sonder else ''}{euro(leasing)} im Monat, Wartung inklusive\n"
            f"- **Miete:** {euro(miete)} im Monat, Wartung inklusive")


def _gesamtkosten(rng):
    while True:
        kauf, wartung, sonder, leasing, miete = _modelle(rng)
        monate = rng.choice([24, 36, 48])
        kosten = {"Kauf": kauf + wartung * monate, "Leasing": sonder + leasing * monate, "Miete": miete * monate}
        werte = sorted(kosten.values())
        if werte[1] - werte[0] >= 50:
            break
    beste = min(kosten, key=kosten.get)
    frage = (f"Die {rng.choice(FIRMEN)} braucht {rng.choice(GERAETE)} für **{monate} Monate**. Es liegen drei Angebote vor:\n\n"
             f"{_angebote_text(kauf, wartung, sonder, leasing, miete)}\n\nBerechnen Sie die Gesamtkosten jeder Variante über die "
             "Laufzeit und geben Sie die günstigste an.")
    weg = schritte(
        f"Kauf: {euro(kauf)} + {monate} · {euro(wartung)} = **{euro(kosten['Kauf'])}**",
        f"Leasing: {euro(sonder) + ' + ' if sonder else ''}{monate} · {euro(leasing)} = **{euro(kosten['Leasing'])}**",
        f"Miete: {monate} · {euro(miete)} = **{euro(kosten['Miete'])}**",
        f"Am günstigsten: **{beste}**",
    )
    felder = [Feld(n.lower(), f"Gesamtkosten {n}", k, "€") for n, k in kosten.items()]
    felder.append(Feld("beste", "Günstigste Variante", beste, typ="text", optionen=list(kosten)))
    return Aufgabe(frage, felder, weg, toleranz=0.001, titel="Gesamtkosten")


def _ab_wann(rng):
    while True:
        kauf, wartung, sonder, leasing, miete = _modelle(rng)
        # bei glatter Division wären beide in einem Monat gleich teuer; das soll die Aufgabe nicht offenlassen
        if (kauf % (miete - wartung)) and ((kauf - sonder) % (leasing - wartung)) and leasing > wartung and kauf > sonder:
            break
    ab_miete = kauf // (miete - wartung) + 1
    ab_leasing = (kauf - sonder) // (leasing - wartung) + 1
    frage = (f"Die {rng.choice(FIRMEN)} überlegt, {rng.choice(GERAETE)} anzuschaffen. Die Nutzungsdauer steht noch nicht fest.\n\n"
             f"{_angebote_text(kauf, wartung, sonder, leasing, miete)}\n\nAb welchem Monat ist der Kauf insgesamt günstiger als die "
             "Miete, und ab welchem Monat günstiger als das Leasing?")
    weg = schritte(
        f"Kosten nach m Monaten: Kauf {euro(kauf)} + {de(wartung)} · m, Miete {de(miete)} · m, "
        f"Leasing {euro(sonder) + ' + ' if sonder else ''}{de(leasing)} · m",
        f"Kauf < Miete: {de(kauf)} + {de(wartung)} m < {de(miete)} m ⇔ {de(kauf)} < {de(miete - wartung)} m ⇔ "
        f"m > {de(kauf / (miete - wartung))} → ab Monat **{ab_miete}**",
        f"Kauf < Leasing: {de(kauf)} + {de(wartung)} m < {de(sonder) + ' + ' if sonder else ''}{de(leasing)} m ⇔ "
        f"{de(kauf - sonder)} < {de(leasing - wartung)} m ⇔ m > {de((kauf - sonder) / (leasing - wartung))} → ab Monat **{ab_leasing}**",
    )
    felder = [Feld("miete", "Kauf günstiger als Miete ab Monat", ab_miete, stellen=0),
              Feld("leasing", "Kauf günstiger als Leasing ab Monat", ab_leasing, stellen=0)]
    return Aufgabe(frage, felder, weg, titel="Ab wann lohnt sich der Kauf?")


# --- Nutzwertanalyse ------------------------------------------------------------

KRITERIEN = ["Preis", "Leistung", "Service", "Lieferzeit", "Garantie", "Energieverbrauch", "Erweiterbarkeit", "Ergonomie", "Support"]
GEWICHTE = [[40, 30, 20, 10], [35, 25, 25, 15], [30, 30, 20, 20], [50, 20, 20, 10], [25, 25, 30, 20], [45, 25, 15, 15],
            [30, 25, 20, 15, 10], [40, 20, 15, 15, 10]]


@art("nutzwert", "Nutzwertanalyse", "Wirtschaft", "Gewichtete Punkte je Anbieter, der Sieger",
     ("Nutzwert", "Entscheidungsmatrix", "Bewertungsmatrix"))
def nutzwert(rng):
    while True:
        gewichte = list(rng.choice(GEWICHTE))
        rng.shuffle(gewichte)
        kriterien = rng.sample(KRITERIEN, len(gewichte))
        anbieter = rng.sample(["Alpha IT", "Beta Systeme", "Gamma Tech", "Delta Data"], rng.choice([2, 3]))
        punkte = {a: [rng.randint(3, 10) for _ in kriterien] for a in anbieter}
        werte = {a: sum(p * g for p, g in zip(punkte[a], gewichte)) / 100 for a in anbieter}
        reihe = sorted(werte.values(), reverse=True)
        if reihe[0] - reihe[1] >= 0.1:
            break
    sieger = max(werte, key=werte.get)
    fehlt = rng.random() < 0.4
    luecke = rng.randrange(len(kriterien))
    kopf = ["Kriterium", "Gewichtung", *anbieter]
    zeilen = [[k, "?" if fehlt and i == luecke else f"{g} %", *(punkte[a][i] for a in anbieter)]
              for i, (k, g) in enumerate(zip(kriterien, gewichte))]
    auftrag = "Berechnen Sie den Nutzwert jedes Anbieters (Summe aus Punkten · Gewichtung, Gewichtung als Anteil, z. B. 40 % = 0,4) und geben Sie den Sieger an."
    if fehlt:
        auftrag = f"Die Gewichtung für „{kriterien[luecke]}“ fehlt; alle Gewichtungen ergeben zusammen 100 %. Ermitteln Sie sie. " + auftrag
    frage = (f"Die {rng.choice(FIRMEN)} wählt einen Dienstleister für ihr neues Ticketsystem. Die Angebote wurden mit 0 bis 10 Punkten "
             f"bewertet:\n\n{tabelle(kopf, zeilen)}\n\n{auftrag}")
    weg = []
    if fehlt:
        andere = [g for i, g in enumerate(gewichte) if i != luecke]
        weg.append(f"Fehlende Gewichtung: 100 % − ({' + '.join(f'{g} %' for g in andere)}) = **{gewichte[luecke]} %**")
    for a in anbieter:
        weg.append(f"{a}: " + " + ".join(f"{p} · {de(g / 100)}" for p, g in zip(punkte[a], gewichte)) + f" = **{de(werte[a])}**")
    weg.append(f"Höchster Nutzwert: **{sieger}**")
    felder = ([Feld("gewicht", f"Gewichtung {kriterien[luecke]}", gewichte[luecke], "%", stellen=0)] if fehlt else [])
    felder += [Feld(f"nutzwert{i}", f"Nutzwert {a}", werte[a]) for i, a in enumerate(anbieter, start=1)]
    felder.append(Feld("sieger", "Sieger", sieger, typ="text", optionen=anbieter))
    return Aufgabe(frage, felder, schritte(*weg), titel="Nutzwertanalyse" + (" mit fehlender Gewichtung" if fehlt else ""))
