/* Interest Press — offline newspaper UI */
(function () {
  "use strict";

  const PRESS = window.PRESS || { articles: [], leads: [], bookmarks: [], sources: [], masthead: {}, counts: {}, thin: {} };
  const byId = Object.create(null);
  (PRESS.articles || []).forEach((a) => { byId[a.id] = a; });

  let view = "front";
  let readerStack = []; // article ids in current lane for ←/→
  let readerIndex = -1;
  let sportsFilter = "all";

  const $ = (sel, el) => (el || document).querySelector(sel);
  const $$ = (sel, el) => Array.from((el || document).querySelectorAll(sel));

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** Minimal markdown → sanitized HTML (no raw HTML passthrough). */
  function mdToHtml(md) {
    if (!md) return "<p><em>(empty)</em></p>";
    let text = String(md).replace(/\r\n/g, "\n");
    // Escape first
    text = esc(text);
    // Links [text](url) — only http(s)
    text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, function (_, label, url) {
      return '<a href="' + url.replace(/"/g, "") + '" target="_blank" rel="noopener noreferrer">' + label + "</a>";
    });
    // Bare URLs
    text = text.replace(/(^|[\s(])(https?:\/\/[^\s)<]+)/g, function (_, pre, url) {
      const clean = url.replace(/[.,;:!?)]+$/, "");
      const trail = url.slice(clean.length);
      return pre + '<a href="' + clean + '" target="_blank" rel="noopener noreferrer">' + clean + "</a>" + trail;
    });
    // Bold / italic (after escape, so * are literal)
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>");
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

    const lines = text.split("\n");
    const out = [];
    let list = null; // 'ul' | 'ol'

    function closeList() {
      if (list) { out.push("</" + list + ">"); list = null; }
    }

    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];
      const h = raw.match(/^(#{2,4})\s+(.+)$/);
      if (h) {
        closeList();
        const lvl = Math.min(h[1].length, 4);
        out.push("<h" + lvl + ">" + h[2] + "</h" + lvl + ">");
        continue;
      }
      const ul = raw.match(/^[\-\*]\s+(.+)$/);
      if (ul) {
        if (list !== "ul") { closeList(); out.push("<ul>"); list = "ul"; }
        out.push("<li>" + ul[1] + "</li>");
        continue;
      }
      const ol = raw.match(/^\d+\.\s+(.+)$/);
      if (ol) {
        if (list !== "ol") { closeList(); out.push("<ol>"); list = "ol"; }
        out.push("<li>" + ol[1] + "</li>");
        continue;
      }
      if (!raw.trim()) {
        closeList();
        continue;
      }
      closeList();
      out.push("<p>" + raw + "</p>");
    }
    closeList();
    return out.join("\n") || "<p><em>(empty)</em></p>";
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    const d = iso.slice(0, 10);
    try {
      const dt = new Date(d + "T12:00:00");
      return dt.toLocaleDateString("en-US", {
        weekday: "long", year: "numeric", month: "long", day: "numeric",
      });
    } catch (_) {
      return d;
    }
  }

  function kickerFor(a) {
    if (a.section === "sports") {
      const t = (a.team || "sports").toUpperCase();
      return { cls: "sports", text: t };
    }
    if (a.section === "space") return { cls: "space", text: "Space & xAI" };
    if (a.section === "bookmarks") return { cls: "", text: "Bookmarks" };
    return { cls: "", text: "Journal" };
  }

  function openReader(id, stack) {
    const a = byId[id];
    if (!a) return;
    readerStack = stack && stack.length ? stack.slice() : [id];
    readerIndex = readerStack.indexOf(id);
    if (readerIndex < 0) { readerStack = [id]; readerIndex = 0; }
    view = "reader";
    render();
    window.scrollTo(0, 0);
  }

  function navReader(delta) {
    if (view !== "reader" || !readerStack.length) return;
    const next = readerIndex + delta;
    if (next < 0 || next >= readerStack.length) return;
    readerIndex = next;
    render();
    window.scrollTo(0, 0);
  }

  function setView(name) {
    view = name;
    readerIndex = -1;
    if (name !== "reader") {
      const h = "#" + name;
      if (location.hash !== h) history.replaceState(null, "", h);
    }
    render();
    window.scrollTo(0, 0);
  }

  function cardHtml(a, opts) {
    opts = opts || {};
    const k = kickerFor(a);
    const hero = opts.hero ? " lead-hero" : "";
    const cls = opts.clip ? "clip-card" : "lead-card";
    return (
      '<article class="' + cls + hero + '" role="button" tabindex="0" data-id="' + esc(a.id) + '">' +
        '<div class="kicker ' + k.cls + '">' + esc(k.text) + "</div>" +
        '<h3 class="card-title">' + esc(a.title) + "</h3>" +
        '<p class="card-excerpt">' + esc(a.excerpt) + "</p>" +
        '<div class="card-meta"><span>' + esc(a.date || "") + '</span>' +
        '<span class="src">' + esc(a.source_name || "") + "</span></div>" +
      "</article>"
    );
  }

  function bindCards(root, stack) {
    $$("[data-id]", root).forEach((el) => {
      const go = () => openReader(el.getAttribute("data-id"), stack);
      el.addEventListener("click", go);
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); }
      });
    });
  }

  function renderFront() {
    const el = $("#view-front");
    const leads = (PRESS.leads || []).map((id) => byId[id]).filter(Boolean);
    if (!leads.length) {
      el.innerHTML = '<div class="thin-banner">No lead stories found in the Interest Journal sources on this box.</div>';
      return;
    }
    let html = '<div class="front-grid">';
    leads.forEach((a, i) => {
      html += cardHtml(a, { hero: i === 0 });
    });
    html += "</div>";
    // Mini desk teasers
    const sports = (PRESS.articles || []).filter((a) => a.section === "sports").slice(0, 3);
    const space = (PRESS.articles || []).filter((a) => a.section === "space").slice(0, 3);
    html += '<div class="desk-head" style="margin-top:28px"><h2>Inside</h2><span class="note">Jump via section nav</span></div>';
    html += '<div class="clip-grid">';
    sports.concat(space).forEach((a) => { html += cardHtml(a, { clip: true }); });
    html += "</div>";
    el.innerHTML = html;
    const stack = leads.map((a) => a.id).concat(sports.concat(space).map((a) => a.id));
    bindCards(el, stack);
  }

  function renderSports() {
    const el = $("#view-sports");
    let arts = (PRESS.articles || []).filter((a) => a.section === "sports");
    // Prefer research over household umbrella when possible — still show all
    arts = arts.slice().sort((a, b) => (b.date || "").localeCompare(a.date || ""));
    let html = '<div class="desk-head"><h2>Sports Desk</h2><span class="note">Ravens · Orioles · Chelsea · Terps</span></div>';
    if (PRESS.thin && PRESS.thin.sports) {
      html += '<div class="thin-banner">Sports Desk is thin today — no sports sections were found in the Interest Journal files on this box.</div>';
      el.innerHTML = html;
      return;
    }
    html += '<div class="team-tabs" id="teamTabs">' +
      ['all','ravens','orioles','chelsea','terps'].map((t) =>
        '<button type="button" data-team="' + t + '"' + (sportsFilter === t ? ' class="active"' : '') + '>' +
        (t === "all" ? "All" : t.charAt(0).toUpperCase() + t.slice(1)) + "</button>"
      ).join("") + "</div>";
    const filtered = sportsFilter === "all" ? arts : arts.filter((a) => a.team === sportsFilter);
    if (!filtered.length) {
      html += '<div class="thin-banner">No clips for this team in the current sources. Try All, or check Archive for source coverage.</div>';
    } else {
      html += '<div class="clip-grid">';
      filtered.forEach((a) => { html += cardHtml(a, { clip: true }); });
      html += "</div>";
    }
    el.innerHTML = html;
    $$("#teamTabs button", el).forEach((btn) => {
      btn.addEventListener("click", () => {
        sportsFilter = btn.getAttribute("data-team");
        renderSports();
      });
    });
    bindCards(el, filtered.map((a) => a.id));
  }

  function renderSpace() {
    const el = $("#view-space");
    const arts = (PRESS.articles || [])
      .filter((a) => a.section === "space")
      .slice()
      .sort((a, b) => (b.date || "").localeCompare(a.date || ""));
    let html = '<div class="desk-head"><h2>Space &amp; xAI</h2><span class="note">SpaceX · Starlink · Elon · agents</span></div>';
    if (PRESS.thin && PRESS.thin.space) {
      html += '<div class="thin-banner">Space &amp; xAI is thin today — no matching sections in the Interest Journal files.</div>';
      el.innerHTML = html;
      return;
    }
    html += '<div class="clip-grid">';
    arts.forEach((a) => { html += cardHtml(a, { clip: true }); });
    html += "</div>";
    el.innerHTML = html;
    bindCards(el, arts.map((a) => a.id));
  }

  function renderBookmarks() {
    const el = $("#view-bookmarks");
    const bms = PRESS.bookmarks || [];
    let html = '<div class="desk-head"><h2>Bookmark Radar</h2><span class="note">From atlas / scrapes</span></div>';
    if (!bms.length || (PRESS.thin && PRESS.thin.bookmarks)) {
      html += '<div class="thin-banner">Bookmark Radar skipped — no readable bookmark titles/URLs found in the local yml/atlas sources.</div>';
      el.innerHTML = html;
      return;
    }
    html += '<ol class="bm-list">';
    bms.forEach((b, i) => {
      const title = b.title || b.url || "Bookmark";
      const link = b.url
        ? '<a href="' + esc(b.url) + '" target="_blank" rel="noopener noreferrer">' + esc(title) + "</a>"
        : "<span>" + esc(title) + "</span>";
      html +=
        "<li><span class=\"num\">" + String(i + 1).padStart(2, "0") + "</span>" +
        "<div>" + link +
        (b.handle ? '<div class="handle">@' + esc(b.handle) + "</div>" : "") +
        "</div><span class=\"handle\">" + esc((b.sources || []).slice(0, 1).join("") || "") + "</span></li>";
    });
    html += "</ol>";
    el.innerHTML = html;
  }

  function renderArchive() {
    const el = $("#view-archive");
    const srcs = PRESS.sources || [];
    let html = '<div class="desk-head"><h2>Archive</h2><span class="note">' + srcs.length + " source files</span></div>";
    html += '<table class="archive-table"><thead><tr><th>Date</th><th>File</th><th>Kind</th><th>Bytes</th><th>Path</th></tr></thead><tbody>';
    srcs.slice().sort((a, b) => (b.date || "").localeCompare(a.date || "")).forEach((s) => {
      html +=
        "<tr><td>" + esc(s.date || "") + "</td><td>" + esc(s.name) + "</td><td>" + esc(s.kind) +
        "</td><td>" + esc(String(s.bytes || "")) + "</td><td><code>" + esc(s.path) + "</code></td></tr>";
    });
    html += "</tbody></table>";
    html += '<p class="note" style="margin-top:14px;font-family:var(--sans);font-size:12px;color:var(--ink-mute)">Generated ' +
      esc(PRESS.generated || "") + " · articles ingested: " + esc(String((PRESS.counts || {}).articles || 0)) + "</p>";
    el.innerHTML = html;
  }

  function renderReader() {
    const el = $("#view-reader");
    const id = readerStack[readerIndex];
    const a = byId[id];
    if (!a) {
      el.innerHTML = '<div class="thin-banner">Article not found.</div>';
      return;
    }
    const k = kickerFor(a);
    let html = '<div class="reader">';
    html += '<div class="reader-bar">' +
      '<button type="button" id="btnBack">← Back</button>' +
      '<button type="button" id="btnPrev"' + (readerIndex <= 0 ? " disabled" : "") + ">Prev article</button>" +
      '<button type="button" id="btnNext"' + (readerIndex >= readerStack.length - 1 ? " disabled" : "") + ">Next article</button>" +
      '<span>' + (readerIndex + 1) + " / " + readerStack.length + "</span></div>";
    html += '<div class="kicker ' + k.cls + '">' + esc(k.text) + "</div>";
    html += "<h2>" + esc(a.title) + "</h2>";
    html += '<div class="reader-meta">' + esc(fmtDate(a.date)) + " · " + esc(a.source_name) +
      " · <code>" + esc(a.source_path) + "</code></div>";
    html += '<div class="reader-body">' + mdToHtml(a.body) + "</div>";
    if (a.urls && a.urls.length) {
      html += '<div class="reader-urls"><strong>Links in source</strong><ul>' +
        a.urls.map((u) => '<li><a href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">' + esc(u) + "</a></li>").join("") +
        "</ul></div>";
    }
    html += "</div>";
    el.innerHTML = html;
    $("#btnBack", el).addEventListener("click", () => setView("front"));
    $("#btnPrev", el).addEventListener("click", () => navReader(-1));
    $("#btnNext", el).addEventListener("click", () => navReader(1));
  }

  function render() {
    // Masthead
    const mh = PRESS.masthead || {};
    $("#tagline").textContent = mh.tagline || "Morning edition from Boyd's Interest Journal";
    $("#mastDate").textContent = fmtDate(mh.date || mh.mtime);
    $("#editionLabel").textContent = "Morning Edition";
    $("#volLabel").textContent = "Sources " + ((PRESS.counts || {}).sources || 0);
    const c = PRESS.counts || {};
    $("#footerCounts").textContent =
      (c.articles || 0) + " articles · " + (c.sports || 0) + " sports · " +
      (c.space || 0) + " space · " + (c.bookmarks || 0) + " bookmarks";

    // Nav active
    $$(".section-nav button").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-view") === view && view !== "reader");
    });

    // Views
    ["front", "sports", "space", "bookmarks", "archive", "reader"].forEach((name) => {
      const sec = $("#view-" + name);
      const on = view === name;
      sec.hidden = !on;
      sec.classList.toggle("active", on);
    });

    if (view === "front") renderFront();
    else if (view === "sports") renderSports();
    else if (view === "space") renderSpace();
    else if (view === "bookmarks") renderBookmarks();
    else if (view === "archive") renderArchive();
    else if (view === "reader") renderReader();
  }

  // Nav clicks
  $$(".section-nav button").forEach((btn) => {
    btn.addEventListener("click", () => setView(btn.getAttribute("data-view")));
  });

  // Keyboard
  document.addEventListener("keydown", (e) => {
    if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
    if (e.key === "Escape" && view === "reader") { setView("front"); return; }
    if (e.key === "ArrowLeft") { navReader(-1); return; }
    if (e.key === "ArrowRight") { navReader(1); return; }
    const map = { "1": "front", "2": "sports", "3": "space", "4": "bookmarks", "5": "archive" };
    if (map[e.key]) setView(map[e.key]);
  });

  // Deep-link: #front #sports #space #bookmarks #archive
  const boot = (location.hash || "").replace(/^#/, "");
  if (["front", "sports", "space", "bookmarks", "archive"].includes(boot)) {
    view = boot;
  }
  window.addEventListener("hashchange", () => {
    const h = (location.hash || "").replace(/^#/, "");
    if (["front", "sports", "space", "bookmarks", "archive"].includes(h) && h !== view) {
      setView(h);
    }
  });

  render();
})();
