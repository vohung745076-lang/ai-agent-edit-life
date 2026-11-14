// Kuto — máy chủ giao diện. Không phụ thuộc gói ngoài.
// Chạy:  .runtime\node\node.exe app\server.mjs   (hoặc bấm đúp start.bat)
import { spawn } from "node:child_process";
import fs from "node:fs";
import fsp from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const APP = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(APP);
const PUBLIC = path.join(APP, "public");
const DATA = path.join(APP, "data");
const JOBS_FILE = path.join(DATA, "jobs.json");
const PORT = Number(process.env.KUTO_PORT || 4173);
const CLAUDE_BIN = process.env.CLAUDE_BIN || "claude";
// Công cụ agent được phép dùng khi chạy nền (không có người bấm duyệt từng lệnh).
const ALLOWED_TOOLS = (process.env.KUTO_ALLOWED_TOOLS ||
  "Bash,PowerShell,Read,Write,Edit,Glob,Grep,Skill,Agent,WebFetch,WebSearch,ToolSearch,mcp__claude_ai_Google_Drive").split(",");

const ID_RE = /^[a-z0-9][a-z0-9._-]{0,80}$/i;
const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8", ".txt": "text/plain; charset=utf-8",
  ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime", ".mp3": "audio/mpeg", ".wav": "audio/wav",
  ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2",
};

fs.mkdirSync(DATA, { recursive: true });
for (const d of ["projects", "styles"]) fs.mkdirSync(path.join(ROOT, d), { recursive: true });

// ───────── tiện ích ─────────
const readJson = async (file, fallback = null) => {
  try { return JSON.parse(await fsp.readFile(file, "utf8")); } catch { return fallback; }
};
const writeJson = (file, data) => fsp.writeFile(file, JSON.stringify(data, null, 2), "utf8");
const send = (res, code, body, type = "application/json; charset=utf-8") => {
  res.writeHead(code, { "Content-Type": type, "Cache-Control": "no-store" });
  res.end(typeof body === "string" || Buffer.isBuffer(body) ? body : JSON.stringify(body));
};
const readBody = (req, limit = 2e6) => new Promise((resolve, reject) => {
  const chunks = []; let size = 0;
  req.on("data", (c) => { size += c.length; if (size > limit) { reject(new Error("Dữ liệu quá lớn")); req.destroy(); } else chunks.push(c); });
  req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
  req.on("error", reject);
});
const slugify = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d")
  .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
const stamp = () => {
  const d = new Date(), p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
};
const today = () => stamp().slice(0, 10);
const inside = (base, target) => { const rel = path.relative(base, target); return rel && !rel.startsWith("..") && !path.isAbsolute(rel); };

// ───────── công việc của agent ─────────
let jobs = (await readJson(JOBS_FILE, [])).map((j) =>
  j.status === "running" || j.status === "queued" ? { ...j, status: "error", result: "Máy chủ khởi động lại khi việc đang chạy." } : j);
const procs = new Map();
let saveTimer = null;
const saveJobs = () => { clearTimeout(saveTimer); saveTimer = setTimeout(() => writeJson(JOBS_FILE, jobs.slice(-60)).catch(() => {}), 400); };
const log = (job, type, text) => {
  job.log.push({ t: Date.now(), type, text: String(text).slice(0, 1200) });
  if (job.log.length > 500) job.log.splice(0, job.log.length - 500);
  saveJobs();
};

function describeTool(name, input = {}) {
  const pick = input.description || input.command || input.file_path || input.pattern || input.skill || input.url || input.prompt || "";
  return `${name}${pick ? " · " + String(pick).replace(/\s+/g, " ").slice(0, 160) : ""}`;
}

function startJob(job) {
  job.status = "running"; job.startedAt = Date.now();
  const args = ["-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits", "--allowedTools", ALLOWED_TOOLS.join(",")];
  if (job.resume) args.push("--resume", job.resume);
  const rt = path.join(ROOT, ".runtime");
  const env = {
    ...process.env,
    PATH: `${path.join(rt, "node")};${path.join(rt, "ffmpeg", "bin")};${process.env.PATH}`,
    HYPERFRAMES_FFMPEG_PATH: path.join(rt, "ffmpeg", "bin", "ffmpeg.exe"),
    HYPERFRAMES_FFPROBE_PATH: path.join(rt, "ffmpeg", "bin", "ffprobe.exe"),
    PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1",
  };
  let child;
  try { child = spawn(CLAUDE_BIN, args, { cwd: ROOT, env, windowsHide: true }); }
  catch (e) { finish(job, "error", `Không chạy được Claude Code: ${e.message}`); return; }
  procs.set(job.id, child);
  child.stdin.end(job.prompt, "utf8");

  let buf = "", errTail = "";
  child.stdout.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    buf += chunk;
    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim(); buf = buf.slice(nl + 1);
      if (!line) continue;
      let ev; try { ev = JSON.parse(line); } catch { continue; }
      if (ev.session_id && !job.sessionId) job.sessionId = ev.session_id;
      if (ev.type === "assistant") {
        for (const b of ev.message?.content || []) {
          if (b.type === "text" && b.text.trim()) log(job, "say", b.text.trim());
          else if (b.type === "tool_use") log(job, "tool", describeTool(b.name, b.input));
        }
      } else if (ev.type === "result") {
        job.result = ev.result || ""; job.isError = !!ev.is_error;
        if (ev.total_cost_usd != null) job.cost = ev.total_cost_usd;
      }
    }
  });
  child.stderr.setEncoding("utf8");
  child.stderr.on("data", (c) => { errTail = (errTail + c).slice(-1500); });
  child.on("error", (e) => finish(job, "error", `Không chạy được Claude Code (${CLAUDE_BIN}): ${e.message}`));
  child.on("close", (code) => {
    if (job.status !== "running") return;
    if (job.stopped) finish(job, "stopped", "Đã dừng theo yêu cầu.");
    else if (code === 0 && !job.isError) finish(job, "done", job.result);
    else finish(job, "error", job.result || errTail || `Claude Code thoát với mã ${code}`);
  });
}

function finish(job, status, result) {
  job.status = status; job.result = result || job.result || ""; job.endedAt = Date.now();
  procs.delete(job.id);
  log(job, status === "done" ? "done" : "error", status === "done" ? "Hoàn tất." : job.result);
  markTargetOnFailure(job).finally(pump);
}

// Nếu agent chết giữa chừng, đừng để dự án kẹt ở trạng thái "đang chạy".
async function markTargetOnFailure(job) {
  if (job.status === "done" || !job.target) return;
  const file = job.target.type === "project"
    ? path.join(ROOT, "projects", job.target.id, "project.json")
    : path.join(ROOT, "styles", job.target.id, "style.json");
  const data = await readJson(file);
  if (!data) return;
  const busy = ["queued", "downloading", "analyzing", "planning", "editing", "rendering", "learning"];
  if (busy.includes(data.status)) {
    data.status = "error";
    data.message = job.status === "stopped" ? "Đã dừng giữa chừng. Gửi góp ý hoặc yêu cầu để chạy tiếp." : `Agent dừng do lỗi: ${String(job.result).slice(0, 300)}`;
    await writeJson(file, data);
  }
}

function pump() {
  if (jobs.some((j) => j.status === "running")) return; // chạy lần lượt: máy ít RAM, render không nên song song
  const next = jobs.find((j) => j.status === "queued");
  if (next) startJob(next);
}

function addJob({ kind, title, prompt, target }) {
  const prev = target && [...jobs].reverse().find((j) => j.sessionId && j.target && j.target.type === target.type && j.target.id === target.id);
  const job = {
    id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`, kind, title, prompt, target: target || null,
    status: "queued", createdAt: Date.now(), log: [], resume: prev?.sessionId || null,
  };
  jobs.push(job); saveJobs(); pump();
  return job;
}

// ───────── trạng thái cho giao diện ─────────
async function listDir(dir) {
  try { return (await fsp.readdir(dir, { withFileTypes: true })).filter((d) => d.isDirectory()).map((d) => d.name); } catch { return []; }
}
const exists = (p) => fsp.access(p).then(() => true, () => false);

async function getState() {
  const projects = [];
  for (const id of await listDir(path.join(ROOT, "projects"))) {
    if (id.startsWith("_")) continue;
    const dir = path.join(ROOT, "projects", id);
    const p = await readJson(path.join(dir, "project.json"));
    if (!p) continue;
    const outputs = [];
    for (const o of p.outputs || []) if (o.file && await exists(path.join(dir, o.file))) outputs.push({ ...o, url: `/files/projects/${id}/${o.file}` });
    projects.push({
      ...p, id, outputs,
      planUrl: (await exists(path.join(dir, "PLAN.md"))) ? `/files/projects/${id}/PLAN.md` : null,
      directionUrl: (await exists(path.join(dir, "DIRECTION.md"))) ? `/files/projects/${id}/DIRECTION.md` : null,
      mtime: (await fsp.stat(path.join(dir, "project.json"))).mtimeMs,
    });
  }
  projects.sort((a, b) => b.mtime - a.mtime);

  const styles = [];
  for (const slug of await listDir(path.join(ROOT, "styles"))) {
    if (slug.startsWith("_")) continue;
    const dir = path.join(ROOT, "styles", slug);
    const s = await readJson(path.join(dir, "style.json"));
    if (!s) continue;
    const url = async (f) => (f && await exists(path.join(dir, f)) ? `/files/styles/${slug}/${f}` : null);
    styles.push({
      ...s, slug,
      demoUrl: await url(s.demo || "demo.mp4"), demoVerticalUrl: await url(s.demo_vertical || "demo-9x16.mp4"),
      referenceUrl: await url("source/reference.mp4"), briefUrl: await url("STYLE.md"),
      metricsUrl: await url("analysis/STYLE_METRICS.md"),
      lessonsUrl: slug === "personal" ? await url("LESSONS.md") : null,
    });
  }
  const rank = { personal: 0, draft: 1, learning: 1, error: 2, approved: 3 };
  styles.sort((a, b) => (rank[a.status] ?? 9) - (rank[b.status] ?? 9) || String(b.created).localeCompare(String(a.created)));

  return {
    projects, styles,
    jobs: jobs.slice(-25).reverse().map((j) => ({
      id: j.id, kind: j.kind, title: j.title, target: j.target, status: j.status,
      createdAt: j.createdAt, startedAt: j.startedAt, endedAt: j.endedAt, result: j.result, log: j.log.slice(-80),
    })),
  };
}

// ───────── hành động ─────────
const URL_RE = /https?:\/\/[^\s"'<>]+/i;

async function createProject(link, note) {
  const id = `${stamp()}${note ? "-" + slugify(note).slice(0, 24) : ""}`.replace(/-+$/, "");
  const dir = path.join(ROOT, "projects", id);
  await fsp.mkdir(path.join(dir, "raw"), { recursive: true });
  await writeJson(path.join(dir, "project.json"), {
    id, title: note ? note.slice(0, 80) : "Video mới", source: link, status: "queued", step: "Đang chờ tới lượt",
    version: 0, outputs: [], styles_used: [], message: "", created: today(),
  });
  return id;
}

async function createStyle(source, note) {
  const slug = `mau-${stamp()}`;
  const dir = path.join(ROOT, "styles", slug);
  await fsp.mkdir(path.join(dir, "source"), { recursive: true });
  await writeJson(path.join(dir, "style.json"), {
    slug, name: "Đang học video mẫu…", status: "learning", source, created: today(), summary: "", topics: [],
    best_for: "", avoid_for: "", tokens: {}, techniques: [], user_notes: note || "", message: "Đang chờ tới lượt",
  });
  return slug;
}

async function ask({ text = "", mode = "auto" }) {
  text = text.trim();
  if (!text) throw new Error("Hãy nhập link hoặc yêu cầu.");
  const link = (text.match(URL_RE) || [])[0];
  const note = link ? text.replace(link, "").trim() : text;
  if (mode === "auto") mode = link ? (/drive\.google\.com|docs\.google\.com/i.test(link) ? "edit" : "learn") : "chat";

  if (mode === "edit") {
    if (!link) throw new Error("Cần link Google Drive chứa video.");
    const id = await createProject(link, note);
    return addJob({
      kind: "edit", title: `Dựng video · ${note || link}`.slice(0, 90), target: { type: "project", id },
      prompt: `Dùng skill kuto-edit để dựng video hoàn chỉnh.\nLink Google Drive: ${link}\nThư mục dự án (đã tạo sẵn, có project.json): projects/${id}\n${note ? `Yêu cầu thêm của người dùng: ${note}\n` : ""}Làm trọn quy trình (xem hiểu → Creative Director chọn phong cách và cấu trúc → dựng → xuất) tới bước giao duyệt, cập nhật project.json ở mỗi bước.`,
    });
  }
  if (mode === "learn") {
    if (!link) throw new Error("Cần link video mẫu (hoặc tải file lên).");
    return learn(link, note);
  }
  return addJob({ kind: "chat", title: text.slice(0, 90), prompt: text });
}

async function learn(source, note) {
  const slug = await createStyle(source, note);
  return addJob({
    kind: "learn", title: `Học mẫu · ${note || source}`.slice(0, 90), target: { type: "style", id: slug },
    prompt: `Dùng skill kuto-learn để học phong cách từ video mẫu theo đủ dây chuyền: thu thập bằng yt-dlp, Video Analysis Agent phân tích 8 nhóm + cấu trúc timeline, ghi vào kho tri thức, dựng demo.\nNguồn: ${source}\nThư mục phong cách (đã tạo sẵn, có style.json): styles/${slug}\n${note ? `Ghi chú của người dùng (điều họ thích ở video này): ${note}\n` : ""}Làm trọn quy trình tới bước có bảng phong cách và video demo chờ duyệt.`,
  });
}

const routes = {
  "POST /api/ask": async (req) => ({ job: (await ask(JSON.parse(await readBody(req)))).id }),

  "POST /api/projects/:id/feedback": async (req, { id }) => {
    const { text } = JSON.parse(await readBody(req));
    if (!text?.trim()) throw new Error("Hãy nhập góp ý.");
    return { job: addJob({
      kind: "revise", title: `Sửa video · ${text}`.slice(0, 90), target: { type: "project", id },
      prompt: `Dùng skill kuto-edit, mục "Sửa theo góp ý".\nDự án: projects/${id}\nGóp ý mới của người dùng:\n"""\n${text.trim()}\n"""\nSửa đúng các chỗ được góp ý ở cả hai khổ, render phiên bản mới, tự kiểm, rồi đặt status review.`,
    }).id };
  },
  "POST /api/projects/:id/finalize": async (_req, { id }) => ({ job: addJob({
    kind: "finalize", title: "Chốt video và ghi nhớ phong cách", target: { type: "project", id },
    prompt: `Người dùng đã CHỐT video của dự án projects/${id}.\n1) Theo skill kuto-edit: render bản giao chất lượng delivery cho cả hai khổ, cập nhật outputs, đặt status done.\n2) Dùng skill kuto-remember để rút bài học từ feedback.md và các thay đổi của dự án này vào styles/personal.\nKết thúc bằng danh sách ngắn những gì đã ghi nhớ.`,
  }).id }),

  "POST /api/styles/:id/save": async (req, { id }) => {
    const patch = JSON.parse(await readBody(req));
    const file = path.join(ROOT, "styles", id, "style.json");
    const s = await readJson(file);
    if (!s) throw new Error("Không tìm thấy phong cách.");
    for (const k of ["name", "summary", "topics", "best_for", "avoid_for", "tokens", "analysis", "user_notes"]) if (k in patch) s[k] = patch[k];
    s.edited_by_user = today();
    await writeJson(file, s);
    return { ok: true };
  },
  "POST /api/styles/:id/approve": async (_req, { id }) => {
    const file = path.join(ROOT, "styles", id, "style.json");
    const s = await readJson(file);
    if (!s) throw new Error("Không tìm thấy phong cách.");
    if (s.status === "personal") return { ok: true };
    s.status = "approved"; s.approved = today(); s.message = "";
    await writeJson(file, s);
    return { ok: true };
  },
  "POST /api/styles/:id/unapprove": async (_req, { id }) => {
    const file = path.join(ROOT, "styles", id, "style.json");
    const s = await readJson(file);
    if (s && s.status === "approved") { s.status = "draft"; await writeJson(file, s); }
    return { ok: true };
  },
  "POST /api/styles/:id/feedback": async (req, { id }) => {
    const { text } = JSON.parse(await readBody(req));
    if (!text?.trim()) throw new Error("Hãy nhập góp ý.");
    return { job: addJob({
      kind: "restyle", title: `Sửa phong cách · ${text}`.slice(0, 90), target: { type: "style", id },
      prompt: `Dùng skill kuto-learn, mục "Sửa theo góp ý".\nPhong cách: styles/${id}\nĐọc lại style.json trước (người dùng có thể đã sửa trực tiếp trên giao diện).\nGóp ý mới của người dùng:\n"""\n${text.trim()}\n"""\nCập nhật kỹ thuật, STYLE.md, dựng lại demo, giữ status draft.`,
    }).id };
  },

  "POST /api/jobs/:id/stop": async (_req, { id }) => {
    const job = jobs.find((j) => j.id === id);
    if (!job) throw new Error("Không tìm thấy việc.");
    if (job.status === "queued") finish(job, "stopped", "Đã huỷ trước khi chạy.");
    else if (job.status === "running") {
      job.stopped = true;
      const child = procs.get(id);
      if (child) spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], { windowsHide: true });
    }
    return { ok: true };
  },
};

// Tải file video mẫu lên: POST /api/upload?name=abc.mp4&note=...  (thân request = nội dung file)
async function upload(req, url) {
  const name = path.basename(url.searchParams.get("name") || "mau.mp4");
  const ext = path.extname(name).toLowerCase();
  if (![".mp4", ".mov", ".m4v", ".webm", ".mkv"].includes(ext)) throw new Error("Chỉ nhận file video (mp4, mov, m4v, webm, mkv).");
  const inbox = path.join(ROOT, "styles", "_inbox");
  await fsp.mkdir(inbox, { recursive: true });
  const file = path.join(inbox, `${stamp()}${ext}`);
  await new Promise((resolve, reject) => {
    const out = fs.createWriteStream(file);
    req.pipe(out); out.on("finish", resolve); out.on("error", reject); req.on("error", reject);
  });
  const job = await learn(file, url.searchParams.get("note") || "");
  return { job: job.id };
}

// Bản xem thử tương thích: giữ nguyên hình, đổi âm thanh AAC sang MP3.
// Trình xem dựng trên Electron (vd. trình duyệt tích hợp của VS Code) không giải mã được AAC nên phát video câm.
const compatJobs = new Map();
function compatCopy(file) {
  const dir = path.join(path.dirname(file), ".compat");
  const target = path.join(dir, path.basename(file));
  if (compatJobs.has(target)) return compatJobs.get(target);
  const job = (async () => {
    const [src, dst] = await Promise.all([fsp.stat(file), fsp.stat(target).catch(() => null)]);
    if (dst && dst.mtimeMs >= src.mtimeMs && dst.size > 0) return target;
    await fsp.mkdir(dir, { recursive: true });
    const tmp = target + ".part.mp4";
    const ffmpeg = path.join(ROOT, ".runtime", "ffmpeg", "bin", "ffmpeg.exe");
    await new Promise((resolve, reject) => {
      const p = spawn(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-i", file, "-c:v", "copy",
        "-c:a", "libmp3lame", "-b:a", "192k", "-movflags", "+faststart", tmp], { windowsHide: true });
      p.on("error", reject);
      p.on("close", (code) => (code === 0 ? resolve() : reject(new Error("Không tạo được bản xem thử tương thích"))));
    });
    await fsp.rename(tmp, target);
    return target;
  })().finally(() => compatJobs.delete(target));
  compatJobs.set(target, job);
  return job;
}

function serveFile(req, res, file) {
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) return send(res, 404, { error: "Không tìm thấy" });
    const type = MIME[path.extname(file).toLowerCase()] || "application/octet-stream";
    const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || "");
    if (range) {
      const start = range[1] ? Number(range[1]) : 0;
      const end = range[2] ? Math.min(Number(range[2]), st.size - 1) : st.size - 1;
      if (start > end || start >= st.size) { res.writeHead(416, { "Content-Range": `bytes */${st.size}` }); return res.end(); }
      res.writeHead(206, { "Content-Type": type, "Content-Range": `bytes ${start}-${end}/${st.size}`, "Accept-Ranges": "bytes", "Content-Length": end - start + 1, "Cache-Control": "no-store" });
      return fs.createReadStream(file, { start, end }).pipe(res);
    }
    res.writeHead(200, { "Content-Type": type, "Content-Length": st.size, "Accept-Ranges": "bytes", "Cache-Control": "no-store" });
    fs.createReadStream(file).pipe(res);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  const pathname = decodeURIComponent(url.pathname);
  try {
    // Chỉ nhận yêu cầu ghi từ chính trang này (chặn trang web khác gọi vào máy chủ cục bộ).
    if (req.method !== "GET") {
      const origin = req.headers.origin;
      if (origin && new URL(origin).host !== req.headers.host) return send(res, 403, { error: "Từ chối" });
    }
    if (req.method === "GET" && pathname === "/api/state") return send(res, 200, await getState());
    if (req.method === "POST" && pathname === "/api/upload") return send(res, 200, await upload(req, url));

    for (const [key, handler] of Object.entries(routes)) {
      const [method, pattern] = key.split(" ");
      if (method !== req.method) continue;
      const m = new RegExp("^" + pattern.replace(/:id/, "([^/]+)") + "$").exec(pathname);
      if (!m) continue;
      if (m[1] && !ID_RE.test(m[1])) return send(res, 400, { error: "Mã không hợp lệ" });
      return send(res, 200, await handler(req, { id: m[1] }));
    }

    if (req.method === "GET" && pathname.startsWith("/files/")) {
      const rel = pathname.slice("/files/".length);
      const file = path.resolve(ROOT, rel);
      const ok = ["projects", "styles"].some((d) => inside(path.join(ROOT, d), file));
      if (!ok) return send(res, 403, { error: "Từ chối" });
      if (url.searchParams.get("compat") === "1" && /\.mp4$/i.test(file)) return serveFile(req, res, await compatCopy(file));
      return serveFile(req, res, file);
    }
    if (req.method === "GET") {
      const file = path.resolve(PUBLIC, "." + (pathname === "/" ? "/index.html" : pathname));
      return inside(PUBLIC, file) ? serveFile(req, res, file) : send(res, 403, { error: "Từ chối" });
    }
    send(res, 404, { error: "Không tìm thấy" });
  } catch (e) {
    send(res, 400, { error: e.message || String(e) });
  }
});

server.listen(PORT, "127.0.0.1", () => console.log(`Kuto đang chạy: http://localhost:${PORT}`));
