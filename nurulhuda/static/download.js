// Downloads with a progress bar, so the page never sits blank while a big PDF arrives.
// Files from our own site (and those proxied through it) download here with a percentage, then save.
// Files from other sites open in a new tab as before, with a note on this page explaining the wait.
(function () {
  var box = null, ctrl = null;

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }
  function mb(n) { return (n / 1048576).toFixed(n > 10485760 ? 0 : 1) + " MB"; }

  function open(title) {
    close();
    box = el("div", "dl-overlay");
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Download");
    var card = el("div", "dl-card");
    card.innerHTML = '<svg class="dl-icon" viewBox="0 0 24 24" width="40" height="40" aria-hidden="true"><path d="M12 3v12m0 0l-5-5m5 5l5-5M4 19h16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    var t = el("p", "dl-title", title); t.dir = "auto"; card.appendChild(t);
    var bar = el("div", "dl-bar"); bar.appendChild(el("span")); card.appendChild(bar);
    card.appendChild(el("p", "dl-pct", "Starting…"));
    card.appendChild(el("p", "dl-note small", ""));
    var actions = el("p", "dl-actions");
    var cancel = el("button", "btn sm outline-dark", "Cancel"); cancel.type = "button";
    cancel.onclick = function () { if (ctrl) ctrl.abort(); close(); };
    actions.appendChild(cancel); card.appendChild(actions);
    box.appendChild(card);
    document.body.appendChild(box);
    cancel.focus();
    return box;
  }
  function close() { if (box) { box.remove(); box = null; } ctrl = null; }
  function set(pct, text, note) {
    if (!box) return;
    var span = box.querySelector(".dl-bar span");
    if (pct == null) { box.querySelector(".dl-bar").classList.add("busy"); }
    else { box.querySelector(".dl-bar").classList.remove("busy"); span.style.width = Math.max(2, pct) + "%"; }
    box.querySelector(".dl-pct").textContent = text;
    if (note != null) box.querySelector(".dl-note").textContent = note;
  }
  function done(url, name, blobUrl) {
    set(100, "Downloaded", "The file is in your Downloads folder.");
    var actions = box.querySelector(".dl-actions");
    actions.innerHTML = "";
    var view = el("a", "btn green sm", "Open the PDF"); view.href = blobUrl; view.target = "_blank"; view.rel = "noopener";
    var ok = el("button", "btn sm outline-dark", "Close"); ok.type = "button"; ok.onclick = close;
    actions.appendChild(view); actions.appendChild(ok);
    ok.focus();
  }

  async function fetchWithProgress(url, name, title) {
    open(title);
    ctrl = new AbortController();
    try {
      var res = await fetch(url, { signal: ctrl.signal });
      if (!res.ok || !res.body) throw new Error("HTTP " + res.status);
      var total = +res.headers.get("Content-Length") || 0, got = 0, chunks = [];
      var reader = res.body.getReader();
      for (;;) {
        var r = await reader.read();
        if (r.done) break;
        chunks.push(r.value); got += r.value.length;
        if (total) set(Math.floor(got / total * 100), Math.floor(got / total * 100) + "%  ·  " + mb(got) + " of " + mb(total));
        else set(null, mb(got) + " downloaded");
      }
      var blobUrl = URL.createObjectURL(new Blob(chunks, { type: "application/pdf" }));
      var a = el("a"); a.href = blobUrl; a.download = name; document.body.appendChild(a); a.click(); a.remove();
      done(url, name, blobUrl);
    } catch (err) {
      if (err && err.name === "AbortError") return;
      // Could not download here (e.g. the connection dropped): offer the plain link instead.
      set(0, "The download stopped.", "Check your connection and try again, or open the file directly.");
      var actions = box.querySelector(".dl-actions");
      actions.innerHTML = "";
      var direct = el("a", "btn green sm", "Open the file directly"); direct.href = url; direct.target = "_blank"; direct.rel = "noopener";
      var ok = el("button", "btn sm outline-dark", "Close"); ok.type = "button"; ok.onclick = close;
      actions.appendChild(direct); actions.appendChild(ok);
    }
  }

  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a[data-dl]");
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey) return;
    var title = a.getAttribute("data-title") || "Your file";
    if (a.getAttribute("data-dl") === "here" && window.fetch && window.ReadableStream) {
      e.preventDefault();
      fetchWithProgress(a.href, a.getAttribute("data-name") || "quran.pdf", title);
    } else {
      // Another site's file: let the link open its new tab, and explain the wait here.
      open(title);
      set(null, "Opening in a new tab…", "This file comes from " + (a.getAttribute("data-source") || "another website") +
          (a.getAttribute("data-size") ? " and is " + a.getAttribute("data-size") : "") +
          ". If the new tab looks blank, it is still loading: large files can take a few minutes on a slow connection.");
      var btn = box.querySelector(".dl-actions button"); btn.textContent = "Close";
    }
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && box) { if (ctrl) ctrl.abort(); close(); } });
})();
