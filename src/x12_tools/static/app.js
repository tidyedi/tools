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

  // A stable, compact key for one segment list: release.edi.sender-receiver.date
  // -- e.g. "004010.850.NORTHWIND-CONTOSO.240402". Everything a companion
  // guide needs to identify *which* convention this list belongs to, in one
  // line, with no counts of anything.
  function listId(release, edi, facts) {
    const sender = (facts && facts.sender_id) || "UNKNOWN";
    const receiver = (facts && facts.receiver_id) || "UNKNOWN";
    const date = (facts && facts.interchange_date) || "UNKNOWN";
    return `${release}.${edi}.${sender}-${receiver}.${date}`;
  }

  function tsListId(ts, facts) {
    return listId(ts.releases.length ? ts.releases.join("+") : "UNKNOWN", ts.transaction_set_id, facts);
  }

  function envelopeListId(facts) {
    const release = facts && facts.group_versions.length ? facts.group_versions.join("+") : "UNKNOWN";
    return listId(release, "ENVELOPE", facts);
  }

  // One identified list on screen: the id line, then its segments as chips.
  function listBlock(id, segments) {
    const block = el("div", { class: "ts-group" });
    block.appendChild(el("h3", { class: "ts-id", text: id }));
    block.appendChild(segmentChips(segments));
    return block;
  }

  // The same lists shown on screen, as plain text meant to be pasted into a
  // convention draft: one identifier line, then that list's segments --
  // nothing else, no counts.
  function plainTextList(entry) {
    const inv = entry.inventory;
    const facts = entry.facts;
    const lines = [];

    if (inv.envelope_segments.length) {
      lines.push(envelopeListId(facts));
      lines.push(inv.envelope_segments.join(", "));
    }

    for (const ts of inv.transaction_sets) {
      if (lines.length) lines.push("");
      lines.push(tsListId(ts, facts));
      lines.push(ts.segments.join(", "));
    }

    return lines.join("\n");
  }

  function copyBlock(text) {
    const wrap = el("div", { class: "copy-wrap" });
    const btn = el("button", { type: "button", class: "ghost", text: "Copy list" });
    const pre = el("pre", { text });
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = "Copied!";
      } catch {
        btn.textContent = "Copy failed — select and copy manually";
      }
      setTimeout(() => {
        btn.textContent = "Copy list";
      }, 1500);
    });
    wrap.appendChild(btn);
    wrap.appendChild(pre);
    return wrap;
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
      panel.appendChild(listBlock(envelopeListId(entry.facts), inv.envelope_segments));
    }
    for (const ts of inv.transaction_sets) {
      panel.appendChild(listBlock(tsListId(ts, entry.facts), ts.segments));
    }

    panel.appendChild(copyBlock(plainTextList(entry)));

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
