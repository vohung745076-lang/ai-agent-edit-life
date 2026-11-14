/* Kuto — giao diện. Hỏi máy chủ /api/state định kỳ rồi vẽ lại phần nào thay đổi. */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const setHTML = (el, html) => { if (el && el._h !== html) { el._h = html; el.innerHTML = html; return true; } return false; };

let state = { projects: [], styles: [], jobs: [] };
let sel = { project: null, style: null };
let styleDirty = false;

// ───────── hình pixel ─────────
const PAL = { k: "#1b1220", w: "#ffffff", a: "var(--accent)", p: "var(--soft)", d: "var(--accent-deep)", g: "#d9d2d8" };
function pixels(rows) {
  const h = rows.length, w = rows[0].length;
  let r = "";
  rows.forEach((row, y) => [...row].forEach((c, x) => { if (PAL[c]) r += `<rect x="${x}" y="${y}" width="1.02" height="1.02" fill="${PAL[c]}"/>`; }));
  return `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">${r}</svg>`;
}
const ART = {
  // Kuto: bé bảng clap có mắt
  mascot: [
    "..kkkkkkkkkkkk..",
    ".kaawwaawwaawwk.",
    ".kawwaawwaawwak.",
    ".kkkkkkkkkkkkkk.",
    ".kwwwwwwwwwwwwk.",
    ".kwwwwwwwwwwwwk.",
    ".kwwkkwwwwkkwwk.",
    ".kwwkwwwwwkwwwk.",
    ".kwwkkwwwwkkwwk.",
    ".kwppwwkkwwppwk.",
    ".kwwwwwwwwwwwwk.",
    ".kwwwwwwwwwwwwk.",
    "..kkkkkkkkkkkk..",
    "...kk......kk...",
    "..kkk......kkk..",
  ],
  logo: [
    "kkkkkkkk",
    "kawawawk",
    "kkkkkkkk",
    "kaaaaaak",
    "kakaakak",
    "kaaaaaak",
    "kkkkkkkk",
    ".kk..kk.",
  ],
  clap: [
    "kkkkkkkkkkkk",
    "kawwawwawwak",
    "kkkkkkkkkkkk",
    "kwwwwwwwwwwk",
    "kwwwkwwwwwwk",
    "kwwwkkkwwwwk",
    "kwwwkkkkkwwk",
    "kwwwkkkwwwwk",
    "kwwwkwwwwwwk",
    "kwwwwwwwwwwk",
    "kkkkkkkkkkkk",
  ],
  eye: [
    "....kkkk....",
    "..kkwwwwkk..",
    ".kwwwaaawwk.",
    "kwwwaakkawwk",
    "kwwwaakkawwk",
    ".kwwwaaawwk.",
    "..kkwwwwkk..",
    "....kkkk....",
    "............",
    ".a...a...a..",
    "..a..a..a...",
  ],
  heart: [
    "..kkk..kkk..",
    ".kaaakkaaak.",
    "kaawaaaaaaak",
    "kawaaaaaaaak",
    "kaaaaaaaaaak",
    ".kaaaaaaaak.",
    "..kaaaaaak..",
    "...kaaaak...",
    "....kaak....",
    ".....kk.....",
  ],
};
$("#mascot").innerHTML = pixels(ART.mascot);
$("#logo").innerHTML = pixels(ART.logo);
$$("[data-ico]").forEach((el) => (el.innerHTML = pixels(ART[el.dataset.ico])));

// ───────── giao diện chung ─────────
const store = { get: (k) => { try { return localStorage.getItem(k); } catch { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch {} } };
const applyTheme = (t) => { document.documentElement.dataset.theme = t; store.set("kuto-theme", t); };
applyTheme(store.get("kuto-theme") || "dau");
$$("[data-theme-pick]").forEach((b) => b.addEventListener("click", () => applyTheme(b.dataset.themePick)));

let toastTimer;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 3800); }

async function api(path, body) {
  const res = await fetch(path, { method: body === undefined ? "GET" : "POST", headers: body === undefined ? {} : { "Content-Type": "application/json" }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Có lỗi xảy ra");
  return data;
}

function route() {
  const [view, arg] = (location.hash.slice(1) || "home").split("/");
  const name = ["home", "projects", "styles", "log"].includes(view) ? view : "home";
  $$(".view").forEach((v) => (v.hidden = v.id !== `view-${name}`));
  $$(".tabs a").forEach((a) => a.classList.toggle("on", a.dataset.nav === name));
  if (name === "projects" && arg) sel.project = arg;
  if (name === "styles" && arg) { if (sel.style !== arg) styleDirty = false; sel.style = arg; }
  render();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);

// ───────── nhãn trạng thái ─────────
const P_STEPS = [["downloading", "Tải cảnh quay"], ["analyzing", "Xem hiểu"], ["planning", "Ý tưởng & kịch bản"], ["editing", "Dựng"], ["rendering", "Xuất"], ["review", "Chờ bạn duyệt"], ["done", "Đã chốt"]];
const P_LABEL = { queued: ["Chờ tới lượt", "wait"], downloading: ["Đang tải", "run"], analyzing: ["Đang xem", "run"], planning: ["Lên ý tưởng", "run"], editing: ["Đang dựng", "run"], rendering: ["Đang xuất", "run"], review: ["Chờ duyệt", "wait"], done: ["Đã chốt", "good"], error: ["Lỗi", "bad"] };
const S_LABEL = { personal: ["Của bạn", "me"], learning: ["Đang học", "run"], draft: ["Chờ duyệt", "wait"], approved: ["Đã duyệt", "good"], error: ["Lỗi", "bad"] };
const J_LABEL = { queued: ["Chờ", "wait"], running: ["Đang chạy", "run"], done: ["Xong", "good"], error: ["Lỗi", "bad"], stopped: ["Đã dừng", ""] };
const chip = ([text, cls]) => `<span class="chip ${cls}">${esc(text)}</span>`;
const time = (ms) => (ms ? new Date(ms).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }) : "");
const busyFor = (type, id) => state.jobs.find((j) => (j.status === "running" || j.status === "queued") && j.target && j.target.type === type && j.target.id === id);

function videoFig(url, label, tall) {
  return url ? `<figure class="${tall ? "tall" : ""}"><video src="${esc(url)}" controls preload="metadata" playsinline></video><figcaption>${esc(label)}</figcaption></figure>` : "";
}
const isTall = (label = "", file = "") => /9x16|9:16|dọc|vertical/i.test(label + " " + file);

// ───────── vẽ ─────────
function render() {
  const running = state.jobs.find((j) => j.status === "running");
  const queued = state.jobs.filter((j) => j.status === "queued").length;
  const pill = $("#busy");
  pill.textContent = running ? `Đang làm${queued ? ` · ${queued} chờ` : ""}` : "Đang rảnh";
  pill.classList.toggle("busy", !!running);
  $("#mascot").classList.toggle("working", !!running);
  const lastSay = running && [...running.log].reverse().find((l) => l.type === "tool" || l.type === "say");
  $("#bubble").textContent = running ? (lastSay ? lastSay.text.split(" · ")[0].slice(0, 22) + "…" : "Đang nghĩ…") : "Sẵn sàng!";

  const waitingP = state.projects.filter((p) => p.status === "review").length;
  const waitingS = state.styles.filter((s) => s.status === "draft").length;
  $("#n-projects").textContent = waitingP || "";
  $("#n-styles").textContent = waitingS || "";

  safe(renderHomeLive, running);
  safe(renderProjects);
  safe(renderStyles);
  safe(renderJobs);
}

function renderHomeLive(running) {
  let html = "";
  if (running) {
    const lines = running.log.slice(-4).map((l) => `<div class="${l.type}">${esc(l.text)}</div>`).join("");
    html = `<div class="live px"><b>Kuto đang làm: ${esc(running.title)}</b><div class="logbox">${lines || "Đang khởi động…"}</div><div class="row"><a class="btn ghost" href="#log">Xem nhật ký</a></div></div>`;
  }
  setHTML($("#home-live"), html);
}

function renderProjects() {
  const list = state.projects;
  if (!sel.project && list[0]) sel.project = list[0].id;
  setHTML($("#project-list"), list.length ? list.map((p) =>
    `<a class="item px ${p.id === sel.project ? "on" : ""}" href="#projects/${esc(p.id)}">${chip(P_LABEL[p.status] || [p.status, ""])}<b>${esc(p.title || p.id)}</b><small>${esc(p.step || "")}</small></a>`).join("")
    : `<div class="empty">Chưa có dự án nào.<br />Dán link Google Drive ở Trang chủ để bắt đầu.</div>`);

  const p = list.find((x) => x.id === sel.project);
  const box = $("#project-detail");
  if (!p) return setHTML(box, list.length ? "" : "");
  const idx = P_STEPS.findIndex(([k]) => k === p.status);
  const steps = P_STEPS.map(([k, label], i) => `<span class="${idx >= 0 && i < idx ? "done" : i === idx ? "now" : ""}">${esc(label)}</span>`).join("");
  const busy = busyFor("project", p.id);
  const vids = (p.outputs || []).slice().reverse();
  const latest = vids.filter((o) => !p.version || new RegExp(`v${p.version}\\b`).test(o.file + o.label));
  const show = latest.length ? latest : vids.slice(0, 2);
  const used = Array.isArray(p.styles_used)
    ? p.styles_used.map((u) => typeof u === "string" ? esc(u) : `${esc(u?.style)}${Array.isArray(u?.techniques) && u.techniques.length ? ": " + esc(u.techniques.join(", ")) : ""}`).join(" · ")
    : esc(p.styles_used || "");

  const html = `
  <div class="panel px">
    ${chip(P_LABEL[p.status] || [p.status, ""])}
    <h3>${esc(p.title || p.id)}</h3>
    <div class="steps">${steps}</div>
    ${p.step ? `<p><b>Bước hiện tại:</b> ${esc(p.step)}</p>` : ""}
    ${p.message ? `<h4>Lời nhắn từ Kuto</h4><div class="note">${esc(p.message)}</div>` : ""}
    <div class="links row">
      ${p.planUrl ? `<a href="${esc(p.planUrl)}" target="_blank" rel="noopener">Ý tưởng &amp; kịch bản (PLAN.md)</a>` : ""}
      ${p.source ? `<a href="${esc(p.source)}" target="_blank" rel="noopener">Thư mục Drive gốc</a>` : ""}
    </div>
    ${used ? `<p><small><b>Phong cách đã dùng:</b> ${used}</small></p>` : ""}
  </div>
  ${show.length ? `<div class="panel px"><h3>Bản dựng${p.version ? ` · phiên bản ${esc(p.version)}` : ""}</h3><div class="videos">${show.map((o) => videoFig(o.url, o.label, isTall(o.label, o.file))).join("")}</div></div>` : ""}
  <div class="panel px">
    <h3>Góp ý cho Kuto</h3>
    <textarea id="p-feedback" placeholder="Ví dụ: chữ ở cảnh 2 to hơn, bỏ hiệu ứng rung, nhạc nhỏ lại, đổi câu kết cho hài hơn…" ${busy ? "disabled" : ""}></textarea>
    <div class="row">
      <button class="btn" data-act="p-feedback" ${busy ? "disabled" : ""}>Gửi góp ý, dựng lại</button>
      <button class="btn ok" data-act="p-final" ${busy || p.status !== "review" ? "disabled" : ""}>✔ Chốt video này</button>
      ${busy ? `<small>Kuto đang xử lý dự án này. <a href="#log"><b>Xem nhật ký</b></a></small>` : p.status === "review" ? `<small>Chốt xong, Kuto xuất bản đẹp nhất và ghi nhớ những gì bạn đã sửa.</small>` : ""}
    </div>
  </div>`;
  // Không vẽ lại khi người dùng đang gõ góp ý hoặc đang xem video
  const typing = $("#p-feedback") && ($("#p-feedback").value || document.activeElement === $("#p-feedback"));
  const playing = $$("video", box).some((v) => !v.paused);
  if (box._h && box._id === p.id && (typing || playing)) return;
  box._id = p.id;
  setHTML(box, html);
}

function linesField(id, label, arr, hint) {
  return `<div class="field"><label for="${id}">${esc(label)}</label><textarea id="${id}" data-edit>${esc((arr || []).join("\n"))}</textarea><small>${esc(hint || "Mỗi dòng một ý")}</small></div>`;
}

function renderStyles() {
  const list = state.styles;
  if (!sel.style && list[0]) sel.style = list[0].slug;
  setHTML($("#style-list"), list.length ? list.map((s) =>
    `<a class="item px ${s.slug === sel.style ? "on" : ""}" href="#styles/${esc(s.slug)}">${chip(S_LABEL[s.status] || [s.status, ""])}<b>${esc(s.name || s.slug)}</b><small>${esc((s.topics || []).join(" · ") || s.source || "")}</small></a>`).join("")
    : `<div class="empty">Thư viện trống.</div>`);

  const s = list.find((x) => x.slug === sel.style);
  const box = $("#style-detail");
  if (!s) return setHTML(box, "");
  const playing = $$("video", box).some((v) => !v.paused);
  if (box._slug === s.slug && (styleDirty || playing || (box.contains(document.activeElement) && /INPUT|TEXTAREA/.test(document.activeElement.tagName)))) return;
  box._slug = s.slug;

  const t = s.tokens || {}, pc = t.pacing || {};
  const busy = busyFor("style", s.slug);
  const personal = s.status === "personal";
  const pal = (t.palette || []).map((c, i) => `<div><input type="color" value="${esc(/^#[0-9a-f]{6}$/i.test(c.hex) ? c.hex : "#000000")}" data-pal="${i}" data-edit /><span>${esc(c.role)}</span><input type="text" value="${esc(c.hex)}" data-palhex="${i}" data-edit maxlength="7" /></div>`).join("");
  const fonts = (t.fonts || []).map((f, i) => `<div class="field"><label>Font ${esc(f.role)}</label><input value="${esc(f.family)}" data-font="${i}" data-edit /><small>Độ đậm <input type="number" value="${esc(f.weight)}" data-fontw="${i}" data-edit min="100" max="900" step="100" style="width:80px;display:inline-block;padding:2px 6px" /> ${esc(f.note || "")}</small></div>`).join("");
  const techs = (s.techniques || []).map((k) => `<div class="tech"><b>${esc(k.name || k.id)}</b>${k.when ? `<p class="yes">${esc(k.when)}</p>` : ""}${k.avoid ? `<p class="no">${esc(k.avoid)}</p>` : ""}</div>`).join("");
  const demos = videoFig(s.demoUrl, "Demo Kuto dựng theo phong cách này") + videoFig(s.demoVerticalUrl, "Demo bản dọc", true) + videoFig(s.referenceUrl, "Video mẫu gốc (chỉ để so sánh)", true);

  setHTML(box, `
  <div class="panel px">
    ${chip(S_LABEL[s.status] || [s.status, ""])}
    <div class="field"><input id="s-name" value="${esc(s.name || "")}" data-edit style="font:700 30px/1.1 var(--display);border-color:transparent;padding-left:0" aria-label="Tên phong cách" /></div>
    ${s.message ? `<div class="note">${esc(s.message)}</div>` : ""}
    <div class="links row">
      ${s.briefUrl ? `<a href="${esc(s.briefUrl)}" target="_blank" rel="noopener">Bảng phong cách đầy đủ (STYLE.md)</a>` : ""}
      ${s.lessonsUrl ? `<a href="${esc(s.lessonsUrl)}" target="_blank" rel="noopener">Bài học đã ghi (LESSONS.md)</a>` : ""}
      ${s.source && /^https?:/.test(s.source) ? `<a href="${esc(s.source)}" target="_blank" rel="noopener">Nguồn video mẫu</a>` : ""}
    </div>
  </div>
  ${demos ? `<div class="panel px"><h3>Xem để duyệt</h3><div class="videos">${demos}</div></div>` : ""}
  <div class="panel px">
    <h3>Bảng phong cách <small style="font:400 13px var(--body);color:var(--muted)">sửa trực tiếp rồi bấm Lưu</small></h3>
    <div class="field"><label for="s-summary">Tóm tắt</label><textarea id="s-summary" data-edit>${esc(s.summary || "")}</textarea></div>
    <div class="grid2" style="margin-top:12px">
      <div class="field"><label for="s-best">Hợp với</label><textarea id="s-best" data-edit>${esc(s.best_for || "")}</textarea></div>
      <div class="field"><label for="s-avoid">Không hợp với</label><textarea id="s-avoid" data-edit>${esc(s.avoid_for || "")}</textarea></div>
    </div>
    <div class="field" style="margin-top:12px"><label for="s-topics">Chủ đề</label><input id="s-topics" value="${esc((s.topics || []).join(", "))}" data-edit /><small>Cách nhau bằng dấu phẩy. Kuto chỉ áp trọn bộ phong cách khi video cùng chủ đề.</small></div>
    ${pal ? `<h4>Bảng màu</h4><div class="pal">${pal}</div>` : ""}
    ${fonts ? `<h4>Font chữ</h4><div class="grid2">${fonts}</div>` : ""}
    <h4>Nhịp cắt</h4>
    <div class="grid2">
      <div class="field"><label for="s-avg">Độ dài cảnh trung bình (giây)</label><input id="s-avg" type="number" step="0.1" min="0" value="${esc(pc.avg_shot ?? "")}" data-edit /></div>
      <div class="field"><label for="s-cpm">Số lần cắt mỗi phút</label><input id="s-cpm" type="number" step="1" min="0" value="${esc(pc.cuts_per_min ?? "")}" data-edit /></div>
      <div class="field"><label for="s-hook">Mở đầu gây chú ý trong (giây)</label><input id="s-hook" type="number" step="0.1" min="0" value="${esc(pc.hook_seconds ?? "")}" data-edit /></div>
    </div>
    <h4>Chuyển động và hiệu ứng</h4>
    <div class="grid2">
      ${linesField("s-trans", "Chuyển cảnh", t.transitions)}
      ${linesField("s-text", "Chuyển động chữ", t.text_motion)}
      ${linesField("s-fx", "Hiệu ứng hình", t.effects)}
      ${linesField("s-audio", "Âm thanh", t.audio)}
    </div>
    ${techs ? `<h4>Kỹ thuật dùng lại được</h4>${techs}` : ""}
    <h4>Ghi chú riêng của bạn</h4>
    <textarea id="s-notes" data-edit placeholder="Điều bạn thích, không thích, muốn đổi cho ra chất riêng…">${esc(s.user_notes || "")}</textarea>
    <div class="row">
      <button class="btn" data-act="s-save">Lưu chỉnh sửa</button>
      ${personal ? "" : s.status === "approved"
        ? `<button class="btn ghost" data-act="s-unapprove">Bỏ duyệt</button><small>Kuto đang được phép dùng phong cách này.</small>`
        : `<button class="btn ok" data-act="s-approve" ${busy || s.status === "learning" ? "disabled" : ""}>✔ Duyệt, cho Kuto dùng</button>`}
    </div>
  </div>
  ${personal ? "" : `<div class="panel px">
    <h3>Nhờ Kuto sửa và dựng lại demo</h3>
    <textarea id="s-feedback" data-edit placeholder="Ví dụ: chữ bật mạnh hơn, đổi màu nhấn sang vàng, bỏ kỹ thuật rung, demo dùng cảnh văn phòng…" ${busy ? "disabled" : ""}></textarea>
    <div class="row"><button class="btn" data-act="s-feedback" ${busy ? "disabled" : ""}>Gửi góp ý</button>${busy ? `<small>Kuto đang xử lý phong cách này. <a href="#log"><b>Xem nhật ký</b></a></small>` : ""}</div>
  </div>`}`);
}

function collectStyle() {
  const s = state.styles.find((x) => x.slug === sel.style);
  const tokens = JSON.parse(JSON.stringify(s.tokens || {}));
  $$("[data-palhex]").forEach((el) => { const v = el.value.trim(); if (/^#[0-9a-f]{6}$/i.test(v)) tokens.palette[el.dataset.palhex].hex = v; });
  $$("[data-font]").forEach((el) => (tokens.fonts[el.dataset.font].family = el.value.trim()));
  $$("[data-fontw]").forEach((el) => (tokens.fonts[el.dataset.fontw].weight = Number(el.value) || 400));
  const num = (id) => { const v = parseFloat($(id).value); return Number.isFinite(v) ? v : undefined; };
  tokens.pacing = { ...(tokens.pacing || {}), avg_shot: num("#s-avg"), cuts_per_min: num("#s-cpm"), hook_seconds: num("#s-hook") };
  const lines = (id) => $(id).value.split("\n").map((x) => x.trim()).filter(Boolean);
  tokens.transitions = lines("#s-trans"); tokens.text_motion = lines("#s-text"); tokens.effects = lines("#s-fx"); tokens.audio = lines("#s-audio");
  return {
    name: $("#s-name").value.trim() || s.name, summary: $("#s-summary").value.trim(), best_for: $("#s-best").value.trim(), avoid_for: $("#s-avoid").value.trim(),
    topics: $("#s-topics").value.split(",").map((x) => x.trim()).filter(Boolean), tokens, user_notes: $("#s-notes").value.trim(),
  };
}

function renderJobs() {
  const box = $("#job-list");
  if (box.contains(document.activeElement) && document.activeElement.tagName === "BUTTON") return;
  const scrolls = $$(".logbox", box).map((el) => [el.dataset.id, el.scrollTop, el.scrollHeight - el.clientHeight - el.scrollTop < 30]);
  const changed = setHTML(box, state.jobs.length ? state.jobs.map((j) => {
    const live = j.status === "running" || j.status === "queued";
    const lines = j.log.map((l) => `<div class="${l.type}">${l.type === "tool" ? "› " : ""}${esc(l.text)}</div>`).join("");
    const link = j.target ? `<a href="#${j.target.type === "project" ? "projects" : "styles"}/${esc(j.target.id)}"><b>Mở ${j.target.type === "project" ? "dự án" : "phong cách"} →</b></a>` : "";
    return `<div class="job px">
      <div class="job-head">${chip(J_LABEL[j.status] || [j.status, ""])}<b>${esc(j.title)}</b><small>${esc(time(j.createdAt))}</small>${link}
        ${live ? `<button class="btn ghost" data-act="j-stop" data-id="${esc(j.id)}">Dừng</button>` : ""}</div>
      ${lines ? `<div class="logbox" data-id="${esc(j.id)}">${lines}</div>` : ""}
    </div>`;
  }).join("") : `<div class="empty">Chưa có việc nào.</div>`);
  if (changed) $$(".logbox", box).forEach((el) => { const s = scrolls.find((x) => x[0] === el.dataset.id); el.scrollTop = !s || s[2] ? el.scrollHeight : s[1]; });
}

// ───────── thao tác ─────────
document.addEventListener("input", (e) => {
  if (!e.target.closest("#style-detail") || !e.target.matches("[data-edit]") || e.target.id === "s-feedback") return;
  styleDirty = true;
  if (e.target.dataset.pal !== undefined) $(`[data-palhex="${e.target.dataset.pal}"]`).value = e.target.value;
  if (e.target.dataset.palhex !== undefined && /^#[0-9a-f]{6}$/i.test(e.target.value)) $(`[data-pal="${e.target.dataset.palhex}"]`).value = e.target.value;
});

document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-act]");
  if (!btn) return;
  const act = btn.dataset.act;
  btn.disabled = true;
  try {
    if (act === "p-feedback") {
      const text = $("#p-feedback").value.trim();
      if (!text) throw new Error("Hãy viết góp ý trước.");
      await api(`/api/projects/${sel.project}/feedback`, { text });
      $("#p-feedback").value = ""; toast("Đã gửi góp ý. Kuto đang dựng lại.");
    } else if (act === "p-final") {
      await api(`/api/projects/${sel.project}/finalize`, {});
      toast("Đã chốt. Kuto xuất bản cuối và ghi nhớ phong cách.");
    } else if (act === "s-save" || act === "s-approve") {
      await api(`/api/styles/${sel.style}/save`, collectStyle());
      if (act === "s-approve") await api(`/api/styles/${sel.style}/approve`, {});
      styleDirty = false; toast(act === "s-approve" ? "Đã duyệt. Kuto sẽ dùng phong cách này khi phù hợp." : "Đã lưu.");
    } else if (act === "s-unapprove") {
      await api(`/api/styles/${sel.style}/unapprove`, {}); toast("Đã bỏ duyệt.");
    } else if (act === "s-feedback") {
      const text = $("#s-feedback").value.trim();
      if (!text) throw new Error("Hãy viết góp ý trước.");
      await api(`/api/styles/${sel.style}/save`, collectStyle());
      await api(`/api/styles/${sel.style}/feedback`, { text });
      $("#s-feedback").value = ""; styleDirty = false; toast("Đã gửi. Kuto đang dựng lại demo.");
    } else if (act === "j-stop") {
      await api(`/api/jobs/${btn.dataset.id}/stop`, {}); toast("Đã yêu cầu dừng.");
    }
    document.activeElement?.blur();
    await refresh();
  } catch (err) { toast(err.message); }
  btn.disabled = false;
});

const hint = (msg, err) => { const h = $("#ask-hint"); h.textContent = msg; h.classList.toggle("err", !!err); };
$("#ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("#ask-text").value.trim();
  const mode = $('input[name="mode"]:checked').value;
  if (!text) return hint("Hãy dán link hoặc gõ yêu cầu.", true);
  try {
    await api("/api/ask", { text, mode });
    $("#ask-text").value = ""; hint("Đã nhận! Kuto bắt đầu làm, theo dõi ở Nhật ký.");
    await refresh();
  } catch (err) { hint(err.message, true); }
});
$("#ref-file").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  hint(`Đang tải lên ${file.name}…`);
  try {
    const note = $("#ask-text").value.trim();
    const res = await fetch(`/api/upload?name=${encodeURIComponent(file.name)}&note=${encodeURIComponent(note)}`, { method: "POST", body: file });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    $("#ask-text").value = ""; hint("Đã tải lên. Kuto bắt đầu học video mẫu này."); await refresh();
  } catch (err) { hint(err.message || "Tải lên thất bại", true); }
  e.target.value = "";
});

// Mỗi phần vẽ riêng: một phần lỗi dữ liệu không làm hỏng cả trang.
const safe = (fn, ...a) => { try { fn(...a); } catch (e) { console.error(e); } };

async function refresh() {
  let next;
  try { next = await api("/api/state"); } catch { $("#busy").textContent = "Mất kết nối máy chủ"; return; }
  state = next;
  safe(render);
}
route();
refresh();
setInterval(refresh, 2500);
