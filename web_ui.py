"""
Web UI cho Odoo Autotest.
Chạy: python web_ui.py  → mở http://localhost:5000
"""
import json
import os
import subprocess
import sys
import webbrowser
import threading

from flask import Flask, Response, request, stream_with_context

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable

app = Flask(__name__)

SUITE_META = {
    "login": {"label": "Suite 1.1 – Đăng nhập", "tcs": [
        {"id": "TC01", "desc": "Đăng nhập thành công với tài khoản hợp lệ"},
        {"id": "TC02", "desc": "Đăng nhập thất bại – sai mật khẩu"},
        {"id": "TC03", "desc": "Đăng nhập thất bại – để trống email"},
        {"id": "TC04", "desc": "Đăng nhập thất bại – để trống mật khẩu"},
        {"id": "TC05", "desc": "Đăng nhập thất bại – email sai định dạng"},
    ]},
    "logout": {"label": "Suite 1.2 – Đăng xuất", "tcs": [
        {"id": "TC06", "desc": "Đăng xuất thành công"},
        {"id": "TC07", "desc": "Session bị hủy sau khi đăng xuất"},
        {"id": "TC08", "desc": "Back button sau logout không vào lại được"},
        {"id": "TC09", "desc": "Đăng nhập lại thành công sau logout"},
    ]},
    "product": {"label": "Suite 2.1 – Sản phẩm", "tcs": [
        {"id": "TC07", "desc": "Tạo sản phẩm mới thành công"},
        {"id": "TC08", "desc": "Tạo sản phẩm – để trống tên"},
        {"id": "TC09", "desc": "Tạo sản phẩm – điền giá bán hợp lệ"},
        {"id": "TC10", "desc": "Cập nhật số lượng tồn kho thành công"},
        {"id": "TC11", "desc": "Tìm kiếm sản phẩm đã tạo"},
        {"id": "TC12", "desc": "Tạo sản phẩm – nhập giá âm"},
        {"id": "TC13", "desc": "Tạo sản phẩm – nhập giá bằng 0"},
        {"id": "TC14", "desc": "Tạo sản phẩm – nhập ký tự đặc biệt vào tên"},
        {"id": "TC15", "desc": "Tạo sản phẩm – nhập tên trùng"},
        {"id": "TC16", "desc": "Kiểm tra refresh sau khi lưu"},
    ]},
    "purchase": {"label": "Suite 3.1 – Mua hàng", "tcs": [
        {"id": "TC12", "desc": "Tạo đơn mua hàng và xác nhận thành công"},
        {"id": "TC13", "desc": "Tạo đơn mua – không chọn nhà cung cấp"},
        {"id": "TC14", "desc": "Nhập kho thành công sau khi xác nhận PO"},
        {"id": "TC15", "desc": "Kiểm tra trạng thái PO sau khi xác nhận"},
        {"id": "TC16", "desc": "Kiểm tra tồn kho tăng sau khi nhập kho"},
        {"id": "TC17", "desc": "Nhập số lượng âm vào đơn mua"},
    ]},
}

# ── HTML template ──────────────────────────────────────────────

_HTML = r"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Odoo Autotest</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f1f5f9;--surface:#ffffff;--surface2:#f8fafc;--border:#e2e8f0;
  --accent:#2563eb;--green:#16a34a;--red:#dc2626;--yellow:#d97706;
  --text:#1e293b;--muted:#64748b;--dim:#94a3b8
}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:var(--bg);color:var(--text);height:100vh;
  display:flex;flex-direction:column;overflow:hidden}

/* ── Header ── */
header{background:var(--surface);border-bottom:1px solid var(--border);
  padding:11px 20px;display:flex;align-items:center;gap:10px;flex-shrink:0;
  box-shadow:0 1px 3px rgba(0,0,0,.06)}
header h1{font-size:.95rem;font-weight:600;letter-spacing:.06em}
#badge{margin-left:auto;font-size:.74rem;padding:3px 10px;border-radius:20px;
  background:var(--bg);color:var(--muted)}
#badge.running{background:#dbeafe;color:#1d4ed8}
#badge.done{background:#dcfce7;color:#15803d}
#badge.error{background:#fee2e2;color:#b91c1c}

/* ── Main ── */
.main{display:flex;flex:1;min-height:0}

/* ── Suite panel ── */
.sp{width:220px;background:var(--surface2);border-right:1px solid var(--border);
  padding:14px 0;overflow-y:auto;flex-shrink:0}
.sp-title{font-size:.66rem;text-transform:uppercase;letter-spacing:.12em;
  color:var(--dim);padding:0 14px 10px}
.s-btn{display:block;width:100%;text-align:left;padding:9px 14px;
  background:none;border:none;border-left:3px solid transparent;
  color:var(--muted);cursor:pointer;transition:all .15s}
.s-btn:hover{background:rgba(37,99,235,.05);color:var(--text)}
.s-btn.active{border-left-color:var(--accent);color:var(--accent);
  background:rgba(37,99,235,.08)}
.s-name{display:block;font-size:.86rem}
.s-meta{font-size:.72rem;color:var(--dim);margin-top:1px}

/* ── TC panel ── */
.tp{flex:1;padding:20px 22px;overflow-y:auto;display:flex;flex-direction:column}
.tp-header{display:flex;justify-content:space-between;align-items:center;
  margin-bottom:14px}
.tp-title{font-size:.98rem;font-weight:600}
.tp-acts{display:flex;gap:6px}

.tc{display:flex;align-items:center;gap:11px;padding:9px 13px;
  border-radius:6px;border:1px solid var(--border);margin-bottom:6px;
  cursor:pointer;transition:border-color .15s,background .15s;user-select:none;
  background:var(--surface)}
.tc:hover{border-color:var(--accent);background:rgba(37,99,235,.03)}
.tc.sel{border-color:var(--green);background:rgba(22,163,74,.05)}
.tc-cb{width:15px;height:15px;accent-color:var(--green);cursor:pointer;flex-shrink:0}
.tc-id{color:var(--accent);font-weight:700;font-size:.8rem;width:42px;flex-shrink:0}
.tc-desc{font-size:.86rem;color:var(--muted)}

.empty{padding:30px;text-align:center;color:var(--dim);font-size:.86rem}

.run-area{margin-top:auto;padding-top:14px;border-top:1px solid var(--border);
  display:flex;justify-content:space-between;align-items:center}
.sel-info{font-size:.8rem;color:var(--muted)}

/* ── Buttons ── */
.btn{padding:5px 13px;border:1px solid var(--border);border-radius:5px;
  background:var(--surface);color:var(--muted);cursor:pointer;
  font-size:.78rem;transition:all .15s}
.btn:hover{background:var(--bg);color:var(--text);border-color:var(--dim)}
.btn-run{padding:9px 26px;background:var(--accent);border:none;border-radius:6px;
  color:#fff;font-weight:600;font-size:.9rem;cursor:pointer;transition:background .15s}
.btn-run:hover:not(:disabled){background:#1d4ed8}
.btn-run:disabled{background:var(--dim);cursor:not-allowed;opacity:.7}

/* ── Output ── */
.op{flex-shrink:0;height:258px;background:#0f172a;
  border-top:1px solid var(--border);display:flex;flex-direction:column}
.op-bar{display:flex;align-items:center;gap:8px;padding:6px 13px;
  background:#1e293b;border-bottom:1px solid #334155}
.op-bar span{font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:#64748b}
.op-bar .sp2{flex:1}
.op-bar .btn{background:#1e293b;border-color:#334155;color:#64748b}
.op-bar .btn:hover{background:#334155;color:#e2e8f0;border-color:#475569}
#out{flex:1;padding:9px 13px;overflow-y:auto;
  font-family:'Cascadia Code','Fira Code','Courier New',monospace;
  font-size:.77rem;line-height:1.7;white-space:pre-wrap;word-break:break-all}
.pass{color:#4ade80}.fail{color:#f87171}.info{color:#60a5fa}
.warn{color:#fbbf24}.sep{color:#334155}.head{color:#e2e8f0;font-weight:bold}
.plain{color:#94a3b8}
</style>
</head>
<body>

<header>
  <span style="font-size:1.15rem">🧪</span>
  <h1>ODOO AUTOTEST</h1>
  <div id="badge">Sẵn sàng</div>
</header>

<div class="main">
  <div class="sp">
    <div class="sp-title">Test Suites</div>
    <div id="suite-list"></div>
  </div>
  <div class="tp" id="tc-panel">
    <div class="empty">← Chọn suite để xem danh sách test case</div>
  </div>
</div>

<div class="op">
  <div class="op-bar">
    <span>Output</span>
    <div class="sp2"></div>
    <button class="btn" onclick="clearOut()">Xóa</button>
  </div>
  <div id="out"></div>
</div>

<script>
const SUITES = __SUITES_JSON__;
let curSuite = null;
const sel = new Set();

/* ── Suite list ── */
function renderSuites() {
  const el = document.getElementById('suite-list');
  el.innerHTML = '';
  for (const [key, m] of Object.entries(SUITES)) {
    const b = document.createElement('button');
    b.className = 'suite-btn s-btn';
    b.dataset.key = key;
    b.innerHTML = `<span class="s-name">${m.label}</span>
      <span class="s-meta">${m.tcs.length ? m.tcs.length + ' TC' : 'Cả suite'}</span>`;
    b.onclick = () => pickSuite(key);
    el.appendChild(b);
  }
}

function pickSuite(key) {
  curSuite = key; sel.clear();
  document.querySelectorAll('.s-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.key === key));
  renderTcPanel();
}

/* ── TC panel ── */
function renderTcPanel() {
  const panel = document.getElementById('tc-panel');
  const m = SUITES[curSuite];

  if (!m.tcs.length) {
    sel.add('__all__');
    panel.innerHTML = `
      <div class="tp-header"><span class="tp-title">${m.label}</span></div>
      <p style="color:var(--muted);font-size:.86rem;margin-bottom:12px">
        Suite này chạy toàn bộ, không tách TC lẻ.
      </p>
      <div class="run-area">
        <span class="sel-info">Chạy cả suite</span>
        <button class="btn-run" onclick="doRun()">▶ Chạy Suite</button>
      </div>`;
    return;
  }

  m.tcs.forEach(tc => sel.add(tc.id));

  panel.innerHTML = `
    <div class="tp-header">
      <span class="tp-title">${m.label}</span>
      <div class="tp-acts">
        <button class="btn" onclick="selAll()">Chọn tất cả</button>
        <button class="btn" onclick="deselAll()">Bỏ chọn</button>
      </div>
    </div>
    <div id="tc-list"></div>
    <div class="run-area">
      <span class="sel-info" id="sel-info"></span>
      <button class="btn-run" id="run-btn" onclick="doRun()">▶ Chạy Test</button>
    </div>`;

  renderItems();
}

function renderItems() {
  const m = SUITES[curSuite];
  const el = document.getElementById('tc-list');
  if (!el) return;
  el.innerHTML = '';
  m.tcs.forEach(tc => {
    const d = document.createElement('div');
    d.className = 'tc' + (sel.has(tc.id) ? ' sel' : '');
    d.dataset.id = tc.id;
    d.innerHTML = `<input type="checkbox" class="tc-cb" ${sel.has(tc.id)?'checked':''}
        onchange="toggleTc('${tc.id}')">
      <span class="tc-id">${tc.id}</span>
      <span class="tc-desc">${tc.desc}</span>`;
    d.onclick = e => { if (e.target.tagName!=='INPUT') toggleTc(tc.id); };
    el.appendChild(d);
  });
  updateInfo();
}

function toggleTc(id) {
  sel.has(id) ? sel.delete(id) : sel.add(id);
  const d = document.querySelector(`.tc[data-id="${id}"]`);
  if (d) { d.classList.toggle('sel', sel.has(id)); d.querySelector('.tc-cb').checked = sel.has(id); }
  updateInfo();
}

function selAll()   { SUITES[curSuite].tcs.forEach(tc => sel.add(tc.id));   renderItems(); }
function deselAll() { sel.clear(); renderItems(); }

function updateInfo() {
  const m = SUITES[curSuite]; if (!m) return;
  const info = document.getElementById('sel-info');
  const btn  = document.getElementById('run-btn');
  if (info) info.textContent = `Đã chọn ${sel.size}/${m.tcs.length}`;
  if (btn)  btn.disabled = sel.size === 0;
}

/* ── Output ── */
function appendOut(text) {
  const el = document.getElementById('out');
  text.split('\n').forEach(line => {
    if (!line) return;
    const s = document.createElement('span');
    let cls = 'plain';
    if (line.includes('✅') || /\bPASS\b/.test(line)) cls = 'pass';
    else if (line.includes('❌') || /\bFAIL\b/.test(line)) cls = 'fail';
    else if (line.includes('📌')) cls = 'info';
    else if (line.includes('⚠') || /\bWARN\b/.test(line)) cls = 'warn';
    else if (/^[= ─═]+$/.test(line.trim()) && line.trim().length > 3) cls = 'sep';
    else if (/Tổng:|SUITE [0-9]/.test(line)) cls = 'head';
    s.className = cls; s.textContent = line + '\n';
    el.appendChild(s);
  });
  el.scrollTop = el.scrollHeight;
}

function clearOut() { document.getElementById('out').innerHTML = ''; }

/* ── Run ── */
async function doRun() {
  if (!curSuite) return;
  const m = SUITES[curSuite];
  const tcs = m.tcs.length
    ? [...sel].filter(id => m.tcs.some(tc => tc.id === id))
    : [];

  const btn   = document.getElementById('run-btn');
  const badge = document.getElementById('badge');
  if (btn) btn.disabled = true;
  badge.textContent = '⏳ Đang chạy...'; badge.className = 'running';

  clearOut();
  appendOut(`Suite: ${m.label}`);
  if (tcs.length) appendOut(`Test cases: ${tcs.join(', ')}`);
  appendOut('═'.repeat(60));

  try {
    const resp = await fetch('/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({suite: curSuite, tcs})
    });

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buf += decoder.decode(value, {stream: true});
      const lines = buf.split('\n');
      buf = lines.pop();
      lines.forEach(l => appendOut(l));
    }
    if (buf) appendOut(buf);

    badge.textContent = '✅ Hoàn thành'; badge.className = 'done';
  } catch (err) {
    appendOut(`\nLỗi kết nối: ${err.message}`);
    badge.textContent = '❌ Lỗi'; badge.className = 'error';
  }

  if (btn) btn.disabled = sel.size === 0;
  setTimeout(() => { badge.textContent = 'Sẵn sàng'; badge.className = ''; }, 4000);
}

renderSuites();
</script>
</body>
</html>"""


# ── Flask routes ──────────────────────────────────────────────

@app.route("/")
def index():
    html = _HTML.replace("__SUITES_JSON__", json.dumps(SUITE_META, ensure_ascii=False))
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/run", methods=["POST"])
def run():
    data = request.get_json(force=True)
    suite = data.get("suite", "purchase")
    tcs   = data.get("tcs", [])

    cmd = [PYTHON, "main.py", "test", suite]
    if tcs:
        cmd.append(",".join(tcs))

    def generate():
        try:
            proc = subprocess.Popen(
                cmd, cwd=SCRIPT_DIR,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
            )
            for line in iter(proc.stdout.readline, ""):
                yield line
            proc.wait()
        except Exception as exc:
            yield f"\nLỗi khởi động process: {exc}\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/plain; charset=utf-8",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    url = "http://localhost:5000"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"🌐  Mở trình duyệt tại {url}")
    print("     Ctrl+C để dừng server\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
