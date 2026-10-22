"""Ausbaustufe: zahlensystem_umrechnen und die Tool-Use-Schleife (API gemockt)."""

import json
import re
from contextlib import contextmanager
from types import SimpleNamespace as NS

import pytest

from saku.sensei import client as ki
from saku.sensei import werkzeuge


@pytest.mark.parametrize("zahl, von, dezimal", [("FF", "hexadezimal", "255"), ("1011", "binaer", "11"),
                                               ("0x1f", "hexadezimal", "31"), ("1 0000", "binaer", "16"), ("42", "dezimal", "42")])
def test_umrechnen(zahl, von, dezimal):
    assert werkzeuge.zahlensystem_umrechnen(zahl, von)["dezimal"] == dezimal
    assert werkzeuge.zahlensystem_umrechnen("255", "dezimal") == {"binaer": "11111111", "dezimal": "255", "hexadezimal": "FF"}


def test_fehler_gehen_an_sensei_zurueck():
    for eingabe in ({"zahl": "12", "von": "binaer"}, {"zahl": "1", "von": "oktal"}, {"zahl": "1"}):
        r = werkzeuge.ergebnis(NS(id="w1", name="zahlensystem_umrechnen", input=eingabe))
        assert r["is_error"] is True and r["tool_use_id"] == "w1"
    assert werkzeuge.ergebnis(NS(id="w2", name="raten", input={}))["is_error"] is True


def test_schleife_rechnet_und_antwortet(con, monkeypatch):
    werkzeug = NS(type="tool_use", id="w1", name="zahlensystem_umrechnen", input={"zahl": "FF", "von": "hexadezimal"})
    runden = [(["Ich rechne kurz."], NS(stop_reason="tool_use", content=[NS(type="text", text="Ich rechne kurz."), werkzeug])),
              (["FF ist 255."], NS(stop_reason="end_turn", content=[NS(type="text", text="FF ist 255.")]))]
    aufrufe = []

    @contextmanager
    def stream(**parameter):
        aufrufe.append({**parameter, "messages": list(parameter["messages"])})
        text, final = runden[len(aufrufe) - 1]
        final.usage = NS(input_tokens=10, cache_read_input_tokens=5, cache_creation_input_tokens=None, output_tokens=7)
        yield NS(text_stream=iter(text), get_final_message=lambda: final)

    monkeypatch.setattr(ki, "verfuegbar", lambda: True)
    monkeypatch.setattr(ki, "_anfrage", lambda *a: (NS(stream=stream), {"model": "demo"}))
    text = "".join(werkzeuge.stream(con, "tutor", "sys", [{"role": "user", "content": "Was ist FF dezimal?"}]))

    assert text == "Ich rechne kurz.\n\nFF ist 255."
    assert all(a["tools"] == [werkzeuge.ZAHLENSYSTEM] for a in aufrufe)
    zweite = aufrufe[1]["messages"]
    assert [n["role"] for n in zweite] == ["user", "assistant", "user"]
    ergebnis = zweite[2]["content"][0]
    assert ergebnis["tool_use_id"] == "w1" and json.loads(ergebnis["content"])["dezimal"] == "255"
    protokoll = con.execute("SELECT zweck, tokens_ein, tokens_aus FROM ki_aufruf").fetchall()
    assert [tuple(z) for z in protokoll] == [("tutor", 15, 7), ("tutor", 15, 7)]


def test_rechenaufgaben_nutzen_die_schleife(app, client, con, monkeypatch):
    app.config["SENSEI_BEREIT"] = True
    benutzt = []
    monkeypatch.setattr(werkzeuge, "stream", lambda *a, **k: benutzt.append("werkzeuge") or iter(["ok"]))
    monkeypatch.setattr(ki, "stream", lambda *a, **k: benutzt.append("client") or iter(["ok"]))
    con.execute("UPDATE teilaufgabe SET typ = 'berechnen' WHERE id = 2")
    con.commit()
    for tid in (2, 1):
        blase = client.post("/sensei/erklaeren", data={"teilaufgabe": tid}).get_data(as_text=True)
        client.get("/sensei/stream/" + re.search(r"/sensei/stream/([0-9a-f]+)", blase).group(1)).get_data()
    assert benutzt == ["werkzeuge", "client"]
