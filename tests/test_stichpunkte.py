"""Stichpunkt-Abgleich für Freitext-Antworten (erfundene Aufgaben und Musterlösungen)."""

import re

from saku.lernen import stichpunkte as sp

VPN = "Die Demo GmbH bindet ihren Außendienst an. Nennen Sie zwei Vorteile eines VPN."
VPN_LOESUNG = """**Lösungshinweis**

Mögliche Antworten:
- Die Verbindung wird verschlüsselt (Vertraulichkeit)
- Zugriff auf interne Ressourcen von unterwegs
- Kostengünstiger als eine Standleitung
- Authentifizierung der Gegenstelle (je 1 Punkt)"""


def test_zerlegen_aufzaehlung_tabelle_fliesstext():
    assert sp.zerlegen(VPN_LOESUNG) == ["Die Verbindung wird verschlüsselt (Vertraulichkeit)", "Zugriff auf interne Ressourcen von unterwegs",
                                        "Kostengünstiger als eine Standleitung", "Authentifizierung der Gegenstelle"]
    assert sp.zerlegen("1. Vollsicherung\n2) Differenzielle Sicherung\na) Inkrementelle Sicherung") == \
        ["Vollsicherung", "Differenzielle Sicherung", "Inkrementelle Sicherung"]
    tabelle = "| Merkmal | TCP | UDP |\n|---|---|---|\n| Verbindung | verbindungsorientiert | verbindungslos |\n| Quittung | ja | nein |"
    assert sp.zerlegen(tabelle) == ["Verbindung – verbindungsorientiert – verbindungslos", "Quittung – ja – nein"]
    assert sp.zerlegen("Ein Router verbindet Netze, z. B. LAN und WAN. Er arbeitet auf Schicht 3.") == \
        ["Ein Router verbindet Netze, z.B. LAN und WAN.", "Er arbeitet auf Schicht 3."]
    assert sp.zerlegen("Beispiele:\n- z. B. Firewall\n- Virenscanner") == ["Firewall", "Virenscanner"]
    assert sp.zerlegen("\n".join(f"- Punkt Nummer {i} mit Inhalt" for i in range(15)))[-1].endswith("9 mit Inhalt")  # höchstens 10
    assert sp.zerlegen("") == [] and sp.zerlegen("Lösungshinweis:") == []
    # nur ein Spiegelstrich ist keine Aufzählung, der Strich gehört trotzdem nicht in den Punkt
    assert sp.zerlegen("Lösungshinweis:\n- Die Verbindung wird verschlüsselt") == ["Die Verbindung wird verschlüsselt"]


def test_nennen_sie_zwei_zaehlt_gegen_zwei():
    r = sp.abgleichen("Verschlüsselung der Daten, außerdem günstiger als eine Standleitung", VPN_LOESUNG, VPN)
    assert r["verlangt"] == 2 and r["ziel"] == 2 and r["erkannt"] == 2 and r["vorschlag"] == 3
    erkannt = [p["text"] for p in r["punkte"] if p["erkannt"]]
    assert erkannt == ["Die Verbindung wird verschlüsselt (Vertraulichkeit)", "Kostengünstiger als eine Standleitung"]
    r = sp.abgleichen("Man kann von unterwegs auf Ressourcen zugreifen", VPN_LOESUNG, VPN)
    assert (r["erkannt"], r["ziel"], r["vorschlag"]) == (1, 2, 2)  # 50 %: teilweise
    assert sp.abgleichen("geht schnell", VPN_LOESUNG, VPN)["vorschlag"] == 1
    # eine Zahl vor dem Substantiv in Sätzen mit Operator, nicht beim Berechnen
    assert sp.verlangte_anzahl("Nennen Sie zwei Vorteile und drei Nachteile.") == 5
    assert sp.verlangte_anzahl("Erläutern Sie zwei wesentliche Unterschiede.") == 2
    assert sp.verlangte_anzahl("Berechnen Sie die Kosten für zwei Jahre.") is None and sp.verlangte_anzahl("Erklären Sie RAID 5.") is None


def test_ohne_anzahl_zaehlt_gegen_alle_punkte():
    loesung = "- Vollsicherung\n- Differenzielle Sicherung\n- Inkrementelle Sicherung"
    r = sp.abgleichen("Vollsicherung und inkrementelle", loesung, "Beschreiben Sie die Arten der Datensicherung.")
    assert (r["erkannt"], r["ziel"], r["vorschlag"]) == (2, 3, 2)


def test_woerter_aus_der_frage_zaehlen_nicht():
    aufgabe = "Erklären Sie, warum eine Firewall den Datenverkehr filtert."
    loesung = "- Die Firewall filtert den Datenverkehr nach Regeln (Ports, Adressen)"
    r = sp.abgleichen("Eine Firewall filtert den Datenverkehr.", loesung, aufgabe)  # nur abgeschrieben
    assert not r["punkte"][0]["erkannt"] and r["punkte"][0]["woerter"] == ["Regeln"]
    assert sp.abgleichen("nach festgelegten Regeln", loesung, aufgabe)["punkte"][0]["erkannt"]
    # besteht ein Punkt nur aus Wörtern der Frage, lässt er sich nicht prüfen und zählt nicht
    assert sp.abgleichen("irgendwas", "- Firewall filtert Datenverkehr", aufgabe) is None


def test_stamm_abkuerzungen_und_komposita():
    loesung = "- Daten werden verschlüsselt übertragen\n- Zugang per VPN\n- Client-Server-Modell"
    r = sp.abgleichen("Verschlüsselung", loesung, "Nennen Sie Maßnahmen.")
    assert [p["erkannt"] for p in r["punkte"]] == [False, False, False]  # 1 von 3 Wörtern reicht nicht
    r = sp.abgleichen("Übertragung mit Verschlüsselung", loesung, "Nennen Sie Maßnahmen.")
    assert r["punkte"][0]["erkannt"] and r["punkte"][0]["treffer"] == ["verschlüsselt", "übertragen"]
    assert sp.abgleichen("über vpn", loesung, "Nennen Sie Maßnahmen.")["punkte"][1]["erkannt"]  # Abkürzung reicht allein
    assert sp.abgleichen("Client und Server", loesung, "Nennen Sie Maßnahmen.")["punkte"][2]["erkannt"]  # Teile des Kompositums
    assert not sp._vorkommt("tcp/ip", sp._menge("nur TCP")) and sp._vorkommt("tcp/ip", sp._menge("TCP und IP"))
    assert not sp._gleich("daten", "datenbank") and sp._gleich("redundant", "redundanz") and sp._gleich("firewall", "firewalls")
    # Zahlen: 7,4 ist ein Fachbegriff, eine einzelne Ziffer nicht
    loesung = "Anbieter B erreicht 7,4 Punkte und wird gewählt."
    assert sp.abgleichen("7,4 Punkte", loesung, "Führen Sie eine Nutzwertanalyse durch.")["erkannt"] == 1
    assert sp.abgleichen("es sind 4", loesung, "Führen Sie eine Nutzwertanalyse durch.")["erkannt"] == 0


def test_hervorheben_und_leere_faelle():
    r = sp.abgleichen("Verschlüsselung", VPN_LOESUNG, VPN)
    assert ("verschlüsselt", True) in r["punkte"][0]["teile"] and "".join(t for t, _ in r["punkte"][0]["teile"]) == r["punkte"][0]["text"]
    assert sp._hervorheben("Netzwerk und Netz", ["Netz"]) == [("Netzwerk und ", False), ("Netz", True)]  # nur ganze Wörter
    assert sp.abgleichen("", VPN_LOESUNG, VPN) is None and sp.abgleichen("   ", VPN_LOESUNG, VPN) is None
    assert sp.abgleichen("etwas", "", VPN) is None and sp.abgleichen("etwas", "Lösungshinweis:", VPN) is None


def test_ueben_zeigt_abgleich_bei_freitext(client, con):
    t_id = con.execute("SELECT id FROM teilaufgabe WHERE text LIKE '%Whitebox%'").fetchone()[0]
    htmx = {"HX-Request": "true"}
    html = client.get(f"/keiko/{t_id}/loesung", query_string={"antwort": "Anweisungsüberdeckung und Pfadüberdeckung"}, headers=htmx)
    html = " ".join(html.get_data(as_text=True).split())
    # „Nennen Sie zwei …“, die Lösung nennt beide in einem Satz: 1 von 2 erkannt, Vorschlag teilweise
    assert "Stichpunkte der Musterlösung: 1 von 2 erkannt" in html and "Teilweise (2)" in html
    assert 'data-stichpunkt-vorschlag="2"' in html and "<mark>Anweisungsüberdeckung</mark>" in html
    assert html.index("stichpunkte") < html.index("Lösungshinweis</p>")  # über der Lösung
    assert "stichpunkte" not in client.get(f"/keiko/{t_id}/loesung", headers=htmx).get_data(as_text=True)  # ohne eigene Antwort
    con.execute("UPDATE teilaufgabe SET antwort = ? WHERE id = ?",
                ('{"art": "einfach", "optionen": [], "ziele": [], "richtig": ["1"], "einheit": "", "vorlage": ""}', t_id))
    con.commit()
    html = client.get(f"/keiko/{t_id}/loesung", query_string={"antwort": "Anweisungsüberdeckung"}, headers=htmx).get_data(as_text=True)
    assert "stichpunkte" not in html  # nur bei Freitext
    assert re.search(r'data-taste="2"', html)  # die Bewertung bleibt wie gehabt


def _whitebox(con) -> int:
    return con.execute("SELECT id FROM teilaufgabe WHERE text LIKE '%Whitebox%'").fetchone()[0]


def test_fuer_teilaufgabe_mit_punktevorschlag(con):
    from saku.lernen import karten
    t = karten.lade(con, [_whitebox(con)])[0]  # 6 Punkte, „Nennen Sie zwei …“
    a = sp.fuer_teilaufgabe(t, "Anweisungsüberdeckung und Pfadüberdeckung")
    assert (a["erkannt"], a["ziel"], a["punkte_vorschlag"]) == (1, 2, 3.0)
    assert sp.fuer_teilaufgabe(t, "Anweisungsüberdeckung, Zweigüberdeckung")["punkte_vorschlag"] == 6
    assert sp.fuer_teilaufgabe(t, "") is None
    t["antwort"] = {"art": "einfach", "optionen": [], "ziele": [], "richtig": ["1"], "einheit": "", "vorlage": ""}
    assert sp.fuer_teilaufgabe(t, "Anweisungsüberdeckung") is None  # feste Formate prüft antwort.vorschlag


def test_simulation_zeigt_hinweis_ohne_vorzubelegen(client, con):
    url = client.post("/shiken/neu", data={"bereich": "Entwicklung und Umsetzung von Algorithmen"}).headers["Location"]
    sim_id = int(url.rsplit("/", 1)[1])
    t_id = _whitebox(con)
    con.execute("DELETE FROM simulation_teilaufgabe")
    con.execute("INSERT INTO simulation_teilaufgabe (simulation_id, teilaufgabe_id, position, antwort) VALUES (?, ?, 1, ?)",
                (sim_id, t_id, "Anweisungsüberdeckung und Pfadüberdeckung"))
    con.execute("UPDATE simulation SET beendet_am = datetime('now') WHERE id = ?", (sim_id,))
    con.commit()
    html = " ".join(client.get(f"/shiken/{sim_id}/auswertung").get_data(as_text=True).split())
    assert "Stichpunkte: 1 von 2 erkannt · Vorschlag 3 P." in html and "<mark>Anweisungsüberdeckung</mark>" in html
    assert not re.search(rf'id="punkte-{t_id}"[^>]*value=', html)  # Freitext: Punkte vergibt der Nutzer


def test_mini_test_vergleicht_freitext(client, con):
    t_id = _whitebox(con)
    station = con.execute("SELECT id FROM station WHERE titel = 'Qualitätssicherung'").fetchone()[0]
    con.executemany("INSERT INTO stationstest (station_id, bestanden) VALUES (?, 1)", [(s,) for s in range(1, station)])
    con.commit()
    html = client.get(f"/michi/{station}/test").get_data(as_text=True)
    assert f'name="antwort-{t_id}"' in html and "Mit der Lösung vergleichen" in html
    htmx = {"HX-Request": "true"}
    teil = client.post(f"/michi/{station}/test/{t_id}/pruefen", data={f"antwort-{t_id}": "Anweisungsüberdeckung und Pfadüberdeckung"},
                       headers=htmx).get_data(as_text=True)
    teil = " ".join(teil.split())
    assert "Stichpunkte: 1 von 2 erkannt · Vorschlag 3 P." in teil and "Anweisungsüberdeckung und Pfadüberdeckung" in teil
    assert 'class="michi-loesung" open' in teil and not re.search(rf'id="punkte-{t_id}"[^>]*value=', teil)
    assert "<summary>Lösung</summary>" in teil
    leer = client.post(f"/michi/{station}/test/{t_id}/pruefen", data={}, headers=htmx).get_data(as_text=True)
    assert "Stichpunkte" not in leer and 'class="michi-loesung" open' in leer  # ohne Antwort nur die Lösung
