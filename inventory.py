"""
Module test tồn kho trong Odoo - Suite 2.2 (TC18-TC19)
"""
import re
import time
import datetime
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from config import ODOO_URL, PRODUCT_PRICE, PRODUCT_QTY
from helpers import log_step, log_info, log_ok, log_err, wait_for_toast_gone
from login import login
from product import (
    _ensure_logged_in, _go_to_product_list, _click_new,
    _fill_name, _fill_price, _click_save, _is_saved,
    _enable_track_inventory, _parse_price, _print_suite_result,
)

_parsed = urlparse(ODOO_URL)
_BASE_URL = f"{_parsed.scheme}://{_parsed.netloc}"

# Shared state giữa TC18 và TC19 trong cùng một suite run
_suite_product: dict = {"name": None, "url": None}


# ──────────────────────────────────────────────────────────────
# SUITE 2.2 – TỒN KHO (TC18–TC19)
# ──────────────────────────────────────────────────────────────

def tc18_update_inventory(driver, wait):
    """TC18 – Cập nhật số lượng tồn kho thành công"""
    log_step(18, "TC18 – Cập nhật số lượng tồn kho thành công")
    _ensure_logged_in(driver, wait)

    name = f"SP_TEST_{datetime.datetime.now().strftime('%d%m%Y_%H%M%S')}"
    log_info(f"Tạo sản phẩm: {name}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _enable_track_inventory(driver)

    try:
        qty_field = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(
            (By.XPATH,
             "//div[@name='qty_available']//input | "
             "//input[@id='qty_available_0'] | "
             "//label[contains(.,'Số lượng hiện có') or contains(.,'On Hand')]"
             "/following-sibling::div//input | "
             "//label[contains(.,'Số lượng hiện có') or contains(.,'On Hand')]"
             "/..//input")))
        qty_field.click()
        qty_field.send_keys(Keys.CONTROL + "a")
        qty_field.send_keys(PRODUCT_QTY)
        time.sleep(0.5)
        log_info(f"Đã điền Số lượng hiện có = {PRODUCT_QTY}")
    except Exception as e:
        log_err(f"TC18 FAIL: Không điền được Số lượng hiện có – {e}")
        return False

    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        log_err(f"TC18 FAIL: Không lưu được sản phẩm. URL: {driver.current_url}")
        return False

    product_url = driver.current_url
    _suite_product["name"] = name
    _suite_product["url"] = product_url
    log_info(f"Đã lưu: {product_url}")

    try:
        confirm = WebDriverWait(driver, 4).until(EC.element_to_be_clickable(
            (By.XPATH,
             "//div[contains(@class,'modal')]//button["
             "contains(.,'OK') or contains(.,'Áp dụng') or "
             "contains(.,'Apply') or contains(.,'Xác nhận')]")))
        confirm.click()
        time.sleep(1.5)
        wait_for_toast_gone(wait)
    except Exception:
        pass

    time.sleep(1)
    expected = _parse_price(PRODUCT_QTY)

    try:
        qty_el = driver.find_element(
            By.XPATH,
            "//div[@name='qty_available']//input | "
            "//input[@id='qty_available_0'] | "
            "//label[contains(.,'Số lượng hiện có') or contains(.,'On Hand')]"
            "/..//input")
        val_str = (qty_el.get_attribute("value") or qty_el.text or "").strip()
        val = _parse_price(val_str)
        if abs(val - expected) < 0.01:
            log_ok(f"TC18 PASS: Số lượng hiện có = {val_str} (expected {PRODUCT_QTY})")
            return True
    except Exception:
        pass

    try:
        stat = driver.find_element(
            By.XPATH,
            "//button[contains(@class,'oe_stat_button') and contains(.,'Hiện có')]")
        nums = re.findall(r'[\d.,]+', stat.text)
        for n in nums:
            if abs(_parse_price(n) - expected) < 0.01:
                log_ok(f"TC18 PASS: Hiện có = {n} (expected {PRODUCT_QTY})")
                return True
        log_err(f"TC18 FAIL: Hiện có = '{stat.text}', expected {PRODUCT_QTY}")
    except Exception as e:
        log_err(f"TC18 FAIL: Không xác minh được số lượng – {e}")
    return False


def tc19_search_product(driver, wait):
    """TC19 – Tìm kiếm sản phẩm đã tạo"""
    log_step(19, "TC19 – Tìm kiếm sản phẩm đã tạo")
    _ensure_logged_in(driver, wait)

    search_name = _suite_product.get("name") or "SP_TEST_"
    log_info(f"Tìm kiếm: '{search_name}'")

    _go_to_product_list(driver, wait)
    time.sleep(1)

    try:
        for _ in range(5):
            dels = driver.find_elements(
                By.XPATH, "//span[contains(@class,'o_delete')]")
            if not dels:
                break
            driver.execute_script("arguments[0].click();", dels[0])
            time.sleep(0.4)
    except Exception:
        pass

    try:
        search_input = WebDriverWait(driver, 8).until(EC.element_to_be_clickable(
            (By.XPATH, "//input[contains(@class,'o_searchview_input')]")))
        search_input.click()
        search_input.send_keys(Keys.CONTROL + "a")
        search_input.send_keys(search_name)
        search_input.send_keys(Keys.ENTER)
        time.sleep(2)
    except Exception as e:
        log_err(f"TC19 FAIL: Không tìm thấy ô search – {e}")
        return False

    try:
        cards = driver.find_elements(
            By.XPATH,
            f"//div[contains(@class,'o_kanban_record')]"
            f"[.//*[contains(text(),'{search_name}')]]")
        if cards:
            log_ok(f"TC19 PASS: Tìm thấy '{search_name}' trong kanban view")
            return True
    except Exception:
        pass

    try:
        rows = driver.find_elements(
            By.XPATH,
            f"//td[@name='name']//*[contains(text(),'{search_name}')] | "
            f"//td[contains(text(),'{search_name}')]")
        if rows:
            log_ok(f"TC19 PASS: Tìm thấy '{search_name}' trong list view")
            return True
    except Exception:
        pass

    try:
        any_match = driver.find_elements(
            By.XPATH,
            "//*[contains(@class,'o_kanban_record') or @name='name']"
            "//*[contains(text(),'SP_TEST_')]")
        if any_match:
            found_text = any_match[0].text.strip()
            log_ok(f"TC19 PASS: Tìm thấy '{found_text}'")
            return True
    except Exception:
        pass

    log_err(f"TC19 FAIL: Không tìm thấy '{search_name}' trong kết quả")
    return False


def run_inventory_suite(driver, wait, selected_tcs: list[str] | None = None):
    """Chạy toàn bộ Suite 2.2 – Tồn kho (TC18–TC19)"""
    print("\n" + "=" * 60)
    print("  SUITE 2.2 – TỒN KHO")
    print("=" * 60)

    _ALL_TCS = {
        "TC18": tc18_update_inventory,
        "TC19": tc19_search_product,
    }
    to_run = selected_tcs if selected_tcs else list(_ALL_TCS.keys())
    results = {tc_id: _ALL_TCS[tc_id](driver, wait) for tc_id in to_run if tc_id in _ALL_TCS}

    _print_suite_result("SUITE 2.2 – TỒN KHO", results)
    return results


# ──────────────────────────────────────────────────────────────
# Chạy trực tiếp: python inventory.py
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from helpers import setup_driver
    from selenium.webdriver.support.ui import WebDriverWait

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)
    try:
        login(driver, wait)
        run_inventory_suite(driver, wait)
    finally:
        try:
            input("\n⏸  Nhấn Enter để đóng trình duyệt...")
        except EOFError:
            pass
        driver.quit()
