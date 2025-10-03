

/**
 * Front-end glue for the minimal Speaker-ID UI.
 *
 * This file binds the HTML forms and buttons in `index.html` to the FastAPI
 * endpoints exposed under `/api`.
 *
 * Endpoints used:
 *   POST /api/identify         -> identify an uploaded clip
 *   POST /api/enroll?name=...  -> enroll one clip for a given user
 *   POST /api/rebuild_centroids-> admin: rebuild master centroids
 *   GET  /api/profiles         -> list enrolled profile names
 */

// Small query helpers -------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

// Pretty-print JSON into a <pre> block
function showJSON(el, obj) {
  try {
    el.textContent = JSON.stringify(obj, null, 2);
  } catch (e) {
    el.textContent = String(obj);
  }
}

// Build FormData with a single file field named "file"
function buildFormDataFromFileInput(inputEl) {
  const file = inputEl.files && inputEl.files[0];
  if (!file) throw new Error("No file selected");
  const fd = new FormData();
  fd.append("file", file, file.name || "clip.wav");
  return fd;
}

// Identify ------------------------------------------------------------------
(async function bindIdentify() {
  const form = $("#identify-form");
  const fileEl = $("#identify-file");
  const thrEl = $("#threshold");
  const out = $("#identify-result");
  if (!form) return;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    out.textContent = "Identifying…";
    try {
      const fd = buildFormDataFromFileInput(fileEl);
      const url = new URL("/api/identify", window.location.origin);
      const thr = thrEl.value.trim();
      if (thr) url.searchParams.set("threshold", thr);

      const res = await fetch(url, { method: "POST", body: fd });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      const json = await res.json();
      showJSON(out, json);
    } catch (err) {
      out.textContent = `Error: ${err.message || err}`;
    }
  });
})();

// Enroll --------------------------------------------------------------------
(async function bindEnroll() {
  const form = $("#enroll-form");
  const nameEl = $("#enroll-name");
  const fileEl = $("#enroll-file");
  const out = $("#enroll-result");
  if (!form) return;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    out.textContent = "Enrolling…";
    try {
      const name = (nameEl.value || "").trim();
      if (!name) throw new Error("Please enter a speaker name");

      const fd = buildFormDataFromFileInput(fileEl);
      const url = new URL("/api/enroll", window.location.origin);
      url.searchParams.set("name", name);

      const res = await fetch(url, { method: "POST", body: fd });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      const json = await res.json();
      showJSON(out, json);
    } catch (err) {
      out.textContent = `Error: ${err.message || err}`;
    }
  });
})();

// Admin: rebuild + profiles --------------------------------------------------
(async function bindAdmin() {
  const out = $("#admin-result");
  const btnRebuild = $("#rebuild-btn");
  const btnProfiles = $("#profiles-btn");
  if (btnRebuild) {
    btnRebuild.addEventListener("click", async () => {
      out.textContent = "Rebuilding centroids…";
      try {
        const res = await fetch("/api/rebuild_centroids", { method: "POST" });
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
        const json = await res.json();
        showJSON(out, json);
      } catch (err) {
        out.textContent = `Error: ${err.message || err}`;
      }
    });
  }

  if (btnProfiles) {
    btnProfiles.addEventListener("click", async () => {
      out.textContent = "Loading profiles…";
      try {
        const res = await fetch("/api/profiles");
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
        const json = await res.json();
        showJSON(out, json);
      } catch (err) {
        out.textContent = `Error: ${err.message || err}`;
      }
    });
  }
})();
