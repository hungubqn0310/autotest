"""
Các hàm tiện ích cho Odoo Automation
"""
import os
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


def log_ok(msg):
    """In thông báo thành công"""
    print(f"  ✅ {msg}")


def log_info(msg):
    """In thông báo thông tin"""
    print(f"  📌 {msg}")


def log_err(msg):
    """In thông báo lỗi"""
    print(f"  ❌ {msg}")


def log_step(step, title):
    """In tiêu đề bước thực hiện"""
    print(f"\n{'='*60}")
    print(f"  BƯỚC {step}: {title}")
    print(f"{'='*60}")


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
