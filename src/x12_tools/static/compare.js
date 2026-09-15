// Compares 2+ parsed convention PDFs against each other -- a distinct job
// from convention.js's "read one or more conventions" (Convention
// importer): this tool's only output is what differs between the uploads,
// not a combined read-through of each one. Reuses /api/convention as-is
// (it already returns each file's own segment_table/segment_details);
// nothing server-side is specific to comparing.
(function () {
  "use strict";

  const form = document.getElementById("compare-form");
  if (!form) return; // not the compare page

  const fileInput = document.getElementById("pdf-file");
  const clearBtn = document.getElementById("clear-btn");
  const submitBtn = document.getElementById("submit-btn");
  const formError = document.getElementById("form-error");
  const results = document.getElementById("results");

  const { el, downloadControl } = window.tableTools;

  let showAllDiffs = false;

  clearBtn.addEventListener("click", () => {
    fileInput.value = "";
    results.hidden = true;
    results.innerHTML = "";
    formError.hidden = true;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;

    const files = fileInput.files;
    if (files.length < 2) {
      formError.textContent = "Choose at least 2 PDF files to compare.";
      formError.hidden = false;
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Comparing…";

    try {
      const body = new FormData();
      for (const file of files) body.append("files", file);
      const response = await fetch("/api/convention", { method: "POST", body });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "request failed");
      }
      renderResults(data.results);
    } catch (err) {
      formError.textContent = err.message;
      formError.hidden = false;
      results.hidden = true;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Compare conventions";
    }
  });

  // --- Diff building -------------------------------------------------------

  // A row's value for one comparable field -- null means the key (pos/ref)
  // wasn't present in this file at all, distinct from an empty string the
  // PDF actually had.
  function fieldValue(row, key) {
    if (!row) return null;
    if (key === "flagged") return row.flagged ? "*" : "";
    return row[key] ?? "";
  }

  const SEGMENT_DIFF_FIELDS = [
    ["segment_id", "Segment"],
    ["name", "Name"],
    ["requirement", "Req"],
    ["max_use", "Max Use"],
    ["repeat", "Repeat"],
    ["notes", "Notes"],
    ["usage", "Usage"],
    ["flagged", "Flagged"],
  ];

  // One diff row per (pos, field) across every uploaded file's segment
  // table -- keyed by pos, which is DLA's own position numbering and stays
  // stable across suffix variants of the same base transaction set (315A
  // vs 315B vs 315N), unlike relying on row order. A pos missing entirely
  // from a file is reported once as "Presence", not once per field --
  // comparing field values when the segment doesn't exist in that file
  // isn't meaningful.
  function buildSegmentDiffs(fileResults) {
    const filenames = fileResults.map((fr) => fr.filename);
    const byPos = new Map();
    for (const fr of fileResults) {
      for (const row of fr.segment_table) {
        if (!byPos.has(row.pos)) byPos.set(row.pos, new Map());
        byPos.get(row.pos).set(fr.filename, row);
      }
    }

    const rows = [];
    for (const [pos, rowsByFile] of byPos) {
      const context = [...rowsByFile.values()][0];
      const missingFrom = filenames.filter((f) => !rowsByFile.has(f));
      if (missingFrom.length) {
        const valuesByFile = {};
        for (const f of filenames) valuesByFile[f] = rowsByFile.has(f) ? "Present" : "— not in this file —";
        rows.push({
          key: pos,
          segmentId: context.segment_id,
          name: context.name,
          field: "Presence",
          valuesByFile,
          allMatch: false,
        });
        continue;
      }
      for (const [fieldKey, label] of SEGMENT_DIFF_FIELDS) {
        const valuesByFile = {};
        let first;
        let allMatch = true;
        for (const filename of filenames) {
          const value = fieldValue(rowsByFile.get(filename), fieldKey);
          valuesByFile[filename] = value;
          if (first === undefined) first = value;
          else if (value !== first) allMatch = false;
        }
        rows.push({ key: pos, segmentId: context.segment_id, name: context.name, field: label, valuesByFile, allMatch });
      }
    }
    return { filenames, rows };
  }

  const ELEMENT_DIFF_FIELDS = [
    ["name", "Name"],
    ["requirement", "Req"],
    ["data_type", "Type"],
    ["min_max", "Min/Max"],
    ["usage", "Usage"],
  ];

  // Same idea as buildSegmentDiffs, keyed by element ref (e.g. "BR02")
  // instead of segment pos. Codes get their own diff row per ref, comparing
  // the code *set* (not individual code rows -- a code present in one
  // file's list and absent from another's is the finding, not a field
  // value).
  function buildElementDiffs(fileResults) {
    const filenames = fileResults.map((fr) => fr.filename);
    const byRef = new Map();
    for (const fr of fileResults) {
      for (const [segmentId, detail] of Object.entries(fr.segment_details)) {
        for (const e of detail.elements) {
          if (!byRef.has(e.ref)) byRef.set(e.ref, new Map());
          byRef.get(e.ref).set(fr.filename, { segmentId, element: e });
        }
      }
    }

    const rows = [];
    for (const [ref, entriesByFile] of byRef) {
      const context = [...entriesByFile.values()][0];
      const missingFrom = filenames.filter((f) => !entriesByFile.has(f));
      if (missingFrom.length) {
        const valuesByFile = {};
        for (const f of filenames) valuesByFile[f] = entriesByFile.has(f) ? "Present" : "— not in this file —";
        rows.push({
          key: ref,
          segmentId: context.segmentId,
          name: context.element.name,
          field: "Presence",
          valuesByFile,
          allMatch: false,
        });
        continue;
      }
      for (const [fieldKey, label] of ELEMENT_DIFF_FIELDS) {
        const valuesByFile = {};
        let first;
        let allMatch = true;
        for (const filename of filenames) {
          const value = entriesByFile.get(filename).element[fieldKey] ?? "";
          valuesByFile[filename] = value;
          if (first === undefined) first = value;
          else if (value !== first) allMatch = false;
        }
        rows.push({ key: ref, segmentId: context.segmentId, name: context.element.name, field: label, valuesByFile, allMatch });
      }

      const codesByFile = {};
      for (const f of filenames) {
        const codes = entriesByFile.get(f).element.codes;
        codesByFile[f] = codes.map((c) => `${c.code} (${c.name})`).sort();
      }
      const firstSet = new Set(codesByFile[filenames[0]]);
      let codesMatch = true;
      for (const f of filenames.slice(1)) {
        const s = codesByFile[f];
        if (s.length !== firstSet.size || s.some((c) => !firstSet.has(c))) codesMatch = false;
      }
      const valuesByFile = {};
      for (const f of filenames) valuesByFile[f] = codesByFile[f].join(", ") || "(none)";
      rows.push({
        key: ref,
        segmentId: context.segmentId,
        name: context.element.name,
        field: "Codes",
        valuesByFile,
        allMatch: codesMatch,
      });
    }
    return { filenames, rows };
  }

  // --- Rendering -------------------------------------------------------

  function diffColumns(keyLabel, filenames) {
    return [
      { label: keyLabel, get: (r) => r.key },
      { label: "Segment", get: (r) => r.segmentId },
      { label: "Name", get: (r) => r.name },
      { label: "Field", get: (r) => r.field },
      ...filenames.map((f) => ({ label: f, get: (r) => r.valuesByFile[f] })),
    ];
  }

  function diffTable(title, keyLabel, diffResult, baseName) {
    const { filenames, rows } = diffResult;
    const visibleRows = showAllDiffs ? rows : rows.filter((r) => !r.allMatch);

    const wrap = el("div", { class: "convention-wrap" });
    const headerCells = [keyLabel, "Segment", "Name", "Field", ...filenames].map((label) => el("th", { text: label }));
    const thead = el("thead", {}, [el("tr", {}, headerCells)]);
    const tbody = el(
      "tbody",
      {},
      visibleRows.map((r) =>
        el(
          "tr",
          {},
          [
            el("td", { text: r.key, class: "mono" }),
            el("td", { text: r.segmentId, class: "mono" }),
            el("td", { text: r.name }),
            el("td", { text: r.field }),
            ...filenames.map((f) =>
              el("td", { text: String(r.valuesByFile[f]), class: r.allMatch ? "" : "diff-mismatch" })
            ),
          ]
        )
      )
    );
    const table = el("table", { class: "convention-table" }, [thead, tbody]);
    const summary = el("summary", { class: "hint", text: `${title}: ${visibleRows.length} of ${rows.length} rows` });
    const details = el("details", { open: "" }, [summary, el("div", { class: "convention-table-wrap" }, [table])]);
    wrap.appendChild(details);
    wrap.appendChild(downloadControl(() => visibleRows, diffColumns(keyLabel, filenames), baseName));
    return wrap;
  }

  function renderResults(fileResults) {
    results.innerHTML = "";

    const toggleLabel = el("label", { class: "inline" });
    const toggleCheckbox = el("input", { type: "checkbox" });
    toggleCheckbox.checked = showAllDiffs;
    toggleCheckbox.addEventListener("change", () => {
      showAllDiffs = toggleCheckbox.checked;
      renderResults(fileResults);
    });
    toggleLabel.appendChild(toggleCheckbox);
    toggleLabel.appendChild(el("span", { text: "Show all compared rows, not just differences" }));
    results.appendChild(el("div", { class: "filter-bar" }, [toggleLabel]));

    const segPanel = el("div", { class: "panel" });
    segPanel.appendChild(el("h2", { text: "Segment differences" }));
    segPanel.appendChild(diffTable("Segment differences", "Pos", buildSegmentDiffs(fileResults), "convention-segment-differences"));
    results.appendChild(segPanel);

    const elPanel = el("div", { class: "panel" });
    elPanel.appendChild(el("h2", { text: "Element differences" }));
    elPanel.appendChild(diffTable("Element differences", "Ref", buildElementDiffs(fileResults), "convention-element-differences"));
    results.appendChild(elPanel);

    results.hidden = false;
  }
})();
