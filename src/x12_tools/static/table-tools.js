// Shared helpers for building/sorting/filtering/downloading tables --
// used by codes.js, convention.js, and reference.js so this logic (and its
// export-format choices) lives in exactly one place.
window.tableTools = (function () {
  "use strict";

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

  function downloadRows(rows, columns, format, baseName, getFile) {
    const records = toRecords(rows, columns, getFile);
    let content, mime, ext;
    if (format === "json") {
      content = JSON.stringify(records, null, 2);
      mime = "application/json";
      ext = "json";
    } else if (format === "pipe") {
      content = toDelimited(records, "|");
      mime = "text/plain";
      ext = "txt";
    } else if (format === "html") {
      content = toHtmlTable(records);
      mime = "text/html";
      ext = "html";
    } else {
      // csv and excel both produce a real CSV -- Excel opens .csv natively,
      // and this avoids adding an external spreadsheet library.
      content = toDelimited(records, ",");
      mime = "text/csv";
      ext = "csv";
    }
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = el("a", { href: url, download: `${baseName}.${ext}` });
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
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
        ["excel", "Excel (CSV)"],
        ["json", "JSON"],
        ["pipe", "Pipe-delimited"],
        ["html", "HTML"],
      ].map(([value, text]) => el("option", { value, text }))
    );
    const btn = el("button", { type: "button", class: "ghost", text: "Download" });
    btn.addEventListener("click", () => downloadRows(getRows(), columns, select.value, baseName, getFile));
    wrap.appendChild(select);
    wrap.appendChild(btn);
    return wrap;
  }

  return { el, csvEscape, toDelimited, toHtmlTable, toRecords, downloadRows, downloadControl };
})();
