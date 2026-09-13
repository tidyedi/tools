(function () {
  "use strict";

  const form = document.getElementById("convention-form");
  if (!form) return; // not the convention page

  const fileInput = document.getElementById("pdf-file");
  const clearBtn = document.getElementById("clear-btn");
  const submitBtn = document.getElementById("submit-btn");
  const formError = document.getElementById("form-error");
  const results = document.getElementById("results");

  clearBtn.addEventListener("click", () => {
    fileInput.value = "";
    results.hidden = true;
    results.innerHTML = "";
    formError.hidden = true;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;

    const file = fileInput.files[0];
    if (!file) {
      formError.textContent = "Choose a PDF file first.";
      formError.hidden = false;
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Parsing…";

    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch("/api/convention", { method: "POST", body });
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
      submitBtn.textContent = "Parse convention";
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

  function segmentTable(rows) {
    const headers = ["Pos", "Loop", "Id", "Segment Name", "Req", "Max Use", "Repeat", "Notes", "Usage"];
    const thead = el("thead", {}, [el("tr", {}, headers.map((h) => el("th", { text: h })))]);
    const trows = rows.map((r) =>
      el("tr", {}, [
        el("td", { text: (r.flagged ? "* " : "") + r.pos, class: "mono" }),
        el("td", { text: r.loop_id || "", class: "mono" }),
        el("td", { text: r.segment_id, class: "mono" }),
        el("td", { text: r.name }),
        el("td", { text: r.requirement, class: "mono" }),
        el("td", { text: r.max_use, class: "mono" }),
        el("td", { text: r.repeat, class: "mono" }),
        el("td", { text: r.notes, class: "mono" }),
        el("td", { text: r.usage }),
      ])
    );
    return el("table", { class: "convention-table" }, [thead, el("tbody", {}, trows)]);
  }

  // Flattened one row per (element, code) pair -- an element with no codes
  // gets one row with the code columns blank.
  function segmentDetailTable(detail) {
    const headers = ["Ref", "Elem#", "Element Name", "Req", "Type", "Min/Max", "Usage", "Code", "Code Name"];
    const thead = el("thead", {}, [el("tr", {}, headers.map((h) => el("th", { text: h })))]);
    const rows = [];
    for (const e of detail.elements) {
      const base = [e.ref, e.element_number, e.name, e.requirement, e.data_type, e.min_max, e.usage];
      if (!e.codes.length) {
        rows.push([...base, "", ""]);
      } else {
        for (const c of e.codes) rows.push([...base, c.code, c.name]);
      }
    }
    const trows = rows.map((cols) =>
      el(
        "tr",
        {},
        cols.map((v, i) => el("td", { text: v, class: i < 2 || i === 7 ? "mono" : "" }))
      )
    );
    return el("table", { class: "convention-table" }, [thead, el("tbody", {}, trows)]);
  }

  function renderResults(data) {
    results.innerHTML = "";

    if (data.segment_table.length) {
      const panel = el("div", { class: "panel" });
      panel.appendChild(el("h2", { text: `Segment table (${data.segment_table.length} rows)` }));
      panel.appendChild(el("div", { class: "convention-table-wrap" }, [segmentTable(data.segment_table)]));
      results.appendChild(panel);
    } else {
      results.appendChild(
        el("div", { class: "panel" }, [
          el("p", { class: "form-error", text: "No segment table found in this PDF." }),
        ])
      );
    }

    const segmentIds = Object.keys(data.segment_details);
    if (segmentIds.length) {
      const panel = el("div", { class: "panel" });
      panel.appendChild(el("h2", { text: `Element definitions & codes (${segmentIds.length} segments)` }));
      for (const sid of segmentIds) {
        const detail = data.segment_details[sid];
        const details = el("details", {});
        details.appendChild(
          el("summary", { text: `${sid} — Pos ${detail.pos}, Max ${detail.max_use} (${detail.elements.length} elements)` })
        );
        details.appendChild(el("div", { class: "convention-table-wrap" }, [segmentDetailTable(detail)]));
        panel.appendChild(details);
      }
      results.appendChild(panel);
    }

    results.hidden = false;
  }
})();
