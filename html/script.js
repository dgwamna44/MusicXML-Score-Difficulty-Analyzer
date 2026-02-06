// script.js (ES module)

function initTooltips() {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]'),
  );
  tooltipTriggerList.forEach((el) => {
    const tooltip = new bootstrap.Tooltip(el, {
      placement: "right",
      trigger: "hover focus",
      delay: { show: 700, hide: 100 },
    });
    el.addEventListener("click", () => {
      tooltip.hide();
      el.blur();
    });
    el.addEventListener("mouseleave", () => tooltip.hide());
  });
}

function buildTimelineTicks(trackEl, ticks, totalMeasures) {
  if (!trackEl) return;
  trackEl.querySelectorAll(".timeline-tick").forEach((node) => node.remove());
  ticks.forEach((tick) => {
    const left = totalMeasures ? (tick.measure / totalMeasures) * 100 : 0;
    const tickEl = document.createElement("div");
    tickEl.className = `timeline-tick ${tick.tempo ? "tick-tempo" : "tick-meter"}`;
    tickEl.style.left = `${Math.max(0, Math.min(100, left))}%`;

    const above = document.createElement("div");
    above.className = "tick-above";
    above.textContent = tick.tempo || tick.meter || "";
    tickEl.appendChild(above);

    if (tick.tempo && tick.meter) {
      const above2 = document.createElement("div");
      above2.className = "tick-above";
      above2.textContent = tick.meter;
      tickEl.appendChild(above2);
    }

    const mark = document.createElement("div");
    mark.className = "tick-mark";
    tickEl.appendChild(mark);

    const below = document.createElement("div");
    below.className = "tick-below";
    below.textContent = tick.key || "";
    tickEl.appendChild(below);

    trackEl.appendChild(tickEl);
  });
}

function getMarkerByLabel(label) {
  const rows = [...document.querySelectorAll(".bar-row")];
  const row = rows.find(
    (r) => r.querySelector(".bar-head span")?.textContent.trim() === label,
  );
  return row ? row.querySelector(".bar .marker") : null;
}

function setMarkerPositions(confidences, opts = {}) {
  if (!confidences) return;
  const emptyLabel = opts.emptyLabel ?? "--";
  const labelMap = {
    availability: "Inst. Availability",
    dynamics: "Dynamics",
    key: "Key",
    range: "Range",
    tempo: "Tempo",
    duration: "Duration",
    articulation: "Articulation",
    rhythm: "Rhythm",
    meter: "Meter",
  };
  Object.entries(confidences).forEach(([key, value]) => {
    const label = labelMap[key];
    if (!label) return;
    const marker = getMarkerByLabel(label);
    if (!marker) return;
    const clamped = value == null ? 0 : Math.max(0, Math.min(0.99, value));
    marker.style.left = `${clamped * 100}%`;
    const scoreEl = document.querySelector(`[data-bar-score="${key}"]`);
    if (scoreEl) {
      if (value == null) {
        scoreEl.textContent = emptyLabel;
      } else {
        const pct = Math.round(value * 100);
        scoreEl.textContent = `${pct}%`;
      }
    }
  });
}

function initGradeOptions() {
  const select = document.getElementById("targetGradeSelect");
  const fullToggle = document.getElementById("fullGradeSearch");
  if (!select || !fullToggle) return;

  const baseOptions = [
    { value: "0.5", label: ".5" },
    { value: "1", label: "1" },
    { value: "2", label: "2" },
    { value: "3", label: "3" },
    { value: "4", label: "4" },
    { value: "5", label: "5+" },
  ];

  const fullOptions = [
    { value: "0.5", label: ".5" },
    { value: "1", label: "1" },
    { value: "1.5", label: "1.5" },
    { value: "2", label: "2" },
    { value: "2.5", label: "2.5" },
    { value: "3", label: "3" },
    { value: "3.5", label: "3.5" },
    { value: "4", label: "4" },
    { value: "4.5", label: "4.5" },
    { value: "5", label: "5+" },
  ];

  const renderOptions = (options) => {
    const current = select.value;
    select.innerHTML = "";
    options.forEach(({ value, label }) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      select.appendChild(opt);
    });
    if (options.some((opt) => opt.value === current)) {
      select.value = current;
    }
  };

  const sync = () => {
    renderOptions(fullToggle.checked ? fullOptions : baseOptions);
  };

  fullToggle.addEventListener("change", sync);
  sync();
}

function initAnalysisRequest() {
  const API_BASE = "http://127.0.0.1:5000";
  window.analysisResult = null;
  const analyzeBtn = document.getElementById("analyzeBtn");
  const targetOnly = document.getElementById("targetOnly");
  const stringsOnly = document.getElementById("stringsOnly");
  const fullGrade = document.getElementById("fullGradeSearch");
  const targetGrade = document.getElementById("targetGradeSelect");
  const modalEl = document.getElementById("progressModal");
  const progressBars = document.getElementById("progressBars");
  const progressText = document.getElementById("progressText");
  const progressOkBtn = document.getElementById("progressOkBtn");
  const progressTimer = document.getElementById("progressTimer");
  const modal = modalEl ? new bootstrap.Modal(modalEl) : null;

  if (!analyzeBtn) return;

  if (progressOkBtn) {
    progressOkBtn.addEventListener("click", () => {
      var measures = window.analysisResult.result.total_measures;
      setMarkerPositions(window.analysisResult?.result?.confidences);
      document.querySelector("#startingMeasureLabel").textContent = 1;
      document.querySelector("#endingMeasureLabel").textContent = measures;
    });
  }

function toMeasureArray(data) {
  if (!data) return [];

  // already an array of objects
  if (Array.isArray(data)) return data.map(x => x.measure).filter(Number.isFinite);

  // single object with a measure
  if (typeof data === "object" && data !== null && "measure" in data) {
    return Number.isFinite(data.measure) ? [data.measure] : [];
  }

  // object-of-objects
  return Object.values(data)
    .map(x => x?.measure)
    .filter(Number.isFinite);
}

function prepareTimelineTicks() {
  const marks = {};

  const analysisData = window.analysisResult?.result;
  const notes = analysisData?.analysis_notes || {};
  const keyData = notes.key;
  const tempoData = notes.tempo;
  const meterData = notes.meter?.meter_data;

  marks.Key   = toMeasureArray(keyData);
  marks.Tempo = toMeasureArray(tempoData);
  marks.Meter = toMeasureArray(meterData);

  return marks; // (optional) useful to return it
}

window.prepareTimelineTicks = prepareTimelineTicks;
  const labelMap = {
    range: "Range",
    key: "Key",
    articulation: "Articulation",
    rhythm: "Rhythm",
    dynamics: "Dynamics",
    availability: "Availability",
    tempo: "Tempo",
    duration: "Duration",
    meter: "Meter",
  };

  const colorMap = {
    range: "orange",
    key: "pink",
    articulation: "green",
    rhythm: "blue",
    dynamics: "red",
    availability: "brown",
    tempo: "yellow",
    duration: "light-green",
    meter: "indigo",
  };

  const barIds = Object.keys(labelMap).reduce((acc, key) => {
    acc[key] = {
      bar: `progress-${key}`,
      pct: `progress-${key}-pct`,
      label: `progress-${key}-label`,
    };
    return acc;
  }, {});

  const ensureProgressBars = () => {
    if (!progressBars) return;
    progressBars.innerHTML = "";
    Object.entries(labelMap).forEach(([key, label]) => {
      const wrapper = document.createElement("div");
      wrapper.className = "progress-item";
      const title = document.createElement("div");
      title.className = "label";
      title.textContent = label;
      const row = document.createElement("div");
      row.className = "progress-row";
      const head = document.createElement("div");
      head.className = "progress-head";
      const headLabel = document.createElement("div");
      headLabel.className = "label";
      headLabel.id = barIds[key].label;
      headLabel.textContent = label;
      const pct = document.createElement("div");
      pct.className = "progress-percent";
      pct.id = barIds[key].pct;
      pct.textContent = "0%";
      head.appendChild(headLabel);
      head.appendChild(pct);
      const barWrap = document.createElement("div");
      barWrap.className = "progress";
      const bar = document.createElement("div");
      bar.className = `progress-bar ${colorMap[key] || ""}`;
      bar.id = barIds[key].bar;
      bar.style.width = "0%";
      barWrap.appendChild(bar);
      row.appendChild(barWrap);
      wrapper.appendChild(head);
      wrapper.appendChild(row);
      progressBars.appendChild(wrapper);
    });
  };

  analyzeBtn.addEventListener("click", async () => {
    const fileInput = document.getElementById("fileInput");
    const file = fileInput?.files?.[0];
    if (!file) {
      alert("Please choose a score file.");
      return;
    }

    const form = new FormData();
    form.append("score_file", file);
    form.append("target_only", String(Boolean(targetOnly?.checked)));
    form.append("strings_only", String(Boolean(stringsOnly?.checked)));
    form.append("full_grade_analysis", String(Boolean(fullGrade?.checked)));
    form.append("target_grade", String(Number(targetGrade?.value || 2)));
    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.error || "Failed to start analysis.");
      return;
    }

    const { job_id: jobId } = await res.json();
    if (!jobId) {
      alert("No job id returned.");
      return;
    }

    window.lastJobId = jobId;
    window.analysisResult = null;

    ensureProgressBars();
    if (progressText) progressText.textContent = "Starting analysis...";
    if (progressOkBtn) progressOkBtn.disabled = true;
    if (progressTimer) progressTimer.textContent = "00m00s";
    modal?.show();
    const startedAt = performance.now();
    let timerId = null;
    if (progressTimer) {
      timerId = setInterval(() => {
        const elapsed = (performance.now() - startedAt) / 1000;
        const minutes = Math.floor(elapsed / 60);
        const seconds = Math.floor(elapsed % 60);
        progressTimer.textContent = `${String(minutes).padStart(2, "0")}m${String(seconds).padStart(2, "0")}s`;
      }, 200);
    }

    const es = new EventSource(`${API_BASE}/api/progress/${jobId}`);
    es.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      if (data.type === "observed") {
        const pct = data.total ? Math.round((data.idx / data.total) * 100) : 0;
        const analyzerKey =
          data.analyzer === "key_range" && data.label
            ? data.label
            : data.analyzer === "tempo_duration" && data.label
              ? data.label
              : data.analyzer;
        const ids = barIds[analyzerKey];
        const bar = ids ? document.getElementById(ids.bar) : null;
        const pctEl = ids ? document.getElementById(ids.pct) : null;
        const labelEl = ids ? document.getElementById(ids.label) : null;
        if (bar) bar.style.width = `${pct}%`;
        if (pctEl) pctEl.textContent = `${pct}%`;
        if (labelEl) {
          const name = labelMap[analyzerKey] || analyzerKey;
          labelEl.textContent = name;
        }
        if (progressText) {
          const name = labelMap[analyzerKey] || analyzerKey;
          progressText.textContent = `${name} grade ${data.grade} - ${pct}%`;
        }
      } else if (data.type === "analyzer") {
        const analyzerKey =
          data.analyzer === "key_range"
            ? "range"
            : data.analyzer === "tempo_duration"
              ? "tempo"
              : data.analyzer;
        const ids = barIds[analyzerKey];
        const bar = ids ? document.getElementById(ids.bar) : null;
        const pctEl = ids ? document.getElementById(ids.pct) : null;
        const labelEl = ids ? document.getElementById(ids.label) : null;
        if (bar && bar.style.width === "0%") {
          bar.style.width = "100%";
        }
        if (pctEl && pctEl.textContent === "0%") {
          pctEl.textContent = "100%";
        }
        if (labelEl) {
          labelEl.textContent = labelMap[analyzerKey] || analyzerKey;
        }
        if (data.analyzer === "tempo_duration") {
          const tempoIds = barIds.tempo;
          const durationIds = barIds.duration;
          const tempoBar = tempoIds
            ? document.getElementById(tempoIds.bar)
            : null;
          const tempoPct = tempoIds
            ? document.getElementById(tempoIds.pct)
            : null;
          const durationBar = durationIds
            ? document.getElementById(durationIds.bar)
            : null;
          const durationPct = durationIds
            ? document.getElementById(durationIds.pct)
            : null;
          if (tempoBar) tempoBar.style.width = "100%";
          if (tempoPct) tempoPct.textContent = "100%";
          if (durationBar) durationBar.style.width = "100%";
          if (durationPct) durationPct.textContent = "100%";
        }
      } else if (data.type === "done") {
        Object.values(barIds).forEach((ids) => {
          const bar = document.getElementById(ids.bar);
          const pctEl = document.getElementById(ids.pct);
          if (bar) bar.style.width = "100%";
          if (pctEl) pctEl.textContent = "100%";
        });
        if (progressText) progressText.textContent = "Done.";
        if (progressOkBtn) progressOkBtn.disabled = false;
        if (timerId) clearInterval(timerId);
        es.close();
        fetch(`${API_BASE}/api/result/${jobId}`)
          .then((r) => r.json())
          .then((result) => {
            window.analysisResult = result;
            console.log("Analysis result:", result);
          })
          .catch((err) => console.error("Failed to fetch result:", err));
        progressOkBtn.addEventListener("click", async () => {
          setMarkerPositions(result?.result?.confidences);
        });
      }
    };

    es.onerror = () => {
      es.close();
      if (progressText) progressText.textContent = "Connection lost.";
      if (timerId) clearInterval(timerId);
      console.warn("Progress stream error; analysisResult not set yet.");
    };
  });
}

function extractScoreTitle(text) {
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(text, "application/xml");
    const parserError = doc.getElementsByTagName("parsererror")[0];
    if (parserError) return null;

    const pickText = (nodes) => {
      for (const node of nodes) {
        const value = node?.textContent?.trim();
        if (value) return value;
      }
      return null;
    };

    const byTag = (name) => pickText(doc.getElementsByTagName(name));
    const byTagNs = (name) => pickText(doc.getElementsByTagNameNS("*", name));

    return (
      byTag("work-title") ||
      byTagNs("work-title") ||
      byTag("movement-title") ||
      byTagNs("movement-title") ||
      byTag("credit-words") ||
      byTagNs("credit-words") ||
      byTag("title") ||
      byTagNs("title")
    );
  } catch {
    return null;
  }
}

async function initVerovio() {
  console.log("initVerovio() starting...");

  const url = new URL(location.href);
  url.searchParams.delete("view");
  if (url.hash && url.hash.includes("view=")) url.hash = "";
  history.replaceState({}, "", url.toString());
  try {
    localStorage.clear();
    sessionStorage.clear();
  } catch {}

  await import("https://editor.verovio.org/javascript/app/verovio-app.js");
  console.log(
    "Verovio loaded:",
    typeof window.Verovio,
    typeof window.Verovio?.App,
  );

  const appEl = document.getElementById("app");
  if (!appEl) return console.error("Missing #app element");

  appEl.style.minHeight = "800px";
  appEl.style.border = "1px solid lightgray";

  let app = new window.Verovio.App(appEl, {
    defaultView: "document",
    documentZoom: 3,
  });

  function ensureZoomWrapper() {
    let root = appEl.querySelector(".verovio-zoom-root");
    if (!root) {
      root = document.createElement("div");
      root.className = "verovio-zoom-root";
      while (appEl.firstChild) root.appendChild(appEl.firstChild);
      appEl.appendChild(root);
    }
    return root;
  }

  function setCssZoomPercent(pct) {
    pct = Number(pct);
    if (!Number.isFinite(pct)) return;
    pct = Math.max(25, Math.min(400, pct));
    const scale = pct / 100;

    const root = ensureZoomWrapper();
    root.style.transform = `scale(${scale})`;

    const unscaledWidth = root.scrollWidth / scale;
    const unscaledHeight = root.scrollHeight / scale;
    root.style.width = `${unscaledWidth}px`;
    root.style.height = `${unscaledHeight}px`;
  }

  const zoomInput = document.getElementById("zoomPct");
  const zoomApply = document.getElementById("zoomApply");
  const fileInput = document.getElementById("fileInput");
  const titleEl = document.getElementById("scoreTitle");
  const clearBtn = document.getElementById("clearBtn");
  const loadLabel = document.querySelector(".score-load");
  const clearButton = document.querySelector(".score-clear");
  const scoreActions = document.querySelectorAll(".score-action");
  const targetOnlyToggle = document.getElementById("targetOnly");
  const observedPane = document.getElementById("observedGradePane");

  let hasActiveScore = false;

  const syncScoreActions = () => {
    if (loadLabel) {
      loadLabel.classList.toggle("is-hidden", hasActiveScore);
      loadLabel.setAttribute(
        "aria-disabled",
        hasActiveScore ? "true" : "false",
      );
    }
    if (clearButton) {
      clearButton.classList.toggle("is-hidden", !hasActiveScore);
      clearButton.disabled = !hasActiveScore;
    }
    scoreActions.forEach((el) => {
      if (el !== clearButton && el !== loadLabel) return;
      el.style.pointerEvents = el.classList.contains("is-hidden") ? "none" : "";
    });
  };

  fileInput?.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const fallbackTitle = file.name.replace(/\.[^/.]+$/, "");
    if (titleEl) {
      titleEl.textContent = `Score Title: ${fallbackTitle}`;
    }

    hasActiveScore = true;
    syncScoreActions();

    try {
      const text = await file.text();
      window.__lastScoreText = text;
      const xmlTitle = extractScoreTitle(text);
      if (titleEl) {
        const cleanTitle =
          xmlTitle && xmlTitle.toLowerCase() !== "title"
            ? xmlTitle
            : fallbackTitle;
        titleEl.textContent = `Score Title: ${cleanTitle}`;
      }

      const head = text.slice(0, 300).toLowerCase();
      const looksLikeMei = head.includes("<mei");
      const looksLikeMusicXml =
        head.includes("<score-partwise") || head.includes("<score-timewise");

      if (!looksLikeMei && !looksLikeMusicXml) {
        console.warn(
          "File doesn't look like MEI or MusicXML. First 300 chars:",
          text.slice(0, 300),
        );
      }

      const p = app.loadData(text);
      if (p?.then) await p;

      console.log(
        "Loaded file:",
        file.name,
        "SVGs:",
        document.querySelectorAll("#app svg").length,
      );
    } catch (err) {
      console.error("Failed to load score:", err);
    }

    setCssZoomPercent(Number(zoomInput?.value || 100));
  });

  if (targetOnlyToggle && observedPane) {
    const sync = () =>
      (observedPane.style.display = targetOnlyToggle.checked ? "none" : "grid");
    targetOnlyToggle.addEventListener("change", sync);
    sync();
  }

  clearBtn?.addEventListener("click", () => {
    if (fileInput) fileInput.value = "";
    if (titleEl) titleEl.textContent = "Score Title: --";

    appEl.innerHTML = "";
    app = new window.Verovio.App(appEl, {
      defaultView: "document",
      documentZoom: 3,
    });

    hasActiveScore = false;
    syncScoreActions();
    console.log("Verovio app reset.");
    setMarkerPositions(
      {
        availability: null,
        dynamics: null,
        key: null,
        range: null,
        tempo: null,
        duration: null,
        articulation: null,
        rhythm: null,
        meter: null,
      },
      { emptyLabel: "--" },
    );
  });

  zoomApply?.addEventListener("click", () =>
    setCssZoomPercent(Number(zoomInput?.value || 100)),
  );
  zoomInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") setCssZoomPercent(Number(zoomInput.value || 100));
  });

  syncScoreActions();
}

// Run immediately (DOM is already present because your script tag is at the bottom)
initTooltips();
initGradeOptions();
initAnalysisRequest();
initVerovio().catch((err) => console.error("initVerovio failed:", err));
