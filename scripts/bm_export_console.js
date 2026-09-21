/*
 British Museum → CSV export for the Nepalese heritage catalogue.

 Use ONLY with the British Museum's permission (text and data mining requires it).
 HOW TO RUN
   1. In Chrome/Edge/Firefox open:
      https://www.britishmuseum.org/collection/search?keyword=nepal
      (or a narrower search, e.g. after applying the "Production place: Nepal" filter —
       the script keeps whatever search is in the address bar)
   2. Open the browser console: F12 (Windows) or Cmd+Option+J (Mac) → "Console" tab.
      Chrome may ask you to type "allow pasting" first.
   3. Paste this whole file and press Enter.
   4. It checks page 1, then fetches one page every 3 seconds (~2 minutes for 37 pages),
      and downloads bm_nepal.csv. Upload that file to the chat.
 It only reads the same search pages you can see; it sends nothing anywhere else.
*/
(async () => {
  const DELAY_MS = 3000;
  const LABELS = ["Museum number", "Production date", "Production place", "Findspot", "Ethnic group",
                  "Authority", "Cultures/periods", "Materials", "Technique", "Object type", "School/style",
                  "Denomination", "Associated names", "Associated places"];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clean = (s) => s.replace(/\b(x\d+|BIOG\d+)\s+/g, "").replace(/\s+/g, " ").trim();

  function parse(doc) {
    const anchors = [...doc.querySelectorAll('h2 a[href*="/collection/object/"]')];
    return anchors.map((a, i) => {
      const h2 = a.closest("h2");
      const nextH2 = anchors[i + 1] ? anchors[i + 1].closest("h2") : null;
      const range = doc.createRange();
      range.setStartAfter(h2);
      if (nextH2) range.setEndBefore(nextH2); else range.setEndAfter(doc.body.lastChild);
      const frag = range.cloneContents();
      const walker = doc.createTreeWalker(frag, NodeFilter.SHOW_TEXT);
      const tokens = [];
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const t = n.textContent.replace(/\s+/g, " ").trim();
        if (t && t !== "|" && !/^(x\d+|BIOG\d+)$/.test(t)) tokens.push(t);
        if (!nextH2 && /^Pagination$/i.test(t)) break;
      }
      const rec = { title: a.textContent.trim(), url: new URL(a.getAttribute("href"), location.origin).href };
      rec.id = rec.url.split("/object/")[1] || rec.url;
      const other = {};
      let cur = null;
      for (const t of tokens) {
        if (/^Pagination$/i.test(t)) break;
        if (LABELS.includes(t)) { cur = t; continue; }
        if (!cur) continue;
        const key = cur;
        const v = clean(t);
        if (!v) continue;
        if (LABELS.includes(key)) rec[key] = rec[key] ? `${rec[key]}; ${v}` : v; else other[key] = v;
      }
      const img = frag.querySelector("img");
      rec.image = img ? new URL(img.getAttribute("src"), location.origin).href : "";
      return rec;
    });
  }

  async function getPage(p) {
    const u = new URL(location.href);
    u.searchParams.set("page", String(p));
    const res = await fetch(u.href, { credentials: "same-origin" });
    if (!res.ok) throw new Error(`Page ${p}: HTTP ${res.status}`);
    return new DOMParser().parseFromString(await res.text(), "text/html");
  }

  // ---- page 1 check
  const first = await getPage(0);
  const firstRecs = parse(first);
  const lastLink = first.querySelector('a[title="Go to last page"], a[href*="page="][rel="last"]');
  const lastPage = lastLink ? +new URL(lastLink.href, location.origin).searchParams.get("page") : 0;
  console.log(`Page 1: ${firstRecs.length} records parsed; last page index = ${lastPage}`);
  console.table(firstRecs.slice(0, 3));
  if (!firstRecs.length || !firstRecs[0]["Museum number"]) {
    console.error("Could not read the results in the expected format. Nothing was downloaded. " +
      "Please right-click one result title → Inspect, copy the surrounding HTML, and share it in the chat.");
    return;
  }

  // ---- remaining pages
  const all = [...firstRecs];
  for (let p = 1; p <= lastPage; p++) {
    await sleep(DELAY_MS);
    try {
      const recs = parse(await getPage(p));
      all.push(...recs);
      console.log(`Page ${p + 1}/${lastPage + 1}: ${recs.length} records (total ${all.length})`);
    } catch (e) {
      console.warn(e.message, "— stopping here; the CSV will contain what was collected.");
      break;
    }
  }

  // ---- de-duplicate by object id
  const seen = new Set();
  const unique = all.filter((r) => (seen.has(r.id) ? false : seen.add(r.id)));
  all.length = 0; all.push(...unique);

  // ---- CSV download
  const cols = ["id", "title", "url", ...LABELS, "image"];
  const q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [cols.join(","), ...all.map((r) => cols.map((c) => q(r[c])).join(","))].join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }));
  a.download = "bm_nepal.csv";
  document.body.appendChild(a); a.click(); a.remove();
  console.log(`Done: ${all.length} records → bm_nepal.csv`);
})();
