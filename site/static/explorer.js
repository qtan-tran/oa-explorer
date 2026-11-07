/* explorer.js — optional progressive enhancement for the M1 demo site.
 *
 * Scope: client-side filtering and title search over the pre-built index.json.
 * The site is fully usable without this file: the complete version list is
 * pre-rendered in the HTML, and every record page is a direct deep link.
 * No network calls except fetching index.json from the same directory.
 * No analytics, no cookies, no external dependencies.
 */
(function () {
  "use strict";

  var mount = document.getElementById("filter-mount");
  var statusEl = document.getElementById("filter-status");
  var table = document.getElementById("version-list");
  if (!mount || !table) { return; }

  fetch("index.json")
    .then(function (r) { return r.json(); })
    .then(function (idx) { install(idx.versions); })
    .catch(function () {
      /* No JS-free behaviour is lost; simply leave the full list. */
      mount.textContent = "";
    });

  function install(versions) {
    var byId = {};
    versions.forEach(function (v) { byId[v.version_id] = v; });

    var facets = {
      country: distinct(versions, "country"),
      "issuer-type": distinct(versions, "issuer_type"),
      function: distinct(versions, "function"),
      area: distinct(versions, "area"),
      "source-status": distinct(versions, "source_status")
    };
    var years = versions.map(function (v) { return v.adopted_year; })
      .filter(Boolean).sort();

    var fs = document.createElement("fieldset");
    var legend = document.createElement("legend");
    legend.textContent = "Filter and search policy versions";
    fs.appendChild(legend);
    var grid = document.createElement("div");
    grid.className = "filters";
    fs.appendChild(grid);

    var controls = {};
    function addSelect(id, label, options) {
      var wrap = document.createElement("div");
      var lb = document.createElement("label");
      lb.setAttribute("for", "flt-" + id);
      lb.textContent = label;
      var sel = document.createElement("select");
      sel.id = "flt-" + id;
      addOption(sel, "", "all");
      options.forEach(function (o) { addOption(sel, o, o); });
      wrap.appendChild(lb); wrap.appendChild(sel);
      grid.appendChild(wrap);
      controls[id] = sel;
    }
    function addOption(sel, value, text) {
      var o = document.createElement("option");
      o.value = value; o.textContent = text;
      sel.appendChild(o);
    }
    addSelect("country", "Country", facets.country);
    addSelect("issuer-type", "Issuer type", facets["issuer-type"]);
    addSelect("function", "Policy function", facets.function);
    addSelect("area", "OA/OS scope", facets.area);
    addSelect("year", "Adopted year", distinctYears(years));
    addSelect("source-status", "Source status", facets["source-status"]);

    var searchWrap = document.createElement("div");
    var searchLb = document.createElement("label");
    searchLb.setAttribute("for", "flt-search");
    searchLb.textContent = "Search titles and issuers";
    var search = document.createElement("input");
    search.type = "search";
    search.id = "flt-search";
    search.setAttribute("autocomplete", "off");
    searchWrap.appendChild(searchLb); searchWrap.appendChild(search);
    grid.appendChild(searchWrap);
    controls.search = search;

    var resetWrap = document.createElement("div");
    var reset = document.createElement("button");
    reset.type = "button";
    reset.textContent = "Reset filters";
    resetWrap.appendChild(reset);
    grid.appendChild(resetWrap);

    mount.appendChild(fs);
    Object.keys(controls).forEach(function (k) {
      controls[k].addEventListener("input", apply);
      controls[k].addEventListener("change", apply);
    });
    reset.addEventListener("click", function () {
      Object.keys(controls).forEach(function (k) {
        controls[k].value = k === "search" ? "" : "";
      });
      apply();
    });

    function matches(row) {
      var v = byId[row.getAttribute("data-version")];
      if (!v) { return false; }
      if (controls.country.value && v.country !== controls.country.value) { return false; }
      if (controls["issuer-type"].value && v.issuer_type !== controls["issuer-type"].value) { return false; }
      if (controls.function.value && v.function !== controls.function.value) { return false; }
      if (controls.area.value && v.area !== controls.area.value) { return false; }
      if (controls.year.value && String(v.adopted_year) !== controls.year.value) { return false; }
      if (controls["source-status"].value && v.source_status !== controls["source-status"].value) { return false; }
      var q = controls.search.value.trim().toLowerCase();
      if (q) {
        var hay = (Object.keys(v.titles).map(function (l) { return v.titles[l]; })
          .concat([v.issuer, v.version_id, v.version_label])).join(" ").toLowerCase();
        if (hay.indexOf(q) === -1) { return false; }
      }
      return true;
    }

    function apply() {
      var rows = table.querySelectorAll("tbody tr");
      var shown = 0;
      rows.forEach(function (row) {
        var ok = matches(row);
        row.hidden = !ok;
        if (ok) { shown += 1; }
      });
      statusEl.textContent = shown + " of " + rows.length +
        " policy versions shown. Facet counts always refer to the corpus in this export, never to a country's sector.";
    }

    apply();
  }

  function distinct(versions, key) {
    var seen = {};
    versions.forEach(function (v) {
      if (v[key]) { seen[v[key]] = true; }
    });
    return Object.keys(seen).sort();
  }
  function distinctYears(years) {
    var seen = {};
    years.forEach(function (y) { seen[y] = true; });
    return Object.keys(seen).sort();
  }
}());
