// Saku: globale Tastenkürzel. Bedienelemente mit data-taste="x" werden per Taste x geklickt.
// Beispiel: <button data-taste=" " hx-get="…">Lösung zeigen</button>
window.saku = {
  oeffne(id) {
    const dialog = document.getElementById(id);
    if (!dialog || dialog.open) return;
    dialog.showModal();
    // ins Eingabefeld, sonst auf „Schließen“ (nicht auf die scrollbare Fläche, die der Browser sonst nimmt)
    (dialog.querySelector("input, textarea") || dialog.querySelector("[aria-label='Schließen']"))?.focus();
  },
  // Mobil: Blatt „Mehr“ mit allen Bereichen; der Eintrag im Verlauf lässt Zurück (Wischgeste, Browser) es schließen
  mehr() {
    saku.oeffne("mehr");
    // htmx stellt beim Zurück nur Einträge mit htmx-Zustand wieder her; den setzt es sonst beim Weitergehen, hier aber erst am
    // Eintrag des Blatts. Ohne ihn bliebe nach Mehr → Seite → Zurück auf der ersten Seite nach dem Laden die neue stehen
    history.replaceState({ htmx: true }, "");
    history.pushState({ mehr: true }, "");
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
  // Code-Editor: Tab rückt um vier Leerzeichen ein, Esc verlässt das Feld, ⌘↵/Strg+↵ führt SQL oder Pseudocode aus
  editorTaste(e) {
    const feld = e.target;
    if (e.key === "Escape") return feld.blur();
    const ausfuehren = e.key === "Enter" && (e.metaKey || e.ctrlKey) && feld.closest(".keiko-antwort, .rechnen-sql")?.querySelector("[data-sql-ausfuehren]");
    if (ausfuehren) {
      e.preventDefault();
      return ausfuehren.click();
    }
    // ↵ behält den Einzug der Zeile, nach DANN, SONST, FÜR … und SOLANGE … eine Stufe mehr
    if (e.key === "Enter" && !(e.shiftKey || e.altKey || e.metaKey || e.ctrlKey)) {
      const zeile = feld.value.slice(feld.value.lastIndexOf("\n", feld.selectionStart - 1) + 1, feld.selectionStart);
      const einzug = zeile.match(/^\s*/)[0] + (/\b(dann|sonst)\s*$|^\s*(für|fuer|solange)\b/i.test(zeile) ? "    " : "");
      if (!einzug) return;
      e.preventDefault();
      feld.setRangeText("\n" + einzug, feld.selectionStart, feld.selectionEnd, "end");
      return feld.dispatchEvent(new Event("input", { bubbles: true }));  // Zeilennummern
    }
    if (e.key !== "Tab") return;
    e.preventDefault();
    if (!e.shiftKey) return feld.setRangeText("    ", feld.selectionStart, feld.selectionEnd, "end");
    // ⇧Tab rückt die Zeile eine Stufe aus (z. B. vor ENDE WENN)
    const anfang = feld.value.lastIndexOf("\n", feld.selectionStart - 1) + 1;
    const weg = feld.value.slice(anfang).match(/^ {0,4}/)[0].length;
    if (weg) feld.setRangeText("", anfang, anfang + weg, "preserve");
  },
  // Zeilennummern neben dem Pseudocode-Editor (die Meldungen nennen die Zeile), mitgescrollt
  zeilen(feld) {
    const rand = feld.previousElementSibling;
    rand.textContent = Array.from({ length: feld.value.split("\n").length }, (_, i) => `${i + 1}\n`).join("");
    rand.scrollTop = feld.scrollTop;
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
    // Farbe, Radius und Namensbreite einmal statt in jedem Bild: WebKit zeichnet sonst beim Zoomen sichtbar langsamer
    const messen = document.createElement("canvas").getContext("2d");
    const breiten = () => daten.knoten.forEach((k) => {
      messen.font = `${rang[k.art] >= 4 ? 600 : 400} 100px Inter, sans-serif`;
      k._breite = messen.measureText(k.name).width / 100;
    });
    daten.knoten.forEach((k) => { k._farbe = farbe(k); k._r = radius(k); });
    breiten();
    document.fonts.ready.then(breiten);  // Inter ist beim ersten Aufruf evtl. noch nicht geladen
    const pulsieren = new Set(daten.pulsieren);

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
        ctx.globalAlpha = hell(k.id) ? 1 : 0.1;
        ctx.beginPath();
        ctx.arc(k.x, k.y, k._r, 0, 2 * Math.PI);
        ctx.fillStyle = k._farbe;
        ctx.fill();
        if (k.id === auswahl || pulsieren.has(k.id)) {
          ctx.lineWidth = 2 / zoom;
          ctx.strokeStyle = f.shu;
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      })
      // Namen nach den Knoten: wichtige zuerst, was einen schon gesetzten Namen verdecken würde, entfällt
      .onRenderFramePost((ctx, zoom) => {
        const nah = mitte_();
        // nur Namen im sichtbaren Ausschnitt (mit Rand für lange Namen)
        const [lo, ru] = [g.screen2GraphCoords(-150, -40), g.screen2GraphCoords(g.width() + 150, g.height() + 40)];
        const kandidaten = g.graphData().nodes.filter((k) => k.x > lo.x && k.x < ru.x && k.y > lo.y && k.y < ru.y
          && (nah ? hell(k.id) && (k.id === nah || zoom >= abZoom[k.art] - 0.6 || rang[k.art] >= 2) : k.id === auswahl || zoom >= abZoom[k.art]));
        kandidaten.sort((a, b) => (b.id === nah) - (a.id === nah) || rang[b.art] - rang[a.art] || b._r - a._r);
        const belegt = [];
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.lineJoin = "round";
        let schrift = "";
        for (const k of kandidaten) {
          const groesse = (k.art === "bereich" ? 13 : 11) / zoom;
          const neu = `${rang[k.art] >= 4 ? 600 : 400} ${groesse}px Inter, sans-serif`;
          if (neu !== schrift) ctx.font = schrift = neu;  // nach Rang sortiert: die Schrift wechselt selten
          const breite = k._breite * groesse, y = k.y + k._r + 2 / zoom;
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
        ctx.arc(k.x, k.y, k._r + 2, 0, 2 * Math.PI);
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
      .d3VelocityDecay(0.5)  // gedämpft: die Knoten gleiten aus statt nachzuschwingen
      // den Großteil der Physik vor dem ersten Bild rechnen: der Graph steht fast fertig da, statt lange aufzuplatzen
      .warmupTicks(Math.min(300, Math.round(60000 / Math.max(1, daten.knoten.length))))
      .cooldownTicks(120);
    g.d3Force("charge").strength((k) => (k.art === "begriff" ? -16 : k.art === "bereich" ? -260 : -70));
    // sanfte Schwerkraft zur Mitte: getrennte Teile (z. B. WiSo) treiben nicht davon
    const mitte = (alpha) => mitte.knoten.forEach((k) => { k.vx -= k.x * 0.04 * alpha; k.vy -= k.y * 0.04 * alpha; });
    mitte.initialize = (knoten) => { mitte.knoten = knoten; };
    g.d3Force("mitte", mitte);
    g.d3Force("link").distance((l) => ({ teil: 36, lernfeld: 80, begriff: 22, voraussetzung: 60 })[l.art])
      .strength((l) => (l.art === "lernfeld" ? 0.04 : 0.5));

    const pfad = { t: "thema", lf: "lernfeld", b: "begriff" };
    let gezoomt = false, selbst = false;
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

    // einmal sofort einpassen, am Ende sanft nachführen; wer selbst zoomt oder zieht, dem bewegt sich die Kamera nicht mehr weg
    let eingepasst = false;
    g.onEngineTick(() => { if (!eingepasst) { eingepasst = true; g.zoomToFit(0, 40); } });
    ["wheel", "pointerdown"].forEach((t) => flaeche.addEventListener(t, () => { selbst = true; }, { capture: true, passive: true }));
    g.onEngineStop(() => {
      if (gezoomt) return;
      gezoomt = true;
      const k = auswahl && finden(auswahl);
      if (k) waehlen(k);
      else if (!selbst) g.zoomToFit(500, 40);
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
  // Formeln (LaTeX aus markdown_zu_html) mit KaTeX setzen: geladen erst, wenn eine Seite Formeln zeigt, gesetzt nur im neuen Teil
  formeln(wurzel) {
    const offen = [...(wurzel.querySelectorAll?.(".formel:not([data-gesetzt])") || [])];
    if (!offen.length) return;
    const laden = (tag, felder) => new Promise((fertig, fehler) => document.head.append(Object.assign(document.createElement(tag), felder, { onload: fertig, onerror: fehler })));
    saku.katex ??= Promise.all([laden("link", { rel: "stylesheet", href: "/static/vendor/katex/katex.min.css" }),
      laden("script", { src: "/static/vendor/katex/katex.min.js" })]);
    saku.katex.then(() => offen.forEach((el) => {
      el.dataset.gesetzt = "";
      katex.render(el.textContent, el, { displayMode: el.classList.contains("formel--block"), throwOnError: false, strict: "ignore" });
      // Klammer und Satzzeichen direkt an der Formel in ihren ersten bzw. letzten Block: um KaTeX' Inline-Blöcke bricht der Browser
      // sonst auch zwischen „(“ und Formel oder vor dem Komma um
      const zeichen = (text) => Object.assign(document.createElement("span"), { className: "formel-zeichen", textContent: text });
      const [davor, danach] = [el.previousSibling, el.nextSibling];
      if (davor?.nodeType === Node.TEXT_NODE && /[(„]$/.test(davor.data)) {
        el.querySelector(".katex-base")?.prepend(zeichen(davor.data.at(-1)));
        davor.deleteData(davor.length - 1, 1);
      }
      if (danach?.nodeType === Node.TEXT_NODE && /^[.,;:)“]/.test(danach.data)) {
        el.querySelector(".katex-base:last-of-type")?.append(zeichen(danach.data[0]));
        danach.deleteData(0, 1);
      }
    }), () => {});  // ohne KaTeX bleibt der LaTeX-Quelltext lesbar stehen
  },
  // Sprungmarken (Einstellungen, Formelsammlung): markiert den letzten Abschnitt, der oben ins Fenster gerückt ist, am Seitenende den letzten
  sprungmarken(nav) {
    const links = [...nav.querySelectorAll("a[href^='#']")];
    const markieren = () => {
      if (!nav.isConnected) return removeEventListener("scroll", markieren);
      const sichtbar = links.filter((a) => !a.hidden);
      const oben = (a) => document.getElementById(a.hash.slice(1)).getBoundingClientRect().top < innerHeight / 3;
      const aktiv = innerHeight + scrollY >= document.documentElement.scrollHeight - 8 ? sichtbar.at(-1) : sichtbar.findLast(oben) || sichtbar[0];
      links.forEach((a) => (a === aktiv ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current")));
      // schmal stehen die Marken als Chips nebeneinander: den aktiven ins Bild schieben
      if (aktiv && nav.scrollWidth > nav.clientWidth && (aktiv.offsetLeft < nav.scrollLeft || aktiv.offsetLeft + aktiv.offsetWidth > nav.scrollLeft + nav.clientWidth)) {
        nav.scrollLeft = aktiv.offsetLeft - 16;
      }
    };
    addEventListener("scroll", markieren, { passive: true });
    markieren();
  },
  // Befehl neben dem Knopf in die Zwischenablage; geht das nicht (eigenes App-Fenster), ist er markiert für ⌘C
  async kopieren(knopf) {
    const code = knopf.parentElement.querySelector("code");
    try {
      await navigator.clipboard.writeText(code.textContent);
      saku.melden("Kopiert");
    } catch {
      getSelection().selectAllChildren(code);
      saku.melden("Markiert, mit ⌘C kopieren");
    }
  },
  // Formelsammlung: Karten nach Text filtern; Gruppen ohne Treffer und ihre Sprungmarken verschwinden
  formelSuche(text) {
    const q = text.trim().toLowerCase();
    document.querySelectorAll(".formel-gruppe").forEach((gruppe) => {
      const karten = [...gruppe.querySelectorAll(".formel-art")];
      karten.forEach((k) => { k.hidden = Boolean(q) && !k.textContent.toLowerCase().includes(q); });
      gruppe.hidden = karten.every((k) => k.hidden);
      document.querySelector(`.sprungmarken a[href="#${gruppe.id}"]`).hidden = gruppe.hidden;
    });
    document.getElementById("formel-leer").hidden = Boolean(document.querySelector(".formel-gruppe:not([hidden])"));
    dispatchEvent(new Event("scroll"));  // Markierung neu setzen
  },
};

// nach dem Laden und nach jedem htmx-Tausch (Prüfen, Rechenweg, Sprint, Probeprüfung, Bereichswechsel)
document.addEventListener("htmx:load", (e) => {
  saku.formeln(e.target);
  e.target.querySelectorAll?.("[data-sprungmarken]").forEach((nav) => saku.sprungmarken(nav));
});

// Antwort mit HX-Trigger: gespeichert
document.addEventListener("gespeichert", () => saku.melden("Gespeichert"));

// Blatt „Mehr“: Schließen (Esc, Knopf, daneben tippen) nimmt seinen Eintrag wieder aus dem Verlauf, Zurück schließt es.
// htmx darf dabei nichts aus dem Verlauf neu aufbauen: dieser Listener läuft vor htmx' onpopstate (gesetzt erst beim Laden)
let mehrZurueck = false;
document.addEventListener("close", (e) => {
  if (e.target.id !== "mehr" || !history.state?.mehr) return;
  mehrZurueck = true;
  history.back();
}, true);
addEventListener("popstate", (e) => {
  const blatt = document.getElementById("mehr");
  if (!mehrZurueck && !blatt?.open) return;
  e.stopImmediatePropagation();
  mehrZurueck = false;
  blatt?.close();
});
// Ein Link oder Formular im Blatt: dessen Eintrag wird zur neuen Seite (hx-replace-url am Blatt), nicht zurückgenommen
document.addEventListener("htmx:beforeRequest", (e) => {
  const blatt = e.target.closest?.("#mehr");
  if (!blatt?.open) return;
  history.replaceState(null, "");
  blatt.close();
});

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

// autofocus greift nicht in jedem Browser beim Laden (WebKit, Fenster ohne Fokus); Rechnen beginnt im ersten Feld
addEventListener("DOMContentLoaded", () => document.querySelector("main [autofocus]")?.focus());

// pywebview meldet sich erst nach dem Laden
addEventListener("pywebviewready", () => saku.fensterfarbe());

// ⌘V mit einem Bild in der Zwischenablage: als Zeichnung anhängen, wenn die Aufgabe eine erlaubt
document.addEventListener("paste", (e) => {
  const datei = [...(e.clipboardData?.files || [])].find((f) => f.type.startsWith("image/"));
  if (datei && document.querySelector(".zeichnung")) { e.preventDefault(); saku.zeichnung(datei); }
});
