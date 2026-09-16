(function () {
  "use strict";
  const D = window.NEPAL_DATA;
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const PAGE = 60;

  if (!D) {
    $("#main").innerHTML = '<p class="empty">The data file did not load. Run <code>python3 scripts/build_data.py</code> to create <code>data/data.js</code>.</p>';
    return;
  }

  // ---------- precompute ----------
  const _counts = {};
  D.objects.forEach((o) => (_counts[o.source] = (_counts[o.source] || 0) + 1));
  const SOURCE_ORDER = Object.keys(_counts).sort((a, b) => _counts[b] - _counts[a]);
  const centuryNum = (c) => { const m = /^(\d+)/.exec(c || ""); return m ? +m[1] : 999; };
  D.objects.forEach((o, i) => {
    o._i = i;
    o._hay = [o.title, o.date, o.type, o.medium, o.place, o.accession, o.credit, o.provenance, o.source].join(" ").toLowerCase();
  });
  const hayOf = (obj) => Object.values(obj).join(" ").toLowerCase();
  D.archives.forEach((a) => (a._hay = hayOf(a)));
  D.repatriation.forEach((r) => (r._hay = hayOf(r)));
  D.institutions.forEach((r) => (r._hay = hayOf(r)));

  const state = { q: "", sources: new Set(), type: "", century: "", open: false, prov: false, weak: false, sort: "rel", shown: PAGE, status: "All" };
  const tokens = () => state.q.toLowerCase().split(/\s+/).filter(Boolean);
  const matchQ = (hay) => tokens().every((t) => hay.includes(t));

  // ---------- header ----------
  const fmt = (n) => n.toLocaleString("en-GB");
  $("#stamp").textContent = `${fmt(D.objects.length)} records from ${SOURCE_ORDER.length} collections via open APIs and the Smithsonian Open Access dataset, harvested ${D.harvested}. Figures change as institutions update their catalogues.`;

  // ---------- filter controls ----------
  const bySource = {};
  D.objects.forEach((o) => (bySource[o.source] = (bySource[o.source] || 0) + 1));
  $("#f-source").innerHTML = SOURCE_ORDER.filter((s) => bySource[s]).map((s, i) =>
    `<div class="src"><label><input type="checkbox" value="${esc(s)}" id="src${i}"> ${esc(s)}</label><span class="n">${fmt(bySource[s])}</span></div>`).join("");

  const types = [...new Set(D.objects.map((o) => o.type).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  $("#f-type").insertAdjacentHTML("beforeend", types.map((t) => `<option>${esc(t)}</option>`).join(""));
  const cents = [...new Set(D.objects.map((o) => o.century))].sort((a, b) => centuryNum(a) - centuryNum(b));
  $("#f-century").insertAdjacentHTML("beforeend", cents.map((c) => `<option>${esc(c)}</option>`).join(""));

  // ---------- objects ----------
  function filteredObjects() {
    let list = D.objects.filter((o) =>
      (state.weak || o.strength !== "weak") &&
      (!state.sources.size || state.sources.has(o.source)) &&
      (!state.type || o.type === state.type) &&
      (!state.century || o.century === state.century) &&
      (!state.open || (o.openImage && o.image)) &&
      (!state.prov || o.provenance) &&
      matchQ(o._hay));
    if (state.sort === "old") list = list.slice().sort((a, b) => centuryNum(a.century) - centuryNum(b.century));
    if (state.sort === "title") list = list.slice().sort((a, b) => a.title.localeCompare(b.title));
    return list;
  }

  function card(o) {
    const img = o.image
      ? `<img src="${esc(o.image)}" alt="" loading="lazy" decoding="async" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'noimg',textContent:'Image did not load — view at source'}))">`
      : `<span class="noimg">No open image in this record — view at source</span>`;
    return `<li class="card"><button type="button" data-i="${o._i}" aria-label="${esc(o.title)}, details">
      <div class="thumb">${img}</div>
      <h3>${esc(o.title)}</h3>
      <p class="meta">${esc(o.date || "Undated")}<br>${esc(o.source)}</p>
      ${o.claim ? '<span class="flag claim">Repatriation claim</span>' : ""}
    </button></li>`;
  }

  function renderObjects() {
    const list = filteredObjects();
    const grid = $("#grid");
    $("#resultline").textContent = list.length === D.objects.length
      ? `Showing all ${fmt(list.length)} records`
      : `${fmt(list.length)} of ${fmt(D.objects.length)} records match`;
    if (!list.length) {
      grid.innerHTML = `<li class="empty">No records match. Try fewer words, or clear filters. Weak keyword matches are hidden unless you include them.</li>`;
    } else {
      grid.innerHTML = list.slice(0, state.shown).map(card).join("");
    }
    $("#more").hidden = list.length <= state.shown;
    $("#more").textContent = `Show ${fmt(Math.min(PAGE, list.length - state.shown))} more`;
    document.querySelector('[data-count="objects"]').textContent = `(${fmt(list.length)})`;
  }

  function openDetail(o) {
    const row = (k, v) => (v ? `<dt>${k}</dt><dd>${esc(v)}</dd>` : "");
    $("#d-body").innerHTML = `<div class="d-grid">
      <div>${o.image ? `<img src="${esc(o.image)}" alt="${esc(o.title)}">` : `<div class="thumb"><span class="noimg">No openly licensed image in the record</span></div>`}</div>
      <div>
        <h2 id="d-title">${esc(o.title)}</h2>
        <p class="meta">${esc(o.source)}, ${esc(o.country)}</p>
        ${o.claim ? `<p class="flag claim">${esc(o.claim)}</p>` : ""}
        <dl class="facts">
          ${row("Date", o.date)}${row("Type", o.type)}${row("Medium", o.medium)}${row("Place", o.place)}
          ${row("Accession", o.accession)}${row("Credit", o.credit)}${row("Data terms", o.dataLicence)}${row("Why listed", o.matchBasis)}
        </dl>
        ${o.provenance ? `<h3>Provenance as published by the institution</h3><p class="prov">${esc(o.provenance)}</p>` : ""}
        <a class="btnlink" href="${esc(o.url)}" target="_blank" rel="noopener">View record at ${esc(o.source)}</a>
      </div></div>`;
    $("#detail").showModal();
  }

  // ---------- archives ----------
  function renderArchives() {
    const list = D.archives.filter((a) => matchQ(a._hay));
    document.querySelector('[data-count="archives"]').textContent = `(${list.length})`;
    $("#archive-list").innerHTML = list.length ? list.map((a) => `<li>
      <div><h3><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.title)}</a></h3>
        <p class="holder">${esc(a.holder)}, ${esc(a.country)}</p></div>
      <div><p>${esc(a.note)}</p>
        <p class="small">${esc(a.kind)}. ${esc(a.dates)}. ${esc(a.extent)}. Reference: ${esc(a.ref)}. ${esc(a.open)}.</p></div>
    </li>`).join("") : `<li class="empty">No archival collections match “${esc(state.q)}”.</li>`;
  }

  // ---------- institutions ----------
  function renderInstitutions() {
    const list = D.institutions.filter((r) => matchQ(r._hay));
    document.querySelector('[data-count="institutions"]').textContent = `(${list.length})`;
    $("#inst-table tbody").innerHTML = list.map((r) => `<tr>
      <td data-l="Institution">${esc(r.name)}<br><span class="no">${esc(r.country)}</span></td>
      <td data-l="Records here">${r.harvested ? `<span class="yes">${fmt(Object.entries(bySource).filter(([k]) => k === r.name || (r.name === "Smithsonian Institution" && k.startsWith("Smithsonian"))).reduce((s, [, n]) => s + n, 0))}</span>` : '<span class="no">Not harvested</span>'}</td>
      <td data-l="Access">${esc(r.access)}</td><td data-l="Reuse terms">${esc(r.licence)}</td><td data-l="Notes">${esc(r.notes)}</td>
      <td data-l="Links"><a href="${esc(r.web)}" target="_blank" rel="noopener">Institution</a><a href="${esc(r.har)}" target="_blank" rel="noopener">Himalayan Art Resources</a></td>
    </tr>`).join("");
  }

  // ---------- repatriation ----------
  const STATUSES = ["All", "Returned", "Agreed, not returned", "Claimed", "Auction halted"];
  $("#statusfilter").innerHTML = STATUSES.map((s) => `<button type="button" aria-pressed="${s === "All"}" data-s="${esc(s)}">${esc(s)}</button>`).join("");
  function renderClaims() {
    const list = D.repatriation.filter((r) => (state.status === "All" || r.status.startsWith(state.status)) && matchQ(r._hay));
    document.querySelector('[data-count="repatriation"]').textContent = `(${list.length})`;
    $("#claim-list").innerHTML = list.length ? list.map((r) => `<li data-s="${esc(r.status)}">
      <div><div class="st">${esc(r.status)}</div><div class="yr">${esc(r.year)}</div></div>
      <div><h3>${esc(r.object)}</h3>
        <p class="who">${esc(r.holder)}</p>
        <p>${/^not stated$/i.test(r.origin) ? "" : `From ${esc(r.origin)}. `}${esc(r.detail)}</p>
        <p class="srcs">Sources: ${r.sources.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(new URL(u).hostname.replace(/^www\./, ""))}</a>`).join("")}</p></div>
    </li>`).join("") : `<li class="empty">No entries match.</li>`;
  }

  // ---------- about ----------
  $("#about").innerHTML = `
    <h2>What this is</h2>
    <p>A starting catalogue of Nepalese material held outside Nepal, built only from data that institutions publish openly, plus hand-entered archival collections and a repatriation tracker drawn from published reporting. It is incomplete by design: many major holders do not publish open data.</p>
    <h2>How records were selected</h2>
    <p>Each harvested record carries a “Why listed” note. Art Institute of Chicago: place of origin names Nepal or a Kathmandu Valley city. Met: the API's <code>geoLocation=Nepal</code> filter. Cleveland: culture field contains Nepal. V&amp;A: place name Nepal. Smithsonian: records from the CC0 Open Access dataset on AWS whose place, culture or title names Nepal or a Kathmandu Valley city; records that only mention Nepal in notes or citations are marked weak. Natural History anthropology records include donor and collector names, so a search for Slusser or Hitchcock finds both objects and papers. Harvard: the API's place ID for Nepal plus its culture ID for Nepalese, merged. Wellcome: keyword search, so modern books and unrelated items appear; records without a Nepalese term in title or place are marked weak and hidden by default.</p>
    <p>Period filters are rough buckets derived automatically from free-text dates and will misplace some records.</p>
    <h2>Reuse terms</h2>
    <p>Terms differ by institution and sometimes by record. Chicago and Cleveland data are CC0; Harvard data comes through a keyed API whose terms should be checked before republishing; Met data is CC0 for Open Access works; Wellcome images carry per-item licences; V&amp;A reuse terms should be checked on the V&amp;A site before republishing. Images are shown from the institutions' own servers, and only where the record marks the image as openly licensed, except V&amp;A thumbnails, which are shown for identification and link back to the source.</p>
    <h2>Known gaps and caveats</h2>
    <p>The Met search index returned ${D.metMissing.length} object IDs whose records now return “not found”: ${D.metMissing.map(esc).join(", ")}. The reason is not known; they may have been deaccessioned or merged.</p>
    <p>Provenance text is reproduced as published by each museum. An absence of provenance, or a clean-looking provenance, is not evidence that an object left Nepal lawfully. Equally, appearing in this catalogue says nothing about an object's legal status.</p>
    <p>The British Museum, Musée Guimet, LACMA, the Museum of Fine Arts Boston, and the Asian Art Museum San Francisco are listed under Institutions but not harvested.</p>
    <h2>Downloads</h2>
    <p><a href="data/objects.csv">objects.csv</a> (flat table), <a href="data/objects.json">objects.json</a>, <a href="data/curated.json">curated.json</a> (archives, institutions, repatriation). Built ${esc(D.built)}.</p>`;

  // ---------- tabs ----------
  function showTab(name) {
    document.querySelectorAll("[role=tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
    document.querySelectorAll("[data-panel]").forEach((p) => (p.hidden = p.dataset.panel !== name));
    const sel = document.querySelector(`[role=tab][data-tab="${name}"]`);
    if (sel) sel.scrollIntoView({ block: "nearest", inline: "nearest" });
    if (location.hash.slice(1) !== name) history.replaceState(null, "", "#" + name);
  }
  document.querySelectorAll("[role=tab]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
  const initial = location.hash.slice(1);
  if (["objects", "archives", "institutions", "repatriation", "about"].includes(initial)) showTab(initial);

  // ---------- events ----------
  function renderAll() { renderObjects(); renderArchives(); renderInstitutions(); renderClaims(); }
  let t;
  $("#q").addEventListener("input", (e) => { clearTimeout(t); t = setTimeout(() => { state.q = e.target.value.trim(); state.shown = PAGE; renderAll(); }, 150); });
  $("#f-source").addEventListener("change", (e) => { e.target.checked ? state.sources.add(e.target.value) : state.sources.delete(e.target.value); state.shown = PAGE; renderObjects(); });
  $("#f-type").addEventListener("change", (e) => { state.type = e.target.value; state.shown = PAGE; renderObjects(); });
  $("#f-century").addEventListener("change", (e) => { state.century = e.target.value; state.shown = PAGE; renderObjects(); });
  $("#f-sort").addEventListener("change", (e) => { state.sort = e.target.value; renderObjects(); });
  [["#f-open", "open"], ["#f-prov", "prov"], ["#f-weak", "weak"]].forEach(([sel, key]) =>
    $(sel).addEventListener("change", (e) => { state[key] = e.target.checked; state.shown = PAGE; renderObjects(); }));
  $("#reset").addEventListener("click", () => {
    Object.assign(state, { sources: new Set(), type: "", century: "", open: false, prov: false, weak: false, sort: "rel", shown: PAGE });
    document.querySelectorAll(".filters input").forEach((i) => (i.checked = false));
    document.querySelectorAll(".filters select").forEach((s) => (s.selectedIndex = 0));
    renderObjects();
  });
  $("#more").addEventListener("click", () => { state.shown += PAGE; renderObjects(); });
  $("#grid").addEventListener("click", (e) => { const b = e.target.closest("button[data-i]"); if (b) openDetail(D.objects[+b.dataset.i]); });
  $("#statusfilter").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-s]"); if (!b) return;
    state.status = b.dataset.s;
    document.querySelectorAll("#statusfilter button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderClaims();
  });
  $("#detail").addEventListener("click", (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });

  renderAll();
})();
