"""
Module test sản phẩm trong Odoo – Suite 2.1 (TC07–TC09)
"""
import re
import time
import datetime
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from config import ODOO_URL, PRODUCT_NAME, PRODUCT_PRICE, PRODUCT_QTY
from helpers import (log_step, log_info, log_ok, log_err,
                     safe_click, wait_for_toast_gone)
from login import login

_parsed = urlparse(ODOO_URL)
_BASE_URL = f"{_parsed.scheme}://{_parsed.netloc}"
_PRODUCTS_URL = f"{_BASE_URL}/odoo/inventory/products"


# ──────────────────────────────────────────────────────────────
# Helpers dùng chung
# ──────────────────────────────────────────────────────────────

def _ensure_logged_in(driver, wait):
    if "/odoo" not in driver.current_url:
        login(driver, wait)


def _go_to_product_list(driver, wait):
    """Điều hướng thẳng đến danh sách sản phẩm."""
    driver.get(_PRODUCTS_URL)
    time.sleep(2)
    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//button[normalize-space()='Mới' or normalize-space()='New']")))


def _click_new(driver, wait):
    safe_click(driver, wait,
        "//button[normalize-space()='Mới' or normalize-space()='New']")
    time.sleep(2)


def _fill_name(driver, wait, name):
    name_field = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//textarea[@id='name_0'] | //input[@id='name_0']")))
    name_field.click()
    name_field.send_keys(Keys.CONTROL + "a")
    name_field.send_keys(Keys.DELETE)
    if name:
        name_field.send_keys(name)
    time.sleep(0.5)


def _fill_price(driver, wait, price):
    try:
        price_field = wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//div[@name='list_price']//input | "
             "//input[@name='list_price'] | "
             "//label[contains(.,'Giá bán') or contains(.,'Sales Price')]"
             "/..//input")))
        price_field.click()
        price_field.send_keys(Keys.CONTROL + "a")
        price_field.send_keys(price)
    except Exception as e:
        log_err(f"Không điền được giá: {e}")
    time.sleep(0.5)


def _click_save(driver, wait):
    try:
        save_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//button[contains(@class,'o_form_button_save')] | "
             "//i[contains(@class,'fa-cloud-upload')]/parent::button | "
             "(//i[@class='fa fa-cloud-upload fa-fw'])[1]/..")))
        driver.execute_script("arguments[0].click();", save_btn)
    except Exception:
        # Fallback: click icon trực tiếp
        try:
            icon = driver.find_element(
                By.XPATH, "(//i[@class='fa fa-cloud-upload fa-fw'])[1]")
            driver.execute_script("arguments[0].click();", icon)
        except Exception:
            pass
    time.sleep(2)
    wait_for_toast_gone(wait)


def _is_saved(driver):
    """Trả về True nếu URL chứa ID số (sản phẩm đã lưu)."""
    return bool(re.search(r'/products/\d+', driver.current_url))


def _get_breadcrumb_name(driver):
    try:
        el = driver.find_element(
            By.XPATH,
            "//ol[contains(@class,'breadcrumb')]//li[last()]/span | "
            "//span[contains(@class,'min-w-0') and contains(@class,'text-truncate')]")
        return el.text.strip()
    except Exception:
        return ""


def _has_name_error(driver):
    """Kiểm tra trường tên bị đánh dấu lỗi bắt buộc."""
    try:
        driver.find_element(
            By.XPATH,
            "//div[@name='name'][contains(@class,'o_field_invalid')] | "
            "//textarea[@id='name_0'][contains(@class,'o_field_invalid')] | "
            "//input[@id='name_0'][contains(@class,'o_field_invalid')]")
        return True
    except Exception:
        pass
    try:
        driver.find_element(
            By.XPATH,
            "//div[contains(@class,'o_notification') and contains(@class,'danger')] | "
            "//div[contains(@class,'o_notification_warning')]")
        return True
    except Exception:
        return False


def _parse_price(val: str) -> float:
    """Chuẩn hoá chuỗi giá về float (hỗ trợ cả định dạng VN/EU: 10.000,00)."""
    val = val.strip()
    if ',' in val and '.' in val:
        # Xác định ký tự thập phân dựa theo vị trí xuất hiện sau cùng
        if val.rfind(',') > val.rfind('.'):
            # EU: 10.000,00 → bỏ dấu chấm, đổi phẩy thành chấm
            val = val.replace('.', '').replace(',', '.')
        else:
            # US: 10,000.00 → bỏ dấu phẩy
            val = val.replace(',', '')
    elif ',' in val:
        # Chỉ có phẩy: nếu phần sau phẩy ≤ 2 chữ số → thập phân
        parts = val.split(',')
        if len(parts[-1]) <= 2:
            val = val.replace(',', '.')
        else:
            val = val.replace(',', '')
    cleaned = re.sub(r'[^\d.]', '', val)
    try:
        return float(cleaned)
    except ValueError:
        return -1.0


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
# TC07 – TC09
# ──────────────────────────────────────────────────────────────

def tc07_create_product_success(driver, wait):
    """TC07 – Tạo sản phẩm mới thành công"""
    log_step(7, "TC07 – Tạo sản phẩm mới thành công")
    _ensure_logged_in(driver, wait)

    name = f"SP_TEST_{datetime.datetime.now().strftime('%d%m%Y_%H%M%S')}"
    log_info(f"Tên: {name} | Giá: {PRODUCT_PRICE}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if _is_saved(driver):
        breadcrumb = _get_breadcrumb_name(driver)
        log_ok(f"TC07 PASS: Lưu thành công. URL: {driver.current_url} | Breadcrumb: '{breadcrumb}'")
        return True
    else:
        log_err(f"TC07 FAIL: Không lưu được sản phẩm. URL: {driver.current_url}")
        return False


def tc08_create_product_empty_name(driver, wait):
    """TC08 – Tạo sản phẩm – để trống tên"""
    log_step(8, "TC08 – Tạo sản phẩm – để trống tên")
    _ensure_logged_in(driver, wait)

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, "")   # Không nhập tên
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        if _has_name_error(driver):
            log_ok("TC08 PASS: Hệ thống báo lỗi trường tên bắt buộc, không lưu được")
        else:
            log_ok("TC08 PASS: Không lưu được sản phẩm khi tên trống (URL không chứa ID)")
        return True
    else:
        log_err(f"TC08 FAIL: Lưu được sản phẩm dù tên trống. URL: {driver.current_url}")
        return False


def tc09_create_product_valid_price(driver, wait):
    """TC09 – Tạo sản phẩm – điền giá bán hợp lệ"""
    log_step(9, "TC09 – Tạo sản phẩm – điền giá bán hợp lệ")
    _ensure_logged_in(driver, wait)

    name = f"SP_TEST_{datetime.datetime.now().strftime('%d%m%Y_%H%M%S')}"
    log_info(f"Tên: {name} | Giá: {PRODUCT_PRICE}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        log_err(f"TC09 FAIL: Không lưu được sản phẩm. URL: {driver.current_url}")
        return False

    # Kiểm tra giá hiển thị đúng sau khi lưu
    try:
        price_el = driver.find_element(
            By.XPATH,
            "//div[@name='list_price']//input | //input[@name='list_price']")
        displayed = price_el.get_attribute("value") or ""
        displayed_val = _parse_price(displayed)
        expected_val = _parse_price(PRODUCT_PRICE)

        if abs(displayed_val - expected_val) < 0.01:
            log_ok(f"TC09 PASS: Giá bán lưu đúng = {displayed} (expected {PRODUCT_PRICE})")
            return True
        else:
            log_err(f"TC09 FAIL: Giá hiển thị '{displayed}' ≠ expected '{PRODUCT_PRICE}'")
            return False
    except Exception as e:
        log_err(f"TC09 FAIL: Không đọc được giá sau khi lưu – {e}")
        return False


def run_product_suite(driver, wait):
    """Chạy toàn bộ Suite 2.1 – Sản phẩm (TC07–TC09)"""
    print("\n" + "=" * 60)
    print("  SUITE 2.1 – SẢN PHẨM")
    print("=" * 60)

    results = {
        "TC07": tc07_create_product_success(driver, wait),
        "TC08": tc08_create_product_empty_name(driver, wait),
        "TC09": tc09_create_product_valid_price(driver, wait),
    }

    _print_suite_result("SUITE 2.1 – SẢN PHẨM", results)
    return results


# ──────────────────────────────────────────────────────────────
# Hàm tạo sản phẩm cũ – dùng bởi main.py (automation flow)
# ──────────────────────────────────────────────────────────────

def create_product(driver, wait):
    """Tạo sản phẩm mới trong Odoo (dùng cho automation flow)."""
    log_step(1, f"TẠO SẢN PHẨM: {PRODUCT_NAME}")

    log_info("Mở menu Sales...")
    safe_click(driver, wait, "//div[contains(text(),'Sales')]")
    time.sleep(1)

    log_info("Mở Products...")
    safe_click(driver, wait, "(//span[contains(text(),'Products')])[1]")
    safe_click(driver, wait, "//a[normalize-space()='Products']")
    time.sleep(2)

    log_info("Nhấn nút Tạo mới...")
    safe_click(driver, wait,
        "//button[contains(.,'Mới') or contains(.,'New') or "
        "contains(.,'Tạo') or contains(.,'Create')]")
    time.sleep(2)

    log_info(f"Điền tên sản phẩm: {PRODUCT_NAME}")
    name_field = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//textarea[@id='name_0'] | //input[@id='name_0']")))
    name_field.send_keys(Keys.CONTROL + "a")
    name_field.send_keys(PRODUCT_NAME)
    time.sleep(0.5)

    log_info(f"Điền giá bán: {PRODUCT_PRICE}")
    try:
        price_field = driver.find_element(By.XPATH,
            "//div[@name='list_price']//input | //input[@name='list_price'] | "
            "//label[contains(.,'Giá bán') or contains(.,'Sales Price')]/..//input")
        price_field.click()
        price_field.send_keys(Keys.CONTROL + "a")
        price_field.send_keys(PRODUCT_PRICE)
    except Exception as e:
        log_err(f"Không điền được giá: {e}")
    time.sleep(0.5)

    log_info("Lưu sản phẩm...")
    try:
        save_btn = driver.find_element(
            By.XPATH, "(//i[@class='fa fa-cloud-upload fa-fw'])[1]")
        driver.execute_script("arguments[0].click();", save_btn)
    except Exception:
        pass
    time.sleep(2)
    wait_for_toast_gone(wait)

    wait.until(lambda d: d.find_element(
        By.XPATH,
        "(//span[contains(@class,'min-w-0') and contains(@class,'text-truncate')])[1]"
    ).text.strip() != "New")
    log_ok(f"Tạo sản phẩm '{PRODUCT_NAME}' thành công! URL: {driver.current_url}")

    _update_inventory(driver, wait)


def _update_inventory(driver, wait):
    """Cập nhật số lượng tồn kho cho sản phẩm."""
    log_info(f"Cập nhật số lượng tồn kho: {PRODUCT_QTY}...")
    try:
        update_qty_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//button[contains(.,'Cập nhật số lượng') or contains(.,'Update Quantity') "
            "or contains(.,'Số lượng') and contains(@class,'btn')]")))
        driver.execute_script("arguments[0].click();", update_qty_btn)
        time.sleep(2)

        try:
            create_quant_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
                "//button[contains(.,'Mới') or contains(.,'New') or "
                "contains(.,'Tạo') or contains(.,'Create')]"
                "[not(contains(@class,'o_invisible'))]")))
            driver.execute_script("arguments[0].click();", create_quant_btn)
            time.sleep(1.5)
        except Exception:
            pass

        qty_input = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//div[@name='inventory_quantity']//input | "
            "//td[@name='inventory_quantity']//input | "
            "//input[@id='inventory_quantity_0'] | "
            "//div[@name='quantity']//input | "
            "//td[@name='quantity']//input")))
        qty_input.click()
        qty_input.send_keys(Keys.CONTROL + "a")
        qty_input.send_keys(PRODUCT_QTY)
        time.sleep(0.5)

        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//button[contains(.,'Áp dụng tất cả') or contains(.,'Apply All') "
            "or contains(.,'Áp dụng') or contains(.,'Apply')]")))
        driver.execute_script("arguments[0].click();", apply_btn)
        time.sleep(1.5)

        try:
            confirm_btn = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//div[@class='modal-footer']//button[contains(.,'OK') "
                    "or contains(.,'Áp dụng') or contains(.,'Apply')]")))
            confirm_btn.click()
            time.sleep(1)
        except Exception:
            pass

        wait_for_toast_gone(wait)
        log_ok(f"Đã cập nhật số lượng tồn kho: {PRODUCT_QTY} đơn vị.")

    except Exception as e:
        log_err(f"Không cập nhật được số lượng: {e}")


# ──────────────────────────────────────────────────────────────
# Chạy trực tiếp: python product.py
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from helpers import setup_driver

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)
    try:
        login(driver, wait)
        run_product_suite(driver, wait)
    finally:
        try:
            input("\n⏸  Nhấn Enter để đóng trình duyệt...")
        except EOFError:
            pass
        driver.quit()
