(function () {
  "use strict";

  const form = document.getElementById("convention-form");
  if (!form) return; // not the convention page

  const fileInput = document.getElementById("pdf-file");
  const clearBtn = document.getElementById("clear-btn");
  const submitBtn = document.getElementById("submit-btn");
  const formError = document.getElementById("form-error");
  const results = document.getElementById("results");

  // Combined, flattened rows across every uploaded file -- rebuilt on each
  // submit, then re-rendered (not re-fetched) whenever a filter changes.
  let segmentRows = [];
  let elementRows = [];

  const segmentFilters = { asterisk: "all", groupByLoop: false };
  const elementFilters = { ref: "", elem: "", name: "", required: "", type: "", code: "" };

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

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else node.setAttribute(key, value);
    }
    for (const child of children || []) {
      node.appendChild(child);
    }
    return node;
  }

  // Flatten every file's segment_table and segment_details into one set of
  // rows each, tagged with the source filename -- the combined-table view
  // the user asked for, rather than one table per upload.
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

  // --- Segment table: filters + optional loop grouping ------------------

  function filteredSegmentRows() {
    return segmentRows.filter((r) => {
      if (segmentFilters.asterisk === "only" && !r.flagged) return false;
      if (segmentFilters.asterisk === "none" && r.flagged) return false;
      return true;
    });
  }

  function segmentTableControls() {
    const bar = el("div", { class: "filter-bar" });

    const asteriskLabel = el("label", { class: "inline" }, [
      el("span", { text: "Flagged (*):" }),
    ]);
    const asteriskSelect = el("select", { id: "asterisk-filter" }, [
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
    const groupCheckbox = el("input", { type: "checkbox", id: "group-by-loop" });
    groupCheckbox.checked = segmentFilters.groupByLoop;
    groupCheckbox.addEventListener("change", () => {
      segmentFilters.groupByLoop = groupCheckbox.checked;
      renderResults();
    });
    groupLabel.appendChild(groupCheckbox);
    groupLabel.appendChild(el("span", { text: "Group by loop" }));
    bar.appendChild(groupLabel);

    return bar;
  }

  function segmentRowCells(r) {
    return [
      el("td", { text: r.file, class: "mono" }),
      el("td", { text: r.level || "", class: "mono" }),
      el("td", { text: r.flagged ? "*" : "", class: "mono" }),
      el("td", { text: r.pos, class: "mono" }),
      el("td", { text: r.loop_id || "", class: "mono" }),
      el("td", { text: r.segment_id, class: "mono" }),
      el("td", { text: r.name }),
      el("td", { text: r.requirement, class: "mono" }),
      el("td", { text: r.max_use, class: "mono" }),
      el("td", { text: r.repeat, class: "mono" }),
      el("td", { text: r.notes, class: "mono" }),
      el("td", { text: r.usage }),
    ];
  }

  function segmentTable() {
    const headers = [
      "File", "Level", "*", "Pos", "Loop", "Id", "Segment Name",
      "Req", "Max Use", "Repeat", "Notes", "Usage",
    ];
    const thead = el("thead", {}, [el("tr", {}, headers.map((h) => el("th", { text: h })))]);
    const rows = filteredSegmentRows();
    const tbody = el("tbody", {});

    if (segmentFilters.groupByLoop) {
      const groups = new Map();
      for (const r of rows) {
        const key = r.loop_id || "(no loop)";
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(r);
      }
      for (const [loopId, groupRows] of groups) {
        const heading = el("tr", { class: "loop-group-row" }, [
          el("td", { text: `Loop ${loopId} (${groupRows.length})`, colspan: String(headers.length) }),
        ]);
        tbody.appendChild(heading);
        for (const r of groupRows) tbody.appendChild(el("tr", {}, segmentRowCells(r)));
      }
    } else {
      for (const r of rows) tbody.appendChild(el("tr", {}, segmentRowCells(r)));
    }

    return el("table", { class: "convention-table" }, [thead, tbody]);
  }

  // --- Element table: combined across every segment, with column filters -

  function filteredElementRows() {
    const f = elementFilters;
    return elementRows.filter((r) => {
      if (f.ref && !r.ref.toLowerCase().includes(f.ref)) return false;
      if (f.elem && !r.element_number.toLowerCase().includes(f.elem)) return false;
      if (f.name && !r.name.toLowerCase().includes(f.name)) return false;
      if (f.required && !r.requirement.toLowerCase().includes(f.required)) return false;
      if (f.type && !r.data_type.toLowerCase().includes(f.type)) return false;
      if (f.code && !(r.code || "").toLowerCase().includes(f.code)) return false;
      return true;
    });
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
        renderElementResults();
      });
      wrap.appendChild(input);
      bar.appendChild(wrap);
    }
    return bar;
  }

  function elementTable() {
    const headers = [
      "File", "Segment", "Ref", "Elem#", "Element Name", "Req", "Type",
      "Min/Max", "Usage", "Code", "Code Name",
    ];
    const thead = el("thead", {}, [el("tr", {}, headers.map((h) => el("th", { text: h })))]);
    const rows = filteredElementRows().map((r) =>
      el("tr", {}, [
        el("td", { text: r.file, class: "mono" }),
        el("td", { text: r.segment_id, class: "mono" }),
        el("td", { text: r.ref, class: "mono" }),
        el("td", { text: r.element_number, class: "mono" }),
        el("td", { text: r.name }),
        el("td", { text: r.requirement, class: "mono" }),
        el("td", { text: r.data_type, class: "mono" }),
        el("td", { text: r.min_max, class: "mono" }),
        el("td", { text: r.usage }),
        el("td", { text: r.code, class: "mono" }),
        el("td", { text: r.code_name }),
      ])
    );
    return el("table", { class: "convention-table" }, [thead, el("tbody", {}, rows)]);
  }

  // Re-render just the element panel (used on every keystroke in its
  // filters, so the segment table -- and its own filter inputs' focus --
  // isn't rebuilt underneath the user).
  function renderElementResults() {
    const panel = document.getElementById("element-panel");
    if (!panel) return;
    const wrap = panel.querySelector(".convention-table-wrap");
    wrap.innerHTML = "";
    wrap.appendChild(elementTable());
  }

  function renderResults() {
    results.innerHTML = "";

    const segPanel = el("div", { class: "panel" });
    segPanel.appendChild(el("h2", { text: `Segment table (${filteredSegmentRows().length} of ${segmentRows.length} rows)` }));
    if (segmentRows.length) {
      segPanel.appendChild(segmentTableControls());
      segPanel.appendChild(el("div", { class: "convention-table-wrap" }, [segmentTable()]));
    } else {
      segPanel.appendChild(el("p", { class: "form-error", text: "No segment table found in these PDFs." }));
    }
    results.appendChild(segPanel);

    if (elementRows.length) {
      const elPanel = el("div", { class: "panel", id: "element-panel" });
      elPanel.appendChild(el("h2", { text: `Element definitions & codes (${elementRows.length} rows)` }));
      elPanel.appendChild(elementTableControls());
      elPanel.appendChild(el("div", { class: "convention-table-wrap" }, [elementTable()]));
      results.appendChild(elPanel);
    }

    results.hidden = false;
  }
})();
