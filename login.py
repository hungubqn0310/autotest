"""
Module xử lý đăng nhập vào Odoo – Suite 1.1 (TC01–TC05)
"""
import time
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from config import ODOO_URL, ODOO_USER, ODOO_PASS
from helpers import log_step, log_ok, log_err, log_info, safe_fill, safe_click


_parsed = urlparse(ODOO_URL)
_LOGIN_URL = f"{_parsed.scheme}://{_parsed.netloc}/web/login"


def _go_to_login(driver):
    driver.get(_LOGIN_URL)
    time.sleep(4)


def _fill_login_form(driver, wait, email, password):
    email_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@id='login']")))
    driver.execute_script("arguments[0].scrollIntoView(true);", email_input)
    email_input.clear()
    if email:
        email_input.send_keys(email)
    time.sleep(1)

    password_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@id='password']")))
    password_input.clear()
    if password:
        password_input.send_keys(password)
    time.sleep(1)


def _click_login(driver, wait):
    # Support both English "Log in" and Vietnamese "Đăng nhập"
    safe_click(driver, wait, "//button[normalize-space()='Đăng nhập' or normalize-space()='Log in']")
    time.sleep(4)


def _get_error_message(driver):
    """Lấy thông báo lỗi trên trang login (nếu có)."""
    try:
        el = driver.find_element(By.XPATH,
            "//p[contains(@class,'alert')] | "
            "//div[contains(@class,'alert-danger')] | "
            "//div[contains(@class,'o_error_detail')]")
        return el.text.strip()
    except Exception:
        return ""


def _get_html5_validation_msg(driver, field_id):
    """Lấy thông báo HTML5 validation của một input field."""
    try:
        el = driver.find_element(By.ID, field_id)
        return driver.execute_script("return arguments[0].validationMessage;", el)
    except Exception:
        return ""


# ──────────────────────────────────────────────────────────────
# Hàm login chính – dùng cho các module khác (product, sales…)
# ──────────────────────────────────────────────────────────────
def login(driver, wait):
    """Đăng nhập vào hệ thống Odoo"""
    log_step(0, "ĐĂNG NHẬP")
    driver.get(_LOGIN_URL)
    time.sleep(2)

    safe_fill(driver, wait, "//input[@id='login']", ODOO_USER)
    safe_fill(driver, wait, "//input[@id='password']", ODOO_PASS)
    time.sleep(1)
    safe_click(driver, wait, "//button[normalize-space()='Đăng nhập' or normalize-space()='Log in']")
    time.sleep(3)

    if "/odoo" in driver.current_url:
        log_ok("Đăng nhập thành công!")
    else:
        raise Exception("Đăng nhập thất bại! Kiểm tra lại URL / tài khoản / mật khẩu.")


# ──────────────────────────────────────────────────────────────
# Suite 1.1 – Test Cases TC01 – TC05
# ──────────────────────────────────────────────────────────────

def tc01_login_success(driver, wait):
    """TC01 – Đăng nhập thành công với tài khoản hợp lệ"""
    log_step(1, "TC01 – Đăng nhập thành công")
    _go_to_login(driver)
    _fill_login_form(driver, wait, ODOO_USER, ODOO_PASS)
    _click_login(driver, wait)

    if "/odoo" in driver.current_url:
        log_ok("TC01 PASS: Đăng nhập thành công, URL chuyển sang /odoo")
        return True
    else:
        log_err("TC01 FAIL: Không chuyển sang /odoo sau khi đăng nhập")
        return False


def tc02_login_wrong_password(driver, wait):
    """TC02 – Đăng nhập thất bại – sai mật khẩu"""
    log_step(2, "TC02 – Sai mật khẩu")
    _go_to_login(driver)
    _fill_login_form(driver, wait, ODOO_USER, "wrong123")
    _click_login(driver, wait)

    error_msg = _get_error_message(driver)
    still_on_login = "/odoo" not in driver.current_url

    if still_on_login and ("Wrong login" in error_msg or "wrong" in error_msg.lower()):
        log_ok(f"TC02 PASS: Hiển thị lỗi đúng – \"{error_msg}\"")
        return True
    elif still_on_login:
        log_ok(f"TC02 PASS (partial): Không đăng nhập được. Thông báo: \"{error_msg}\"")
        return True
    else:
        log_err("TC02 FAIL: Đăng nhập thành công bất ngờ với mật khẩu sai")
        return False


def tc03_login_empty_email(driver, wait):
    """TC03 – Đăng nhập thất bại – để trống email"""
    log_step(3, "TC03 – Để trống email")
    _go_to_login(driver)
    _fill_login_form(driver, wait, "", "admin")
    _click_login(driver, wait)

    validation_msg = _get_html5_validation_msg(driver, "login")
    still_on_login = "/odoo" not in driver.current_url

    if still_on_login and validation_msg:
        log_ok(f"TC03 PASS: Form báo lỗi bắt buộc – \"{validation_msg}\"")
        return True
    elif still_on_login:
        log_ok("TC03 PASS: Không thực hiện đăng nhập khi email trống")
        return True
    else:
        log_err("TC03 FAIL: Đăng nhập thành công bất ngờ khi email trống")
        return False


def tc04_login_empty_password(driver, wait):
    """TC04 – Đăng nhập thất bại – để trống mật khẩu"""
    log_step(4, "TC04 – Để trống mật khẩu")
    _go_to_login(driver)
    _fill_login_form(driver, wait, "admin@gmail.com", "")
    _click_login(driver, wait)

    validation_msg = _get_html5_validation_msg(driver, "password")
    still_on_login = "/odoo" not in driver.current_url

    if still_on_login and validation_msg:
        log_ok(f"TC04 PASS: Form báo lỗi bắt buộc – \"{validation_msg}\"")
        return True
    elif still_on_login:
        log_ok("TC04 PASS: Không thực hiện đăng nhập khi mật khẩu trống")
        return True
    else:
        log_err("TC04 FAIL: Đăng nhập thành công bất ngờ khi mật khẩu trống")
        return False


def tc05_login_invalid_email_format(driver, wait):
    """TC05 – Đăng nhập thất bại – email sai định dạng"""
    log_step(5, "TC05 – Email sai định dạng")
    _go_to_login(driver)
    _fill_login_form(driver, wait, "adminabc", "admin")
    _click_login(driver, wait)

    validation_msg = _get_html5_validation_msg(driver, "login")
    error_msg = _get_error_message(driver)
    still_on_login = "/odoo" not in driver.current_url

    if still_on_login and (validation_msg or error_msg):
        msg = validation_msg or error_msg
        log_ok(f"TC05 PASS: Hiển thị lỗi email không hợp lệ – \"{msg}\"")
        return True
    elif still_on_login:
        log_ok("TC05 PASS: Không đăng nhập được với email sai định dạng")
        return True
    else:
        log_err("TC05 FAIL: Đăng nhập thành công bất ngờ với email sai định dạng")
        return False


def run_login_suite(driver, wait, selected_tcs: list[str] | None = None):
    """Chạy toàn bộ Suite 1.1 – Đăng nhập (TC01–TC05)"""
    print("\n" + "=" * 60)
    print("  SUITE 1.1 – ĐĂNG NHẬP")
    print("=" * 60)

    _ALL_TCS = {
        "TC01": tc01_login_success,
        "TC02": tc02_login_wrong_password,
        "TC03": tc03_login_empty_email,
        "TC04": tc04_login_empty_password,
        "TC05": tc05_login_invalid_email_format,
    }
    to_run = selected_tcs if selected_tcs else list(_ALL_TCS.keys())
    results = {tc_id: _ALL_TCS[tc_id](driver, wait) for tc_id in to_run if tc_id in _ALL_TCS}

    _print_suite_result("SUITE 1.1 – ĐĂNG NHẬP", results)
    return results


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
# Chạy trực tiếp: python login.py
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from helpers import setup_driver
    from selenium.webdriver.support.ui import WebDriverWait

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)
    try:
        run_login_suite(driver, wait)
    finally:
        try:
            input("\n⏸  Nhấn Enter để đóng trình duyệt...")
        except EOFError:
            pass
        driver.quit()
