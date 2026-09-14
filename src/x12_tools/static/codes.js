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

  // Same shape as the segment-inventory identifier: release.edi.sender-receiver.date.
  function tsListId(ts, facts) {
    const release = ts.releases.length ? ts.releases.join("+") : "UNKNOWN";
    const sender = (facts && facts.sender_id) || "UNKNOWN";
    const receiver = (facts && facts.receiver_id) || "UNKNOWN";
    const date = (facts && facts.interchange_date) || "UNKNOWN";
    return `${release}.${ts.transaction_set_id}.${sender}-${receiver}.${date}`;
  }

  // One raw segment's tokens (segment ID first, then every data element),
  // rendered with the token at `position` (1-based, matching X12's own
  // element numbering, so it lines up with tokens[position]) wrapped in
  // <mark> -- lets a reviewer see exactly where a "values found" entry came
  // from on the wire.
  function rawSegmentLine(tokens, position, separator) {
    const line = el("div", { class: "raw-segment" });
    tokens.forEach((tok, i) => {
      if (i > 0) line.appendChild(document.createTextNode(separator));
      line.appendChild(i === position ? el("mark", { text: tok }) : document.createTextNode(tok));
    });
    return line;
  }

  function rawSegmentsCell(c, separator) {
    const cell = el("td", { class: "mono" });
    for (const tokens of c.raw_segments) {
      cell.appendChild(rawSegmentLine(tokens, c.position, separator));
    }
    return cell;
  }

  function codeTable(ts, facts, separator) {
    const id = tsListId(ts, facts);
    const wrap = el("div", { class: "convention-wrap" });
    wrap.appendChild(el("h3", { class: "ts-id", text: id }));

    if (!ts.codes.length) {
      wrap.appendChild(
        el("p", {
          class: "hint",
          text: "No coded elements covered by element_definitions.py were found here.",
        })
      );
      return wrap;
    }

    const headers = ["Segment", "Pos", "Name", "Req", "Min", "Max", "Values found", "Raw segment"];
    const thead = el("thead", {}, [el("tr", {}, headers.map((label) => el("th", { text: label })))]);
    const rows = ts.codes.map((c) =>
      el("tr", {}, [
        el("td", { text: c.segment_id, class: "mono" }),
        el("td", { text: String(c.position), class: "mono" }),
        el("td", { text: c.name }),
        el("td", { text: c.requirement, class: "mono" }),
        el("td", { text: String(c.min_length), class: "mono" }),
        el("td", { text: String(c.max_length), class: "mono" }),
        el("td", { text: c.values.join(", ") }),
        rawSegmentsCell(c, separator),
      ])
    );
    const table = el("table", { class: "convention-table" }, [thead, el("tbody", {}, rows)]);
    wrap.appendChild(el("div", { class: "convention-table-wrap" }, [table]));
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

    for (const ts of entry.inventory.transaction_sets) {
      panel.appendChild(codeTable(ts, entry.facts, entry.inventory.separator));
    }
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
