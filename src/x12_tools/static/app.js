(function () {
  "use strict";

  const form = document.getElementById("edi-form");
  if (!form) return; // not the segments page

  const ediField = document.getElementById("edi");
  const fileInput = document.getElementById("file");
  const clearBtn = document.getElementById("clear-btn");
  const submitBtn = document.getElementById("submit-btn");
  const formError = document.getElementById("form-error");
  const results = document.getElementById("results");

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;
    file.text().then((text) => {
      ediField.value = text;
    });
  });

  clearBtn.addEventListener("click", () => {
    ediField.value = "";
    fileInput.value = "";
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

  function severityCountsRow(counts) {
    const parts = ["fatal", "error", "warning"]
      .filter((sev) => counts[sev] > 0)
      .map((sev) => el("span", { class: `sev-${sev}`, text: `${counts[sev]} ${sev}` }));
    if (!parts.length) {
      return el("p", { class: "hint", text: "No findings — this interchange was already clean." });
    }
    return el("div", { class: "severity-counts" }, parts);
  }

  function diagnosticsList(diagnostics) {
    if (!diagnostics.length) return null;
    const items = diagnostics.map((d) => {
      const loc = d.offset !== null ? ` (byte ${d.offset})` : "";
      return el("li", {}, [
        el("span", { class: `diag-code sev-${d.severity}`, text: d.code }),
        el("span", { text: ` — ${d.message}${loc}` }),
      ]);
    });
    return el("ul", { class: "diag-list" }, items);
  }

  function segmentChips(segments) {
    return el(
      "div",
      { class: "segment-chips" },
      segments.map((s) => el("span", { class: "segment-chip", text: s }))
    );
  }

  function renderInterchange(entry) {
    const panel = el("div", { class: "panel" });
    panel.appendChild(el("h2", { text: `Interchange ${entry.index}` }));

    if (!entry.recovered) {
      panel.appendChild(
        el("p", { class: "form-error", text: "No ISA header could be located — nothing to inventory." })
      );
      const diags = diagnosticsList(entry.diagnostics);
      if (diags) panel.appendChild(diags);
      return panel;
    }

    panel.appendChild(severityCountsRow(entry.severity_counts));
    const diags = diagnosticsList(entry.diagnostics);
    if (diags) panel.appendChild(diags);

    const inv = entry.inventory;
    if (inv.envelope_segments.length) {
      panel.appendChild(el("h3", { text: "Envelope" }));
      panel.appendChild(segmentChips(inv.envelope_segments));
    }

    for (const ts of inv.transaction_sets) {
      const group = el("div", { class: "ts-group" });
      const occ = ts.occurrences === 1 ? "1 occurrence" : `${ts.occurrences} occurrences`;
      group.appendChild(
        el("h3", {}, [
          document.createTextNode(ts.transaction_set_id + " "),
          el("span", { class: "occurrences", text: `(${occ})` }),
        ])
      );
      group.appendChild(segmentChips(ts.segments));
      panel.appendChild(group);
    }

    const details = el("details", { class: "cleansed-wrap" });
    details.appendChild(el("summary", { text: "Cleansed interchange" }));
    const pre = el("pre", { text: entry.cleansed_text || "" });
    details.appendChild(pre);
    panel.appendChild(details);

    return panel;
  }

  function renderResults(data) {
    results.innerHTML = "";
    for (const entry of data.interchanges) {
      results.appendChild(renderInterchange(entry));
    }
    results.hidden = false;
  }
})();
