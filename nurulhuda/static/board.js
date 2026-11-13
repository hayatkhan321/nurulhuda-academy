// Lesson board: a Quran page (King Fahd Complex Uthmanic Hafs text and font) or a blank page that the teacher can
// highlight and write on, shown live to the student. Marks travel as small messages over the class's own video
// connection (Daily app messages), so nothing new is stored or paid for. On the practice page they travel between
// browser tabs instead.
//
// NHBoard.start(el, {role: "teacher"|"student"|"observer", send: fn(msg), dataUrl})  -> returns {receive(msg, from)}
(function () {
  var W = 760;                       // every board is laid out 760 units wide, then scaled to fit the screen,
  var BLANK_H = 1000;                // so marks land on the same word on every device
  var TOOLS = [
    { id: "hl-yellow", kind: "hl", color: "rgba(255, 214, 0, 0.42)", w: 22, label: "Yellow highlighter" },
    { id: "hl-green", kind: "hl", color: "rgba(46, 204, 113, 0.38)", w: 22, label: "Green highlighter" },
    { id: "hl-pink", kind: "hl", color: "rgba(255, 64, 160, 0.34)", w: 22, label: "Pink highlighter" },
    { id: "hl-blue", kind: "hl", color: "rgba(52, 152, 219, 0.36)", w: 22, label: "Blue highlighter" },
    { id: "pen-red", kind: "pen", color: "#d62828", w: 3.5, label: "Red pen" },
    { id: "pen-blue", kind: "pen", color: "#1d4ed8", w: 3.5, label: "Blue pen" },
    { id: "eraser", kind: "eraser", label: "Eraser: tap a mark to remove it" }
  ];
  var MAX_PTS = 250;                 // points per message, to stay well under the message size limit

  function h(tag, attrs, kids) {
    var e = document.createElement(tag);
    for (var k in attrs || {}) { if (k === "text") e.textContent = attrs[k]; else if (k === "html") e.innerHTML = attrs[k]; else e.setAttribute(k, attrs[k]); }
    (kids || []).forEach(function (c) { if (c) e.appendChild(c); });
    return e;
  }

  function start(root, opt) {
    var teacher = opt.role === "teacher";
    var state = { view: "p1", page: 1, studentDraws: false, tool: TOOLS[0], strokes: {}, data: null };
    var mine = []; // ids of strokes I drew on each view, newest last, for Undo
    var dataPromise = null;

    // --- layout -------------------------------------------------------------------------------------
    root.innerHTML = "";
    root.classList.add("board");
    var bar = h("div", { class: "board-bar" });
    var nav = h("div", { class: "board-nav" });
    var tools = h("div", { class: "board-tools", role: "toolbar", "aria-label": "Marking tools" });
    var info = h("p", { class: "board-info small" });
    bar.appendChild(nav); bar.appendChild(tools);
    var wrap = h("div", { class: "board-wrap" });
    var stage = h("div", { class: "board-stage" });
    var sheet = h("div", { class: "board-sheet", dir: "rtl", lang: "ar" });
    var canvas = h("canvas", { class: "board-canvas", "aria-label": "Lesson board" });
    stage.appendChild(sheet); stage.appendChild(canvas); wrap.appendChild(stage);
    root.appendChild(bar); root.appendChild(info); root.appendChild(wrap);
    var ctx = canvas.getContext("2d");

    // Page controls: teacher only. The student's board follows the teacher.
    var pageIn, surahSel, juzSel;
    if (teacher) {
      var prev = h("button", { type: "button", class: "btn sm outline-dark", text: "‹ Previous" });
      var next = h("button", { type: "button", class: "btn sm outline-dark", text: "Next ›" });
      pageIn = h("input", { type: "number", min: "1", max: "604", value: "1", "aria-label": "Page", class: "board-page" });
      surahSel = h("select", { "aria-label": "Surah" }, [h("option", { value: "", text: "Surah…" })]);
      juzSel = h("select", { "aria-label": "Juz" }, [h("option", { value: "", text: "Juz…" })]);
      var blank = h("button", { type: "button", class: "btn sm outline-dark", text: "Blank board" });
      var allow = h("label", { class: "board-allow small" }, [h("input", { type: "checkbox" }), document.createTextNode(" Student can mark")]);
      // "Next" moves forward through the mushaf (pages are numbered left to right in the controls).
      prev.onclick = function () { go(Math.max(1, state.page - 1)); };
      next.onclick = function () { go(Math.min(604, state.page + 1)); };
      pageIn.onchange = function () { var n = parseInt(pageIn.value, 10); if (n >= 1 && n <= 604) go(n); };
      surahSel.onchange = function () { if (surahSel.value) go(+surahSel.value); surahSel.value = ""; };
      juzSel.onchange = function () { if (juzSel.value) go(+juzSel.value); juzSel.value = ""; };
      blank.onclick = function () { show("blank"); broadcastView(); };
      allow.firstChild.onchange = function () { state.studentDraws = allow.firstChild.checked; opt.send({ k: "perm", draw: state.studentDraws }); };
      [prev, h("span", { class: "small", text: "Page" }), pageIn, next, surahSel, juzSel, blank, allow].forEach(function (x) { nav.appendChild(x); });
    }

    var toolBtns = {};
    TOOLS.forEach(function (t) {
      var b = h("button", { type: "button", class: "tool tool-" + t.kind, title: t.label, "aria-label": t.label, "aria-pressed": "false" });
      if (t.kind !== "eraser") b.style.setProperty("--c", t.color.replace(/0\.\d+\)/, "1)"));
      else b.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M16 3l5 5-11 11H5v-5L16 3z" fill="none" stroke="currentColor" stroke-width="2"/></svg>';
      b.onclick = function () { state.tool = t; paintTools(); };
      tools.appendChild(b); toolBtns[t.id] = b;
    });
    var undo = h("button", { type: "button", class: "btn sm outline-dark", text: "Undo" });
    var clear = h("button", { type: "button", class: "btn sm outline-dark", text: teacher ? "Clear page" : "Clear my marks" });
    undo.onclick = function () { var id = mine.pop(); if (id) { remove(id); opt.send({ k: "del", v: state.view, id: id }); } };
    clear.onclick = function () {
      if (teacher) { state.strokes[state.view] = []; mine = []; redraw(); opt.send({ k: "clear", v: state.view }); }
      else { mine.forEach(function (id) { remove(id); opt.send({ k: "del", v: state.view, id: id }); }); mine = []; }
    };
    tools.appendChild(undo); tools.appendChild(clear);
    function paintTools() {
      for (var id in toolBtns) toolBtns[id].setAttribute("aria-pressed", String(id === state.tool.id));
      var can = canDraw();
      tools.hidden = !can;
      canvas.style.cursor = can ? (state.tool.kind === "eraser" ? "pointer" : "crosshair") : "default";
      canvas.style.touchAction = can ? "none" : "auto";
      info.textContent = teacher ? "" : can ? "Your teacher has let you mark the board." : "Your teacher's board. Marks appear here as your teacher writes.";
    }
    function canDraw() { return teacher || (opt.role === "student" && state.studentDraws); }

    // --- the Quran text --------------------------------------------------------------------------------
    function loadData() {
      if (!dataPromise) dataPromise = fetch(opt.dataUrl).then(function (r) { return r.json(); }).then(function (d) {
        state.data = d;
        if (teacher) {
          d.surahs.forEach(function (s, i) { surahSel.appendChild(h("option", { value: s[2], text: (i + 1) + ". " + s[1] })); });
          d.juz.forEach(function (p, i) { juzSel.appendChild(h("option", { value: p, text: "Juz " + (i + 1) })); });
        }
        return d;
      });
      return dataPromise;
    }
    function renderPage(n) {
      var d = state.data, html = [];
      d.pages[n - 1].forEach(function (a) {
        var s = d.surahs[a[0] - 1];
        if (a[1] === 1) {
          html.push('<div class="q-head"><span>سُورَةُ ' + s[0] + "</span></div>");
          if (a[0] !== 1 && a[0] !== 9) html.push('<div class="q-bism">' + d.pages[0][0][2].split(" ")[0] + "</div>");
        }
        html.push('<span class="q-aya">' + a[2] + " </span>");
      });
      sheet.className = "board-sheet q-page";
      sheet.innerHTML = '<div class="q-text">' + html.join("") + '</div><p class="q-foot">' + n + "</p>";
    }

    // --- views and drawing -----------------------------------------------------------------------------
    var height = BLANK_H, scale = 1;
    function show(view) {
      state.view = view;
      mine = [];
      var ready = Promise.resolve();
      if (view === "blank") { sheet.className = "board-sheet blank"; sheet.innerHTML = ""; }
      else {
        state.page = +view.slice(1);
        if (pageIn) pageIn.value = state.page;
        ready = loadData().then(function () { renderPage(state.page); return document.fonts && document.fonts.ready; });
      }
      return ready.then(function () { fit(); });
    }
    function go(n) { show("p" + n).then(broadcastView); }
    function broadcastView() { opt.send({ k: "view", v: state.view }); }

    function fit() {
      height = state.view === "blank" ? BLANK_H : Math.max(600, Math.ceil(sheet.scrollHeight));
      sheet.style.height = height + "px";
      scale = Math.min(1.4, wrap.clientWidth / W) || 1;
      stage.style.transform = "scale(" + scale + ")";
      stage.style.height = height + "px";
      wrap.style.height = Math.ceil(height * scale) + "px";
      var dpr = Math.min(3, (window.devicePixelRatio || 1) * scale);
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(height * dpr);
      canvas.style.width = W + "px"; canvas.style.height = height + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      redraw();
    }
    window.addEventListener("resize", function () { clearTimeout(fit.t); fit.t = setTimeout(fit, 120); });

    function list() { return state.strokes[state.view] || (state.strokes[state.view] = []); }
    function drawStroke(s) {
      var p = s.p; if (!p || p.length < 2) return;
      ctx.save();
      ctx.lineCap = s.kind === "hl" ? "butt" : "round"; ctx.lineJoin = "round";
      ctx.strokeStyle = s.c; ctx.lineWidth = s.w;
      ctx.globalCompositeOperation = s.kind === "hl" ? "multiply" : "source-over";
      ctx.beginPath(); ctx.moveTo(p[0], p[1]);
      if (p.length === 2) ctx.lineTo(p[0] + 0.1, p[1]);
      for (var i = 2; i < p.length; i += 2) ctx.lineTo(p[i], p[i + 1]);
      ctx.stroke(); ctx.restore();
    }
    function redraw() { ctx.clearRect(0, 0, W, height); list().forEach(drawStroke); }
    function add(view, s) {
      var l = state.strokes[view] || (state.strokes[view] = []);
      if (l.some(function (x) { return x.id === s.id; })) return;
      l.push(s); if (view === state.view) drawStroke(s);
    }
    function remove(id, view) {
      view = view || state.view;
      var l = state.strokes[view] || [];
      // a long stroke is sent in parts that share an id prefix ("abc", "abc~1", ...)
      state.strokes[view] = l.filter(function (s) { return s.id !== id && s.id.split("~")[0] !== id; });
      if (view === state.view) redraw();
    }

    var cur = null;
    function pos(e) { var r = canvas.getBoundingClientRect(); return [Math.round((e.clientX - r.left) / scale), Math.round((e.clientY - r.top) / scale)]; }
    canvas.addEventListener("pointerdown", function (e) {
      if (!canDraw()) return;
      e.preventDefault(); canvas.setPointerCapture(e.pointerId);
      var xy = pos(e);
      if (state.tool.kind === "eraser") { eraseAt(xy); return; }
      cur = { id: Math.random().toString(36).slice(2, 9), kind: state.tool.kind, c: state.tool.color, w: state.tool.w, p: xy };
    });
    canvas.addEventListener("pointermove", function (e) {
      if (!cur) { if (e.buttons && state.tool.kind === "eraser" && canDraw()) eraseAt(pos(e)); return; }
      var xy = pos(e), p = cur.p;
      if (Math.abs(xy[0] - p[p.length - 2]) + Math.abs(xy[1] - p[p.length - 1]) < 2) return;
      if (cur.kind === "hl" && p.length >= 2 && Math.abs(xy[1] - p[1]) < 14) xy[1] = p[1]; // keep highlights on the line
      ctx.save(); ctx.lineCap = cur.kind === "hl" ? "butt" : "round"; ctx.strokeStyle = cur.c; ctx.lineWidth = cur.w;
      ctx.globalCompositeOperation = cur.kind === "hl" ? "multiply" : "source-over";
      ctx.beginPath(); ctx.moveTo(p[p.length - 2], p[p.length - 1]); ctx.lineTo(xy[0], xy[1]); ctx.stroke(); ctx.restore();
      p.push(xy[0], xy[1]);
    });
    function finish() {
      if (!cur) return;
      var s = cur; cur = null;
      list().push(s); mine.push(s.id); redraw();
      // send in parts small enough for one message each
      for (var i = 0, part = 0; i < s.p.length; i += MAX_PTS * 2, part++) {
        var pts = s.p.slice(Math.max(0, i - 2), i + MAX_PTS * 2);
        opt.send({ k: "stroke", v: state.view, s: { id: part ? s.id + "~" + part : s.id, kind: s.kind, c: s.c, w: s.w, p: pts } });
      }
    }
    canvas.addEventListener("pointerup", finish);
    canvas.addEventListener("pointercancel", finish);
    function eraseAt(xy) {
      var l = list();
      for (var i = l.length - 1; i >= 0; i--) {
        var s = l[i], r = s.w / 2 + 8;
        for (var j = 0; j < s.p.length; j += 2) {
          if (Math.abs(s.p[j] - xy[0]) < r && Math.abs(s.p[j + 1] - xy[1]) < r) {
            if (!teacher && mine.indexOf(s.id.split("~")[0]) < 0) return; // a student only erases their own marks
            var id = s.id.split("~")[0]; remove(id); opt.send({ k: "del", v: state.view, id: id }); return;
          }
        }
      }
    }

    // --- messages ------------------------------------------------------------------------------------------
    function sendState() {
      opt.send({ k: "view", v: state.view });
      opt.send({ k: "perm", draw: state.studentDraws });
      (state.strokes[state.view] || []).forEach(function (s) { opt.send({ k: "stroke", v: state.view, s: s }); });
    }
    function receive(m) {
      if (!m || typeof m !== "object") return;
      if (m.k === "hello") { if (teacher) sendState(); return; }
      if (m.k === "view" && !teacher) { if (m.v !== state.view) show(m.v); return; }
      if (m.k === "perm" && !teacher) { state.studentDraws = !!m.draw; paintTools(); return; }
      if (m.k === "stroke" && m.s && m.s.p) { add(m.v, m.s); return; }
      if (m.k === "del") { remove(m.id, m.v); return; }
      if (m.k === "clear") { state.strokes[m.v] = []; if (m.v === state.view) redraw(); }
    }

    paintTools();
    show(state.view);
    if (!teacher) opt.send({ k: "hello" });
    return { receive: receive, sendState: sendState, refit: fit };
  }

  window.NHBoard = { start: start };
})();
