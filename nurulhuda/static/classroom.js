/* Classroom activity, raised hands and backgrounds, on top of the Daily call frame.
   Records times only (microphone or camera off and back on, raised hand, lost connection). Never sound or video.
   The server (classroom.py) decides what is reportable: a microphone off for more than 15 seconds, any camera-off. */
(function () {
  "use strict";
  var HAND_BEFORE_MS = 60000, NUDGE_AFTER_MS = 15000;

  function start(opt) {
    var frame = opt.frame, queue = [], state = { mic: null, camera: null }, net = null;
    var handUp = null, lastHand = 0, joined = false, nudgeTimer = null;
    var bar = document.getElementById("cls-status"), hands = document.getElementById("cls-hands");
    var handBtn = document.getElementById("cls-hand"), toast = document.getElementById("cls-toast");
    var remote = {};   // session_id -> {name, mic, camera}

    function say(msg) {
      if (!toast) { return; }
      toast.textContent = msg; toast.hidden = false;
      clearTimeout(toast._t); toast._t = setTimeout(function () { toast.hidden = true; }, 7000);
    }

    // --- intervals --------------------------------------------------------------------------------
    function push(kind, startedMs, cause, extra) {
      var item = { kind: kind, secs: Math.max(0, (Date.now() - startedMs) / 1000), endedAt: Date.now(), cause: cause || "unknown" };
      if (extra) { for (var k in extra) { item[k] = extra[k]; } }
      queue.push(item);
    }
    function flush(final) {
      if (!queue.length) { return; }
      var items = queue.splice(0).map(function (it) {
        var out = { kind: it.kind, secs: Math.round(it.secs * 10) / 10, ago: Math.max(0, (Date.now() - it.endedAt) / 1000), cause: it.cause };
        if (it.announced) { out.announced = true; }
        return out;
      });
      fetch(opt.eventsUrl, { method: "POST", keepalive: !!final, credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF": opt.csrf }, body: JSON.stringify({ items: items }) })
        .catch(function () { if (!final) { Array.prototype.unshift.apply(queue, items.map(function (i) {
          return { kind: i.kind, secs: i.secs, endedAt: Date.now() - i.ago * 1000, cause: i.cause, announced: i.announced }; })); } });
    }
    setInterval(function () { flush(false); }, 10000);

    function trackState(t) {
      // Daily: state is "playable"/"sendable"/"loading" when on; "off" (off.byUser, off.byBandwidth), "blocked", "interrupted".
      if (!t) { return { on: false, cause: "unknown" }; }
      if (t.state === "playable" || t.state === "sendable" || t.state === "loading") { return { on: true }; }
      if (t.state === "blocked") { return { on: false, cause: "device" }; }
      if (t.state === "interrupted") { return { on: false, cause: "network" }; }
      if (t.off && t.off.byBandwidth) { return { on: false, cause: "network" }; }
      if (t.off && t.off.byUser) { return { on: false, cause: "user" }; }
      return { on: false, cause: "unknown" };
    }

    function localUpdate(p) {
      if (!p || !p.tracks) { return; }
      [["mic", p.tracks.audio], ["camera", p.tracks.video]].forEach(function (pair) {
        var kind = pair[0], s = trackState(pair[1]), cur = state[kind];
        if (cur === null) { state[kind] = s.on ? { on: true } : { on: false, since: Date.now(), cause: s.cause, announced: kind === "mic" && Date.now() - lastHand < HAND_BEFORE_MS }; return; }
        if (cur.on && !s.on) {
          state[kind] = { on: false, since: Date.now(), cause: s.cause, announced: kind === "mic" && (handUp !== null || Date.now() - lastHand < HAND_BEFORE_MS) };
          if (kind === "mic" && s.cause === "user" && !state.mic.announced) {
            clearTimeout(nudgeTimer);
            nudgeTimer = setTimeout(function () {
              if (state.mic && !state.mic.on && !state.mic.announced) { say(opt.text.nudge); }
            }, NUDGE_AFTER_MS);
          }
          if (kind === "camera" && s.cause === "user") { say(opt.text.cameraOff); }
        } else if (!cur.on && s.on) {
          push(kind, cur.since, cur.cause, { announced: cur.announced });
          state[kind] = { on: true };
          if (kind === "mic") { clearTimeout(nudgeTimer); if (handUp !== null) { setHand(false); } }
        }
      });
      paint();
    }

    function closeAll(cause) {
      ["mic", "camera"].forEach(function (k) {
        var cur = state[k];
        if (cur && !cur.on) { push(k, cur.since, cur.cause === "user" ? "user" : (cur.cause || cause), { announced: cur.announced }); state[k] = null; }
      });
      if (net) { push("network", net, "network"); net = null; }
      if (handUp !== null) { push("hand", handUp, "user"); handUp = null; }
    }

    // --- raised hand --------------------------------------------------------------------------------
    function setHand(up) {
      if (up && handUp === null) { handUp = Date.now(); lastHand = handUp; }
      else if (!up && handUp !== null) { push("hand", handUp, "user"); handUp = null; }
      if (handBtn) { handBtn.setAttribute("aria-pressed", String(handUp !== null)); handBtn.textContent = handUp !== null ? opt.text.lower : opt.text.raise; }
      if (joined) { frame.sendAppMessage({ nhh: { up: handUp !== null, name: opt.name, role: opt.role } }, "*"); }
      paintHands();
    }
    var raised = {};
    function paintHands() {
      if (!hands) { return; }
      var names = Object.keys(raised).map(function (k) { return raised[k]; });
      if (handUp !== null) { names.unshift(opt.text.you); }
      hands.hidden = !names.length;
      hands.textContent = names.length ? "✋ " + names.join(", ") + " " + opt.text.raised : "";
    }
    if (handBtn) { handBtn.onclick = function () { setHand(handUp === null); }; }

    // --- who is in the room, with microphone and camera indicators ---------------------------------
    function paint() {
      if (!bar) { return; }
      var parts = [];
      Object.keys(remote).forEach(function (id) {
        var r = remote[id];
        parts.push(r.name + ": " + (r.mic ? opt.text.micOn : opt.text.micOff) + ", " + (r.camera ? opt.text.camOn : opt.text.camOff));
      });
      bar.textContent = parts.length ? parts.join(" · ") : opt.text.waiting;
    }
    function remoteUpdate(p) {
      if (!p || p.local) { return; }
      remote[p.session_id] = { name: p.user_name || opt.text.guest,
        mic: trackState(p.tracks && p.tracks.audio).on, camera: trackState(p.tracks && p.tracks.video).on };
      paint();
    }

    frame.on("joined-meeting", function (e) {
      joined = true;
      var ps = frame.participants();
      localUpdate(ps.local);
      Object.keys(ps).forEach(function (k) { if (k !== "local") { remoteUpdate(ps[k]); } });
      applyBackground(opt.background.mode);
    });
    frame.on("participant-joined", function (e) { remoteUpdate(e.participant); if (handUp !== null) { setHand(true); } });
    frame.on("participant-updated", function (e) { if (e.participant.local) { localUpdate(e.participant); } else { remoteUpdate(e.participant); } });
    frame.on("participant-left", function (e) {
      delete remote[e.participant.session_id]; delete raised[e.participant.session_id]; paint(); paintHands();
    });
    frame.on("network-connection", function (e) {
      if (e.event === "interrupted" && net === null) { net = Date.now(); }
      else if (e.event === "connected" && net !== null) { push("network", net, "network"); net = null; }
    });
    frame.on("app-message", function (e) {
      if (e && e.data && e.data.nhh) {
        if (e.data.nhh.up) { raised[e.fromId] = e.data.nhh.name || opt.text.guest; } else { delete raised[e.fromId]; }
        paintHands();
      }
    });
    frame.on("left-meeting", function () { closeAll("left"); flush(true); });
    window.addEventListener("pagehide", function () { closeAll("left"); flush(true); });

    // --- backgrounds --------------------------------------------------------------------------------
    var bgSel = document.getElementById("cls-bg"), bgNote = document.getElementById("cls-bg-note"), bgBuffer = null;
    function supported() {
      try { var s = window.DailyIframe.supportedBrowser(); return !!(s && s.supported && s.supportsVideoProcessing); }
      catch (e) { return false; }
    }
    function applyBackground(mode) {
      if (!joined) { return; }
      if (!supported()) {
        if (bgSel) { bgSel.disabled = true; }
        if (bgNote) { bgNote.hidden = false; }
        return;
      }
      if (bgSel) { bgSel.value = mode; }
      if (mode === "blur") {
        frame.updateInputSettings({ video: { processor: { type: "background-blur", config: { strength: opt.background.strength } } } }).catch(function () {});
      } else if (mode === "branded" && opt.background.image) {
        var go = function (src) {
          frame.updateInputSettings({ video: { processor: { type: "background-image", config: { source: src } } } })
            .catch(function () { frame.updateInputSettings({ video: { processor: { type: "background-blur", config: { strength: opt.background.strength } } } }).catch(function () {}); });
        };
        if (bgBuffer) { go(bgBuffer.slice(0)); }
        else {
          fetch(opt.background.image).then(function (r) { return r.arrayBuffer(); })
            .then(function (b) { bgBuffer = b; go(b.slice(0)); })
            .catch(function () { go(new URL(opt.background.image, location.href).href); });
        }
      } else {
        frame.updateInputSettings({ video: { processor: { type: "none" } } }).catch(function () {});
      }
    }
    if (bgSel) { bgSel.onchange = function () { applyBackground(bgSel.value); }; }
    frame.on("video-processor-error", function () {
      if (bgNote) { bgNote.hidden = false; }
    });

    paint();
    return { setHand: setHand };
  }

  window.NHClassroom = { start: start };
})();
