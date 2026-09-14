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

  const elementFilters = { ref: "", elem: "", name: "", required: "", type: "", code: "" };
  let elementSort = null;

  clearBtn.addEventListener("click", () => {
    fileInput.value = "";
    results.hidden = true;
    results.innerHTML = "";
    formError.hidden = true;
    segmentRows = [];
    elementRows = [];
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
    wrap.appendChild(el("h3", { class: "ts-id", text: filename }));

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
    wrap.appendChild(el("div", { class: "convention-table-wrap" }, [table]));
    return wrap;
  }

  // --- Element table ---------------------------------------------------

  const ELEMENT_COLUMNS = [
    { key: "segment_id", label: "Segment", get: (r) => r.segment_id },
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
      if (f.required && !r.requirement.toLowerCase().includes(f.required)) return false;
      if (f.type && !r.data_type.toLowerCase().includes(f.type)) return false;
      if (f.code && !(r.code || "").toLowerCase().includes(f.code)) return false;
      return true;
    });
    return applySort(rows, elementSort, ELEMENT_COLUMNS);
  }

  function elementTableControls() {
    const bar = el("div", { class: "filter-bar" });
    const fields = [
      ["ref", "Ref"],
      ["elem", "Elem#"],
      ["name", "Element Name"],
      ["required", "Req"],
      ["type", "Type"],
      ["code", "Code"],
    ];
    for (const [key, label] of fields) {
      const wrap = el("label", { class: "inline" }, [el("span", { text: `${label}:` })]);
      const input = el("input", { type: "text", value: elementFilters[key], placeholder: "filter…" });
      input.addEventListener("input", () => {
        elementFilters[key] = input.value.trim().toLowerCase();
        renderResults();
      });
      wrap.appendChild(input);
      bar.appendChild(wrap);
    }
    bar.appendChild(
      downloadControl(() => filteredElementRows(), ELEMENT_COLUMNS, "convention-elements", (r) => r.file)
    );
    return bar;
  }

  function elementFileSection(filename, rows) {
    const wrap = el("div", { class: "convention-wrap" });
    wrap.appendChild(el("h3", { class: "ts-id", text: filename }));

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
    wrap.appendChild(el("div", { class: "convention-table-wrap" }, [table]));
    return wrap;
  }

  function renderResults() {
    results.innerHTML = "";

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
