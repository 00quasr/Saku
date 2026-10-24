"""Wirtschaft: Handelskalkulation und Angebotsvergleich, Kauf/Leasing/Miete, Nutzwertanalyse."""

from decimal import ROUND_HALF_UP, Decimal

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, de, euro, schritte, tabelle

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "kalkulation": """| Schritt | gerechnet vom |
| --- | --- |
| Listeneinkaufspreis − Liefererrabatt = Zieleinkaufspreis | Listeneinkaufspreis |
| − Liefererskonto = Bareinkaufspreis | Zieleinkaufspreis |
| + Bezugskosten = **Bezugspreis** | |
| + Handlungskosten = **Selbstkosten** | Bezugspreis |
| + Gewinn = Barverkaufspreis | Selbstkosten |
| + Kundenskonto = Zielverkaufspreis | im Hundert: Barverkaufspreis : (100 − s) · 100 |
| + Kundenrabatt = Listenverkaufspreis netto | im Hundert: Zielverkaufspreis : (100 − r) · 100 |
| + Umsatzsteuer 19 % = brutto | Listenverkaufspreis netto |

- Angebotsvergleich: Bezugspreis jedes Angebots für die ganze Menge, das günstigste gewinnt
- Differenzkalkulation (Verkaufspreis vom Markt vorgegeben): vorwärts bis zu den Selbstkosten, rückwärts vom Listenverkaufspreis bis zum Barverkaufspreis (Rabatt und Skonto jetzt vom Hundert); Gewinn = Barverkaufspreis − Selbstkosten, in % der Selbstkosten
- Rückwärtskalkulation (höchster Einkaufspreis): Kundenrabatt und -skonto vom Hundert abziehen, Gewinn und Handlungskosten auf Hundert herausrechnen (: (100 + p) · 100), Bezugskosten abziehen, Liefererskonto und -rabatt im Hundert (: (100 − p) · 100)
- *Typische Fehler:* Skonto vom Listenpreis statt vom Zieleinkaufspreis, Zuschläge addiert statt nacheinander, Kundenskonto und -rabatt vom statt im Hundert, Gewinn in Prozent vom Barverkaufspreis statt von den Selbstkosten

*Beispiel:* 1.000 € − 10 % = 900 €, − 2 % Skonto = 882 €, + 20 € Bezugskosten = 902 € Bezugspreis""",
    "vergleich": """- Gesamtkosten = einmalige Kosten + monatliche Kosten · Monate
- Kauf: Preis + Wartung · Monate; Leasing: Sonderzahlung + Rate · Monate; Miete: Rate · Monate
- Ab wann lohnt sich der Kauf? Kauf + w · m < Rate · m ⇔ m > Kaufpreis : (Rate − w) → der erste ganze Monat danach
- Fixkosten fallen unabhängig von der Nutzung an, variable Kosten mit ihr
- *Typische Fehler:* Wartung oder Sonderzahlung vergessen, mit Jahren statt Monaten multipliziert, den Monat des Gleichstands statt des ersten Monats danach angegeben

*Beispiel:* 4.800 € + 30 €/Monat gegen Miete 190 €/Monat: m > 4.800 : 160 = 30 → ab Monat 31""",
    "nutzwert": """- Gewichtungen zusammen 100 %; eine fehlende = 100 % − Summe der übrigen
- Teilnutzwert = Punkte · Gewichtung (als Anteil, 40 % = 0,4)
- Nutzwert = Summe der Teilnutzwerte; der höchste Nutzwert gewinnt

*Beispiel:* Punkte 8, 6, 9 bei 50 %, 30 %, 20 %: 8 · 0,5 + 6 · 0,3 + 9 · 0,2 = 7,6""",
}


WAREN = [("Notebooks", [650, 850, 980, 1200, 1450]), ("Monitore", [180, 240, 320, 450]), ("Switches", [380, 520, 890, 1250]),
         ("Server", [2400, 3600, 4800, 5600]), ("Multifunktionsdrucker", [480, 760, 1150]), ("Dockingstationen", [120, 160, 220])]


def _cent(x: Decimal) -> Decimal:
    """Auf Cent runden wie in der Prüfung (kaufmännisch)."""
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


def _prozent(p: Decimal) -> str:
    return f"{de(float(p))} %"


# typische Fehler (Feld.typisch): Prozent vom falschen Grundwert
SKONTO_VOM_LISTENPREIS = "Du hast den Skonto vom Listenpreis berechnet; erst geht der Rabatt ab, der Skonto rechnet vom Zieleinkaufspreis."
VOM_HUNDERT = ("Du hast Kundenskonto und -rabatt vom Hundert aufgeschlagen; der Kunde zieht sie vom höheren Preis ab, also im Hundert "
               "rechnen: Preis : (100 − p) · 100.")


@art("kalkulation", "Kalkulation", "Wirtschaft", "Bezugs-, Angebots-, Differenz- und Rückwärtskalkulation, Angebotsvergleich",
     ("Kalkulation", "Angebotsvergleich", "Bezugspreis"), formeln=FORMELN["kalkulation"])
def kalkulation(rng):
    return rng.choice([_vorwaerts, _vorwaerts, _angebotsvergleich, _differenz, _rueckwaerts])(rng)


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
    vom_lep = zep - _cent(lep * skonto / h)
    bzp_feld = Feld("bzp", "Bezugspreis", float(bzp), "€", typisch=(
        (float(vom_lep + bezug), SKONTO_VOM_LISTENPREIS), (float(bep), "Du hast die Bezugskosten vergessen.")))
    sk_feld = Feld("sk", "Selbstkosten", float(sk), "€", typisch=((float(bep + _cent(bep * hk / h)), "Du hast die Bezugskosten vergessen."),))
    if variante == "bezug":
        zeilen = zeilen[:7]
        felder = [Feld("zep", "Zieleinkaufspreis", float(zep), "€"),
                  Feld("bep", "Bareinkaufspreis", float(bep), "€", typisch=((float(vom_lep), SKONTO_VOM_LISTENPREIS),)), bzp_feld]
        auftrag = "Berechnen Sie mit einer Bezugskalkulation den Ziel- und den Bareinkaufspreis sowie den Bezugspreis je Stück."
        daten = (f"- Listeneinkaufspreis: {euro(lep)}\n- Liefererrabatt: {_prozent(rabatt)}\n- Liefererskonto: {_prozent(skonto)}\n"
                 f"- Bezugskosten (Fracht, Verpackung): {euro(bezug)}")
    else:
        daten = (f"- Listeneinkaufspreis: {euro(lep)}, Liefererrabatt {_prozent(rabatt)}, Liefererskonto {_prozent(skonto)}\n"
                 f"- Bezugskosten: {euro(bezug)}\n- Handlungskostenzuschlag: {_prozent(hk)}\n- Gewinnzuschlag: {_prozent(gewinn)}\n"
                 f"- Kundenskonto: {_prozent(k_skonto)}, Kundenrabatt: {_prozent(k_rabatt)}\n- Umsatzsteuer: 19 %")
        if variante == "selbstkosten":
            felder = [bzp_feld, sk_feld, Feld("bvp", "Barverkaufspreis", float(bvp), "€", typisch=(
                (float(bzp + _cent(bzp * (hk + gewinn) / h)), "Du hast die Zuschläge addiert; der Gewinn rechnet von den Selbstkosten, "
                                                              "nicht vom Bezugspreis."),))]
            auftrag = "Berechnen Sie den Bezugspreis, die Selbstkosten und den Barverkaufspreis je Stück."
            zeilen = zeilen[:11]
        else:
            vom_hundert = _cent(_cent(bvp * (h + k_skonto) / h) * (h + k_rabatt) / h)
            felder = [sk_feld, Feld("lvp", "Listenverkaufspreis netto", float(lvp), "€", typisch=((float(vom_hundert), VOM_HUNDERT),)),
                      Feld("brutto", "Listenverkaufspreis brutto", float(lvp + ust), "€", typisch=(
                          (float(lvp), "Das ist der Nettopreis; brutto kommen 19 % Umsatzsteuer dazu."),
                          (float(vom_hundert * Decimal("1.19")), VOM_HUNDERT)))]
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


def _saetze(rng) -> dict:
    """Prozentsätze und Bezugskosten einer Kalkulation, als Decimal."""
    d = lambda werte: Decimal(rng.choice(werte))  # noqa: E731
    return {"rabatt": d([5, 10, 12, 15, 20, 25]), "skonto": d([2, 3]), "bezug": d([15, 20, 25, 30, 45, 60]),
            "hk": d([20, 25, 30, 35, 40]), "k_skonto": d([2, 3]), "k_rabatt": d([5, 10, 15])}


def _daten(z: dict, mit_lep: bool = True) -> str:
    teile = ([f"- Listeneinkaufspreis: {euro(z['lep'])}"] if mit_lep else []) + [
        f"- Liefererrabatt: {_prozent(z['rabatt'])}, Liefererskonto: {_prozent(z['skonto'])}",
        f"- Bezugskosten: {euro(z['bezug'])}", f"- Handlungskostenzuschlag: {_prozent(z['hk'])}",
        f"- Kundenskonto: {_prozent(z['k_skonto'])}, Kundenrabatt: {_prozent(z['k_rabatt'])}"]
    return "\n".join(teile)


def _differenz(rng):
    """Der Markt gibt den Listenverkaufspreis vor: Was bleibt als Gewinn?"""
    ware, preise = rng.choice(WAREN)
    z, h = _saetze(rng) | {"lep": Decimal(rng.choice(preise))}, Decimal(100)
    r = _cent(z["lep"] * z["rabatt"] / h)
    s_ = _cent((z["lep"] - r) * z["skonto"] / h)
    bzp = z["lep"] - r - s_ + z["bezug"]
    hkz = _cent(bzp * z["hk"] / h)
    sk = bzp + hkz
    # Marktpreis mit 9 am Ende, so dass 5 bis 25 % Gewinn bleiben
    ziel = sk * (1 + Decimal(rng.randint(5, 25)) / h) / (1 - z["k_skonto"] / h) / (1 - z["k_rabatt"] / h)
    lvp = Decimal(int(ziel / 10) * 10 + 9)
    kr = _cent(lvp * z["k_rabatt"] / h)
    zvp = lvp - kr
    ks = _cent(zvp * z["k_skonto"] / h)
    bvp = zvp - ks
    gewinn = bvp - sk
    prozent = gewinn / sk * h
    firma = rng.choice(FIRMEN)
    frage = (f"Die {firma} kauft {ware} ein. Die Konkurrenz verkauft dasselbe Gerät für **{euro(lvp)} netto**; "
             f"teurer kann die {firma} nicht anbieten. Für die Kalkulation gelten:\n\n{_daten(z)}\n\n"
             "Führen Sie eine Differenzkalkulation durch: Berechnen Sie Selbstkosten, Barverkaufspreis und den Gewinn in Euro und in "
             "Prozent der Selbstkosten (Cent und Prozent auf zwei Nachkommastellen).")
    zeilen = [["Listeneinkaufspreis", "", euro(z["lep"])], ["− Liefererrabatt", _prozent(z["rabatt"]), euro(r)],
              ["− Liefererskonto", _prozent(z["skonto"]), euro(s_)], ["+ Bezugskosten", "", euro(z["bezug"])],
              ["= Bezugspreis", "", euro(bzp)], ["+ Handlungskosten", _prozent(z["hk"]), euro(hkz)],
              ["**= Selbstkosten**", "", f"**{euro(sk)}**"], ["", "", ""],
              ["Listenverkaufspreis (vorgegeben)", "", euro(lvp)], ["− Kundenrabatt (vom Hundert)", _prozent(z["k_rabatt"]), euro(kr)],
              ["= Zielverkaufspreis", "", euro(zvp)], ["− Kundenskonto (vom Hundert)", _prozent(z["k_skonto"]), euro(ks)],
              ["**= Barverkaufspreis**", "", f"**{euro(bvp)}**"],
              ["**Gewinn** = Barverkaufspreis − Selbstkosten", f"**{de(float(prozent))} %**", f"**{euro(gewinn)}**"]]
    weg = (tabelle(["Schritt", "%", "Betrag"], zeilen)
           + "\n\nVom Listenverkaufspreis wird rückwärts gerechnet: Rabatt und Skonto stehen jetzt am höheren Preis, also vom "
             f"Hundert. Gewinn in Prozent = {euro(gewinn)} : {euro(sk)} · 100 = {de(float(prozent))} %.")
    vom_listenpreis = "Du hast vom Listenverkaufspreis gerechnet; Kundenrabatt und -skonto gehen vorher ab."
    felder = [Feld("sk", "Selbstkosten", float(sk), "€"), Feld("bvp", "Barverkaufspreis", float(bvp), "€"),
              Feld("gewinn", "Gewinn", float(gewinn), "€", typisch=((float(lvp - sk), vom_listenpreis),)),
              Feld("prozent", "Gewinn in Prozent", float(prozent), "%", typisch=(
                  (float(gewinn / bvp * h), "Du hast den Gewinn auf den Barverkaufspreis bezogen; Grundwert sind die Selbstkosten."),
                  (float((lvp - sk) / sk * h), vom_listenpreis)))]
    return Aufgabe(frage, felder, weg, toleranz=0.001, titel="Differenzkalkulation")


def _rueckwaerts(rng):
    """Der Verkaufspreis steht fest: Wie viel darf der Einkauf höchstens kosten?"""
    ware, preise = rng.choice(WAREN)
    z, h = _saetze(rng), Decimal(100)
    gewinn = Decimal(rng.choice([8, 10, 12, 15, 20]))
    lvp = Decimal(int(Decimal(rng.choice(preise)) * Decimal("1.6") / 10) * 10 + 9)
    kr = _cent(lvp * z["k_rabatt"] / h)
    zvp = lvp - kr
    ks = _cent(zvp * z["k_skonto"] / h)
    bvp = zvp - ks
    sk = _cent(bvp / (h + gewinn) * h)
    bzp = _cent(sk / (h + z["hk"]) * h)
    bep = bzp - z["bezug"]
    zep = _cent(bep / (h - z["skonto"]) * h)
    lep = _cent(zep / (h - z["rabatt"]) * h)
    frage = (f"Die {rng.choice(FIRMEN)} will {ware} für **{euro(lvp)} netto** anbieten, mehr zahlt der Markt nicht. Sie plant mit "
             f"**{_prozent(gewinn)} Gewinn**; außerdem gelten:\n\n{_daten(z, mit_lep=False)}\n\nFühren Sie eine Rückwärtskalkulation "
             "durch: Wie hoch dürfen Barverkaufspreis, Selbstkosten, Bezugspreis und der Listeneinkaufspreis höchstens sein? "
             "Runden Sie jeden Schritt auf Cent.")
    zeilen = [["Listenverkaufspreis (vorgegeben)", "", euro(lvp)], ["− Kundenrabatt (vom Hundert)", _prozent(z["k_rabatt"]), euro(kr)],
              ["= Zielverkaufspreis", "", euro(zvp)], ["− Kundenskonto (vom Hundert)", _prozent(z["k_skonto"]), euro(ks)],
              ["**= Barverkaufspreis**", "", f"**{euro(bvp)}**"], ["− Gewinn (auf Hundert)", _prozent(gewinn), euro(bvp - sk)],
              ["**= Selbstkosten**", "", f"**{euro(sk)}**"], ["− Handlungskosten (auf Hundert)", _prozent(z["hk"]), euro(sk - bzp)],
              ["**= Bezugspreis**", "", f"**{euro(bzp)}**"], ["− Bezugskosten", "", euro(z["bezug"])],
              ["= Bareinkaufspreis", "", euro(bep)], ["+ Liefererskonto (im Hundert)", _prozent(z["skonto"]), euro(zep - bep)],
              ["= Zieleinkaufspreis", "", euro(zep)], ["+ Liefererrabatt (im Hundert)", _prozent(z["rabatt"]), euro(lep - zep)],
              ["**= Listeneinkaufspreis höchstens**", "", f"**{euro(lep)}**"]]
    weg = (tabelle(["Schritt", "%", "Betrag"], zeilen)
           + f"\n\nAuf Hundert heißt: der Prozentsatz hing am kleineren Wert, also Selbstkosten = Barverkaufspreis : "
             f"{de(float(h + gewinn))} % · 100 %. Im Hundert: der Lieferer zog den Rabatt vom größeren Wert ab, also Listeneinkaufspreis "
             f"= Zieleinkaufspreis : {de(float(h - z['rabatt']))} % · 100 %.")
    abgezogen = "Du hast {} vom Hundert abgezogen; er hing am kleineren Wert, also auf Hundert herausrechnen: Wert : (100 + p) · 100."
    felder = [Feld("bvp", "Barverkaufspreis", float(bvp), "€"),
              Feld("sk", "Selbstkosten", float(sk), "€", typisch=((float(bvp - _cent(bvp * gewinn / h)), abgezogen.format("den Gewinn")),)),
              Feld("bzp", "Bezugspreis", float(bzp), "€",
                   typisch=((float(sk - _cent(sk * z["hk"] / h)), abgezogen.format("den Handlungskostenzuschlag")),)),
              Feld("lep", "Listeneinkaufspreis höchstens", float(lep), "€", typisch=(
                  (float(_cent(_cent(bep * (h + z["skonto"]) / h) * (h + z["rabatt"]) / h)),
                   "Du hast Skonto und Rabatt vom Hundert aufgeschlagen; der Lieferer zog sie vom höheren Preis ab, also im Hundert."),
                  (float(_cent(_cent(bzp / (h - z["skonto"]) * h) / (h - z["rabatt"]) * h)), "Du hast die Bezugskosten nicht abgezogen.")))]
    return Aufgabe(frage, felder, weg, toleranz=0.001, titel="Rückwärtskalkulation")


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
            falsch = [(float(listen - r - _cent(listen * skonto / 100) + fracht), SKONTO_VOM_LISTENPREIS)]
            if fracht:
                falsch.append((float(listen - r - s), "Du hast den Versand vergessen; er gehört als Bezugskosten zum Bezugspreis."))
            angebote.append((name, stueck, rabatt, skonto, fracht, listen, r, s, listen - r - s + fracht, tuple(falsch)))
        bezugspreise = sorted(a[8] for a in angebote)
        if bezugspreise[1] - bezugspreise[0] >= 1:
            break
    bester = min(angebote, key=lambda a: a[8])[0]
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
    felder = [Feld(f"angebot_{a[0].lower()}", f"Bezugspreis Angebot {a[0]}", float(a[8]), "€", typisch=a[9]) for a in angebote]
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
     ("Leasing", "Miete", "Kostenarten", "Kostenvergleich", "Wirtschaftlichkeit", "Amortisation"), formeln=FORMELN["vergleich"])
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
    jahre = "Du hast mit Jahren statt Monaten multipliziert."
    typisch = {"Kauf": [(kauf, "Du hast die Wartung vergessen; sie kommt jeden Monat dazu."), (kauf + wartung * monate / 12, jahre)],
               "Leasing": [(sonder + leasing * monate / 12, jahre), (leasing * monate, "Du hast die Sonderzahlung vergessen.")],
               "Miete": [(miete * monate / 12, jahre)]}
    felder = [Feld(n.lower(), f"Gesamtkosten {n}", k, "€", typisch=tuple(typisch[n])) for n, k in kosten.items()]
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
    gleichstand = "In diesem Monat ist der Kauf noch teurer; günstiger wird er erst im nächsten ganzen Monat."
    wartung_fehlt = "Du hast die Wartung beim Kauf vergessen; sie schmälert die monatliche Ersparnis."
    felder = [Feld("miete", "Kauf günstiger als Miete ab Monat", ab_miete, stellen=0, typisch=(
                  (ab_miete - 1, gleichstand), (kauf // miete + 1, wartung_fehlt))),
              Feld("leasing", "Kauf günstiger als Leasing ab Monat", ab_leasing, stellen=0, typisch=(
                  (ab_leasing - 1, gleichstand), ((kauf - sonder) // leasing + 1, wartung_fehlt),
                  (kauf // (leasing - wartung) + 1, "Du hast die Sonderzahlung des Leasings vergessen.")))]
    return Aufgabe(frage, felder, weg, titel="Ab wann lohnt sich der Kauf?")


# --- Nutzwertanalyse ------------------------------------------------------------

KRITERIEN = ["Preis", "Leistung", "Service", "Lieferzeit", "Garantie", "Energieverbrauch", "Erweiterbarkeit", "Ergonomie", "Support"]
GEWICHTE = [[40, 30, 20, 10], [35, 25, 25, 15], [30, 30, 20, 20], [50, 20, 20, 10], [25, 25, 30, 20], [45, 25, 15, 15],
            [30, 25, 20, 15, 10], [40, 20, 15, 15, 10]]


@art("nutzwert", "Nutzwertanalyse", "Wirtschaft", "Gewichtete Punkte je Anbieter, der Sieger",
     ("Nutzwert", "Entscheidungsmatrix", "Bewertungsmatrix"), formeln=FORMELN["nutzwert"])
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
