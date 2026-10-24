"""Strom & Hardware: Energiekosten, elektrische Größen, USV und RAID."""

import math

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, de, euro, schritte

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "energie": """- Leistung P = U · I (W = V · A), Strom I = P : U
- Arbeit W = P · t; kWh = Watt · Stunden : 1.000
- Kosten = kWh · Preis je kWh; Jahr: Leistung · Stunden je Tag · Tage
- Amortisationszeit = Anschaffung (oder Mehrpreis) : Einsparung pro Jahr
- USV: Wirkleistung P = Scheinleistung S (VA) · Leistungsfaktor cos φ
- Überbrückungszeit = Akkuenergie (V · Ah = Wh) · Wirkungsgrad : Last in W (· 60 für Minuten)

*Beispiel:* 10 PCs à 80 W, 8 h an 220 Tagen: 10 · 80 · 8 · 220 = 1.408 kWh; bei 0,32 €/kWh 450,56 €""",
    "raid": """| RAID | Nutzkapazität (n Platten, je c) | verkraftbare Ausfälle |
| --- | --- | --- |
| 0 | n · c | 0 |
| 1 | c | n − 1 |
| 5 | (n − 1) · c | 1 |
| 6 | (n − 2) · c | 2 |
| 10 | n : 2 · c | 1 sicher (bis n : 2, wenn nie beide eines Paares) |

- Verschieden große Platten: jede zählt nur so viel wie die kleinste
- Effizienz = Nutzkapazität : Gesamtkapazität

*Beispiel:* RAID 5 aus 4 × 8 TB: 3 · 8 = 24 TB nutzbar, Effizienz 75 %, 1 Ausfall""",
    "verfuegbarkeit": """- Verfügbarkeit V = Betriebszeit : Gesamtzeit; Ausfallzeit = (1 − V) · Gesamtzeit
- Hier: Jahr = 365 Tage = 8.760 h, Monat = 30 Tage = 720 h = 43.200 min
- Seriell (alle Komponenten nötig): V = V₁ · V₂ · …
- Parallel (redundant, eine reicht): V = 1 − (1 − V₁) · (1 − V₂) · …
- Aus MTBF (mittlere Zeit zwischen Ausfällen) und MTTR (mittlere Reparaturzeit): V = MTBF : (MTBF + MTTR)

*Beispiel:* 99,9 % im Jahr: 0,001 · 8.760 h = 8,76 h Ausfall; zwei Server mit je 99 % redundant: 1 − 0,01 · 0,01 = 99,99 %""",
}


PREISE = [0.28, 0.30, 0.32, 0.34, 0.35, 0.38, 0.40]  # €/kWh


@art("energie", "Energie und Strom", "Strom & Hardware", "Stromkosten, Einsparung und Amortisation, P = U · I, USV",
     ("Energiekosten", "Energieeffizien", "Stromkosten", "Stromverbrauch", "Elektrische Größe", "USV", "Unterbrechungsfrei"),
     formeln=FORMELN["energie"])
def energie(rng):
    return rng.choice([_kosten, _einsparung, _elektrisch, _usv])(rng)


def _kosten(rng):
    geraet, watt, stunden, anzahl = rng.choice([
        ("Arbeitsplatz-PCs", [65, 80, 120, 150], [8, 9, 10], range(5, 31)),
        ("Monitore", [18, 25, 30, 45], [8, 9, 10], range(10, 41)),
        ("Server", [250, 350, 450, 600], [24], range(1, 5)),
        ("Netzwerkdrucker", [40, 60, 90], [10, 12], range(1, 4)),
    ])
    watt, stunden, anzahl, preis = rng.choice(watt), rng.choice(stunden), rng.choice(anzahl), rng.choice(PREISE)
    tage = 365 if stunden == 24 else rng.choice([220, 230, 250])
    standby = rng.choice([0, 0, 0.5, 1, 2, 3]) if stunden < 24 else 0
    betrieb = anzahl * watt * stunden * tage / 1000
    ruhe = anzahl * standby * (8760 - stunden * tage) / 1000
    kwh = betrieb + ruhe
    zeit = "rund um die Uhr an 365 Tagen" if stunden == 24 else f"an {tage} Arbeitstagen je {stunden} Stunden"
    satz = f" In der übrigen Zeit des Jahres (8.760 Stunden insgesamt) bleiben sie im Standby mit **{de(standby)} W**." if standby else ""
    frage = (f"Die {rng.choice(FIRMEN)} betreibt **{anzahl} {geraet}** mit je **{watt} W** Leistungsaufnahme, {zeit}.{satz} "
             f"Der Strompreis beträgt **{de(preis)} €/kWh**.\n\nBerechnen Sie den Energiebedarf pro Jahr in kWh und die Stromkosten "
             "pro Jahr (auf Cent gerundet).")
    weg = [f"Betrieb: {anzahl} · {watt} W · {stunden} h · {tage} Tage = {de(betrieb * 1000)} Wh = {de(betrieb)} kWh"]
    if standby:
        weg += [f"Standby-Stunden: 8.760 h − {stunden} h · {tage} = {de(8760 - stunden * tage)} h",
                f"Standby: {anzahl} · {de(standby)} W · {de(8760 - stunden * tage)} h = {de(ruhe)} kWh",
                f"Zusammen: {de(betrieb)} + {de(ruhe)} = **{de(kwh)} kWh**"]
    weg.append(f"Kosten: {de(kwh)} kWh · {de(preis)} €/kWh = **{euro(kwh * preis)}**")
    felder = [Feld("kwh", "Energiebedarf", kwh, "kWh/Jahr"), Feld("kosten", "Stromkosten", kwh * preis, "€/Jahr")]
    return Aufgabe(frage, felder, schritte(*weg), toleranz=0.002, titel="Stromkosten")


def _einsparung(rng):
    while True:
        preis = rng.choice(PREISE)
        if rng.random() < 0.5:
            anzahl, alt = rng.randint(1, 4), rng.choice([400, 450, 500, 600])
            neu, stunden, tage = round(alt * rng.uniform(0.4, 0.6), -1), 24, 365
            preis_neu, was = rng.choice([1800, 2400, 3000, 3600]), "Server"
            text = (f"Die {rng.choice(FIRMEN)} will **{anzahl} alte Server** mit je **{alt} W** durch neue mit je **{de(neu)} W** "
                    f"ersetzen. Die Server laufen rund um die Uhr an 365 Tagen. Ein neuer Server kostet **{euro(preis_neu)}**.")
        else:
            anzahl, alt = rng.randint(10, 40), rng.choice([35, 40, 45, 50])
            neu, stunden, tage = rng.choice([14, 16, 18, 20]), rng.choice([8, 9, 10]), rng.choice([220, 230, 250])
            preis_neu, was = rng.choice([20, 25, 30, 40, 50]), "Monitor"
            text = (f"Die {rng.choice(FIRMEN)} beschafft **{anzahl} Monitore**. Das sparsame Modell braucht **{neu} W**, das "
                    f"Standardmodell **{alt} W**, kostet aber je Gerät **{euro(preis_neu)}** mehr. Die Monitore laufen an "
                    f"{tage} Tagen je {stunden} Stunden.")
        kwh = anzahl * (alt - neu) * stunden * tage / 1000
        ersparnis = kwh * preis
        jahre = anzahl * preis_neu / ersparnis
        if 0.3 <= jahre <= 10:
            break
    frage = (f"{text} Der Strompreis beträgt **{de(preis)} €/kWh**.\n\nBerechnen Sie die Einsparung pro Jahr in Euro und die "
             "Amortisationszeit in Jahren (zwei Nachkommastellen).")
    kosten = "Anschaffung" if was == "Server" else "Mehrpreis"
    weg = schritte(
        f"Eingesparte Leistung: {de(alt)} W − {de(neu)} W = {de(alt - neu)} W je {was}",
        f"Eingesparte Energie: {anzahl} · {de(alt - neu)} W · {stunden} h · {tage} Tage = {de(kwh * 1000)} Wh = {de(kwh)} kWh",
        f"Einsparung: {de(kwh)} kWh · {de(preis)} €/kWh = **{euro(ersparnis)}** pro Jahr",
        f"{kosten}: {anzahl} · {euro(preis_neu)} = {euro(anzahl * preis_neu)}",
        f"Amortisation = {kosten} : Einsparung = {euro(anzahl * preis_neu)} : {euro(ersparnis)} = **{de(jahre)} Jahre**",
    )
    felder = [Feld("ersparnis", "Einsparung", ersparnis, "€/Jahr"), Feld("jahre", "Amortisationszeit", jahre, "Jahre")]
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="Einsparung und Amortisation")


def _elektrisch(rng):
    if rng.random() < 0.5:
        strom, stunden = rng.choice([0.3, 0.4, 0.5, 0.65, 0.8, 1.2, 1.5, 2.5]), rng.choice([8, 10, 24])
        leistung = 230 * strom
        frage = (f"Ein Strommessgerät zeigt am Arbeitsplatzrechner eines Mitarbeiters der {rng.choice(FIRMEN)} bei **230 V** "
                 f"einen Strom von **{de(strom)} A**.\n\nBerechnen Sie die Leistungsaufnahme in Watt und die elektrische Arbeit in kWh, "
                 f"wenn der Rechner **{stunden} Stunden** läuft.")
        weg = schritte(f"P = U · I = 230 V · {de(strom)} A = **{de(leistung)} W**",
                       f"W = P · t = {de(leistung)} W · {stunden} h = {de(leistung * stunden)} Wh = **{de(leistung * stunden / 1000)} kWh**")
        felder = [Feld("leistung", "Leistung", leistung, "W"), Feld("arbeit", "Elektrische Arbeit", leistung * stunden / 1000, "kWh")]
        return Aufgabe(frage, felder, weg, toleranz=0.002, titel="Leistung und Arbeit")
    while True:
        leistung, anzahl = rng.choice([460, 575, 690, 805, 920, 1035]), rng.randint(2, 6)
        gesamt = leistung / 230 * anzahl
        if abs(gesamt - 16) > 0.5:
            break
    reicht = "Ja" if gesamt < 16 else "Nein"
    frage = (f"Im Serverraum der {rng.choice(FIRMEN)} sollen **{anzahl} Server** mit je **{leistung} W** an einen Stromkreis mit "
             "**230 V** angeschlossen werden, der mit **16 A** abgesichert ist.\n\nBerechnen Sie den Strom je Server und für alle "
             "Server zusammen, und entscheiden Sie, ob die Absicherung reicht.")
    weg = schritte(f"I = P : U = {leistung} W : 230 V = **{de(leistung / 230)} A** je Server",
                   f"Zusammen: {anzahl} · {de(leistung / 230)} A = **{de(gesamt)} A**",
                   f"{de(gesamt)} A {'<' if gesamt < 16 else '>'} 16 A → **{reicht}**, die Absicherung "
                   f"{'reicht' if reicht == 'Ja' else 'reicht nicht'}")
    felder = [Feld("strom", "Strom je Server", leistung / 230, "A"), Feld("gesamt", "Strom zusammen", gesamt, "A"),
              Feld("reicht", "Reicht die Absicherung?", reicht, typ="text", optionen=["Ja", "Nein"])]
    return Aufgabe(frage, felder, weg, toleranz=0.002, titel="Strom und Absicherung")


GERAETE = [("Server", [250, 350, 400]), ("Switch", [40, 60, 80]), ("NAS", [60, 90, 120]), ("Firewall", [30, 45]), ("Router", [20, 25])]


def _usv(rng):
    while True:
        va, cos_phi = rng.choice([1000, 1500, 2000, 3000]), rng.choice([0.6, 0.7, 0.8, 0.9])
        geraete = [(name, rng.choice(werte)) for name, werte in rng.sample(GERAETE, rng.randint(2, 4))]
        last = sum(w for _, w in geraete)
        akkus, ah, wirkung = rng.choice([2, 4]), rng.choice([7, 9, 12, 18]), rng.choice([0.8, 0.85, 0.9])
        wh = akkus * 12 * ah
        minuten = wh * wirkung / last * 60
        if last <= va * cos_phi and 3 <= minuten <= 120:
            break
    liste = "\n".join(f"- {name}: {w} W" for name, w in geraete)
    frage = (f"Die {rng.choice(FIRMEN)} schützt ihren Netzwerkschrank mit einer USV: **{de(va)} VA**, Leistungsfaktor "
             f"**{de(cos_phi)}**, Akkus **{akkus} × 12 V / {ah} Ah**, Wirkungsgrad **{de(wirkung * 100)} %**. Angeschlossen sind:\n\n"
             f"{liste}\n\nBerechnen Sie die Wirkleistung der USV, ihre Auslastung in Prozent (eine Nachkommastelle) und die "
             "Überbrückungszeit in Minuten (eine Nachkommastelle).")
    weg = schritte(
        f"Wirkleistung: P = S · cos φ = {de(va)} VA · {de(cos_phi)} = **{de(va * cos_phi)} W**",
        f"Last: {' + '.join(str(w) for _, w in geraete)} = {last} W → Auslastung {last} : {de(va * cos_phi)} = **{de(last / (va * cos_phi) * 100, 1)} %**",
        f"Akkuenergie: {akkus} · 12 V · {ah} Ah = {de(wh)} Wh, nutzbar · {de(wirkung)} = {de(wh * wirkung)} Wh",
        f"Zeit: {de(wh * wirkung)} Wh : {last} W = {de(wh * wirkung / last, 3)} h · 60 = **{de(minuten, 1)} min**",
    )
    felder = [Feld("wirk", "Wirkleistung der USV", va * cos_phi, "W", stellen=0),
              Feld("auslastung", "Auslastung", last / (va * cos_phi) * 100, "%", stellen=1),
              Feld("minuten", "Überbrückungszeit", minuten, "min", stellen=1)]
    return Aufgabe(frage, felder, weg, toleranz=0.005, titel="USV")


# --- RAID -------------------------------------------------------------------

# Level → (Nutzplatten aus n, garantiert verkraftbare Ausfälle aus n, Erklärung)
RAID = {
    0: (lambda n: n, lambda n: 0, "Striping ohne Redundanz: alle Platten speichern Daten, ein Ausfall zerstört alles"),
    1: (lambda n: 1, lambda n: n - 1, "Spiegelung: alle Platten tragen dieselben Daten"),
    5: (lambda n: n - 1, lambda n: 1, "verteilte Parität: eine Platte Kapazität geht für die Parität drauf"),
    6: (lambda n: n - 2, lambda n: 2, "doppelte Parität: zwei Platten Kapazität gehen für die Parität drauf"),
    10: (lambda n: n // 2, lambda n: 1, "Spiegelpaare, darüber Striping: die Hälfte ist Spiegel. Sicher verkraftet wird "
         "nur ein Ausfall, denn fallen beide Platten eines Paares aus, sind die Daten weg"),
}
PLATTEN = {0: range(2, 7), 1: [2], 5: range(3, 9), 6: range(4, 9), 10: [4, 6, 8]}
GROESSEN = [1, 2, 4, 6, 8, 10, 12, 16, 18, 20]


@art("raid", "RAID", "Strom & Hardware", "Nutzkapazität und verkraftbare Plattenausfälle für RAID 0, 1, 5, 6 und 10",
     ("RAID", "Festplattenverbund"), formeln=FORMELN["raid"])
def raid(rng):
    return rng.choice([_kapazitaet, _plattenzahl, _gemischt])(rng)


def _kapazitaet(rng):
    level = rng.choice(list(RAID))
    n, tb = rng.choice(list(PLATTEN[level])), rng.choice(GROESSEN)
    nutz, ausfall, erklaerung = RAID[level]
    frage = (f"Für den Dateiserver der {rng.choice(FIRMEN)} wird ein **RAID {level}** aus **{n} Festplatten** mit je **{tb} TB** "
             "eingerichtet.\n\nBerechnen Sie die Nutzkapazität und die Speichereffizienz (Nutzkapazität im Verhältnis zur "
             "Gesamtkapazität), und geben Sie an, wie viele Platten im ungünstigsten Fall ausfallen dürfen, ohne dass Daten verloren gehen.")
    weg = schritte(
        f"RAID {level}: {erklaerung}",
        f"Nutzkapazität: {nutz(n)} · {tb} TB = **{de(nutz(n) * tb)} TB**",
        f"Effizienz: {de(nutz(n) * tb)} TB : {de(n * tb)} TB = **{de(nutz(n) / n * 100, 1)} %**",
        f"Verkraftbare Ausfälle: **{ausfall(n)}**",
    )
    felder = [Feld("nutz", "Nutzkapazität", nutz(n) * tb, "TB"), Feld("effizienz", "Speichereffizienz", nutz(n) / n * 100, "%", stellen=1),
              Feld("ausfall", "Verkraftbare Plattenausfälle", ausfall(n), stellen=0)]
    return Aufgabe(frage, felder, weg, titel=f"RAID {level}")


def _plattenzahl(rng):
    while True:
        bedarf, tb = rng.choice([8, 12, 16, 18, 20, 24, 30, 36, 40, 48]), rng.choice([2, 4, 6, 8, 10, 12])
        daten = math.ceil(bedarf / tb)
        if 2 <= daten <= 6:
            break
    frage = (f"Die {rng.choice(FIRMEN)} braucht für ihre Datensicherung mindestens **{bedarf} TB** Nutzkapazität und verwendet "
             f"Festplatten mit je **{tb} TB**.\n\nWie viele Platten sind mindestens nötig bei RAID 5, bei RAID 6 und bei RAID 10?")
    weg = schritte(
        f"Platten für die Daten: {bedarf} TB : {tb} TB = {de(bedarf / tb)} → aufrunden: {daten}",
        f"RAID 5: eine Platte für die Parität dazu → {daten} + 1 = **{daten + 1}**",
        f"RAID 6: zwei Platten für die Parität dazu → {daten} + 2 = **{daten + 2}**",
        f"RAID 10: jede Datenplatte wird gespiegelt → {daten} · 2 = **{daten * 2}**",
    )
    felder = [Feld("raid5", "RAID 5", daten + 1, "Platten", stellen=0), Feld("raid6", "RAID 6", daten + 2, "Platten", stellen=0),
              Feld("raid10", "RAID 10", daten * 2, "Platten", stellen=0)]
    return Aufgabe(frage, felder, weg, titel="Wie viele Platten?")


def _gemischt(rng):
    level = rng.choice([0, 1, 5])
    n = 2 if level == 1 else rng.randint(3, 5)
    while True:
        platten = sorted((rng.choice([2, 4, 6, 8]) for _ in range(n)), reverse=True)
        if len(set(platten)) > 1:
            break
    nutz, _, erklaerung = RAID[level]
    kleinste, brutto = platten[-1], sum(platten)
    frage = (f"Ein Mitarbeiter der {rng.choice(FIRMEN)} baut aus vorhandenen Festplatten ein **RAID {level}**: "
             f"{' + '.join(f'{p} TB' for p in platten)}.\n\nBerechnen Sie die Nutzkapazität und wie viel Speicherplatz ungenutzt bleibt.")
    weg = schritte(
        f"Ein RAID nutzt auf jeder Platte nur so viel, wie die kleinste hat: {kleinste} TB",
        f"RAID {level}: {erklaerung} → {nutz(n)} · {kleinste} TB = **{de(nutz(n) * kleinste)} TB**",
        f"Ungenutzt: {brutto} TB gesamt − {n} · {kleinste} TB = **{de(brutto - n * kleinste)} TB**",
    )
    felder = [Feld("nutz", "Nutzkapazität", nutz(n) * kleinste, "TB"), Feld("frei", "Ungenutzt", brutto - n * kleinste, "TB")]
    return Aufgabe(frage, felder, weg, titel="Platten verschiedener Größe")


# --- Verfügbarkeit ------------------------------------------------------------

def _prozent(v: float, stellen: int = 3) -> str:
    return f"{de(v * 100, stellen)} %"


@art("verfuegbarkeit", "Verfügbarkeit", "Strom & Hardware", "Ausfallzeit aus Prozent, seriell und redundant, MTBF und MTTR",
     ("Verfügbarkeit", "Ausfallsicherheit", "Ausfallwahrscheinlichkeit", "MTBF", "Redundanz"), formeln=FORMELN["verfuegbarkeit"])
def verfuegbarkeit(rng):
    return rng.choice([_ausfallzeit, _sla, _system, _mtbf])(rng)


def _ausfallzeit(rng):
    v = rng.choice([0.99, 0.995, 0.998, 0.999, 0.9995, 0.9999])
    jahr, monat = (1 - v) * 8760, (1 - v) * 43200
    frage = (f"Der Hoster der {rng.choice(FIRMEN)} garantiert für den Webserver eine Verfügbarkeit von **{_prozent(v, 2)}**.\n\n"
             "Wie lange darf der Server höchstens ausfallen: in Stunden pro Jahr (365 Tage) und in Minuten pro Monat (30 Tage)?")
    weg = schritte(f"Erlaubter Ausfall: 100 % − {_prozent(v, 2)} = {_prozent(1 - v, 2)} = {de(1 - v, 4)}",
                   f"Jahr: {de(1 - v, 4)} · 8.760 h = **{de(jahr)} h**",
                   f"Monat: {de(1 - v, 4)} · 43.200 min = **{de(monat, 1)} min**")
    felder = [Feld("jahr", "Ausfall pro Jahr", jahr, "h"), Feld("monat", "Ausfall pro Monat", monat, "min", stellen=1)]
    return Aufgabe(frage, felder, weg, toleranz=0.002, titel="Ausfallzeit aus Prozent")


def _sla(rng):
    while True:
        stunden = rng.choice([1, 2, 4, 6, 8, 10, 12, 24])
        noetig = 1 - stunden / 8760
        angebot = rng.choice([0.995, 0.998, 0.999, 0.9995, 0.9999])
        if abs(angebot - noetig) > 0.00005:
            break
    reicht = "Ja" if angebot > noetig else "Nein"
    frage = (f"Das Warenwirtschaftssystem der {rng.choice(FIRMEN)} darf im Jahr (365 Tage) höchstens **{stunden} "
             f"{'Stunde' if stunden == 1 else 'Stunden'}** ausfallen. Ein Rechenzentrum bietet ein SLA mit **{_prozent(angebot, 2)}** "
             "Verfügbarkeit an.\n\nWelche Verfügbarkeit ist mindestens nötig (drei Nachkommastellen), und reicht das Angebot?")
    weg = schritte(f"Nötig: 1 − {stunden} h : 8.760 h = {de(noetig, 6)} = **{_prozent(noetig)}**",
                   f"Angebot {_prozent(angebot, 2)} {'>' if reicht == 'Ja' else '<'} {_prozent(noetig)} → **{reicht}**")
    felder = [Feld("noetig", "Nötige Verfügbarkeit", noetig * 100, "%", stellen=3),
              Feld("reicht", "Reicht das Angebot?", reicht, typ="text", optionen=["Ja", "Nein"])]
    return Aufgabe(frage, felder, weg, toleranz=0.00001, titel="Nötige Verfügbarkeit")


def _system(rng):
    router, firewall, storage = rng.choice([0.995, 0.998, 0.999]), rng.choice([0.998, 0.999, 0.9995]), rng.choice([0.995, 0.998, 0.999])
    server, anzahl = rng.choice([0.95, 0.97, 0.98, 0.99]), rng.choice([2, 2, 3])
    cluster = 1 - (1 - server) ** anzahl
    gesamt = router * firewall * cluster * storage
    frage = (f"Ein Dienst der {rng.choice(FIRMEN)} ist nur erreichbar, wenn Router, Firewall, der Server-Verbund und das Storage "
             f"laufen (in Reihe). Der Server-Verbund besteht aus **{anzahl} redundanten Servern**; einer reicht.\n\n"
             f"- Router: {_prozent(router, 2)}\n- Firewall: {_prozent(firewall, 2)}\n- je Server: {_prozent(server, 2)}\n"
             f"- Storage: {_prozent(storage, 2)}\n\nBerechnen Sie die Verfügbarkeit des Server-Verbunds und des gesamten Dienstes "
             "(in Prozent, drei Nachkommastellen).")
    weg = schritte(f"Server-Verbund parallel: 1 − (1 − {de(server, 4)}){'²' if anzahl == 2 else '³'} = 1 − {de(1 - server, 4)}"
                   f"{'²' if anzahl == 2 else '³'} = **{_prozent(cluster)}**",
                   f"Gesamt in Reihe: {de(router, 4)} · {de(firewall, 4)} · {de(cluster, 6)} · {de(storage, 4)} = **{_prozent(gesamt)}**",
                   "In Reihe sinkt die Verfügbarkeit mit jedem Glied, Redundanz hebt sie an.")
    felder = [Feld("cluster", "Server-Verbund", cluster * 100, "%", stellen=3), Feld("gesamt", "Gesamter Dienst", gesamt * 100, "%", stellen=3)]
    return Aufgabe(frage, felder, weg, toleranz=0.00001, titel="Seriell und redundant")


def _mtbf(rng):
    mtbf, mttr = rng.choice([2000, 4000, 5000, 8760, 10000, 20000]), rng.choice([2, 4, 6, 8, 12, 24])
    v = mtbf / (mtbf + mttr)
    frage = (f"Laut Datenblatt hat ein Switch der {rng.choice(FIRMEN)} eine MTBF von **{de(mtbf)} Stunden**; eine Reparatur dauert "
             f"im Mittel (MTTR) **{mttr} Stunden**.\n\nBerechnen Sie die Verfügbarkeit in Prozent (drei Nachkommastellen) und die zu "
             "erwartende Ausfallzeit pro Jahr (365 Tage) in Stunden.")
    weg = schritte(f"V = MTBF : (MTBF + MTTR) = {de(mtbf)} : {de(mtbf + mttr)} = {de(v, 6)} = **{_prozent(v)}**",
                   f"Ausfall pro Jahr: (1 − {de(v, 6)}) · 8.760 h = **{de((1 - v) * 8760)} h**")
    felder = [Feld("v", "Verfügbarkeit", v * 100, "%", stellen=3), Feld("ausfall", "Ausfall pro Jahr", (1 - v) * 8760, "h")]
    return Aufgabe(frage, felder, weg, toleranz=0.002, titel="MTBF und MTTR")
