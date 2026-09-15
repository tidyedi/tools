(function () {
  "use strict";

  const segTbody = document.getElementById("seg-tbody");
  if (!segTbody) return; // not the reference page

  const { el, downloadControl } = window.tableTools;

  const SEGMENT_ROWS = JSON.parse(document.getElementById("segment-rows-data").textContent);
  const ELEMENT_ROWS = JSON.parse(document.getElementById("element-rows-data").textContent);

  // Generic click-to-sort wiring for a <thead> whose <th>s carry
  // data-key -- toggles asc/desc on repeat clicks of the same column.
  function wireSortableHeaders(theadEl, onSort) {
    let state = null; // { key, dir }
    theadEl.querySelectorAll("th.sortable").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.key;
        state = state && state.key === key ? { key, dir: -state.dir } : { key, dir: 1 };
        onSort(state);
      });
    });
  }

  function applySort(rows, sort) {
    if (!sort) return rows;
    return rows.slice().sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      const cmp = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv));
      return cmp * sort.dir;
    });
  }

  // --- Segment names table ------------------------------------------------

  (function setupSegmentTable() {
    const filters = { segment: "", name: "", has_elements: "all", source: "" };
    let sort = null;
    let groupByLetter = false;

    document.getElementById("seg-filter-segment").addEventListener("input", (e) => {
      filters.segment = e.target.value.trim().toLowerCase();
      render();
    });
    document.getElementById("seg-filter-name").addEventListener("input", (e) => {
      filters.name = e.target.value.trim().toLowerCase();
      render();
    });
    document.getElementById("seg-filter-has-elements").addEventListener("change", (e) => {
      filters.has_elements = e.target.value;
      render();
    });
    document.getElementById("seg-filter-source").addEventListener("input", (e) => {
      filters.source = e.target.value.trim().toLowerCase();
      render();
    });
    document.getElementById("seg-group-by-letter").addEventListener("change", (e) => {
      groupByLetter = e.target.checked;
      render();
    });

    wireSortableHeaders(document.querySelector("#seg-table thead"), (s) => {
      sort = s;
      render();
    });

    const downloadWrap = document.getElementById("seg-download");
    const columns = [
      { label: "Segment", get: (r) => r.segment },
      { label: "Name", get: (r) => r.name },
      { label: "Release", get: (r) => r.release },
      { label: "Has elements", get: (r) => (r.has_elements ? "Yes" : "No") },
      { label: "Source", get: (r) => r.source },
    ];
    downloadWrap.appendChild(downloadControl(() => currentRows(), columns, "segment-names"));

    function currentRows() {
      let rows = SEGMENT_ROWS.filter((r) => {
        if (filters.segment && !r.segment.toLowerCase().includes(filters.segment)) return false;
        if (filters.name && !r.name.toLowerCase().includes(filters.name)) return false;
        if (filters.has_elements === "yes" && !r.has_elements) return false;
        if (filters.has_elements === "no" && r.has_elements) return false;
        if (filters.source && !r.source.toLowerCase().includes(filters.source)) return false;
        return true;
      });
      return applySort(rows, sort);
    }

    function render() {
      const rows = currentRows();
      document.getElementById("seg-count-line").textContent =
        `Showing ${rows.length} of ${SEGMENT_ROWS.length} segments.`;
      segTbody.innerHTML = "";

      const renderRow = (r) =>
        el("tr", {}, [
          el("td", { text: r.segment, class: "mono" }),
          el("td", { text: r.name }),
          el("td", { text: r.release, class: "mono" }),
          el("td", { text: r.has_elements ? "Yes" : "No" }),
          el("td", { text: r.source }),
        ]);

      if (groupByLetter) {
        const groups = new Map();
        for (const r of rows) {
          const key = r.segment[0] || "?";
          if (!groups.has(key)) groups.set(key, []);
          groups.get(key).push(r);
        }
        for (const [letter, groupRows] of groups) {
          segTbody.appendChild(
            el("tr", { class: "loop-group-row" }, [
              el("td", { text: `${letter} (${groupRows.length})`, colspan: "5" }),
            ])
          );
          for (const r of groupRows) segTbody.appendChild(renderRow(r));
        }
      } else {
        for (const r of rows) segTbody.appendChild(renderRow(r));
      }
    }

    render();
  })();

  // --- Element definitions table -------------------------------------------

  (function setupElementTable() {
    const elTbody = document.getElementById("el-tbody");
    const filters = { ref: "", name: "", requirement: "", data_type: "", source: "" };
    let sort = null;
    let groupBySegment = true;

    for (const key of ["ref", "name", "requirement", "data_type", "source"]) {
      document.getElementById(`el-filter-${key}`).addEventListener("input", (e) => {
        filters[key] = e.target.value.trim().toLowerCase();
        render();
      });
    }
    document.getElementById("el-group-by-segment").addEventListener("change", (e) => {
      groupBySegment = e.target.checked;
      render();
    });

    wireSortableHeaders(document.querySelector("#el-table thead"), (s) => {
      sort = s;
      render();
    });

    const downloadWrap = document.getElementById("el-download");
    const columns = [
      { label: "Ref", get: (r) => r.ref },
      { label: "Name", get: (r) => r.name },
      { label: "Req", get: (r) => r.requirement },
      { label: "Type", get: (r) => r.data_type },
      { label: "Min", get: (r) => r.min_length },
      { label: "Max", get: (r) => r.max_length },
      { label: "Release", get: (r) => r.release },
      { label: "Source", get: (r) => r.source },
    ];
    downloadWrap.appendChild(downloadControl(() => currentRows(), columns, "element-definitions"));

    function currentRows() {
      let rows = ELEMENT_ROWS.filter((r) => {
        if (filters.ref && !r.ref.toLowerCase().includes(filters.ref)) return false;
        if (filters.name && !r.name.toLowerCase().includes(filters.name)) return false;
        if (filters.requirement && !r.requirement.toLowerCase().includes(filters.requirement)) return false;
        if (filters.data_type && !r.data_type.toLowerCase().includes(filters.data_type)) return false;
        if (filters.source && !r.source.toLowerCase().includes(filters.source)) return false;
        return true;
      });
      return applySort(rows, sort);
    }

    function render() {
      const rows = currentRows();
      const segmentCount = new Set(rows.map((r) => r.segment)).size;
      document.getElementById("el-count-line").textContent =
        `Showing ${rows.length} of ${ELEMENT_ROWS.length} elements, across ${segmentCount} segments.`;
      elTbody.innerHTML = "";

      const renderRow = (r) =>
        el("tr", {}, [
          el("td", { text: r.ref, class: "mono" }),
          el("td", { text: r.name }),
          el("td", { text: r.requirement, class: "mono" }),
          el("td", { text: r.data_type, class: "mono" }),
          el("td", { text: String(r.min_length), class: "mono" }),
          el("td", { text: String(r.max_length), class: "mono" }),
          el("td", { text: r.release, class: "mono" }),
          el("td", { text: r.source }),
        ]);

      if (groupBySegment) {
        const groups = new Map();
        for (const r of rows) {
          if (!groups.has(r.segment)) groups.set(r.segment, []);
          groups.get(r.segment).push(r);
        }
        for (const [segment, groupRows] of groups) {
          elTbody.appendChild(
            el("tr", { class: "loop-group-row" }, [
              el("td", { text: `${segment} (${groupRows.length})`, colspan: "8" }),
            ])
          );
          for (const r of groupRows) elTbody.appendChild(renderRow(r));
        }
      } else {
        for (const r of rows) elTbody.appendChild(renderRow(r));
      }
    }

    render();
  })();
})();
