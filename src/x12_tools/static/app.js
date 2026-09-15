(function () {
  "use strict";

  const form = document.getElementById("edi-form");
  if (!form) return; // not the segments page

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

  const segmentNamesDataEl = document.getElementById("segment-names-data");
  const SEGMENT_NAMES = segmentNamesDataEl ? JSON.parse(segmentNamesDataEl.textContent) : {};

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
      const response = await fetch("/api/segments", {
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
      submitBtn.textContent = "Cleanse & list segments";
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

  // A stable, compact key for one transaction set type's segment list:
  // release.edi.sender-receiver.date -- e.g.
  // "004010.850.NORTHWIND-CONTOSO.2024-04-02". More than one release for the
  // same type in this submission joins with "+" (e.g. "004010+005010"). No
  // counts of anything -- just enough to say which convention this list is for.
  //
  // ``suffix`` is the implementation-convention suffix (e.g. the "A" in
  // "315A") -- assigned by whoever publishes the convention, not carried
  // anywhere in the EDI itself, so it's a manual field appended to the EDI
  // number here rather than something read off the interchange.
  function tsListId(ts, facts, suffix) {
    const release = ts.releases.length ? ts.releases.join("+") : "UNKNOWN";
    const sender = (facts && facts.sender_id) || "UNKNOWN";
    const receiver = (facts && facts.receiver_id) || "UNKNOWN";
    const date = (facts && facts.interchange_date) || "UNKNOWN";
    const edi = ts.transaction_set_id + (suffix || "");
    return `${release}.${edi}.${sender}-${receiver}.${date}`;
  }

  // One transaction set type's segment list as an editable convention table:
  // Segment, Elements and Used come from the EDI (read-only); Segment name is
  // pre-filled from a local X12 reference when known (editable). "Copy table"
  // reads the table's current state (including your edits) as tab-separated
  // text, ready to paste into a spreadsheet -- the identifier is repeated on
  // every row so a pasted table still says which convention it's for.
  function conventionTable(ts, facts) {
    const id = tsListId(ts, facts);
    const wrap = el("div", { class: "convention-wrap" });
    wrap.appendChild(el("h3", { class: "ts-id", text: id }));

    const headerCells = ["Segment", "Elements", "Used", "Segment name"].map((label) =>
      el("th", { text: label })
    );
    const thead = el("thead", {}, [el("tr", {}, headerCells)]);

    const rows = ts.segments.map((seg) => {
      const nameCell = el("td", { contenteditable: "true", class: "editable" });
      nameCell.textContent = SEGMENT_NAMES[seg.segment_id] || "";
      return el("tr", {}, [
        el("td", { text: seg.segment_id, class: "mono" }),
        el("td", { text: String(seg.element_count), class: "mono" }),
        el("td", { text: String(seg.populated_count), class: "mono" }),
        nameCell,
      ]);
    });
    const tbody = el("tbody", {}, rows);

    const table = el("table", { class: "convention-table" }, [thead, tbody]);
    wrap.appendChild(el("div", { class: "convention-table-wrap" }, [table]));
    wrap.appendChild(copyButtons(id, table));
    return wrap;
  }

  function cellValue(td) {
    return td.textContent.trim();
  }

  const TABLE_HEADER = ["Identifier", "Segment", "Elements", "Used", "Segment name"];

  // The table's current state (including edits) as rows of plain strings,
  // header first -- the one source both export formats read from.
  function tableRows(id, table) {
    const rows = [TABLE_HEADER];
    for (const tr of table.tBodies[0].rows) {
      rows.push([id, ...Array.from(tr.cells).map(cellValue)]);
    }
    return rows;
  }

  function toTSV(rows) {
    return rows.map((r) => r.join("\t")).join("\n");
  }

  // A GitHub-flavored Markdown table. Pipes in a cell (unlikely here, but a
  // hand-typed note could have one) are escaped so they don't break the row.
  function toMarkdown(rows) {
    const escape = (cell) => cell.replace(/\|/g, "\\|");
    const [header, ...body] = rows;
    const lines = [
      `| ${header.map(escape).join(" | ")} |`,
      `| ${header.map(() => "---").join(" | ")} |`,
      ...body.map((row) => `| ${row.map(escape).join(" | ")} |`),
    ];
    return lines.join("\n");
  }

  function copyButton(label, getText) {
    const btn = el("button", { type: "button", class: "ghost", text: label });
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(getText());
        btn.textContent = "Copied!";
      } catch {
        btn.textContent = "Copy failed — select and copy manually";
      }
      setTimeout(() => {
        btn.textContent = label;
      }, 1500);
    });
    return btn;
  }

  function copyButtons(id, table) {
    return el("div", { class: "copy-buttons" }, [
      copyButton("Copy table", () => toTSV(tableRows(id, table))),
      copyButton("Copy as Markdown", () => toMarkdown(tableRows(id, table))),
    ]);
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
          text: "Cannot be cleansed — a fatal finding remains, so this isn't a conformant interchange. Segment list withheld.",
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

    for (const ts of entry.inventory.transaction_sets) {
      panel.appendChild(conventionTable(ts, entry.facts));
    }
    return panel;
  }

  function renderResults(data) {
    results.innerHTML = "";
    const showHeading = data.interchanges.length > 1; // only disambiguate when there's more than one
    for (const entry of data.interchanges) {
      results.appendChild(renderInterchange(entry, showHeading));
    }
    results.hidden = false;
  }
})();
