(function () {
  "use strict";

  const form = document.getElementById("convention-form");
  if (!form) return; // not the convention page

  const fileInput = document.getElementById("pdf-file");
  const clearBtn = document.getElementById("clear-btn");
  const submitBtn = document.getElementById("submit-btn");
  const formError = document.getElementById("form-error");
  const results = document.getElementById("results");

  const { el, downloadControl } = window.tableTools;

  // Combined, flattened rows across every uploaded file -- rebuilt on each
  // submit, then re-rendered (not re-fetched) whenever a filter/sort changes.
  let segmentRows = [];
  let elementRows = [];

  const segmentFilters = { asterisk: "all" };
  let segmentGroupByLoop = false;
  let segmentSort = null; // { key, dir }

  const elementFilters = { ref: "", elem: "", name: "", required: "", type: "", usage: "", code: "" };
  let elementSort = null;

  // Kept alongside the flattened segmentRows/elementRows -- the differences
  // panel needs each file's own segment_table/segment_details intact (not
  // flattened) to compare file-against-file, not just list rows.
  let lastFileResults = [];
  let showAllDiffs = false;

  clearBtn.addEventListener("click", () => {
    fileInput.value = "";
    results.hidden = true;
    results.innerHTML = "";
    formError.hidden = true;
    segmentRows = [];
    elementRows = [];
    lastFileResults = [];
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;

    const files = fileInput.files;
    if (!files.length) {
      formError.textContent = "Choose at least one PDF file.";
      formError.hidden = false;
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Parsing…";

    try {
      const body = new FormData();
      for (const file of files) body.append("files", file);
      const response = await fetch("/api/convention", { method: "POST", body });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "request failed");
      }
      combineResults(data.results);
      lastFileResults = data.results;
      renderResults();
    } catch (err) {
      formError.textContent = err.message;
      formError.hidden = false;
      results.hidden = true;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Parse convention(s)";
    }
  });

  // Flatten every file's segment_table and segment_details into one set of
  // rows each, tagged with the source filename -- kept internally so
  // filtering/sorting/downloading can work across every upload, even though
  // the filename is shown as a heading per file, not a table column.
  function combineResults(fileResults) {
    segmentRows = [];
    elementRows = [];
    for (const fr of fileResults) {
      for (const r of fr.segment_table) {
        segmentRows.push({ file: fr.filename, ...r });
      }
      for (const [segmentId, detail] of Object.entries(fr.segment_details)) {
        for (const e of detail.elements) {
          const base = {
            file: fr.filename,
            segment_id: segmentId,
            seg_pos: detail.pos,
            ref: e.ref,
            element_number: e.element_number,
            name: e.name,
            requirement: e.requirement,
            data_type: e.data_type,
            min_max: e.min_max,
            usage: e.usage,
          };
          if (!e.codes.length) {
            elementRows.push({ ...base, code: "", code_name: "" });
          } else {
            for (const c of e.codes) elementRows.push({ ...base, code: c.code, code_name: c.name });
          }
        }
      }
    }
  }

  function applySort(rows, sort, columns) {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    return rows.slice().sort((a, b) => {
      const av = col.get(a);
      const bv = col.get(b);
      const cmp = col.numeric ? av - bv : String(av).localeCompare(String(bv));
      return cmp * sort.dir;
    });
  }

  // Groups already-filtered/sorted rows by file, preserving relative order
  // within each group -- each file becomes its own headed section instead
  // of a "File" column repeated down every row.
  function groupByFile(rows) {
    const groups = new Map();
    for (const r of rows) {
      if (!groups.has(r.file)) groups.set(r.file, []);
      groups.get(r.file).push(r);
    }
    return groups;
  }

  function sortableHeaderRow(columns, sortState, onSort) {
    return el(
      "tr",
      {},
      columns.map((col) => {
        const th = el("th", { text: col.label, class: "sortable" });
        th.addEventListener("click", () => {
          const next =
            sortState() && sortState().key === col.key
              ? { key: col.key, dir: -sortState().dir }
              : { key: col.key, dir: 1 };
          onSort(next);
        });
        return th;
      })
    );
  }

  // --- Differences -----------------------------------------------------

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

  function diffColumns(keyLabel, filenames) {
    return [
      { label: keyLabel, get: (r) => r.key },
      { label: "Segment", get: (r) => r.segmentId },
      { label: "Name", get: (r) => r.name },
      { label: "Field", get: (r) => r.field },
      ...filenames.map((f) => ({ label: f, get: (r) => r.valuesByFile[f] })),
    ];
  }

  // One diff sub-table (Segment differences or Element differences) --
  // shares the "show all" toggle's current state with its sibling, so both
  // tables expand/collapse together.
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

  // Only meaningful with 2+ files -- comparing one convention against
  // itself has nothing to say.
  function differencesPanel(fileResults) {
    if (fileResults.length < 2) return null;

    const panel = el("div", { class: "panel" });
    panel.appendChild(el("h2", { text: "Differences" }));
    panel.appendChild(
      el("p", {
        class: "hint",
        text: "Compares every uploaded file's segment table and element definitions, keyed by position/ref (stable across suffix variants like 315A/B/N), not by row order.",
      })
    );

    const toggleLabel = el("label", { class: "inline" });
    const toggleCheckbox = el("input", { type: "checkbox" });
    toggleCheckbox.checked = showAllDiffs;
    toggleCheckbox.addEventListener("change", () => {
      showAllDiffs = toggleCheckbox.checked;
      renderResults();
    });
    toggleLabel.appendChild(toggleCheckbox);
    toggleLabel.appendChild(el("span", { text: "Show all compared rows, not just differences" }));
    panel.appendChild(el("div", { class: "filter-bar" }, [toggleLabel]));

    panel.appendChild(diffTable("Segment differences", "Pos", buildSegmentDiffs(fileResults), "convention-segment-differences"));
    panel.appendChild(diffTable("Element differences", "Ref", buildElementDiffs(fileResults), "convention-element-differences"));
    return panel;
  }

  // --- Segment table -------------------------------------------------------

  const SEGMENT_COLUMNS = [
    { key: "level", label: "Level", get: (r) => r.level || "" },
    { key: "flagged", label: "*", get: (r) => (r.flagged ? "*" : "") },
    { key: "pos", label: "Pos", get: (r) => r.pos },
    { key: "loop_id", label: "Loop", get: (r) => r.loop_id || "" },
    { key: "segment_id", label: "Id", get: (r) => r.segment_id },
    { key: "name", label: "Segment Name", get: (r) => r.name },
    { key: "requirement", label: "Req", get: (r) => r.requirement },
    { key: "max_use", label: "Max Use", get: (r) => r.max_use },
    { key: "repeat", label: "Repeat", get: (r) => r.repeat },
    { key: "notes", label: "Notes", get: (r) => r.notes },
    { key: "usage", label: "Usage", get: (r) => r.usage },
  ];

  function filteredSegmentRows() {
    let rows = segmentRows.filter((r) => {
      if (segmentFilters.asterisk === "only" && !r.flagged) return false;
      if (segmentFilters.asterisk === "none" && r.flagged) return false;
      return true;
    });
    return applySort(rows, segmentSort, SEGMENT_COLUMNS);
  }

  function segmentTableControls() {
    const bar = el("div", { class: "filter-bar" });

    const asteriskLabel = el("label", { class: "inline" }, [el("span", { text: "Flagged (*):" })]);
    const asteriskSelect = el("select", {}, [
      el("option", { value: "all", text: "All" }),
      el("option", { value: "only", text: "Only *" }),
      el("option", { value: "none", text: "No *" }),
    ]);
    asteriskSelect.value = segmentFilters.asterisk;
    asteriskSelect.addEventListener("change", () => {
      segmentFilters.asterisk = asteriskSelect.value;
      renderResults();
    });
    asteriskLabel.appendChild(asteriskSelect);
    bar.appendChild(asteriskLabel);

    const groupLabel = el("label", { class: "inline" });
    const groupCheckbox = el("input", { type: "checkbox" });
    groupCheckbox.checked = segmentGroupByLoop;
    groupCheckbox.addEventListener("change", () => {
      segmentGroupByLoop = groupCheckbox.checked;
      renderResults();
    });
    groupLabel.appendChild(groupCheckbox);
    groupLabel.appendChild(el("span", { text: "Group by loop" }));
    bar.appendChild(groupLabel);

    bar.appendChild(
      downloadControl(() => filteredSegmentRows(), SEGMENT_COLUMNS, "convention-segments", (r) => r.file)
    );

    return bar;
  }

  function segmentRowCells(r) {
    return SEGMENT_COLUMNS.map((col) => el("td", { text: String(col.get(r)), class: "mono" }));
  }

  function segmentFileSection(filename, rows) {
    const wrap = el("div", { class: "convention-wrap" });

    const thead = el("thead", {}, [
      sortableHeaderRow(SEGMENT_COLUMNS, () => segmentSort, (s) => {
        segmentSort = s;
        renderResults();
      }),
    ]);
    const tbody = el("tbody", {});

    if (segmentGroupByLoop) {
      const groups = new Map();
      for (const r of rows) {
        const key = r.loop_id || "(no loop)";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(r);
      }
      for (const [loopId, groupRows] of groups) {
        tbody.appendChild(
          el("tr", { class: "loop-group-row" }, [
            el("td", { text: `Loop ${loopId} (${groupRows.length})`, colspan: String(SEGMENT_COLUMNS.length) }),
          ])
        );
        for (const r of groupRows) tbody.appendChild(el("tr", {}, segmentRowCells(r)));
      }
    } else {
      for (const r of rows) tbody.appendChild(el("tr", {}, segmentRowCells(r)));
    }

    const table = el("table", { class: "convention-table" }, [thead, tbody]);
    const summary = el("summary", { class: "ts-id", text: `${filename} (${rows.length} rows)` });
    wrap.appendChild(
      el("details", { open: "" }, [summary, el("div", { class: "convention-table-wrap" }, [table])])
    );
    return wrap;
  }

  // --- Element table ---------------------------------------------------

  const ELEMENT_COLUMNS = [
    { key: "ref", label: "Ref", get: (r) => r.ref },
    { key: "element_number", label: "Elem#", get: (r) => r.element_number },
    { key: "name", label: "Element Name", get: (r) => r.name },
    { key: "requirement", label: "Req", get: (r) => r.requirement },
    { key: "data_type", label: "Type", get: (r) => r.data_type },
    { key: "min_max", label: "Min/Max", get: (r) => r.min_max },
    { key: "usage", label: "Usage", get: (r) => r.usage },
    { key: "code", label: "Code", get: (r) => r.code },
    { key: "code_name", label: "Code Name", get: (r) => r.code_name },
  ];

  function filteredElementRows() {
    const f = elementFilters;
    let rows = elementRows.filter((r) => {
      if (f.ref && !r.ref.toLowerCase().includes(f.ref)) return false;
      if (f.elem && !r.element_number.toLowerCase().includes(f.elem)) return false;
      if (f.name && !r.name.toLowerCase().includes(f.name)) return false;
      if (f.required && r.requirement !== f.required) return false;
      if (f.type && r.data_type !== f.type) return false;
      if (f.usage && r.usage !== f.usage) return false;
      if (f.code && (r.code || "") !== f.code) return false;
      return true;
    });
    return applySort(rows, elementSort, ELEMENT_COLUMNS);
  }

  // Distinct, non-empty values a column actually takes across every parsed
  // file -- populates its filter dropdown so only real choices are offered.
  function distinctValues(getter) {
    return [...new Set(elementRows.map(getter).filter((v) => v))].sort();
  }

  function elementTableControls() {
    const bar = el("div", { class: "filter-bar" });

    const textFields = [
      ["ref", "Ref"],
      ["elem", "Elem#"],
      ["name", "Element Name"],
    ];
    for (const [key, label] of textFields) {
      const wrap = el("label", { class: "inline" }, [el("span", { text: `${label}:` })]);
      const input = el("input", { type: "text", value: elementFilters[key], placeholder: "filter…" });
      input.addEventListener("input", () => {
        elementFilters[key] = input.value.trim().toLowerCase();
        renderResults();
      });
      wrap.appendChild(input);
      bar.appendChild(wrap);
    }

    const dropdownFields = [
      ["required", "Req", (r) => r.requirement],
      ["type", "Type", (r) => r.data_type],
      ["usage", "Usage", (r) => r.usage],
      ["code", "Code", (r) => r.code],
    ];
    for (const [key, label, getter] of dropdownFields) {
      const wrap = el("label", { class: "inline" }, [el("span", { text: `${label}:` })]);
      const select = el("select", {}, [
        el("option", { value: "", text: "All" }),
        ...distinctValues(getter).map((v) => el("option", { value: v, text: v })),
      ]);
      select.value = elementFilters[key];
      select.addEventListener("change", () => {
        elementFilters[key] = select.value;
        renderResults();
      });
      wrap.appendChild(select);
      bar.appendChild(wrap);
    }

    bar.appendChild(
      downloadControl(() => filteredElementRows(), ELEMENT_COLUMNS, "convention-elements", (r) => r.file)
    );
    return bar;
  }

  function elementFileSection(filename, rows) {
    const wrap = el("div", { class: "convention-wrap" });

    const thead = el("thead", {}, [
      sortableHeaderRow(ELEMENT_COLUMNS, () => elementSort, (s) => {
        elementSort = s;
        renderResults();
      }),
    ]);
    const tbody = el(
      "tbody",
      {},
      rows.map((r) => el("tr", {}, ELEMENT_COLUMNS.map((col) => el("td", { text: String(col.get(r) ?? "") }))))
    );
    const table = el("table", { class: "convention-table" }, [thead, tbody]);
    const summary = el("summary", { class: "ts-id", text: `${filename} (${rows.length} rows)` });
    wrap.appendChild(
      el("details", { open: "" }, [summary, el("div", { class: "convention-table-wrap" }, [table])])
    );
    return wrap;
  }

  function renderResults() {
    results.innerHTML = "";

    const diffPanel = differencesPanel(lastFileResults);
    if (diffPanel) results.appendChild(diffPanel);

    const segRows = filteredSegmentRows();
    const segPanel = el("div", { class: "panel" });
    segPanel.appendChild(
      el("h2", { text: `Segment table (${segRows.length} of ${segmentRows.length} rows)` })
    );
    if (segmentRows.length) {
      segPanel.appendChild(segmentTableControls());
      for (const [filename, rows] of groupByFile(segRows)) {
        segPanel.appendChild(segmentFileSection(filename, rows));
      }
    } else {
      segPanel.appendChild(el("p", { class: "form-error", text: "No segment table found in these PDFs." }));
    }
    results.appendChild(segPanel);

    if (elementRows.length) {
      const elRows = filteredElementRows();
      const elPanel = el("div", { class: "panel" });
      elPanel.appendChild(el("h2", { text: `Element definitions & codes (${elRows.length} of ${elementRows.length} rows)` }));
      elPanel.appendChild(elementTableControls());
      for (const [filename, rows] of groupByFile(elRows)) {
        elPanel.appendChild(elementFileSection(filename, rows));
      }
      results.appendChild(elPanel);
    }

    results.hidden = false;
  }
})();
