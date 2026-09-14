(function () {
  "use strict";

  const form = document.getElementById("edi-form");
  if (!form) return; // not the codes page

  const ediField = document.getElementById("edi");
  const fileInput = document.getElementById("file");
  const sampleSelect = document.getElementById("sample-select");
  const sampleNote = document.getElementById("sample-note");
  const clearBtn = document.getElementById("clear-btn");
  const submitBtn = document.getElementById("submit-btn");
  const formError = document.getElementById("form-error");
  const results = document.getElementById("results");

  const samplesDataEl = document.getElementById("samples-data");
  const SAMPLES = samplesDataEl ? JSON.parse(samplesDataEl.textContent) : [];

  const { el, downloadControl } = window.tableTools;

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;
    file.text().then((text) => {
      ediField.value = text;
      sampleSelect.value = "";
      sampleNote.hidden = true;
    });
  });

  if (sampleSelect) {
    sampleSelect.addEventListener("change", () => {
      const sample = SAMPLES.find((s) => s.slug === sampleSelect.value);
      if (!sample) {
        sampleNote.hidden = true;
        return;
      }
      ediField.value = sample.edi;
      fileInput.value = "";
      sampleNote.textContent = sample.blurb;
      sampleNote.hidden = false;
    });
  }

  clearBtn.addEventListener("click", () => {
    ediField.value = "";
    fileInput.value = "";
    if (sampleSelect) sampleSelect.value = "";
    sampleNote.hidden = true;
    results.hidden = true;
    results.innerHTML = "";
    formError.hidden = true;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    submitBtn.disabled = true;
    submitBtn.textContent = "Working…";

    try {
      const response = await fetch("/api/codes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ edi: ediField.value }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "request failed");
      }
      renderResults(data);
    } catch (err) {
      formError.textContent = err.message;
      formError.hidden = false;
      results.hidden = true;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Cleanse & list codes";
    }
  });

  // Same shape as the segment-inventory identifier: release.edi.sender-receiver.date.
  function interchangeId(facts) {
    const sender = (facts && facts.sender_id) || "UNKNOWN";
    const receiver = (facts && facts.receiver_id) || "UNKNOWN";
    const date = (facts && facts.interchange_date) || "UNKNOWN";
    return `${sender}-${receiver}.${date}`;
  }

  // One occurrence's raw segment, with the token at `position` (1-based,
  // matching X12's own element numbering, so it lines up with tokens[position])
  // wrapped in <mark> -- shows exactly where this row's value sits on the wire.
  function rawSegmentCell(o, separator) {
    const cell = el("td", { class: "mono" });
    const line = el("div", { class: "raw-segment" });
    o.raw_segment.forEach((tok, i) => {
      if (i > 0) line.appendChild(document.createTextNode(separator));
      line.appendChild(i === o.position ? el("mark", { text: tok }) : document.createTextNode(tok));
    });
    cell.appendChild(line);
    return cell;
  }

  const COLUMNS = [
    { key: "ref", label: "Ref", get: (o) => `${o.segment_id}${String(o.position).padStart(2, "0")}` },
    { key: "name", label: "Name", get: (o) => o.name },
    { key: "requirement", label: "Req", get: (o) => o.requirement },
    { key: "min_length", label: "Min", get: (o) => o.min_length, numeric: true },
    { key: "max_length", label: "Max", get: (o) => o.max_length, numeric: true },
    { key: "value", label: "Value", get: (o) => o.value },
  ];

  // One interchange's occurrence table: sortable by clicking a header
  // (defaults to -- and can be reset to -- true file order), filterable by
  // a text box per column, and downloadable in several formats.
  function occurrenceTable(occurrences, facts, separator) {
    const wrap = el("div", { class: "convention-wrap" });
    wrap.appendChild(el("h3", { class: "ts-id", text: interchangeId(facts) }));

    if (!occurrences.length) {
      wrap.appendChild(
        el("p", { class: "hint", text: "No elements covered by element_definitions.py were found here." })
      );
      return wrap;
    }

    const fileOrder = occurrences.map((o, i) => ({ o, i }));
    const filters = { ref: "", name: "", requirement: "", value: "" };
    let sort = null; // { key, dir: 1 | -1 } | null (null = original file order)

    const filterBar = el("div", { class: "filter-bar" });
    const filterInputs = {};
    for (const key of ["ref", "name", "requirement", "value"]) {
      const label = COLUMNS.find((c) => c.key === key)?.label || key;
      const wrapLabel = el("label", { class: "inline" }, [el("span", { text: `${label}:` })]);
      const input = el("input", { type: "text", placeholder: "filter…" });
      input.addEventListener("input", () => {
        filters[key] = input.value.trim().toLowerCase();
        renderBody();
      });
      filterInputs[key] = input;
      wrapLabel.appendChild(input);
      filterBar.appendChild(wrapLabel);
    }

    const resetBtn = el("button", { type: "button", class: "ghost", text: "Reset order" });
    resetBtn.addEventListener("click", () => {
      sort = null;
      renderBody();
    });
    filterBar.appendChild(resetBtn);

    const exportColumns = [
      ...COLUMNS,
      { key: "raw_segment", label: "Raw segment", get: (o) => o.raw_segment.join(separator) },
    ];
    const downloadPicker = downloadControl(() => currentRows(), exportColumns, "code-inventory");
    filterBar.appendChild(downloadPicker);

    wrap.appendChild(filterBar);

    const headers = [...COLUMNS, { key: "raw_segment", label: "Raw segment" }];
    const headRow = el("tr", {}, headers.map((col) => {
      const th = el("th", { text: col.label });
      if (col.key !== "raw_segment") {
        th.classList.add("sortable");
        th.addEventListener("click", () => {
          sort = sort && sort.key === col.key ? { key: col.key, dir: -sort.dir } : { key: col.key, dir: 1 };
          renderBody();
        });
      }
      return th;
    }));
    const thead = el("thead", {}, [headRow]);
    const tbody = el("tbody", {});
    const table = el("table", { class: "convention-table" }, [thead, tbody]);
    // The row count doubles as the <summary> -- clicking it rolls the table
    // up/down, same as the rest of the app's collapsible sections.
    const summary = el("summary", { class: "hint" });
    const details = el("details", { open: "" }, [
      summary,
      el("div", { class: "convention-table-wrap" }, [table]),
    ]);
    wrap.appendChild(details);

    function currentRows() {
      let rows = fileOrder.filter(({ o }) => {
        if (filters.ref && !COLUMNS[0].get(o).toLowerCase().includes(filters.ref)) return false;
        if (filters.name && !o.name.toLowerCase().includes(filters.name)) return false;
        if (filters.requirement && !o.requirement.toLowerCase().includes(filters.requirement)) return false;
        if (filters.value && !o.value.toLowerCase().includes(filters.value)) return false;
        return true;
      });
      if (sort) {
        const col = COLUMNS.find((c) => c.key === sort.key);
        rows = rows.slice().sort((a, b) => {
          const av = col.get(a.o);
          const bv = col.get(b.o);
          const cmp = col.numeric ? av - bv : String(av).localeCompare(String(bv));
          return cmp * sort.dir;
        });
      }
      return rows.map(({ o }) => o);
    }

    function renderBody() {
      const rows = currentRows();
      summary.textContent = sort
        ? `Showing ${rows.length} of ${occurrences.length} rows, sorted by ${sort.key} (${sort.dir > 0 ? "asc" : "desc"}).`
        : `Showing ${rows.length} of ${occurrences.length} rows, in file order.`;
      tbody.innerHTML = "";
      for (const o of rows) {
        const cells = COLUMNS.map((col) =>
          el("td", { text: String(col.get(o)), class: col.numeric || col.key === "ref" || col.key === "requirement" ? "mono" : "" })
        );
        cells.push(rawSegmentCell(o, separator));
        tbody.appendChild(el("tr", {}, cells));
      }
    }

    renderBody();
    return wrap;
  }

  function renderInterchange(entry, showHeading) {
    const panel = el("div", { class: "panel" });
    if (showHeading) panel.appendChild(el("h2", { text: `Interchange ${entry.index}` }));

    if (!entry.recovered) {
      panel.appendChild(
        el("p", { class: "form-error", text: "No ISA header could be located — nothing to inventory." })
      );
      return panel;
    }

    if (entry.has_fatal) {
      panel.appendChild(
        el("p", {
          class: "form-error",
          text: "Cannot be cleansed — a fatal finding remains, so this isn't a conformant interchange. Code inventory withheld.",
        })
      );
      const fatals = entry.diagnostics.filter((d) => d.severity === "fatal");
      panel.appendChild(
        el(
          "ul",
          { class: "fatal-list" },
          fatals.map((d) => el("li", { text: `${d.code} — ${d.message}` }))
        )
      );
      return panel;
    }

    panel.appendChild(occurrenceTable(entry.inventory.occurrences, entry.facts, entry.inventory.separator));
    return panel;
  }

  function renderResults(data) {
    results.innerHTML = "";
    const showHeading = data.interchanges.length > 1;
    for (const entry of data.interchanges) {
      results.appendChild(renderInterchange(entry, showHeading));
    }
    results.hidden = false;
  }
})();
