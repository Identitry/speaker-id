

// Minimal client for the FastAPI endpoints used by the web UI.
// No bundler required; this file can be included directly in index.html.
// A global `window.SpeakerApi` object is exported for convenience.

(function () {
  async function postFile(url, file, query = {}) {
    const qs = new URLSearchParams(query).toString();
    const full = qs ? `${url}?${qs}` : url;

    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch(full, { method: "POST", body: fd });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      const err = new Error(`HTTP ${res.status}: ${txt || res.statusText}`);
      err.status = res.status;
      err.body = txt;
      throw err;
    }
    return res.json();
  }

  async function getJson(url) {
    const res = await fetch(url);
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      const err = new Error(`HTTP ${res.status}: ${txt || res.statusText}`);
      err.status = res.status;
      err.body = txt;
      throw err;
    }
    return res.json();
  }

  const SpeakerApi = {
    /**
     * Enroll a speaker by uploading a WAV file.
     * @param {File|Blob} file - WAV audio (mono recommended)
     * @param {string} name - Display name for the speaker
     * @returns {Promise<{ok: boolean, name: string}>}
     */
    enroll(file, name) {
      if (!file) throw new Error("enroll: file is required");
      if (!name) throw new Error("enroll: name is required");
      return postFile("/api/enroll", file, { name });
    },

    /**
     * Identify the speaker in a WAV file.
     * @param {File|Blob} file - WAV audio (mono recommended)
     * @param {number} [threshold=0.82] - Acceptance threshold [0..1]
     * @returns {Promise<{speaker:string, confidence:number, topN:Array<{name:string, score:number}>}>}
     */
    identify(file, threshold = 0.82) {
      if (!file) throw new Error("identify: file is required");
      return postFile("/api/identify", file, { threshold });
    },

    /** Check API health */
    health() {
      return getJson("/api/health");
    },
  };

  // Expose globally
  window.SpeakerApi = SpeakerApi;
})();
