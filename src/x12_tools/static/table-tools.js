// Shared helpers for building/sorting/filtering/downloading tables --
// used by codes.js, convention.js, and reference.js so this logic (and its
// export-format choices) lives in exactly one place.
window.tableTools = (function () {
  "use strict";

  // A column's `get()` can wrap a substring in this pair to mark it for
  // bold+color rendering in the .xlsx export (xlsx_export.py looks for the
  // same character) -- e.g. the one highlighted token in a raw segment
  // string. Every other format strips it and keeps just the plain text.
  const HIGHLIGHT_MARKER = "\u0001";

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

  function csvEscape(value, delimiter) {
    const s = String(value ?? "");
    return s.includes(delimiter) || s.includes('"') || s.includes("\n") ? `"${s.replace(/"/g, '""')}"` : s;
  }

  function toDelimited(records, delimiter) {
    if (!records.length) return "";
    const headers = Object.keys(records[0]);
    const lines = [headers.join(delimiter)];
    for (const r of records) {
      lines.push(headers.map((h) => csvEscape(r[h], delimiter)).join(delimiter));
    }
    return lines.join("\r\n");
  }

  function toHtmlTable(records) {
    if (!records.length) return "<table></table>";
    const headers = Object.keys(records[0]);
    const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
    const head = `<tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr>`;
    const body = records.map((r) => `<tr>${headers.map((h) => `<td>${esc(r[h])}</td>`).join("")}</tr>`).join("\n");
    return `<table border="1">\n${head}\n${body}\n</table>`;
  }

  // `columns` is [{label, get(row)}, ...]. `getFile` is an optional
  // (row) => filename function -- when given, a File column is added to
  // every export even on pages where the on-screen table hides it.
  function toRecords(rows, columns, getFile) {
    return rows.map((row) => {
      const record = {};
      if (getFile) record.File = getFile(row);
      for (const col of columns) record[col.label] = col.get(row);
      return record;
    });
  }

  // Every non-.xlsx format writes plain text -- strip the highlight
  // sentinel rather than leak a raw control character into the file.
  function stripMarkers(records) {
    return records.map((r) => {
      const clean = {};
      for (const [k, v] of Object.entries(r)) {
        clean[k] = typeof v === "string" ? v.split(HIGHLIGHT_MARKER).join("") : v;
      }
      return clean;
    });
  }

  function triggerBlobDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = el("a", { href: url, download: filename });
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // A real .xlsx workbook (bold header, frozen, sized columns) is built
  // server-side -- keeps every page free of a client-side spreadsheet
  // library, matching this project's stance of loading only its own JS.
  async function downloadXlsx(records, baseName) {
    const response = await fetch("/api/export/xlsx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: baseName, records }),
    });
    if (!response.ok) {
      throw new Error(`export failed (${response.status})`);
    }
    triggerBlobDownload(await response.blob(), `${baseName}.xlsx`);
  }

  async function downloadRows(rows, columns, format, baseName, getFile) {
    const records = toRecords(rows, columns, getFile);
    if (format === "excel") {
      await downloadXlsx(records, baseName);
      return;
    }
    const clean = stripMarkers(records);
    let content, mime, ext;
    if (format === "json") {
      content = JSON.stringify(clean, null, 2);
      mime = "application/json";
      ext = "json";
    } else if (format === "pipe") {
      content = toDelimited(clean, "|");
      mime = "text/plain";
      ext = "txt";
    } else if (format === "html") {
      content = toHtmlTable(clean);
      mime = "text/html";
      ext = "html";
    } else {
      content = toDelimited(clean, ",");
      mime = "text/csv";
      ext = "csv";
    }
    triggerBlobDownload(new Blob([content], { type: mime }), `${baseName}.${ext}`);
  }

  // A format <select> plus a Download button. `getRows` returns the
  // current (filtered/sorted) array of row objects at click time.
  function downloadControl(getRows, columns, baseName, getFile) {
    const wrap = el("span", { class: "inline" });
    const select = el(
      "select",
      {},
      [
        ["csv", "CSV"],
        ["excel", "Excel (XLSX)"],
        ["json", "JSON"],
        ["pipe", "Pipe-delimited"],
        ["html", "HTML"],
      ].map(([value, text]) => el("option", { value, text }))
    );
    const btn = el("button", { type: "button", class: "ghost", text: "Download" });
    btn.addEventListener("click", async () => {
      const originalText = btn.textContent;
      btn.disabled = true;
      try {
        await downloadRows(getRows(), columns, select.value, baseName, getFile);
      } catch (err) {
        btn.textContent = "Download failed";
        setTimeout(() => {
          btn.textContent = originalText;
        }, 2000);
        console.error(err);
      } finally {
        btn.disabled = false;
        if (btn.textContent === "Download failed") return; // let the timeout restore it
        btn.textContent = originalText;
      }
    });
    wrap.appendChild(select);
    wrap.appendChild(btn);
    return wrap;
  }

  return {
    el,
    csvEscape,
    toDelimited,
    toHtmlTable,
    toRecords,
    downloadRows,
    downloadControl,
    HIGHLIGHT_MARKER,
  };
})();
