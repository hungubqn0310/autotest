"""
Các hàm tiện ích cho Odoo Automation
"""
import os
import re
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time


def _win_chrome_hwnds() -> set:
    """Trả về tập hợp HWND của tất cả cửa sổ Chrome đang mở (Windows only)."""
    import ctypes
    from ctypes import wintypes
    hwnds: set = set()

    def _cb(hwnd, _):
        buf = ctypes.create_unicode_buffer(64)
        ctypes.windll.user32.GetClassNameW(hwnd, buf, 64)
        if buf.value == "Chrome_WidgetWin_1":
            hwnds.add(hwnd)
        return True

    cb_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    ctypes.windll.user32.EnumWindows(cb_type(_cb), 0)
    return hwnds


def _win_activate_new_chrome(before: set, retries: int = 8) -> None:
    """Chờ Chrome mới xuất hiện rồi đưa lên foreground (Windows only)."""
    import ctypes
    for _ in range(retries):
        time.sleep(0.5)
        new = _win_chrome_hwnds() - before
        if new:
            hwnd = next(iter(new))
            ctypes.windll.user32.ShowWindow(hwnd, 3)          # SW_MAXIMIZE
            # Trick: giả lập nhấn Alt để lấy foreground lock, sau đó set foreground
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt key down
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # Alt key up
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return


def setup_driver():
    """Khởi tạo Chrome driver với các cấu hình"""
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")

    driver_path = ChromeDriverManager().install()
    # webdriver-manager đôi khi trả về THIRD_PARTY_NOTICES thay vì binary thực
    binary_name = "chromedriver.exe" if os.name == "nt" else "chromedriver"
    if not driver_path.endswith(binary_name):
        driver_path = os.path.join(os.path.dirname(driver_path), binary_name)

    service = Service(driver_path)

    # Snapshot các Chrome window hiện có trước khi Selenium mở thêm (Windows)
    before = _win_chrome_hwnds() if os.name == "nt" else set()

    driver = webdriver.Chrome(service=service, options=options)

    # Đưa Chrome window mới lên foreground (Windows only; Linux đã tự lên)
    if os.name == "nt":
        _win_activate_new_chrome(before)

    return driver


# ── Progress overlay (cập nhật live trên trình duyệt Odoo) ──────
_ov_driver = None
_cdp_driver_ref = None  # driver instance that has CDP script registered

try:
    from suite_meta import TC_META as _TC_META
except Exception:
    _TC_META = {}

# Persistent JS: defines window.__tcBuild* functions + reinjects panels from localStorage.
# Registered via CDP addScriptToEvaluateOnNewDocument so it runs on every page load.
_PERSISTENT_SCRIPT = r"""
window.__tcEsc = function(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
};
window.__tcBuildProgress = function(d) {
    if (!d || !d.tcs) return;
    var old = document.getElementById('__tc_progress__'); if (old) old.remove();
    var imap={waiting:'□',running:'⏳',pass:'✅',fail:'❌'};
    var cmap={waiting:'#475569',running:'#60a5fa',pass:'#4ade80',fail:'#f87171'};
    var dmap={waiting:'chờ',running:'đang chạy',pass:'PASS',fail:'FAIL'};
    var esc=window.__tcEsc;
    var rows=d.tcs.map(function(t){
        var s=t.status||'waiting';
        return '<div data-tc="'+esc(t.id)+'" style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #1e293b">'+
            '<span class="tc-icon" style="font-size:13px">'+(imap[s]||'□')+'</span>'+
            '<span class="tc-id" style="font-weight:700;font-size:11px;color:'+(cmap[s]||'#475569')+'">'+esc(t.id)+'</span>'+
            '<span class="tc-desc" style="font-size:10px;color:'+(cmap[s]||'#475569')+'">'+(dmap[s]||'chờ')+'</span>'+
            '</div>';
    }).join('');
    var passed=d.tcs.filter(function(t){return t.status==='pass';}).length;
    var failed=d.tcs.filter(function(t){return t.status==='fail';}).length;
    var done=passed+failed, total=d.tcs.length;
    var sc=failed>0?'#fbbf24':(done===total&&total>0?'#4ade80':'#475569');
    var p=document.createElement('div'); p.id='__tc_progress__';
    p.style.cssText='position:fixed;bottom:20px;right:20px;z-index:2147483647;background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:10px;font-family:monospace;font-size:12px;min-width:220px;max-height:65vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.8);border:1px solid #334155';
    p.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:12px">'+
        '<span style="font-weight:bold;font-size:11px;color:#60a5fa">'+esc(d.label)+'</span>'+
        '<button onclick="document.getElementById(\'__tc_progress__\').remove()" style="background:none;border:none;color:#475569;cursor:pointer;font-size:16px;line-height:1;padding:0">✕</button>'+
        '</div>'+rows+'<div id="__tc_summary__" style="margin-top:10px;font-size:11px;color:'+sc+'">'+done+'/'+total+' hoàn thành · '+passed+' PASS · '+failed+' FAIL</div>';
    document.body.appendChild(p);
};
window.__tcBuildDetail = function(d) {
    if (!d || !d.id) return;
    var old=document.getElementById('__tc_detail__'); if (old) old.remove();
    var esc=window.__tcEsc;
    var bgBadge=d.status==='pass'?'#16a34a':(d.status==='fail'?'#b91c1c':'#1d4ed8');
    var icon=d.status==='pass'?'✅ ':(d.status==='fail'?'❌ ':'');
    var border=d.status==='pass'?'#4ade80':(d.status==='fail'?'#f87171':'#334155');
    var steps=(d.steps||[]).map(function(s){return '<li style="margin-bottom:3px">'+esc(s)+'</li>';}).join('');
    var di=d.data_input?'<div style="margin-top:8px"><div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#475569;margin-bottom:3px">Data Input</div><div style="color:#94a3b8;white-space:pre-wrap">'+esc(d.data_input)+'</div></div>':'';
    var p=document.createElement('div'); p.id='__tc_detail__';
    p.style.cssText='position:fixed;top:20px;right:20px;z-index:2147483647;background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:10px;font-family:sans-serif;font-size:12px;width:340px;max-height:80vh;overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.8);border:1px solid '+border+';line-height:1.5';
    p.innerHTML='<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;gap:8px">'+
        '<div><span id="__tc_badge__" style="background:'+bgBadge+';color:#fff;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:700;margin-right:6px">'+icon+esc(d.id)+'</span>'+
        '<span style="font-size:10px;color:#475569">'+esc(d.suite||'')+'</span>'+
        '<div style="margin-top:5px;font-weight:600;font-size:12px;color:#e2e8f0">'+esc(d.desc||'')+'</div></div>'+
        '<button onclick="document.getElementById(\'__tc_detail__\').remove()" style="background:none;border:none;color:#475569;cursor:pointer;font-size:16px;line-height:1;padding:0;flex-shrink:0">✕</button></div>'+
        '<div style="border-top:1px solid #1e293b;padding-top:8px">'+
        '<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#475569;margin-bottom:3px">Pre-condition</div>'+
        '<div style="color:#94a3b8;white-space:pre-wrap">'+esc(d.precondition||'')+'</div></div>'+
        '<div style="margin-top:8px"><div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#475569;margin-bottom:3px">Steps</div>'+
        '<ol style="padding-left:16px;margin:0;color:#94a3b8">'+steps+'</ol></div>'+
        di+
        '<div style="margin-top:8px"><div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#475569;margin-bottom:3px">Expected</div>'+
        '<div style="color:#86efac">'+esc(d.expected||'')+'</div></div>';
    document.body.appendChild(p);
};
window.__tcReinject = function() {
    try { var pd=localStorage.getItem('__tcp__'); if(pd) window.__tcBuildProgress(JSON.parse(pd)); } catch(e){}
    try { var dd=localStorage.getItem('__tcd__'); if(dd) window.__tcBuildDetail(JSON.parse(dd)); } catch(e){}
};
if (document.body) { window.__tcReinject(); }
else { document.addEventListener('DOMContentLoaded', window.__tcReinject); }
"""


def init_progress(driver, tc_ids, label):
    """Inject panel tiến trình lên Chrome và đăng ký CDP để panel tồn tại qua navigation."""
    global _ov_driver, _cdp_driver_ref
    _ov_driver = driver
    import json as _j

    # Register persistent script via CDP once per driver instance
    if driver is not _cdp_driver_ref:
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": _PERSISTENT_SCRIPT}
            )
            _cdp_driver_ref = driver
        except Exception:
            pass

    # localStorage is origin-specific. Navigate to Odoo domain first so
    # our data is stored on the same origin the tests will run on.
    try:
        from urllib.parse import urlparse as _up
        from config import ODOO_URL as _OU
        _odoo_base = f"{_up(_OU).scheme}://{_up(_OU).netloc}"
        if _odoo_base not in driver.current_url:
            driver.get(_odoo_base)
            time.sleep(2)
    except Exception:
        pass

    tc_list = [{"id": tc_id, "status": "waiting"} for tc_id in tc_ids]
    progress_data = {"label": label, "tcs": tc_list}

    # Store initial state in localStorage (now on Odoo domain)
    try:
        driver.execute_script(
            "localStorage.setItem('__tcp__', arguments[0]); localStorage.removeItem('__tcd__');",
            _j.dumps(progress_data, ensure_ascii=False)
        )
    except Exception:
        pass

    # Define builder functions on current page + build panels immediately
    try:
        driver.execute_script(_PERSISTENT_SCRIPT)
    except Exception:
        pass


def _ov_update(tc_id, status):
    """Cập nhật trạng thái TC trong localStorage + DOM. CDP script sẽ tái inject sau mỗi navigation."""
    if not _ov_driver:
        return
    import json as _j

    if status == "running":
        meta = _TC_META.get(tc_id, {})
        detail_data = {
            "id": tc_id,
            "status": "running",
            "desc": meta.get("desc", ""),
            "suite": meta.get("suite_label", ""),
            "precondition": meta.get("precondition", ""),
            "steps": meta.get("steps", []),
            "data_input": meta.get("data_input", ""),
            "expected": meta.get("expected", ""),
        }
        script = """
var tcId = arguments[0], detailJson = arguments[1];
// update progress state in localStorage
var pd = JSON.parse(localStorage.getItem('__tcp__') || '{"tcs":[]}');
(pd.tcs||[]).forEach(function(t){ if(t.id===tcId) t.status='running'; });
localStorage.setItem('__tcp__', JSON.stringify(pd));
// update detail state in localStorage
localStorage.setItem('__tcd__', detailJson);
// direct DOM update for progress panel row
var row = document.querySelector('[data-tc="'+tcId+'"]');
if (row) {
    row.querySelector('.tc-icon').textContent = '⏳';
    row.querySelector('.tc-id').style.color = '#60a5fa';
    row.querySelector('.tc-desc').textContent = 'đang chạy';
    row.querySelector('.tc-desc').style.color = '#60a5fa';
    row.scrollIntoView({block:'nearest'});
} else if (window.__tcBuildProgress) { window.__tcBuildProgress(pd); }
// update summary
var rows = document.querySelectorAll('#__tc_progress__ [data-tc]');
var passed=[].filter.call(rows,function(r){return r.querySelector('.tc-icon').textContent==='✅';}).length;
var failed=[].filter.call(rows,function(r){return r.querySelector('.tc-icon').textContent==='❌';}).length;
var done=passed+failed, sm=document.getElementById('__tc_summary__');
if (sm) { sm.textContent=done+'/'+rows.length+' hoàn thành · '+passed+' PASS · '+failed+' FAIL'; sm.style.color=failed>0?'#fbbf24':(done===rows.length?'#4ade80':'#475569'); }
// show detail panel (3s delay if old one is still visible)
function showNewDetail() {
    var dd=localStorage.getItem('__tcd__');
    if (dd && window.__tcBuildDetail) try { window.__tcBuildDetail(JSON.parse(dd)); } catch(e){}
}
var oldDetail = document.getElementById('__tc_detail__');
if (oldDetail) { setTimeout(showNewDetail, 3000); } else { showNewDetail(); }
"""
        try:
            _ov_driver.execute_script(script, tc_id, _j.dumps(detail_data, ensure_ascii=False))
        except Exception:
            pass

    elif status in ("pass", "fail"):
        script = """
var tcId = arguments[0], tcStatus = arguments[1];
// update progress localStorage
var pd = JSON.parse(localStorage.getItem('__tcp__') || '{"tcs":[]}');
(pd.tcs||[]).forEach(function(t){ if(t.id===tcId) t.status=tcStatus; });
localStorage.setItem('__tcp__', JSON.stringify(pd));
// update detail localStorage status field
var dd_str=localStorage.getItem('__tcd__');
if (dd_str) { try { var dd=JSON.parse(dd_str); if(dd.id===tcId){ dd.status=tcStatus; localStorage.setItem('__tcd__',JSON.stringify(dd)); } } catch(e){} }
// direct DOM update for progress panel row
var icon=tcStatus==='pass'?'✅':'❌', color=tcStatus==='pass'?'#4ade80':'#f87171';
var row=document.querySelector('[data-tc="'+tcId+'"]');
if (row) {
    row.querySelector('.tc-icon').textContent=icon;
    row.querySelector('.tc-id').style.color=color;
    row.querySelector('.tc-desc').textContent=tcStatus==='pass'?'PASS':'FAIL';
    row.querySelector('.tc-desc').style.color=color;
} else if (window.__tcBuildProgress) { window.__tcBuildProgress(pd); }
var rows=document.querySelectorAll('#__tc_progress__ [data-tc]');
var passed=[].filter.call(rows,function(r){return r.querySelector('.tc-icon').textContent==='✅';}).length;
var failed=[].filter.call(rows,function(r){return r.querySelector('.tc-icon').textContent==='❌';}).length;
var done=passed+failed, sm=document.getElementById('__tc_summary__');
if (sm) { sm.textContent=done+'/'+rows.length+' hoàn thành · '+passed+' PASS · '+failed+' FAIL'; sm.style.color=failed>0?'#fbbf24':(done===rows.length?'#4ade80':'#475569'); }
// update detail panel badge if visible
var p=document.getElementById('__tc_detail__');
if (p) {
    var badge=document.getElementById('__tc_badge__');
    if (badge) { badge.style.background=tcStatus==='pass'?'#16a34a':'#b91c1c'; badge.textContent=(tcStatus==='pass'?'✅ ':'❌ ')+tcId; }
    p.style.borderColor=tcStatus==='pass'?'#4ade80':'#f87171';
}
"""
        try:
            _ov_driver.execute_script(script, tc_id, status)
        except Exception:
            pass


def log_ok(msg):
    print(f"  ✅ {msg}")
    m = re.search(r'\b(TC\d+)\s+PASS', msg)
    if m:
        _ov_update(m.group(1), "pass")


def log_info(msg):
    print(f"  📌 {msg}")


def log_err(msg):
    print(f"  ❌ {msg}")
    m = re.search(r'\b(TC\d+)\s+FAIL', msg)
    if m:
        _ov_update(m.group(1), "fail")


def log_step(step, title):
    print(f"\n{'='*60}")
    print(f"  BƯỚC {step}: {title}")
    print(f"{'='*60}")
    m = re.match(r'(TC\d+)', title)
    if m:
        _ov_update(m.group(1), "running")


def safe_click(driver, wait, xpath, use_js=False, timeout=20):
    """Click an element safely, retry with JS if needed."""
    el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    if use_js:
        driver.execute_script("arguments[0].click();", el)
    else:
        try:
            el.click()
        except Exception:
            driver.execute_script("arguments[0].click();", el)
    return el


def safe_fill(driver, wait, xpath, value, clear=True):
    """Fill input field."""
    el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    if clear:
        el.triple_click() if hasattr(el, 'triple_click') else (
            el.click(),
            el.send_keys(Keys.CONTROL + "a"),
            el.send_keys(Keys.DELETE)
        )
        el.clear()
    el.send_keys(value)
    return el


def wait_for_url_contains(driver, fragment, timeout=15):
    """Chờ URL chứa chuỗi cụ thể"""
    end = time.time() + timeout
    while time.time() < end:
        if fragment in driver.current_url:
            return True
        time.sleep(0.5)
    return False


def wait_for_toast_gone(wait):
    """Chờ thông báo loading/saving biến mất."""
    try:
        wait.until(EC.invisibility_of_element_located(
            (By.XPATH, "//div[contains(@class,'o_loading')]")))
    except Exception:
        pass


def get_status_badge(driver, wait):
    """Lấy trạng thái hiển thị trên form (statusbar)."""
    try:
        el = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'o_statusbar_status')]//button[@aria-checked='true'] | "
                       "//div[contains(@class,'o_status_bar')]//span[contains(@class,'o_arrow_button_current')]")))
        return el.text.strip()
    except Exception:
        return ""


def dismiss_popup_if_any(driver):
    """Đóng dialog/popup nếu có."""
    try:
        btn = driver.find_element(By.XPATH,
            "//div[@class='modal-footer']//button[contains(.,'OK') or contains(.,'Xác nhận') or contains(.,'Đóng')]")
        btn.click()
        time.sleep(0.5)
    except Exception:
        pass


def show_results_overlay(driver, title, results):
    """Inject panel kết quả test vào góc phải trình duyệt Odoo."""
    if not results:
        return
    import json as _json
    data = {
        "title": title,
        "results": [{"id": k, "ok": bool(v)} for k, v in results.items()],
    }
    script = f"""
(function(d){{
    let old = document.getElementById('__tc_results__');
    if (old) old.remove();
    let passed = d.results.filter(r=>r.ok).length, total = d.results.length;
    let sumColor = passed===total?'#4ade80':(passed===0?'#f87171':'#fbbf24');
    let rows = d.results.map(r=>`
        <div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #1e293b">
            <span style="font-size:13px">${{r.ok?'✅':'❌'}}</span>
            <span style="color:${{r.ok?'#4ade80':'#f87171'}};font-weight:700;font-size:11px">${{r.id}}</span>
            <span style="color:#64748b;font-size:10px">${{r.ok?'PASS':'FAIL'}}</span>
        </div>`).join('');
    let p = document.createElement('div');
    p.id = '__tc_results__';
    p.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:2147483647;'+
        'background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:10px;'+
        'font-family:monospace;font-size:12px;min-width:220px;max-height:65vh;'+
        'overflow-y:auto;box-shadow:0 8px 32px rgba(0,0,0,.8);border:1px solid #334155';
    p.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;gap:12px">
            <span style="font-weight:bold;font-size:11px;color:#60a5fa">${{d.title}}</span>
            <button onclick="document.getElementById('__tc_results__').remove()"
                style="background:none;border:none;color:#475569;cursor:pointer;font-size:16px;line-height:1;padding:0">✕</button>
        </div>
        ${{rows}}
        <div style="margin-top:10px;font-weight:bold;font-size:12px;color:${{sumColor}}">
            Tổng: ${{passed}}/${{total}} PASS
        </div>`;
    document.body.appendChild(p);
}})({_json.dumps(data, ensure_ascii=False)});
"""
    try:
        driver.execute_script(script)
    except Exception:
        pass


def select_first_dropdown_item(driver, wait, input_xpath, search_value=""):
    """Điền vào Many2one field và chọn item đầu tiên trong dropdown."""
    el = wait.until(EC.element_to_be_clickable((By.XPATH, input_xpath)))
    el.click()
    el.send_keys(Keys.CONTROL + "a")
    el.send_keys(Keys.DELETE)
    el.clear()
    if search_value:
        el.send_keys(search_value)
    else:
        el.send_keys(" ")  # trigger dropdown
    time.sleep(1.5)
    # Chọn item đầu tiên trong dropdown (bỏ qua "Tạo" / "Create")
    item = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//ul[contains(@class,'ui-autocomplete') or contains(@class,'dropdown-menu')]"
                   "//li[not(contains(@class,'o_m2o_dropdown_option'))]//a | "
                   "//ul[contains(@class,'ui-autocomplete')]//li[1]//a")))
    item.click()
    time.sleep(0.5)
