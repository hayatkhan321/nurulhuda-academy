/* Practice check (staff test). Records one verse, runs the HisnLabs tajweed-v2 model (Apache-2.0) in the browser with
   onnxruntime-web, and sends only what the model heard (its phonetic script, confidence and timings) to the server,
   which returns remarks per word. The audio never leaves this device. */
(function () {
  "use strict";
  // Our own copy first (works behind office and school web filters), then the original on Hugging Face.
  // Our own browser-friendly build (public/models/NOTICE.md). The int8 file on Hugging Face cannot run in browsers.
  var MODEL_URLS = ["/models/tajweed-v2-int8.onnx"];
  var MODEL_URL = location.origin + MODEL_URLS[0];  // the cache key, whichever copy was downloaded
  var MODEL_CACHE = "nh-model-tajweed-v2-web-1";  // change the name whenever the model file changes
  if ("caches" in window) {  // drop copies of older model files (the first one could not run in browsers)
    caches.keys().then(function (keys) {
      keys.forEach(function (k) { if (k.indexOf("nh-model-") === 0 && k !== MODEL_CACHE) caches.delete(k); });
    }).catch(function () {});
  }
  var ORT_DIST = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/";
  var PHONEMES = ["ء", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر",
    "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ", "ف", "ق",
    "ك", "ل", "م", "ن", "ه", "و", "ي", "ا", "ۦ", "ۥ", "َ",
    "ُ", "ِ", "۪", "ـ", "ٲ", "ڇ", "ں", "۾", "ۜ", "ؙ"];
  var SR = 16000, LEAD = Math.round(SR * 0.4);  // the training clips start and end with 0.4 s of silence

  function $(id) { return document.getElementById(id); }

  /* ---------- the model ---------- */
  function fetchModel(onProgress) {
    var cacheOk = "caches" in window;
    var cached = cacheOk ? caches.open(MODEL_CACHE).then(function (c) { return c.match(MODEL_URL); }).catch(function () { return null; }) : Promise.resolve(null);
    return cached.then(function (hit) {
      if (hit) return hit.arrayBuffer();
      var tried = [];
      function tryFrom(i) {
        if (i >= MODEL_URLS.length) {
          var err = new Error(tried.join("; ")); err.stage = "download"; throw err;
        }
        var where = MODEL_URLS[i].charAt(0) === "/" ? "this website" : MODEL_URLS[i].split("/")[2];
        return fetch(MODEL_URLS[i]).then(function (res) {
          var type = res.headers.get("Content-Type") || "";
          if (!res.ok || type.indexOf("text/html") === 0) { tried.push(where + " " + (res.ok ? "no file" : res.status)); return tryFrom(i + 1); }
          return res;
        }, function (e) { tried.push(where + " blocked (" + e.message + ")"); return tryFrom(i + 1); });
      }
      return tryFrom(0).then(function (res) {
        var total = +res.headers.get("Content-Length") || 23e6, got = 0, parts = [];
        if (!res.body || !res.body.getReader) return res.arrayBuffer();
        var reader = res.body.getReader();
        function pump() {
          return reader.read().then(function (r) {
            if (r.done) return;
            parts.push(r.value); got += r.value.length; onProgress(Math.min(99, Math.round(100 * got / total)));
            return pump();
          });
        }
        return pump().then(function () {
          var buf = new Uint8Array(got), o = 0;
          parts.forEach(function (p) { buf.set(p, o); o += p.length; });
          if (cacheOk) {
            caches.open(MODEL_CACHE).then(function (c) { return c.put(MODEL_URL, new Response(buf.slice().buffer)); }).catch(function () {});
          }
          return buf.buffer;
        });
      });
    });
  }

  function loadSession(onProgress) {
    if (typeof ort === "undefined") {
      var e0 = new Error("cdn.jsdelivr.net blocked"); e0.stage = "engine"; return Promise.reject(e0);
    }
    ort.env.wasm.wasmPaths = ORT_DIST;
    ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 1) : 1;
    return fetchModel(onProgress).then(function (buf) {
      return ort.InferenceSession.create(buf, { executionProviders: ["wasm"] }).catch(function (e) {
        if ("caches" in window) caches.delete(MODEL_CACHE).catch(function () {});  // a bad copy is not kept
        var err = new Error(String(e && e.message || e)); err.stage = "start"; throw err;
      });
    });
  }

  /* audio: Float32Array at 16 kHz → {heard, probs, times} exactly like HisnLabs inference.hear() */
  function hear(session, audio) {
    var padded = new Float32Array(audio.length + 2 * LEAD);
    padded.set(audio, LEAD);
    var mel = NHMel.logMel(padded, 3000), frames = Math.min(3000, Math.floor(mel.frames / 2) * 2);
    var data = mel.data;
    if (frames !== mel.frames) {  // keep the first `frames` columns of every band
      data = new Float32Array(80 * frames);
      for (var m = 0; m < 80; m++) data.set(mel.data.subarray(m * mel.frames, m * mel.frames + frames), m * frames);
    }
    var feeds = {};
    feeds[session.inputNames[0] === "riwaya" ? session.inputNames[1] : session.inputNames[0]] = new ort.Tensor("float32", data, [1, 80, frames]);
    feeds.riwaya = new ort.Tensor("int64", BigInt64Array.from([0n]), [1]);  // 0 = Hafs
    return session.run(feeds).then(function (out) {
      var lp = out[session.outputNames[0]], T = lp.dims[1], V = lp.dims[2], d = lp.data;
      var step = padded.length / SR / T, lead = LEAD / SR;
      var heard = "", probs = [], times = [], prev = 0, lastFrame = -1;
      for (var t = 0; t < T; t++) {
        var best = 0, bv = -Infinity;
        for (var v = 0; v < V; v++) { var x = d[t * V + v]; if (x > bv) { bv = x; best = v; } }
        if (best !== 0) lastFrame = t;
        if (best !== prev && best !== 0) {
          heard += PHONEMES[best - 1]; probs.push(Math.exp(bv)); times.push((t + 0.5) * step - lead);
        }
        prev = best;
      }
      times.push(lastFrame >= 0 ? (lastFrame + 1) * step - lead : 0);
      return { heard: heard, probs: probs, times: times };
    });
  }

  /* ---------- recording ---------- */
  function toMono16k(arrayBuf) {
    var Ctx = window.AudioContext || window.webkitAudioContext, ctx = new Ctx();
    return new Promise(function (ok, bad) { ctx.decodeAudioData(arrayBuf, ok, bad); }).then(function (decoded) {
      ctx.close && ctx.close();
      var n = Math.ceil(decoded.duration * SR), off = new OfflineAudioContext(1, n, SR);
      var src = off.createBufferSource(); src.buffer = decoded; src.connect(off.destination); src.start();
      return off.startRendering();
    }).then(function (b) { return b.getChannelData(0); });
  }

  /* ---------- the verse (King Fahd Complex text, never typed by hand) ---------- */
  var quran = null;
  function verseWords(s, a) {
    var words = [];
    quran.pages.forEach(function (p) {
      p.forEach(function (v) {
        if (v[0] === s && v[1] === a) {
          v[2].split(/[\s ]+/).forEach(function (w) {
            if (/[ء-يٱۥۦ]/.test(w)) words.push(w);  // leave out the verse number and ۞
          });
        }
      });
    });
    return words;
  }

  /* ---------- the page ---------- */
  function start(opt) {
    var rec = $("pc-rec"), lbl = rec.querySelector(".lbl"), status = $("pc-status"), timeEl = $("pc-time");
    var surahSel = $("pc-surah"), ayahSel = $("pc-ayah"), textEl = $("pc-text");
    var session = null, recorder = null, chunks = [], t0 = 0, timer = null, stream = null;
    var current = null;  // {id, words, marks}

    function say(msg, kind) { status.textContent = msg; status.className = "pc-status" + (kind ? " " + kind : ""); }
    function pick(name) { var el = document.querySelector('input[name="' + name + '"]:checked'); return el && el.value; }

    function fillAyahs() {
      var n = +surahSel.selectedOptions[0].dataset.verses, keep = ayahSel.value;
      ayahSel.innerHTML = "";
      for (var i = 1; i <= n; i++) { var o = document.createElement("option"); o.value = i; o.textContent = i; ayahSel.appendChild(o); }
      if (keep && keep <= n) ayahSel.value = keep;
    }
    function showVerse() {
      $("pc-result").hidden = true; current = null;
      if (!quran) return;
      var words = verseWords(+surahSel.value, +ayahSel.value);
      textEl.innerHTML = "";
      words.forEach(function (w, i) {
        var b = document.createElement("button");
        b.type = "button"; b.className = "pc-w"; b.textContent = w; b.dataset.i = i;
        textEl.appendChild(b); textEl.appendChild(document.createTextNode(" "));
      });
    }
    function relabel() {
      var age = pick("reader");
      document.querySelectorAll("[data-child]").forEach(function (el) { el.textContent = el.dataset[age === "adult" ? "adult" : "child"]; });
    }
    document.querySelectorAll('input[name="reader"]').forEach(function (r) { r.addEventListener("change", relabel); });
    surahSel.addEventListener("change", function () { fillAyahs(); showVerse(); });
    ayahSel.addEventListener("change", showVerse);
    fillAyahs();

    fetch(opt.dataUrl).then(function (r) { return r.json(); }).then(function (d) { quran = d; showVerse(); });

    if (!navigator.mediaDevices || !window.MediaRecorder) {
      say("This browser cannot record. Please use a recent Chrome, Edge or Safari.", "bad");
      return;
    }
    loadSession(function (p) { say("Loading the checker: " + p + "%"); }).then(function (s) {
      session = s; rec.disabled = false; lbl.textContent = "Record the verse";
      say("Ready. Press the button, recite the verse, then press it again.");
    }).catch(function (e) {
      var why = e && e.stage === "download" ? "The checker could not be downloaded. A web filter on this network may be blocking it."
        : e && e.stage === "engine" ? "The checker's engine could not be loaded. A web filter on this network may be blocking it."
        : e && e.stage === "start" ? "The checker downloaded but could not start in this browser."
        : "The checker could not be loaded.";
      say(why + " Please send a screenshot of this message. (Details: " + (e && e.message || e) + ")", "bad");
      if (window.console) console.error("Practice check:", e);
    });

    function stopRec() {
      if (recorder && recorder.state === "recording") recorder.stop();
    }
    rec.addEventListener("click", function () {
      if (recorder && recorder.state === "recording") { stopRec(); return; }
      navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: false, noiseSuppression: false, autoGainControl: true } })
        .then(function (st) {
          stream = st; chunks = [];
          recorder = new MediaRecorder(st);
          recorder.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
          recorder.onstop = finished;
          recorder.start();
          t0 = Date.now(); rec.classList.add("on"); lbl.textContent = "Stop";
          $("pc-result").hidden = true;
          say("Listening… recite the verse now.");
          timer = setInterval(function () {
            var s = (Date.now() - t0) / 1000;
            timeEl.textContent = s.toFixed(0) + " s";
            if (s >= opt.maxSeconds) stopRec();
          }, 250);
        })
        .catch(function () { say("The microphone was not allowed. Allow it in the browser's address bar and try again.", "bad"); });
    });

    function finished() {
      clearInterval(timer); rec.classList.remove("on"); lbl.textContent = "Record again"; timeEl.textContent = "";
      if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
      rec.disabled = true;
      say("Checking…");
      var blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      var seconds = 0;
      blob.arrayBuffer().then(toMono16k).then(function (audio) {
        seconds = audio.length / SR;
        if (seconds < 0.6) throw new Error("short");
        return hear(session, audio.length > SR * opt.maxSeconds ? audio.subarray(0, SR * opt.maxSeconds) : audio);
      }).then(function (h) {
        return fetch(opt.checkUrl, {
          method: "POST", credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRF": opt.csrf },
          body: JSON.stringify({ surah: +surahSel.value, ayah: +ayahSel.value, reader: pick("reader"), gender: pick("gender"),
                                 seconds: seconds, heard: h.heard, probs: h.probs, times: h.times })
        }).then(function (r) { return r.json().then(function (j) { j._status = r.status; return j; }); });
      }).then(function (j) {
        rec.disabled = false;
        if (j.error) { say(j.error, "bad"); return; }
        show(j);
      }).catch(function (e) {
        rec.disabled = false;
        say(e && e.message === "short" ? "That was too short. Record the whole verse." : "Something went wrong while checking. Please try again.", "bad");
      });
    }

    function show(j) {
      var spans = textEl.querySelectorAll(".pc-w");
      var aligned = spans.length === j.words;  // 3 verses in the whole Quran split a word differently
      current = { id: j.id, marks: {} };
      spans.forEach(function (s) { s.classList.remove("flag", "ok", "missed"); s.classList.add("ok"); });
      var list = $("pc-notes"); list.innerHTML = "";
      var maybeList = $("pc-maybe"); maybeList.innerHTML = "";
      var flagged = 0, maybe = 0;
      spans.forEach(function (s) { s.classList.remove("maybe", "skip"); });
      if (aligned) j.result.forEach(function (w, k) { var i = w.i != null ? w.i : k; if (w.skipped && spans[i]) { spans[i].classList.remove("ok"); spans[i].classList.add("skip"); } });
      j.result.forEach(function (w, k) {
        var i = w.i != null ? w.i : k;
        if (w.ok) return;
        var sure = !!w.sure;
        if (sure) flagged++; else maybe++;
        if (aligned && spans[i]) { spans[i].classList.remove("ok"); spans[i].classList.add(sure ? "flag" : "maybe"); }
        var li = document.createElement("li"); li.dataset.i = i;
        var word = aligned && spans[i] ? spans[i].textContent : "Word " + (i + 1);
        li.innerHTML = '<span class="pc-nw" dir="rtl" lang="ar"></span><div class="pc-nt"></div>' +
          '<div class="pc-yn" role="group" aria-label="Is this remark right?"><button type="button" data-v="right">Right</button><button type="button" data-v="wrong">Wrong</button></div>';
        li.querySelector(".pc-nw").textContent = word;
        var nt = li.querySelector(".pc-nt");
        w.notes.forEach(function (n) {
          if (sure && !n.sure) return;
          var p = document.createElement("p"); p.textContent = n.en;
          var ar = document.createElement("span"); ar.className = "ar"; ar.dir = "rtl"; ar.lang = "ar"; ar.textContent = n.ar;
          p.appendChild(ar); nt.appendChild(p);
        });
        (sure ? list : maybeList).appendChild(li);
      });
      $("pc-maybe-box").hidden = !maybe;
      $("pc-maybe-n").textContent = maybe;
      if (!flagged) {
        var li0 = document.createElement("li"); li0.className = "pc-none";
        li0.textContent = j.strictness === "gentle"
          ? "No remarks. (For children the check only speaks when it is very sure.) Did the reader make a mistake? Tap the word above."
          : "No remarks. Did the reader make a mistake? Tap the word above.";
        list.appendChild(li0);
      }
      $("pc-saved").textContent = ""; $("pc-note").value = "";
      $("pc-result").hidden = false;
      if (j.words > 2 && flagged >= j.words && !j.result.some(function (w) { return w.skipped; })) { say("Every word has a remark: was the verse recited the one chosen above? If not, choose it and record again.", "bad"); return; }
      say(flagged ? flagged + " word" + (flagged > 1 ? "s" : "") + " with a remark. Please review them below." : "Done. Please review below.", "good");
    }

    $("pc-maybe").addEventListener("click", function (e) { $("pc-notes").onclickShared(e); });
    $("pc-notes").onclickShared = function (e) {
      var b = e.target.closest("button[data-v]"); if (!b || !current) return;
      var li = b.closest("li");
      current.marks[li.dataset.i] = b.dataset.v;
      li.querySelectorAll("button[data-v]").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    };
    $("pc-notes").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-v]"); if (!b || !current) return;
      var li = b.closest("li");
      current.marks[li.dataset.i] = b.dataset.v;
      li.querySelectorAll("button[data-v]").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    });
    textEl.addEventListener("click", function (e) {
      var w = e.target.closest(".pc-w"); if (!w || !current || w.classList.contains("flag") || w.classList.contains("maybe") || w.classList.contains("skip")) return;
      var i = w.dataset.i;
      if (current.marks[i] === "missed") { delete current.marks[i]; w.classList.remove("missed"); }
      else { current.marks[i] = "missed"; w.classList.add("missed"); }
    });
    $("pc-save").addEventListener("click", function () {
      if (!current) return;
      fetch(opt.reviewUrl + current.id + "/review", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF": opt.csrf },
        body: JSON.stringify({ marks: current.marks, note: $("pc-note").value })
      }).then(function (r) { $("pc-saved").textContent = r.ok ? "Saved. Thank you." : "Not saved. Please try again."; });
    });
  }

  window.NHPracticeCheck = { start: start, hear: hear };
})();
