// Saku: globale Tastenkürzel. Bedienelemente mit data-taste="x" werden per Taste x geklickt.
// Beispiel: <button data-taste=" " hx-get="…">Lösung zeigen</button>
window.saku = {
  oeffne(id) {
    const dialog = document.getElementById(id);
    if (!dialog || dialog.open) return;
    dialog.showModal();
    dialog.querySelector("input, textarea")?.focus();
  },
  sensei() {
    document.body.classList.toggle("sensei-offen");
    document.dispatchEvent(new CustomEvent("sensei:umschalten"));
  },
  // kurze Rückmeldung unten rechts, z. B. „Gespeichert“
  melden(text) {
    const toast = document.getElementById("toast");
    toast.textContent = text;
    toast.classList.add("sichtbar");
    clearTimeout(toast.zeit);
    toast.zeit = setTimeout(() => toast.classList.remove("sichtbar"), 1600);
  },
  // Code-Editor: Tab rückt um vier Leerzeichen ein, Esc verlässt das Feld
  editorTaste(e) {
    const feld = e.target;
    if (e.key === "Escape") return feld.blur();
    if (e.key !== "Tab" || e.shiftKey) return;
    e.preventDefault();
    feld.setRangeText("    ", feld.selectionStart, feld.selectionEnd, "end");
  },
  // Ausgefüllte Tabelle als Markdown ins versteckte Antwortfeld (für Sensei „Prüfen“)
  tabelleAlsText(tabelle) {
    const zeilen = [...tabelle.rows].map((r) => "| " + [...r.cells].map((c) => (c.querySelector("input")?.value ?? c.textContent).trim()).join(" | ") + " |");
    tabelle.closest(".keiko-antwort").querySelector("textarea[name=antwort]").value = zeilen.join("\n");
  },
  // Wissensgraph (force-graph): Hover hebt die Nachbarschaft hervor, Klick öffnet die Notiz, Beschriftung je nach Zoom
  graph(flaeche, start) {
    const daten = JSON.parse(document.getElementById("graph-daten").textContent);
    const notiz = document.getElementById("notiz");
    const token = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
    const f = Object.fromEntries(["washi", "sumi", "sumi-mittel", "linie", "ai", "shu", "beni", "yamabuki", "matcha"].map((n) => [n, token(`--${n}`)]));
    const mischen = (a, b, t) => "#" + [1, 3, 5].map((i) => {
      const x = parseInt(a.slice(i, i + 2), 16), y = parseInt(b.slice(i, i + 2), 16);
      return Math.round(x + (y - x) * t).toString(16).padStart(2, "0");
    }).join("");
    const lernstand = (k) => !k.geuebt ? (k.teilaufgaben ? f["sumi-mittel"] : f.linie)
      : k.beherrschung < 0.5 ? mischen(f.beni, f.yamabuki, k.beherrschung * 2) : mischen(f.yamabuki, f.matcha, (k.beherrschung - 0.5) * 2);
    const farbe = (k) => ({ bereich: f.sumi, lernfeld: f.ai, begriff: f["sumi-mittel"] })[k.art] || lernstand(k);
    const groesst = {};
    daten.knoten.forEach((k) => { groesst[k.art] = Math.max(groesst[k.art] || 1, k.wert || 0); });
    const radius = (k) => ({ bereich: 9, lernfeld: 5, thema: 3 + 5 * Math.sqrt((k.wert || 0) / groesst.thema),
      unterthema: 1.8 + 3 * Math.sqrt((k.wert || 0) / groesst.unterthema), begriff: 1.2 + 2.8 * Math.sqrt((k.wert || 0) / groesst.begriff) })[k.art];
    const abZoom = { bereich: 0, thema: 0.5, lernfeld: 1.1, unterthema: 1.4, begriff: 2.6 };  // ab hier steht der Name da
    const rang = { bereich: 5, thema: 4, lernfeld: 3, unterthema: 2, begriff: 1 };

    const nachbarn = new Map(daten.knoten.map((k) => [k.id, new Set()]));
    daten.kanten.forEach((l) => { nachbarn.get(l.source)?.add(l.target); nachbarn.get(l.target)?.add(l.source); });
    const id = (x) => (typeof x === "object" ? x.id : x);
    let fokus = null, auswahl = start;
    const mitte_ = () => fokus || auswahl;  // Hover geht vor, sonst bleibt die Auswahl hervorgehoben
    const hell = (k) => !mitte_() || k === mitte_() || nachbarn.get(mitte_()).has(k);
    const anFokus = (l) => mitte_() && (id(l.source) === mitte_() || id(l.target) === mitte_());

    const zeigen = new Set(["bereich", "thema", "unterthema", "lernfeld", "begriff"]);
    const sichtbar = () => {
      const knoten = daten.knoten.filter((k) => zeigen.has(k.art)), ids = new Set(knoten.map((k) => k.id));
      return { nodes: knoten, links: daten.kanten.filter((l) => ids.has(id(l.source)) && ids.has(id(l.target))) };
    };

    const g = ForceGraph()(flaeche)
      .width(flaeche.clientWidth).height(flaeche.clientHeight)
      .backgroundColor("rgba(0,0,0,0)")  // zeichnet nur neu, solange die Physik läuft oder der Zeiger sich bewegt
      .graphData(sichtbar())
      .nodeCanvasObject((k, ctx, zoom) => {
        const r = radius(k);
        ctx.globalAlpha = hell(k.id) ? 1 : 0.1;
        ctx.beginPath();
        ctx.arc(k.x, k.y, r, 0, 2 * Math.PI);
        ctx.fillStyle = farbe(k);
        ctx.fill();
        if (k.id === auswahl || daten.pulsieren.includes(k.id)) {
          ctx.lineWidth = 2 / zoom;
          ctx.strokeStyle = f.shu;
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      })
      // Namen nach den Knoten: wichtige zuerst, was einen schon gesetzten Namen verdecken würde, entfällt
      .onRenderFramePost((ctx, zoom) => {
        const nah = mitte_();
        const kandidaten = g.graphData().nodes.filter((k) => (nah ? hell(k.id) && (k.id === nah || zoom >= abZoom[k.art] - 0.6 || rang[k.art] >= 2)
          : k.id === auswahl || zoom >= abZoom[k.art]));
        kandidaten.sort((a, b) => (b.id === nah) - (a.id === nah) || rang[b.art] - rang[a.art] || radius(b) - radius(a));
        const belegt = [];
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.lineJoin = "round";
        for (const k of kandidaten) {
          const groesse = (k.art === "bereich" ? 13 : 11) / zoom;
          ctx.font = `${rang[k.art] >= 4 ? 600 : 400} ${groesse}px Inter, sans-serif`;
          const breite = ctx.measureText(k.name).width, y = k.y + radius(k) + 2 / zoom;
          const box = [k.x - breite / 2 - 2 / zoom, y, k.x + breite / 2 + 2 / zoom, y + groesse * 1.2];
          if (belegt.some((b) => b[0] < box[2] && box[0] < b[2] && b[1] < box[3] && box[1] < b[3])) continue;
          belegt.push(box);
          ctx.lineWidth = 3 / zoom;
          ctx.strokeStyle = f.washi;
          ctx.strokeText(k.name, k.x, y);
          ctx.fillStyle = k.art === "begriff" ? f["sumi-mittel"] : f.sumi;
          ctx.fillText(k.name, k.x, y);
        }
      })
      .nodePointerAreaPaint((k, c, ctx) => {
        ctx.fillStyle = c;
        ctx.beginPath();
        ctx.arc(k.x, k.y, radius(k) + 2, 0, 2 * Math.PI);
        ctx.fill();
      })
      .linkColor((l) => anFokus(l) ? f.shu : mitte_() ? f.linie + "40" : l.art === "voraussetzung" ? f["sumi-mittel"] : f.linie + "b0")
      .linkWidth((l) => anFokus(l) ? 1.4 : l.art === "teil" ? 0.9 : 0.5)
      .linkLineDash((l) => (l.art === "voraussetzung" ? [3, 2] : null))
      .linkDirectionalArrowLength((l) => (l.art === "voraussetzung" ? 3 : 0))
      .linkDirectionalArrowRelPos(1)
      .onNodeHover((k) => { fokus = k ? k.id : null; flaeche.style.cursor = k ? "pointer" : ""; })
      .onNodeClick((k) => waehlen(k))
      .onBackgroundClick(() => { auswahl = null; notiz.hidden = true; neuZeichnen(); })
      .onBackgroundRightClick(() => g.zoomToFit(400, 40))
      .d3VelocityDecay(0.35)
      .warmupTicks(40)  // die ersten Schritte ohne Zeichnen: kein Aufplatzen beim Öffnen
      .cooldownTicks(160);
    g.d3Force("charge").strength((k) => (k.art === "begriff" ? -16 : k.art === "bereich" ? -260 : -70));
    // sanfte Schwerkraft zur Mitte: getrennte Teile (z. B. WiSo) treiben nicht davon
    const mitte = (alpha) => mitte.knoten.forEach((k) => { k.vx -= k.x * 0.04 * alpha; k.vy -= k.y * 0.04 * alpha; });
    mitte.initialize = (knoten) => { mitte.knoten = knoten; };
    g.d3Force("mitte", mitte);
    g.d3Force("link").distance((l) => ({ teil: 36, lernfeld: 80, begriff: 22, voraussetzung: 60 })[l.art])
      .strength((l) => (l.art === "lernfeld" ? 0.04 : 0.5));

    const pfad = { t: "thema", lf: "lernfeld", b: "begriff" };
    let gezoomt = false;
    // der gewählte Knoten in die Mitte der Fläche, die die Notiz frei lässt
    const zeigeAuf = (k, zoom) => {
      g.zoom(zoom, 600);
      g.centerAt(k.x + (notiz.hidden ? 0 : (notiz.offsetWidth + 12) / 2 / zoom), k.y, 600);
    };
    const waehlen = (k) => {
      auswahl = k.id;
      gezoomt = true;  // kein Einpassen mehr über die Auswahl hinweg
      notiz.hidden = false;
      zeigeAuf(k, Math.max(g.zoom(), 2));
      const [, art, nr] = k.id.match(/^([a-z]+)(\d+)$/);
      htmx.ajax("GET", `/niwa/${pfad[art]}/${nr}`, { target: "#notiz", swap: "innerHTML" }).then(() => { notiz.hidden = false; });
    };
    const finden = (kid) => g.graphData().nodes.find((k) => k.id === kid);

    [700, 1800, 3200].forEach((ms) => setTimeout(() => gezoomt || g.zoomToFit(400, 40), ms));  // schon während die Physik arbeitet
    g.onEngineStop(() => {
      if (gezoomt) return;
      gezoomt = true;
      const k = auswahl && finden(auswahl);
      k ? waehlen(k) : g.zoomToFit(500, 40);
    });

    // Notizen und Listen verweisen mit data-knoten auf Knoten im Graphen
    document.querySelector(".niwa").addEventListener("click", (e) => {
      const ziel = e.target.closest("[data-knoten]");
      const k = ziel && finden(ziel.dataset.knoten);
      if (!k) return;
      if (ziel.closest(".graph-notiz")) waehlen(k);
      else { auswahl = k.id; zeigeAuf(k, Math.max(g.zoom(), 2)); }
    });
    document.querySelectorAll(".graph-filter input").forEach((box) => box.addEventListener("change", () => {
      box.checked ? zeigen.add(box.dataset.art) : zeigen.delete(box.dataset.art);
      g.graphData(sichtbar());
    }));
    const suche = document.getElementById("graph-suche");
    const treffer = () => {
      const q = suche.value.trim().toLowerCase();
      if (!q) return null;
      const alle = g.graphData().nodes.filter((k) => k.name.toLowerCase().includes(q));
      return alle.sort((a, b) => b.name.toLowerCase().startsWith(q) - a.name.toLowerCase().startsWith(q) || radius(b) - radius(a))[0];
    };
    const neuZeichnen = () => g.zoom(g.zoom());  // ohne Bewegung zeichnet force-graph sonst nicht neu
    document.getElementById("graph-alles")?.addEventListener("click", () => { auswahl = null; notiz.hidden = true; g.zoomToFit(500, 40); });
    suche.addEventListener("input", () => { fokus = treffer()?.id || null; neuZeichnen(); });
    suche.addEventListener("keydown", (e) => {
      if (e.key === "Escape") { suche.value = ""; fokus = null; suche.blur(); neuZeichnen(); }
      if (e.key === "Enter" && treffer()) { e.preventDefault(); fokus = null; waehlen(treffer()); }
    });

    new ResizeObserver(() => g.width(flaeche.clientWidth).height(flaeche.clientHeight)).observe(flaeche);
    // Beim Wechsel in einen anderen Bereich die Zeichenschleife beenden
    const aufraeumen = (e) => {
      if (!e.detail.target?.contains(flaeche)) return;  // Notizen laden zählt nicht
      g._destructor();
      document.removeEventListener("htmx:beforeSwap", aufraeumen);
    };
    document.addEventListener("htmx:beforeSwap", aufraeumen);
  },
  // Analyse: eine Themenauswahl für alle Korrektur-Formulare, erst beim Anklicken befüllt (spart tausende <option>)
  themenwahl(auswahl) {
    if (auswahl.dataset.gefuellt) return;
    auswahl.insertAdjacentHTML("beforeend", document.getElementById("themenwahl").innerHTML);
    auswahl.value = auswahl.dataset.wert;
    auswahl.dataset.gefuellt = "1";
  },
  // Zeichenaufgaben: Bild verkleinern (spart Tokens), als data-URL ins Formular, Vorschau zeigen
  async zeichnung(datei) {
    const feld = document.querySelector(".zeichnung");
    if (!feld || !datei || !datei.type.startsWith("image/")) return;
    const bild = await createImageBitmap(datei);
    const faktor = Math.min(1, 1600 / Math.max(bild.width, bild.height));
    const leinwand = Object.assign(document.createElement("canvas"), { width: Math.round(bild.width * faktor), height: Math.round(bild.height * faktor) });
    leinwand.getContext("2d").drawImage(bild, 0, 0, leinwand.width, leinwand.height);
    const url = leinwand.toDataURL("image/jpeg", 0.85);
    feld.querySelector("[name=zeichnung]").value = url;
    feld.querySelector("[name=zeichnung_da]").value = "1";
    const vorschau = feld.querySelector(".zeichnung-vorschau");
    vorschau.src = url;
    vorschau.hidden = false;
    saku.melden("Zeichnung angehängt");
  },
  farbschema(wert) {
    const dunkel = wert === "dunkel" || (wert === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.classList.toggle("dark", dunkel);
    saku.fensterfarbe();
  },
  // Im App-Fenster (pywebview) bekommt die Titelleiste die Farbe der Seite
  fensterfarbe() {
    const farbe = getComputedStyle(document.documentElement).getPropertyValue("--washi").trim();
    window.pywebview?.api?.setze(farbe);
  },
};

// Antwort mit HX-Trigger: gespeichert
document.addEventListener("gespeichert", () => saku.melden("Gespeichert"));

// Bereichsbilder einmal vorab dekodieren, damit sie beim Wechsel nicht nachträglich aufploppen
addEventListener("load", () => {
  const vorladen = () => ["heute", "michi", "keiko", "shiken", "niwa", "bunseki", "sensei", "willkommen", "mankai"].forEach((name) => {
    const bild = new Image();
    bild.src = `/static/img/${name}-1200.jpg`;
    bild.decode().catch(() => {});
  });
  (window.requestIdleCallback || setTimeout)(vorladen);
});

// Tippt man gerade? Dann keine Einzeltasten.
function frei(e) {
  const feld = e.target.closest?.("input, textarea, select, [contenteditable='true']");
  // Auswahlknöpfe sind keine Texteingabe: Ziffer wählt, Enter prüft (Pfeiltasten bleiben beim Browser)
  const auswahl = feld?.matches("[type=radio], [type=checkbox]") && (e.key === "Enter" || /^\d$/.test(e.key));
  return (!feld || auswahl) && !e.metaKey && !e.ctrlKey && !e.altKey;
}

document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    saku.oeffne("suche-dialog");
    return;
  }
  if (!frei(e)) return;

  const taste = e.key.length === 1 ? e.key.toLowerCase() : e.key;
  // Enter und Leertaste auf einem fokussierten Knopf macht der Browser selbst
  if ((taste === "Enter" || taste === " ") && e.target.closest?.("button, a, summary, [role='button']")) return;
  if (taste === "?") {
    e.preventDefault();
    saku.oeffne("hilfe-dialog");
    return;
  }

  const bereich = document.querySelector("dialog[open]") || document;
  const ziel = [...bereich.querySelectorAll(`[data-taste="${CSS.escape(taste)}"]`)]
    .find((el) => !el.disabled && el.getClientRects().length);
  if (ziel) {
    e.preventDefault();
    ziel.click();
  }
});

// pywebview meldet sich erst nach dem Laden
addEventListener("pywebviewready", () => saku.fensterfarbe());

// ⌘V mit einem Bild in der Zwischenablage: als Zeichnung anhängen, wenn die Aufgabe eine erlaubt
document.addEventListener("paste", (e) => {
  const datei = [...(e.clipboardData?.files || [])].find((f) => f.type.startsWith("image/"));
  if (datei && document.querySelector(".zeichnung")) { e.preventDefault(); saku.zeichnung(datei); }
});
