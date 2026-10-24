"""Projekt: Netzplan mit Vorwärts- und Rückwärtsrechnung, Puffern und kritischem Pfad."""

from saku.lernen.rechnen.basis import FIRMEN, Aufgabe, Feld, art, schritte, tabelle

# Formeln und Merksätze je Art: Formelsammlung und Karte zeigen sie nach dem Rechenweg
FORMELN = {
    "netzplan": """- Vorwärts: FAZ = größter FEZ der Vorgänger (Start 0), FEZ = FAZ + Dauer
- Projektdauer = FEZ des letzten Vorgangs
- Rückwärts: SEZ = kleinster SAZ der Nachfolger (Ende = Projektdauer), SAZ = SEZ − Dauer
- Gesamtpuffer GP = SAZ − FAZ = SEZ − FEZ
- Freier Puffer FP = kleinster FAZ der Nachfolger − FEZ
- Kritischer Pfad: alle Vorgänge mit GP = 0, vom Start bis zum Ende
- *Typische Fehler:* alle Dauern addiert statt den längsten Weg genommen, FAZ aus dem kleinsten FEZ, Gesamt- und freien Puffer verwechselt, SEZ − FAZ statt SAZ − FAZ

*Beispiel:* A (3 Tage) → B (2 Tage): FAZ B = FEZ A = 3, FEZ B = 5""",
}


TAETIGKEITEN = ["Ist-Analyse", "Soll-Konzept", "Angebote einholen", "Hardware bestellen", "Netzwerk verkabeln", "Server einrichten",
                "Clients installieren", "Software anpassen", "Daten übernehmen", "Tests", "Schulung", "Dokumentation"]
PROJEKTE = ["die Einführung eines Ticketsystems", "den Umzug des Serverraums", "die Erneuerung der Arbeitsplatzrechner",
            "die Einführung einer Warenwirtschaft", "den Aufbau eines Gäste-WLANs"]


def plan(rng) -> list[dict]:
    """Vorgänge A, B, … mit Dauer und Vorgängern (Indizes); A beginnt, der letzte schließt alle offenen Enden ab."""
    n = rng.randint(5, 8)
    mitte = sorted(rng.sample(range(1, len(TAETIGKEITEN)), n - 2))
    namen = [TAETIGKEITEN[0], *(TAETIGKEITEN[i] for i in mitte), rng.choice(["Abnahme", "Übergabe", "Inbetriebnahme"])]
    vorgaenge = []
    for i in range(n):
        if i == 0:
            vor = []
        elif i == n - 1:
            vor = [v for v in range(i) if not any(v in w["vor"] for w in vorgaenge)]
        else:
            moeglich = list(range(max(0, i - 3), i))
            vor = sorted(rng.sample(moeglich, min(len(moeglich), rng.choice([1, 1, 2]))))
        vorgaenge.append({"id": "ABCDEFGH"[i], "name": namen[i], "dauer": rng.randint(1, 8), "vor": vor})
    return vorgaenge


def berechnen(vorgaenge: list[dict]) -> int:
    """Trägt FAZ, FEZ, SAZ, SEZ, GP und FP ein (Vorgänger stehen immer vorher); gibt die Projektdauer zurück."""
    for v in vorgaenge:
        v["faz"] = max((vorgaenge[i]["fez"] for i in v["vor"]), default=0)
        v["fez"] = v["faz"] + v["dauer"]
    ende = max(v["fez"] for v in vorgaenge)
    for i in reversed(range(len(vorgaenge))):
        v = vorgaenge[i]
        nach = [w for w in vorgaenge if i in w["vor"]]
        v["sez"] = min((w["saz"] for w in nach), default=ende)
        v["saz"] = v["sez"] - v["dauer"]
        v["gp"] = v["saz"] - v["faz"]
        v["fp"] = min((w["faz"] for w in nach), default=ende) - v["fez"]
    return ende


def kritische_pfade(vorgaenge: list[dict]) -> list[str]:
    """Alle Wege vom Start zum Ende über Vorgänge ohne Puffer, die lückenlos aneinander anschließen."""
    def weiter(i: int) -> list[str]:
        v = vorgaenge[i]
        nach = [j for j, w in enumerate(vorgaenge) if i in w["vor"] and w["gp"] == 0 and w["faz"] == v["fez"]]
        return [v["id"]] if not nach else [v["id"] + "-" + rest for j in nach for rest in weiter(j)]
    return [p for p in weiter(0) if p.endswith(vorgaenge[-1]["id"])] if vorgaenge[0]["gp"] == 0 else []


@art("netzplan", "Netzplan", "Projekt", "Vorgänge mit Dauer und Vorgängern: Projektdauer, Puffer, kritischer Pfad",
     ("Netzplan", "Gantt", "Kritischer Pfad", "Projektplanung", "Zeitplanung"), formeln=FORMELN["netzplan"])
def netzplan(rng):
    while True:
        vorgaenge = plan(rng)
        dauer = berechnen(vorgaenge)
        pfade = kritische_pfade(vorgaenge)
        mit_puffer = [v for v in vorgaenge if v["gp"] > 0]
        if len(pfade) == 1 and mit_puffer:
            break
    x = rng.choice(mit_puffer)
    pfad = pfade[0]
    projektdauer = Feld("dauer", "Projektdauer", dauer, "Tage", stellen=0, typisch=(
        (sum(v["dauer"] for v in vorgaenge), "Du hast alle Dauern addiert; parallele Vorgänge laufen gleichzeitig, es zählt der längste Weg."),))
    gp = Feld("gp", f"Gesamtpuffer {x['id']}", x["gp"], "Tage", stellen=0, typisch=(
        (-x["gp"], "Du hast FAZ und SAZ vertauscht; GP = SAZ − FAZ."),
        (x["fp"], "Das ist der freie Puffer; der Gesamtpuffer ist SAZ − FAZ."),
        (x["gp"] + x["dauer"], "Du hast SEZ − FAZ gerechnet, da steckt die Dauer mit drin; GP = SAZ − FAZ.")))
    variante = rng.choice(["puffer", "zeiten", "frei"])
    if variante == "puffer":
        felder = [projektdauer, gp, Feld("pfad", "Kritischer Pfad", pfad, typ="pfad")]
        auftrag = f"die Projektdauer, den Gesamtpuffer von Vorgang {x['id']} und den kritischen Pfad (z. B. „A-B-D“)"
    elif variante == "zeiten":
        # FAZ aus dem kleinsten FEZ der Vorgänger, SEZ aus dem größten SAZ der Nachfolger
        faz = min((vorgaenge[i]["fez"] for i in x["vor"]), default=0)
        sez = max((w["saz"] for w in vorgaenge if vorgaenge.index(x) in w["vor"]), default=dauer)
        frueh = "Ein Vorgang beginnt erst, wenn alle Vorgänger fertig sind: FAZ = größter FEZ der Vorgänger."
        spaet = "SEZ = kleinster SAZ der Nachfolger, nicht der größte: sonst käme ein Nachfolger zu spät."
        typisch = {"faz": [(faz, frueh)], "fez": [(faz + x["dauer"], frueh)], "saz": [(sez - x["dauer"], spaet)], "sez": [(sez, spaet)]}
        felder = [Feld(k, f"{k.upper()} {x['id']}", x[k], stellen=0, typisch=tuple(typisch[k])) for k in ("faz", "fez", "saz", "sez")]
        felder.append(projektdauer)
        auftrag = f"für Vorgang {x['id']} den frühesten und spätesten Anfangs- und Endzeitpunkt (FAZ, FEZ, SAZ, SEZ) sowie die Projektdauer"
    else:
        felder = [gp, Feld("fp", f"Freier Puffer {x['id']}", x["fp"], "Tage", stellen=0, typisch=(
                      (x["gp"], "Das ist der Gesamtpuffer; der freie Puffer reicht nur bis zum frühesten Start eines Nachfolgers."),
                      (x["fp"] + x["dauer"], "Du hast vom FAZ statt vom FEZ gerechnet; FP = kleinster FAZ der Nachfolger − FEZ."))),
                  Feld("pfad", "Kritischer Pfad", pfad, typ="pfad")]
        auftrag = f"den Gesamtpuffer und den freien Puffer von Vorgang {x['id']} sowie den kritischen Pfad (z. B. „A-B-D“)"
    zeilen = [[v["id"], v["name"], v["dauer"], ", ".join(vorgaenge[i]["id"] for i in v["vor"]) or "–"] for v in vorgaenge]
    frage = (f"Die {rng.choice(FIRMEN)} plant {rng.choice(PROJEKTE)}. Die Vorgänge:\n\n"
             f"{tabelle(['Vorgang', 'Tätigkeit', 'Dauer (Tage)', 'Vorgänger'], zeilen)}\n\n"
             f"Erstellen Sie einen Netzplan (der erste Vorgang beginnt bei FAZ = 0) und ermitteln Sie {auftrag}.")
    weg = schritte(
        "Vorwärts: FAZ = größter FEZ aller Vorgänger (Start 0), FEZ = FAZ + Dauer",
        f"Projektdauer = FEZ des letzten Vorgangs = **{dauer} Tage**",
        "Rückwärts: SEZ = kleinster SAZ aller Nachfolger (am Ende die Projektdauer), SAZ = SEZ − Dauer",
        "Gesamtpuffer GP = SAZ − FAZ, freier Puffer FP = kleinster FAZ der Nachfolger − FEZ",
        f"Kritischer Pfad: die Vorgänge mit GP = 0 → **{pfad}**",
    )
    werte = [[v["id"], v["dauer"], v["faz"], v["fez"], v["saz"], v["sez"], v["gp"], v["fp"]] for v in vorgaenge]
    return Aufgabe(frage, felder, weg + "\n\n" + tabelle(["Vorgang", "Dauer", "FAZ", "FEZ", "SAZ", "SEZ", "GP", "FP"], werte),
                   titel={"puffer": "Puffer und kritischer Pfad", "zeiten": "FAZ, FEZ, SAZ, SEZ", "frei": "Gesamt- und freier Puffer"}[variante])
