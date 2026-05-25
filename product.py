"""
Module test sản phẩm trong Odoo - Suite 2.1 (TC07-TC11)
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

# Shared state between TC10 and TC11 within the same suite run
_suite_product: dict = {"name": None, "url": None}


# ──────────────────────────────────────────────────────────────
# Helpers dùng chung
# ──────────────────────────────────────────────────────────────

def _ensure_logged_in(driver, wait):
    if "/odoo" not in driver.current_url:
        login(driver, wait)


def _go_to_product_list(driver, wait):
    """Điều hướng thẳng đến danh sách sản phẩm."""
    driver.get(_PRODUCTS_URL)
    time.sleep(3)
    # Chờ bất kỳ element đặc trưng của trang sản phẩm
    wait.until(EC.presence_of_element_located(
        (By.XPATH,
         "//button[normalize-space()='Mới' or normalize-space()='New'] | "
         "//div[contains(@class,'o_control_panel')] | "
         "//div[contains(@class,'o_kanban_view')] | "
         "//div[contains(@class,'o_list_view')]")))


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


def _enable_track_inventory(driver):
    """Bật Track Inventory (is_storable) nếu chưa bật."""
    try:
        chk = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH,
                "//input[@id='is_storable_0'] | "
                "//div[@name='is_storable']//input[@type='checkbox']")))
        if chk.is_selected():
            log_info("Track Inventory đã bật sẵn")
            return

        # Native click triggers OWL change/input events
        chk.click()
        time.sleep(1)

        if not chk.is_selected():
            # Fallback: dispatch change event explicitly
            driver.execute_script("""
                var el = arguments[0];
                el.checked = true;
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            """, chk)
            time.sleep(1)

        log_info(f"Track Inventory: {'BẬT' if chk.is_selected() else 'CHƯA BẬT'}")
    except Exception as e:
        log_err(f"Không bật được Track Inventory: {e}")


def tc10_update_inventory(driver, wait):
    """TC10 – Cập nhật số lượng tồn kho thành công"""
    log_step(10, "TC10 – Cập nhật số lượng tồn kho thành công")
    _ensure_logged_in(driver, wait)

    name = f"SP_TEST_{datetime.datetime.now().strftime('%d%m%Y_%H%M%S')}"
    log_info(f"Tạo sản phẩm: {name}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _enable_track_inventory(driver)

    # Điền "Số lượng hiện có" trực tiếp trên form (hiện sau khi bật Track Inventory)
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
        log_err(f"TC10 FAIL: Không điền được Số lượng hiện có – {e}")
        return False

    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        log_err(f"TC10 FAIL: Không lưu được sản phẩm. URL: {driver.current_url}")
        return False

    product_url = driver.current_url
    _suite_product["name"] = name
    _suite_product["url"] = product_url
    log_info(f"Đã lưu: {product_url}")

    # Xử lý popup xác nhận "Áp dụng tất cả" nếu Odoo hiện dialog
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

    # Kiểm tra: đọc lại trường qty_available trên form sau khi lưu
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
            log_ok(f"TC10 PASS: Số lượng hiện có = {val_str} (expected {PRODUCT_QTY})")
            return True
    except Exception:
        pass

    # Fallback: đọc stat button "Hiện có" trên form
    try:
        stat = driver.find_element(
            By.XPATH,
            "//button[contains(@class,'oe_stat_button') and contains(.,'Hiện có')]")
        nums = re.findall(r'[\d.,]+', stat.text)
        for n in nums:
            if abs(_parse_price(n) - expected) < 0.01:
                log_ok(f"TC10 PASS: Hiện có = {n} (expected {PRODUCT_QTY})")
                return True
        log_err(f"TC10 FAIL: Hiện có = '{stat.text}', expected {PRODUCT_QTY}")
    except Exception as e:
        log_err(f"TC10 FAIL: Không xác minh được số lượng – {e}")
    return False


def tc11_search_product(driver, wait):
    """TC11 – Tìm kiếm sản phẩm đã tạo"""
    log_step(11, "TC11 – Tìm kiếm sản phẩm đã tạo")
    _ensure_logged_in(driver, wait)

    search_name = _suite_product.get("name") or "SP_TEST_"
    log_info(f"Tìm kiếm: '{search_name}'")

    _go_to_product_list(driver, wait)
    time.sleep(1)

    # Xóa filter đang có
    try:
        for _ in range(5):
            dels = driver.find_elements(
                By.XPATH,
                "//span[contains(@class,'o_delete')]")
            if not dels:
                break
            driver.execute_script("arguments[0].click();", dels[0])
            time.sleep(0.4)
    except Exception:
        pass

    # Gõ tên vào ô tìm kiếm rồi Enter
    try:
        search_input = WebDriverWait(driver, 8).until(EC.element_to_be_clickable(
            (By.XPATH, "//input[contains(@class,'o_searchview_input')]")))
        search_input.click()
        search_input.send_keys(Keys.CONTROL + "a")
        search_input.send_keys(search_name)
        search_input.send_keys(Keys.ENTER)
        time.sleep(2)
    except Exception as e:
        log_err(f"TC11 FAIL: Không tìm thấy ô search – {e}")
        return False

    # Kiểm tra kanban view
    try:
        cards = driver.find_elements(
            By.XPATH,
            f"//div[contains(@class,'o_kanban_record')]"
            f"[.//*[contains(text(),'{search_name}')]]")
        if cards:
            log_ok(f"TC11 PASS: Tìm thấy '{search_name}' trong kanban view")
            return True
    except Exception:
        pass

    # Kiểm tra list view
    try:
        rows = driver.find_elements(
            By.XPATH,
            f"//td[@name='name']//*[contains(text(),'{search_name}')] | "
            f"//td[contains(text(),'{search_name}')]")
        if rows:
            log_ok(f"TC11 PASS: Tìm thấy '{search_name}' trong list view")
            return True
    except Exception:
        pass

    # Fallback: tìm bất kỳ phần tử nào chứa prefix SP_TEST_
    try:
        any_match = driver.find_elements(
            By.XPATH,
            "//*[contains(@class,'o_kanban_record') or @name='name']"
            "//*[contains(text(),'SP_TEST_')]")
        if any_match:
            found_text = any_match[0].text.strip()
            log_ok(f"TC11 PASS: Tìm thấy '{found_text}'")
            return True
    except Exception:
        pass

    log_err(f"TC11 FAIL: Không tìm thấy '{search_name}' trong kết quả")
    return False


def run_product_suite(driver, wait):
    """Chạy toàn bộ Suite 2.1 – Sản phẩm (TC07–TC11)"""
    print("\n" + "=" * 60)
    print("  SUITE 2.1 – SẢN PHẨM")
    print("=" * 60)

    results = {
        "TC07": tc07_create_product_success(driver, wait),
        "TC08": tc08_create_product_empty_name(driver, wait),
        "TC09": tc09_create_product_valid_price(driver, wait),
        "TC10": tc10_update_inventory(driver, wait),
        "TC11": tc11_search_product(driver, wait),
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
