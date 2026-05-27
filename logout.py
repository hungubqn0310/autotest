"""
Module xử lý đăng xuất khỏi Odoo – Suite 1.2 (TC06–TC09)
"""
import time
from urllib.parse import urlparse
from config import ODOO_URL, ODOO_USER, ODOO_PASS
from helpers import log_step, log_ok, log_err, safe_click
from login import login

_parsed = urlparse(ODOO_URL)
_LOGIN_URL = f"{_parsed.scheme}://{_parsed.netloc}/web/login"
_BASE_URL  = f"{_parsed.scheme}://{_parsed.netloc}"


def _ensure_logged_in(driver, wait):
    """Đảm bảo đang ở trạng thái đã đăng nhập trước mỗi test case."""
    if "/odoo" not in driver.current_url:
        login(driver, wait)


def _do_logout(driver, wait):
    """Click avatar → chọn Đăng xuất trong dropdown."""
    # Chờ SPA render xong navbar trước khi click
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(@class,'o_user_menu')]")))
    time.sleep(1)
    safe_click(driver, wait, "//button[contains(@class,'o_user_menu')]", use_js=True)
    time.sleep(0.8)
    safe_click(driver, wait, "//*[@data-menu='logout']")
    time.sleep(2)


def _print_suite_result(title, results):
    passed = sum(1 for v in results.values() if v)
    print("\n" + "=" * 60)
    print(f"  KẾT QUẢ {title}")
    print("=" * 60)
    for tc, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {tc}")
    print(f"\n  Tổng: {passed}/{len(results)} test case passed")
    print("=" * 60)


# ──────────────────────────────────────────────────────────────
# TC06 – TC09
# ──────────────────────────────────────────────────────────────

def tc06_logout_success(driver, wait):
    """TC06 – Đăng xuất thành công"""
    log_step(6, "TC06 – Đăng xuất thành công")
    _ensure_logged_in(driver, wait)
    time.sleep(1)
    _do_logout(driver, wait)

    if "/web/login" in driver.current_url:
        log_ok(f"TC06 PASS: Đăng xuất thành công. URL: {driver.current_url}")
        return True
    else:
        log_err(f"TC06 FAIL: Vẫn ở dashboard sau logout. URL: {driver.current_url}")
        return False


def tc07_session_invalidated_after_logout(driver, wait):
    """TC07 – Sau logout, truy cập /odoo trực tiếp phải bị redirect về login"""
    log_step(7, "TC07 – Session bị hủy sau logout")
    _ensure_logged_in(driver, wait)
    time.sleep(1)
    _do_logout(driver, wait)

    driver.get(f"{_BASE_URL}/odoo")
    time.sleep(2)

    if "/odoo" not in driver.current_url:
        log_ok(f"TC07 PASS: Truy cập /odoo bị redirect về login. URL: {driver.current_url}")
        return True
    else:
        log_err(f"TC07 FAIL: Vẫn truy cập được /odoo sau logout. URL: {driver.current_url}")
        return False


def tc08_back_button_after_logout(driver, wait):
    """TC08 – Nhấn Back sau logout không quay lại được dashboard"""
    log_step(8, "TC08 – Back button sau logout")
    _ensure_logged_in(driver, wait)
    time.sleep(1)
    _do_logout(driver, wait)

    driver.back()
    time.sleep(2)

    still_on_odoo = "/odoo" in driver.current_url
    if still_on_odoo:
        driver.refresh()
        time.sleep(2)
        still_on_odoo = "/odoo" in driver.current_url

    if not still_on_odoo:
        log_ok(f"TC08 PASS: Back button không vào được dashboard. URL: {driver.current_url}")
        return True
    else:
        log_err(f"TC08 FAIL: Vẫn thấy dashboard sau Back. URL: {driver.current_url}")
        return False


def tc09_relogin_after_logout(driver, wait):
    """TC09 – Đăng nhập lại thành công sau khi logout"""
    log_step(9, "TC09 – Đăng nhập lại sau logout")
    _ensure_logged_in(driver, wait)
    time.sleep(1)
    _do_logout(driver, wait)

    login(driver, wait)
    time.sleep(1)

    if "/odoo" in driver.current_url:
        log_ok("TC09 PASS: Đăng nhập lại thành công sau logout")
        return True
    else:
        log_err("TC09 FAIL: Không đăng nhập lại được sau logout")
        return False


def run_logout_suite(driver, wait, selected_tcs: list[str] | None = None):
    """Chạy toàn bộ Suite 1.2 – Đăng xuất (TC06–TC09)"""
    print("\n" + "=" * 60)
    print("  SUITE 1.2 – ĐĂNG XUẤT")
    print("=" * 60)

    _ALL_TCS = {
        "TC06": tc06_logout_success,
        "TC07": tc07_session_invalidated_after_logout,
        "TC08": tc08_back_button_after_logout,
        "TC09": tc09_relogin_after_logout,
    }
    to_run = selected_tcs if selected_tcs else list(_ALL_TCS.keys())
    results = {tc_id: _ALL_TCS[tc_id](driver, wait) for tc_id in to_run if tc_id in _ALL_TCS}

    _print_suite_result("SUITE 1.2 – ĐĂNG XUẤT", results)
    return results


# ──────────────────────────────────────────────────────────────
# Chạy trực tiếp: python logout.py
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from helpers import setup_driver
    from selenium.webdriver.support.ui import WebDriverWait

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)
    try:
        run_logout_suite(driver, wait)
    finally:
        try:
            input("\n⏸  Nhấn Enter để đóng trình duyệt...")
        except EOFError:
            pass
        driver.quit()
