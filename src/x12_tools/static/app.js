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

  // A stable, compact key for one transaction set type's segment list:
  // release.edi.sender-receiver.date -- e.g.
  // "004010.850.NORTHWIND-CONTOSO.2024-04-02". More than one release for the
  // same type in this submission joins with "+" (e.g. "004010+005010"). No
  // counts of anything -- just enough to say which convention this list is for.
  function tsListId(ts, facts) {
    const release = ts.releases.length ? ts.releases.join("+") : "UNKNOWN";
    const sender = (facts && facts.sender_id) || "UNKNOWN";
    const receiver = (facts && facts.receiver_id) || "UNKNOWN";
    const date = (facts && facts.interchange_date) || "UNKNOWN";
    return `${release}.${ts.transaction_set_id}.${sender}-${receiver}.${date}`;
  }

  // The lists shown on screen, as a pipe-delimited table meant to be pasted
  // into a convention draft: one row per segment -- identifier | segment |
  // element count -- across every transaction set type in this interchange.
  function plainTextList(entry) {
    const facts = entry.facts;
    const lines = [];

    for (const ts of entry.inventory.transaction_sets) {
      const id = tsListId(ts, facts);
      for (const seg of ts.segments) {
        lines.push(`${id} | ${seg.segment_id} | ${seg.element_count}`);
      }
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

    panel.appendChild(copyBlock(plainTextList(entry)));
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
