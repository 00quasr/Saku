"""IHK-Operatoren: was eine Aufgabe mit „Nennen Sie …“, „Erläutern Sie …“ usw. verlangt.
Erkannt wird am Aufgabentext, angezeigt als Chip; Sensei bewertet danach (nennen: Stichworte reichen)."""

import re

# Operator → (Anzeige, was verlangt wird); Reihenfolge ungefähr nach Anspruch
OPERATOREN = {
    "nennen": ("Nennen", "Begriffe oder Fakten aufzählen, ohne Erklärung. Stichworte reichen."),
    "angeben": ("Angeben", "Kurz und ohne Begründung hinschreiben, z. B. einen Wert oder eine Bezeichnung."),
    "identifizieren": ("Identifizieren", "Das Gesuchte erkennen und benennen."),
    "zuordnen": ("Zuordnen", "Elemente den passenden Kategorien zuweisen."),
    "beschreiben": ("Beschreiben", "Den Sachverhalt in eigenen Worten und ganzen Sätzen wiedergeben, ohne zu werten."),
    "darstellen": ("Darstellen", "Strukturiert zeigen, oft als Grafik, Tabelle oder Diagramm."),
    "skizzieren": ("Skizzieren", "Grob zeichnen, aber fachlich richtig."),
    "unterscheiden": ("Unterscheiden", "Die Merkmale nennen, in denen sich zwei Dinge unterscheiden."),
    "vergleichen": ("Vergleichen", "Gemeinsamkeiten und Unterschiede nach Kriterien gegenüberstellen."),
    "erklaeren": ("Erklären", "Ursachen und Zusammenhänge so darstellen, dass sie nachvollziehbar sind."),
    "erlaeutern": ("Erläutern", "Beschreiben und mit Beispiel oder Begründung verständlich machen. Ein Stichwort reicht nicht."),
    "begruenden": ("Begründen", "Eine Aussage mit Argumenten stützen: Warum ist das so?"),
    "berechnen": ("Berechnen", "Rechenweg mit Ansatz und Ergebnis samt Einheit angeben."),
    "ermitteln": ("Ermitteln", "Ein Ergebnis aus den Angaben bestimmen, rechnerisch oder logisch, und den Weg zeigen."),
    "ergaenzen": ("Ergänzen", "Vorgegebenes (Tabelle, Code, Diagramm) fachlich richtig vervollständigen."),
    "erstellen": ("Erstellen", "Eigenes Modell, Diagramm, Code oder SQL nach den Vorgaben anfertigen."),
    "entwerfen": ("Entwerfen", "Eine eigene Lösung planen und ausarbeiten, z. B. ein Modell oder einen Algorithmus."),
    "analysieren": ("Analysieren", "Bestandteile und Zusammenhänge herausarbeiten und auswerten."),
    "beurteilen": ("Beurteilen", "Ein eigenes, begründetes Urteil anhand von Kriterien fällen."),
    "bewerten": ("Bewerten", "Ein Werturteil mit Kriterien und Begründung fällen."),
}

# Wortstamm im Aufgabentext → Operator („Stellen Sie … dar“, „Geben Sie … an“, „Ordnen Sie … zu“)
_MUSTER = [
    (r"\bnennen\s+sie\b", "nennen"), (r"\bgeben\s+sie\b[^.?!]{0,120}?\ban\b", "angeben"),
    (r"\bidentifizieren\s+sie\b", "identifizieren"), (r"\bordnen\s+sie\b[^.?!]{0,120}?\bzu\b", "zuordnen"),
    (r"\bbeschreiben\s+sie\b", "beschreiben"), (r"\bstellen\s+sie\b[^.?!]{0,120}?\bdar\b", "darstellen"),
    (r"\bskizzieren\s+sie\b", "skizzieren"), (r"\bunterscheiden\s+sie\b", "unterscheiden"),
    (r"\bvergleichen\s+sie\b", "vergleichen"), (r"\berklären\s+sie\b", "erklaeren"), (r"\berläutern\s+sie\b", "erlaeutern"),
    (r"\bbegründen\s+sie\b", "begruenden"), (r"\bberechnen\s+sie\b", "berechnen"), (r"\bermitteln\s+sie\b", "ermitteln"),
    (r"\b(?:ergänzen|vervollständigen)\s+sie\b", "ergaenzen"), (r"\berstellen\s+sie\b", "erstellen"),
    (r"\bentwerfen\s+sie\b", "entwerfen"), (r"\banalysieren\s+sie\b", "analysieren"),
    (r"\bbeurteilen\s+sie\b", "beurteilen"), (r"\bbewerten\s+sie\b", "bewerten"),
]


def erkennen(text: str | None) -> list[dict]:
    """Operatoren in der Reihenfolge ihres Vorkommens: [{schluessel, name, erklaerung}]."""
    treffer = sorted((m.start(), schluessel) for muster, schluessel in _MUSTER
                     for m in re.finditer(muster, text or "", re.I))
    gesehen = dict.fromkeys(s for _, s in treffer)
    return [{"schluessel": s, "name": OPERATOREN[s][0], "erklaerung": OPERATOREN[s][1]} for s in gesehen]


def fuer_sensei(text: str | None) -> str:
    """Zeile für den Bewertungs-Prompt, leer ohne Operator."""
    ops = erkennen(text)
    return "Operatoren: " + "; ".join(f"{o['name']} ({o['erklaerung']})" for o in ops) if ops else ""
