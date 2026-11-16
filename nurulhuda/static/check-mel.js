/* Whisper's 80-band log-mel spectrogram, the same numbers as faster_whisper.FeatureExtractor(feature_size=80)(audio,
   padding=0): 16 kHz audio, 400-point Hann window, hop 160, reflect padding, Slaney mel filters, log10, top 8 dB kept,
   then (x + 4) / 4. Used by the Practice check to feed the HisnLabs tajweed-v2 model in the browser. */
(function (root) {
  "use strict";
  var N_FFT = 400, HOP = 160, BINS = N_FFT / 2 + 1, SR = 16000;
  var tables = null;

  function melFilters(nMels) {
    var fft = new Float64Array(BINS), i, m;
    for (i = 0; i < BINS; i++) fft[i] = i * SR / N_FFT;
    var maxMel = 45.245640471924965, fSp = 200 / 3, minLogHz = 1000, minLogMel = minLogHz / fSp,
        logstep = Math.log(6.4) / 27, freqs = new Float64Array(nMels + 2);
    for (m = 0; m < nMels + 2; m++) {
      var mel = maxMel * m / (nMels + 1);
      freqs[m] = mel >= minLogMel ? minLogHz * Math.exp(logstep * (mel - minLogMel)) : fSp * mel;
    }
    var w = [];
    for (m = 0; m < nMels; m++) {
      var row = new Float32Array(BINS), enorm = 2 / (freqs[m + 2] - freqs[m]);
      for (i = 0; i < BINS; i++) {
        var lower = (fft[i] - freqs[m]) / (freqs[m + 1] - freqs[m]);
        var upper = (freqs[m + 2] - fft[i]) / (freqs[m + 2] - freqs[m + 1]);
        row[i] = Math.max(0, Math.min(lower, upper)) * enorm;
      }
      var lo = 0, hi = BINS;  // only the non-zero part of each filter is used
      while (lo < BINS && row[lo] === 0) lo++;
      while (hi > lo && row[hi - 1] === 0) hi--;
      w.push({ lo: lo, hi: hi, row: row });
    }
    return w;
  }

  function setup() {
    if (tables) return tables;
    var win = new Float64Array(N_FFT), cos = new Float64Array(N_FFT), sin = new Float64Array(N_FFT), i;
    for (i = 0; i < N_FFT; i++) {
      win[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N_FFT);  // np.hanning(401)[:-1]
      cos[i] = Math.cos(2 * Math.PI * i / N_FFT);
      sin[i] = Math.sin(2 * Math.PI * i / N_FFT);
    }
    tables = { win: win, cos: cos, sin: sin, mel: melFilters(80) };
    return tables;
  }

  /* audio: Float32Array at 16 kHz. Returns {data: Float32Array [80 * frames], frames} (row-major, band first). */
  function logMel(audio, maxFrames) {
    var T = setup(), pad = N_FFT / 2, n = audio.length, len = n + 2 * pad, i, k, f, m;
    var x = new Float64Array(len);
    for (i = 0; i < len; i++) {
      var j = i - pad;
      if (j < 0) j = -j; else if (j >= n) j = 2 * (n - 1) - j;  // reflect
      x[i] = audio[Math.min(Math.max(j, 0), n - 1)];
    }
    var frames = Math.floor((len - N_FFT) / HOP) + 1 - 1;  // the last STFT frame is dropped, like Whisper
    if (maxFrames) frames = Math.min(frames, maxFrames);
    var power = new Float64Array(BINS), seg = new Float64Array(N_FFT);
    var out = new Float32Array(80 * frames), top = -Infinity;
    for (f = 0; f < frames; f++) {
      var off = f * HOP;
      for (i = 0; i < N_FFT; i++) seg[i] = x[off + i] * T.win[i];
      for (k = 0; k < BINS; k++) {
        var re = 0, im = 0, idx = 0;
        for (i = 0; i < N_FFT; i++) {
          re += seg[i] * T.cos[idx]; im -= seg[i] * T.sin[idx];
          idx += k; if (idx >= N_FFT) idx -= N_FFT;
        }
        power[k] = re * re + im * im;
      }
      for (m = 0; m < 80; m++) {
        var F = T.mel[m], s = 0;
        for (k = F.lo; k < F.hi; k++) s += F.row[k] * power[k];
        var v = Math.log10(Math.max(s, 1e-10));
        out[m * frames + f] = v;
        if (v > top) top = v;
      }
    }
    for (i = 0; i < out.length; i++) out[i] = (Math.max(out[i], top - 8) + 4) / 4;
    return { data: out, frames: frames };
  }

  root.NHMel = { logMel: logMel };
  if (typeof module !== "undefined") module.exports = root.NHMel;
})(typeof window !== "undefined" ? window : globalThis);
