"""
Module test sản phẩm trong Odoo - Suite 2.1 (TC10-TC17)
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
_PRODUCTS_URLS = [
    f"{_BASE_URL}/odoo/inventory/products",
    f"{_BASE_URL}/odoo/sales/products",
    f"{_BASE_URL}/web#action=product.product_template_action_all",
]
_PRODUCTS_URL = _PRODUCTS_URLS[0]


# ──────────────────────────────────────────────────────────────
# Helpers dùng chung
# ──────────────────────────────────────────────────────────────

def _ensure_logged_in(driver, wait):
    if "/odoo" not in driver.current_url:
        login(driver, wait)


_PRODUCT_PAGE_XPATH = (
    "//button[normalize-space()='Mới' or normalize-space()='New'] | "
    "//div[contains(@class,'o_control_panel')] | "
    "//div[contains(@class,'o_kanban_view')] | "
    "//div[contains(@class,'o_list_view')] | "
    "//div[contains(@class,'o_view_controller')] | "
    "//div[contains(@class,'o_action_manager')]"
)


def _go_to_product_list(driver, wait):
    """Điều hướng đến danh sách sản phẩm, thử nhiều URL."""
    for url in _PRODUCTS_URLS:
        driver.get(url)
        time.sleep(4)
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, _PRODUCT_PAGE_XPATH)))
            log_info(f"Đã vào trang sản phẩm: {driver.current_url}")
            return
        except Exception:
            log_info(f"URL {url} không phản hồi, thử tiếp...")
    raise Exception(f"Không thể điều hướng đến trang sản phẩm. URL hiện tại: {driver.current_url}")


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
        try:
            icon = driver.find_element(
                By.XPATH, "(//i[@class='fa fa-cloud-upload fa-fw'])[1]")
            driver.execute_script("arguments[0].click();", icon)
        except Exception:
            pass
    time.sleep(2)
    wait_for_toast_gone(wait)


def _is_saved(driver):
    """Trả về True nếu URL chứa ID số (sản phẩm đã lưu).
    Hỗ trợ cả /products/22 và /action-453/22 (Odoo 17+).
    """
    return bool(re.search(r'/(products|action-\d+)/\d+', driver.current_url))


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
        if val.rfind(',') > val.rfind('.'):
            val = val.replace('.', '').replace(',', '.')
        else:
            val = val.replace(',', '')
    elif ',' in val:
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

        chk.click()
        time.sleep(1)

        if not chk.is_selected():
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
# SUITE 2.1 – SẢN PHẨM (TC10–TC17)
# ──────────────────────────────────────────────────────────────

def tc10_create_product_success(driver, wait):
    """TC10 – Tạo sản phẩm mới thành công"""
    log_step(10, "TC10 – Tạo sản phẩm mới thành công")
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
        log_ok(f"TC10 PASS: Lưu thành công. URL: {driver.current_url} | Breadcrumb: '{breadcrumb}'")
        return True
    else:
        log_err(f"TC10 FAIL: Không lưu được sản phẩm. URL: {driver.current_url}")
        return False


def tc11_create_product_empty_name(driver, wait):
    """TC11 – Tạo sản phẩm – để trống tên"""
    log_step(11, "TC11 – Tạo sản phẩm – để trống tên")
    _ensure_logged_in(driver, wait)

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, "")   # Không nhập tên
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        if _has_name_error(driver):
            log_ok("TC11 PASS: Hệ thống báo lỗi trường tên bắt buộc, không lưu được")
        else:
            log_ok("TC11 PASS: Không lưu được sản phẩm khi tên trống (URL không chứa ID)")
        return True
    else:
        log_err(f"TC11 FAIL: Lưu được sản phẩm dù tên trống. URL: {driver.current_url}")
        return False


def tc12_create_product_valid_price(driver, wait):
    """TC12 – Tạo sản phẩm – điền giá bán hợp lệ"""
    log_step(12, "TC12 – Tạo sản phẩm – điền giá bán hợp lệ")
    _ensure_logged_in(driver, wait)

    name = f"SP_TEST_{datetime.datetime.now().strftime('%d%m%Y_%H%M%S')}"
    log_info(f"Tên: {name} | Giá: {PRODUCT_PRICE}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        log_err(f"TC12 FAIL: Không lưu được sản phẩm. URL: {driver.current_url}")
        return False

    try:
        price_el = driver.find_element(
            By.XPATH,
            "//div[@name='list_price']//input | //input[@name='list_price']")
        displayed = price_el.get_attribute("value") or ""
        displayed_val = _parse_price(displayed)
        expected_val = _parse_price(PRODUCT_PRICE)

        if abs(displayed_val - expected_val) < 0.01:
            log_ok(f"TC12 PASS: Giá bán lưu đúng = {displayed} (expected {PRODUCT_PRICE})")
            return True
        else:
            log_err(f"TC12 FAIL: Giá hiển thị '{displayed}' ≠ expected '{PRODUCT_PRICE}'")
            return False
    except Exception as e:
        log_err(f"TC12 FAIL: Không đọc được giá sau khi lưu – {e}")
        return False


def tc13_create_product_zero_price(driver, wait):
    """TC13 – Tạo sản phẩm – nhập giá bằng 0"""
    log_step(13, "TC13 – Tạo sản phẩm – nhập giá bằng 0")
    _ensure_logged_in(driver, wait)

    name = "SP_TEST_FREE"
    log_info(f"Tên: {name} | Giá: 0")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, "0")
    _click_save(driver, wait)

    if _is_saved(driver):
        log_ok(f"TC13 PASS: Lưu sản phẩm với giá 0 thành công. URL: {driver.current_url}")
        return True

    try:
        driver.find_element(By.XPATH,
            "//div[contains(@class,'o_notification_warning')] | "
            "//div[contains(@class,'o_notification') and contains(@class,'warning')]")
        log_ok("TC13 PASS: Hệ thống hiển thị cảnh báo khi giá = 0 (theo rule hệ thống)")
        return True
    except Exception:
        pass

    log_err(f"TC13 FAIL: Không lưu được và không có cảnh báo. URL: {driver.current_url}")
    return False


def tc14_create_product_special_chars(driver, wait):
    """TC14 – Tạo sản phẩm – nhập ký tự đặc biệt vào tên"""
    log_step(14, "TC14 – Tạo sản phẩm – nhập ký tự đặc biệt vào tên")
    _ensure_logged_in(driver, wait)

    name = "SP_@#$%"
    log_info(f"Tên: {name} | Giá: {PRODUCT_PRICE}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        log_err(f"TC14 FAIL: Không lưu được sản phẩm tên đặc biệt. URL: {driver.current_url}")
        return False

    breadcrumb = _get_breadcrumb_name(driver)
    if any(c in breadcrumb for c in ["@", "#", "$", "%", "SP_"]):
        log_ok(f"TC14 PASS: Lưu thành công, tên hiển thị đúng: '{breadcrumb}'")
        return True

    log_ok(f"TC14 PASS: Lưu thành công (breadcrumb: '{breadcrumb}'). URL: {driver.current_url}")
    return True


def tc15_create_product_duplicate_name(driver, wait):
    """TC15 – Tạo sản phẩm – nhập tên trùng"""
    log_step(15, "TC15 – Tạo sản phẩm – nhập tên trùng")
    _ensure_logged_in(driver, wait)

    name = "SP_TEST_DUPLICATE"
    log_info(f"Tên: {name} | Giá: {PRODUCT_PRICE}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        log_err(f"TC15 FAIL: Không tạo được sản phẩm lần đầu. URL: {driver.current_url}")
        return False

    log_info("Tạo lần 2 với tên trùng...")
    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if _is_saved(driver):
        log_ok(f"TC15 PASS: Hệ thống cho phép lưu tên trùng (theo rule Odoo). URL: {driver.current_url}")
        return True

    try:
        driver.find_element(By.XPATH,
            "//div[contains(@class,'o_notification')] | "
            "//div[contains(@class,'alert')]")
        log_ok("TC15 PASS: Hệ thống hiển thị cảnh báo trùng tên")
        return True
    except Exception:
        pass

    log_err(f"TC15 FAIL: Không lưu được và không có cảnh báo. URL: {driver.current_url}")
    return False


def tc16_refresh_after_save(driver, wait):
    """TC16 – Kiểm tra refresh sau khi lưu"""
    log_step(16, "TC16 – Kiểm tra refresh sau khi lưu")
    _ensure_logged_in(driver, wait)

    name = "SP_REFRESH"
    log_info(f"Tên: {name} | Giá: {PRODUCT_PRICE}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        log_err(f"TC16 FAIL: Không lưu được sản phẩm trước khi refresh. URL: {driver.current_url}")
        return False

    log_info(f"Đã lưu: {driver.current_url}. Refresh trang...")
    driver.refresh()
    time.sleep(3)
    wait_for_toast_gone(wait)

    if not _is_saved(driver):
        log_err(f"TC16 FAIL: Sau khi refresh, URL không còn ID. URL: {driver.current_url}")
        return False

    try:
        name_el = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//textarea[@id='name_0'] | //input[@id='name_0']")))
        displayed_name = (name_el.get_attribute("value") or name_el.text or "").strip()
        if name in displayed_name or displayed_name.startswith("SP_REFRESH"):
            log_ok(f"TC16 PASS: Dữ liệu vẫn còn sau refresh. Tên: '{displayed_name}'")
            return True
        log_err(f"TC16 FAIL: Tên sau refresh '{displayed_name}' ≠ '{name}'")
        return False
    except Exception as e:
        if _is_saved(driver):
            log_ok(f"TC16 PASS: Record vẫn còn sau refresh. URL: {driver.current_url}")
            return True
        log_err(f"TC16 FAIL: Không xác minh được dữ liệu sau refresh – {e}")
        return False


def tc17_search_product_after_create(driver, wait):
    """TC17 – Kiểm tra tìm kiếm sản phẩm sau khi tạo"""
    log_step(17, "TC17 – Kiểm tra tìm kiếm sản phẩm sau khi tạo")
    _ensure_logged_in(driver, wait)

    name = "SP_SEARCH"
    log_info(f"Tạo sản phẩm: {name}")

    _go_to_product_list(driver, wait)
    _click_new(driver, wait)
    _fill_name(driver, wait, name)
    _fill_price(driver, wait, PRODUCT_PRICE)
    _click_save(driver, wait)

    if not _is_saved(driver):
        log_err(f"TC17 FAIL: Không lưu được sản phẩm để tìm kiếm. URL: {driver.current_url}")
        return False

    log_info("Đã lưu, quay lại danh sách để tìm kiếm...")
    _go_to_product_list(driver, wait)
    time.sleep(1.5)

    # Xóa filter đang có
    try:
        for _ in range(5):
            dels = driver.find_elements(By.XPATH, "//span[contains(@class,'o_delete')]")
            if not dels:
                break
            driver.execute_script("arguments[0].click();", dels[0])
            time.sleep(0.4)
    except Exception:
        pass

    # Gõ vào ô search
    try:
        search_input = WebDriverWait(driver, 8).until(EC.element_to_be_clickable(
            (By.XPATH, "//input[contains(@class,'o_searchview_input')]")))
        search_input.click()
        search_input.send_keys(Keys.CONTROL + "a")
        search_input.send_keys(name)
        time.sleep(1)  # Chờ dropdown Odoo 17 xuất hiện

        # Odoo 17: chọn option "Name" trong dropdown nếu có
        try:
            name_option = driver.find_element(By.XPATH,
                "//div[contains(@class,'o_searchview_autocomplete')]"
                "//li[contains(.,'Name') or contains(.,'Tên') or contains(.,'Product')]"
                "[1]")
            name_option.click()
            time.sleep(1.5)
        except Exception:
            # Không có dropdown → nhấn Enter
            search_input.send_keys(Keys.ENTER)
            time.sleep(2)
    except Exception as e:
        log_err(f"TC17 FAIL: Không tìm thấy ô search – {e}")
        return False

    # Kiểm tra kết quả — kanban view
    try:
        cards = driver.find_elements(By.XPATH,
            f"//div[contains(@class,'o_kanban_record')][.//*[contains(text(),'{name}')]]")
        if cards:
            log_ok(f"TC17 PASS: Tìm thấy '{name}' trong kanban view")
            return True
    except Exception:
        pass

    # Kiểm tra kết quả — list view
    try:
        rows = driver.find_elements(By.XPATH,
            f"//td[@name='name']//*[contains(text(),'{name}')] | "
            f"//td[contains(text(),'{name}')]")
        if rows:
            log_ok(f"TC17 PASS: Tìm thấy '{name}' trong list view")
            return True
    except Exception:
        pass

    # Fallback rộng: bất kỳ element nào chứa text SP_SEARCH trên trang
    try:
        any_match = driver.find_elements(By.XPATH,
            f"//*[contains(text(),'{name}') or contains(@title,'{name}')]"
            f"[not(contains(@class,'o_searchview'))]")
        if any_match:
            log_ok(f"TC17 PASS: Tìm thấy '{name}' trên trang kết quả")
            return True
    except Exception:
        pass

    log_err(f"TC17 FAIL: Không tìm thấy '{name}' trong kết quả tìm kiếm")
    return False


def run_product_suite(driver, wait, selected_tcs: list[str] | None = None):
    """Chạy toàn bộ Suite 2.1 – Sản phẩm (TC10–TC17)"""
    print("\n" + "=" * 60)
    print("  SUITE 2.1 – SẢN PHẨM")
    print("=" * 60)

    _ALL_TCS = {
        "TC10": tc10_create_product_success,
        "TC11": tc11_create_product_empty_name,
        "TC12": tc12_create_product_valid_price,
        "TC13": tc13_create_product_zero_price,
        "TC14": tc14_create_product_special_chars,
        "TC15": tc15_create_product_duplicate_name,
        "TC16": tc16_refresh_after_save,
        "TC17": tc17_search_product_after_create,
    }
    to_run = selected_tcs if selected_tcs else list(_ALL_TCS.keys())
    results = {tc_id: _ALL_TCS[tc_id](driver, wait) for tc_id in to_run if tc_id in _ALL_TCS}

    _print_suite_result("SUITE 2.1 – SẢN PHẨM", results)
    return results


# ──────────────────────────────────────────────────────────────
# Hàm tạo sản phẩm cũ – dùng bởi main.py (automation flow)
# ──────────────────────────────────────────────────────────────

def create_product(driver, wait):
    """Tạo sản phẩm mới trong Odoo (dùng cho automation flow)."""
    log_step(1, f"TẠO SẢN PHẨM: {PRODUCT_NAME}")

    _ensure_logged_in(driver, wait)
    _go_to_product_list(driver, wait)
    _click_new(driver, wait)

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

    log_info("Bật Track Inventory (storable)...")
    _enable_track_inventory(driver)

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
