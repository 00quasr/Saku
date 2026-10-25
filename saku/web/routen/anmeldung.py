"""Anmeldung mit Passwort, nur wenn SAKU_PASSWORT gesetzt ist (Saku im Netz, docs/DEPLOY.md); lokal leitet sie nur weiter."""

import hashlib
import hmac
import threading
import time

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

bp = Blueprint("anmeldung", __name__)

VERSUCHE = 5  # Fehlversuche je IP, danach gesperrt …
SPERRE = 15 * 60  # … für so viele Sekunden ab dem ersten
VERZOEGERUNG = 1.0  # Sekunden nach jedem Fehlversuch
_fehlversuche: dict[str, list[float]] = {}  # IP → Zeitpunkte (monotonic), nur im Speicher: ein Neustart vergisst sie
_sperre = threading.Lock()


def _versuch(ip: str) -> bool:
    """Zählt den Versuch dieser IP schon vor dem Vergleich, sonst kämen gleichzeitige Anfragen alle an der Sperre vorbei;
    False, wenn sie gesperrt ist. Abgelaufenes fällt dabei für alle IPs weg."""
    jetzt = time.monotonic()
    with _sperre:
        for schluessel in list(_fehlversuche):
            if not (frisch := [t for t in _fehlversuche[schluessel] if jetzt - t < SPERRE]):
                del _fehlversuche[schluessel]
            else:
                _fehlversuche[schluessel] = frisch
        if len(versuche := _fehlversuche.setdefault(ip, [])) >= VERSUCHE:
            return False
        versuche.append(jetzt)
        return True


def _gleich(eingabe: str, passwort: str) -> bool:
    # in konstanter Zeit, über die Hashes auch unabhängig von der Länge
    return hmac.compare_digest(hashlib.sha256(eingabe.encode()).digest(), hashlib.sha256(passwort.encode()).digest())


@bp.route("/anmelden", methods=["GET", "POST"])
def anmelden():
    passwort = current_app.config["PASSWORT"]
    if not passwort or session.get("angemeldet"):
        return redirect(url_for("heute.index"))
    if request.method == "GET":
        return render_template("anmelden.html")
    ip = request.remote_addr or "?"
    if not _versuch(ip):
        return render_template("anmelden.html", fehler="Zu viele Versuche. In einer Viertelstunde geht es wieder."), 429
    if _gleich(request.form.get("passwort", ""), passwort):
        with _sperre:
            _fehlversuche.pop(ip, None)
        session.clear()
        session.permanent = True  # 30 Tage (PERMANENT_SESSION_LIFETIME), sonst endete sie mit dem Browser
        session["angemeldet"] = True
        return redirect(url_for("heute.index"))
    time.sleep(VERZOEGERUNG)
    return render_template("anmelden.html", fehler="Das Passwort stimmt nicht."), 401


@bp.post("/abmelden")
def abmelden():
    session.clear()
    return redirect(url_for("anmeldung.anmelden"))
