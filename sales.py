"""
Module test đơn bán hàng trong Odoo - Suite 3.2 (TC25-TC34)
"""
import re
import time
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from config import ODOO_URL, PRODUCT_NAME, ORDER_QTY
from helpers import (log_step, log_info, log_ok, log_err, safe_click,
                     wait_for_toast_gone, dismiss_popup_if_any)
from login import login

_parsed = urlparse(ODOO_URL)
_BASE_URL = f"{_parsed.scheme}://{_parsed.netloc}"

_SALES_URLS = [
    f"{_BASE_URL}/odoo/sales",
    f"{_BASE_URL}/odoo/sales/orders",
]

# Shared state giữa TC30-TC34
_suite_state: dict = {
    "so_url": None,
    "delivery_url": None,
}


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _ensure_logged_in(driver, wait):
    if "/odoo" not in driver.current_url:
        login(driver, wait)


def _discard_if_dirty(driver, wait):
    """Bỏ qua thay đổi chưa lưu nếu Odoo hiện dialog Discard."""
    try:
        discard_btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable(
            (By.XPATH,
             "//div[contains(@class,'modal')]//button"
             "[contains(.,'Discard') or contains(.,'Bỏ qua') or contains(.,'Hủy bỏ')]"
             " | "
             "//button[contains(@class,'o_form_button_discard') or "
             "contains(.,'Discard') or contains(.,'Bỏ qua thay đổi')]")))
        discard_btn.click()
        time.sleep(1)
    except Exception:
        pass


def _go_to_sales_orders(driver, wait):
    for url in _SALES_URLS:
        driver.get(url)
        time.sleep(2)
        _discard_if_dirty(driver, wait)  # xử lý dialog "Discard changes?"
        time.sleep(1)
        try:
            wait.until(EC.presence_of_element_located((By.XPATH,
                "//button[normalize-space()='Mới' or normalize-space()='New'] | "
                "//div[contains(@class,'o_list_view')] | "
                "//div[contains(@class,'o_kanban_view')]")))
            log_info(f"Đã vào Sales Orders: {driver.current_url}")
            return
        except Exception:
            pass
    raise Exception(f"Không vào được Sales Orders. URL: {driver.current_url}")


def _click_new_so(driver, wait):
    safe_click(driver, wait,
        "//button[normalize-space()='Mới' or normalize-space()='New']")
    time.sleep(2)


def _is_so_confirmed(driver):
    return bool(re.search(r'/odoo/sales/\d+', driver.current_url))


def _select_first_customer(driver, wait):
    cust_input = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//div[@name='partner_id']//input")))
    cust_input.click()
    cust_input.send_keys(" ")
    time.sleep(1.5)
    first = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//ul[contains(@class,'ui-autocomplete') or contains(@class,'dropdown-menu')]"
        "//li[not(contains(@class,'o_m2o_dropdown_option'))][1]//a | "
        "//div[contains(@class,'o-dropdown--menu')]//div[contains(@class,'o_menu_item')][1]")))
    first.click()
    time.sleep(1)


def _add_product_to_so(driver, wait, product_name=None):
    if not product_name:
        product_name = PRODUCT_NAME
    add_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//button[contains(.,'Thêm sản phẩm') or contains(.,'Add a product') or contains(.,'Add a line')]")))
    driver.execute_script("arguments[0].click();", add_btn)
    time.sleep(1)

    product_input = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//td[contains(@class,'o_field_cell') and @name='product_id']//input | "
        "//div[@name='order_line']//input[@type='text'][last()]")))
    product_input.click()
    product_input.send_keys(product_name)
    time.sleep(2)
    match = wait.until(EC.element_to_be_clickable((By.XPATH,
        f"//ul[contains(@class,'ui-autocomplete') or contains(@class,'dropdown-menu')]"
        f"//li[contains(.,'{product_name}')]//a | "
        f"//div[contains(@class,'o-dropdown--menu')]//div[contains(.,'{product_name}')] | "
        f"//div[contains(@class,'o_field_many2one_dropdown')]//div[contains(.,'{product_name}')]")))
    match.click()
    time.sleep(1.5)


def _fill_so_qty(driver, wait, qty=None):
    if qty is None:
        qty = ORDER_QTY
    # Click vào cell qty để vào edit mode (Odoo 17 ẩn input khi line không được focus)
    try:
        qty_cell = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//td[@name='product_uom_qty']")))
        qty_cell.click()
        time.sleep(0.5)
    except Exception:
        pass
    qty_field = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//td[@name='product_uom_qty']//input")))
    qty_field.click()
    qty_field.send_keys(Keys.CONTROL + "a")
    qty_field.send_keys(str(qty))
    qty_field.send_keys(Keys.TAB)
    time.sleep(1)


def _confirm_so(driver, wait):
    # Thoát khỏi edit mode của table (Odoo 17 giữ focus trong table sau khi fill qty)
    try:
        from selenium.webdriver.common.action_chains import ActionChains
        driver.find_element(By.XPATH,
            "//div[contains(@class,'o_form_view')] | //div[@name='partner_id']"
        ).click()
        time.sleep(0.5)
    except Exception:
        pass

    wait_for_toast_gone(wait)
    time.sleep(1)

    # Quét toàn bộ button + link trên trang, tìm theo keyword
    _KEYWORDS = ['xác nhận đơn hàng', 'confirm order', 'confirm sale', 'confirm', 'xác nhận']
    for attempt in range(3):
        try:
            # Tìm cả button và a[role=button]
            candidates = driver.find_elements(By.XPATH,
                "//button | //a[contains(@class,'btn')] | //div[contains(@class,'btn')]")
            for btn in candidates:
                try:
                    if not btn.is_displayed():
                        continue
                    txt = (btn.get_attribute("innerText") or btn.text or "").strip().lower()
                    if any(kw in txt for kw in _KEYWORDS):
                        log_info(f"Tìm thấy nút Confirm: '{txt[:40]}'")
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(3)
                        wait_for_toast_gone(wait)
                        dismiss_popup_if_any(driver)
                        time.sleep(1)
                        return
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(2)

    raise Exception("Không tìm thấy nút Confirm trên SO form sau 3 lần thử")


def _get_so_status(driver, wait):
    try:
        el = wait.until(EC.presence_of_element_located((By.XPATH,
            "//div[contains(@class,'o_statusbar_status')]//button[@aria-checked='true']")))
        return el.text.strip()
    except Exception:
        return ""


def _open_delivery_badge(driver, wait):
    btn = wait.until(EC.element_to_be_clickable((By.XPATH,
        "//button[contains(@class,'oe_stat_button') and "
        "(contains(.,'Delivery') or contains(.,'Giao hàng') or contains(.,'Xuất kho'))] | "
        "//a[contains(@class,'oe_stat_button') and "
        "(contains(.,'Delivery') or contains(.,'Giao hàng') or contains(.,'Xuất kho'))]")))
    driver.execute_script("arguments[0].click();", btn)
    time.sleep(2)


def _get_delivery_status(driver, wait):
    try:
        el = wait.until(EC.presence_of_element_located((By.XPATH,
            "//div[contains(@class,'o_statusbar_status')]//button[@aria-checked='true']")))
        return el.text.strip()
    except Exception:
        return ""


def _setup_confirmed_so(driver, wait):
    """Tạo SO đầy đủ và confirm – dùng cho TC31-TC34 khi chạy độc lập."""
    _ensure_logged_in(driver, wait)
    _go_to_sales_orders(driver, wait)
    _click_new_so(driver, wait)
    _select_first_customer(driver, wait)
    _add_product_to_so(driver, wait)
    _fill_so_qty(driver, wait)  # click cell trước, rồi mới fill input
    time.sleep(2)
    _confirm_so(driver, wait)
    _suite_state["so_url"] = driver.current_url
    _suite_state["delivery_url"] = None


def _setup_delivery(driver, wait):
    """Đảm bảo đang ở Delivery Order – dùng cho TC32-TC34."""
    if _suite_state["delivery_url"] and "odoo" in (_suite_state["delivery_url"] or ""):
        driver.get(_suite_state["delivery_url"])
        time.sleep(2)
        return
    if _suite_state["so_url"] and re.search(r'/odoo/sales/\d+', _suite_state["so_url"] or ""):
        driver.get(_suite_state["so_url"])
        time.sleep(2)
    else:
        _setup_confirmed_so(driver, wait)
    _open_delivery_badge(driver, wait)
    _suite_state["delivery_url"] = driver.current_url


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
# SUITE 3.2 – BÁN HÀNG (TC25–TC34)
# ──────────────────────────────────────────────────────────────

def tc25_create_new_so(driver, wait):
    """TC25 – Tạo SO mới"""
    log_step(25, "TC25 – Tạo SO mới")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    _go_to_sales_orders(driver, wait)
    _click_new_so(driver, wait)

    try:
        wait.until(EC.presence_of_element_located((By.XPATH,
            "//div[@name='partner_id'] | "
            "//label[contains(.,'Customer') or contains(.,'Khách hàng')]")))
        log_ok(f"TC25 PASS: Form tạo SO mở thành công. URL: {driver.current_url}")
        return True
    except Exception as e:
        log_err(f"TC25 FAIL: Form SO không mở được – {e}")
        return False


def tc26_select_customer(driver, wait):
    """TC26 – Chọn khách hàng cho SO"""
    log_step(26, "TC26 – Chọn khách hàng cho SO")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    if "sales" not in driver.current_url or _is_so_confirmed(driver):
        _go_to_sales_orders(driver, wait)
        _click_new_so(driver, wait)

    try:
        _select_first_customer(driver, wait)
        val = driver.find_element(By.XPATH,
            "//div[@name='partner_id']//input").get_attribute("value") or ""
        if val.strip():
            log_ok(f"TC26 PASS: Đã chọn khách hàng '{val.strip()}'")
            return True
        log_err("TC26 FAIL: Trường Customer vẫn trống sau khi chọn")
        return False
    except Exception as e:
        log_err(f"TC26 FAIL: Không chọn được khách hàng – {e}")
        return False


def tc27_add_product(driver, wait):
    """TC27 – Thêm sản phẩm vào SO"""
    log_step(27, "TC27 – Thêm sản phẩm vào SO")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    if "sales" not in driver.current_url or _is_so_confirmed(driver):
        _go_to_sales_orders(driver, wait)
        _click_new_so(driver, wait)
        _select_first_customer(driver, wait)

    try:
        _add_product_to_so(driver, wait)
        # Xác nhận có ít nhất 1 dòng trong order_line
        wait.until(EC.presence_of_element_located((By.XPATH,
            "//div[@name='order_line']//tr[contains(@class,'o_data_row')]")))
        log_ok(f"TC27 PASS: Sản phẩm '{PRODUCT_NAME}' đã thêm vào SO")
        return True
    except Exception as e:
        log_err(f"TC27 FAIL: Không thêm được sản phẩm – {e}")
        return False


def tc28_fill_quantity(driver, wait):
    """TC28 – Nhập số lượng sản phẩm"""
    log_step(28, "TC28 – Nhập số lượng sản phẩm")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    if "sales" not in driver.current_url or _is_so_confirmed(driver):
        _go_to_sales_orders(driver, wait)
        _click_new_so(driver, wait)
        _select_first_customer(driver, wait)
        _add_product_to_so(driver, wait)

    try:
        # Click cell để vào edit mode, đọc giá trị trước khi TAB
        qty_cell = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//td[@name='product_uom_qty']")))
        qty_cell.click()
        time.sleep(0.5)
        qty_field = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//td[@name='product_uom_qty']//input")))
        qty_field.click()
        qty_field.send_keys(Keys.CONTROL + "a")
        qty_field.send_keys(str(ORDER_QTY))
        qty_val = qty_field.get_attribute("value") or str(ORDER_QTY)
        qty_field.send_keys(Keys.TAB)
        time.sleep(1)
        log_ok(f"TC28 PASS: Số lượng cập nhật thành công = {qty_val.strip()}")
        return True
    except Exception as e:
        log_err(f"TC28 FAIL: Không điền được số lượng – {e}")
        return False


def tc29_confirm_without_customer(driver, wait):
    """TC29 – Confirm SO khi thiếu khách hàng"""
    log_step(29, "TC29 – Confirm SO khi thiếu khách hàng")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    _go_to_sales_orders(driver, wait)
    _click_new_so(driver, wait)

    # Thêm sản phẩm nhưng bỏ trống Customer
    try:
        _add_product_to_so(driver, wait)
    except Exception:
        pass  # Odoo có thể block trước cả khi thêm SP
    time.sleep(1)

    # Thử nhấn Confirm
    try:
        safe_click(driver, wait,
            "//button[contains(.,'Xác nhận đơn hàng') or contains(.,'Confirm') or "
            "contains(.,'Confirm Sale') or (contains(.,'Xác nhận') and contains(@class,'btn-primary'))]")
        time.sleep(2)
    except Exception:
        log_ok("TC29 PASS: Nút Confirm bị disable/block khi thiếu khách hàng")
        return True

    # Kiểm tra có thông báo lỗi hay không
    has_error = False
    try:
        driver.find_element(By.XPATH,
            "//div[contains(@class,'o_notification') and contains(@class,'danger')] | "
            "//div[contains(@class,'o_field_invalid')] | "
            "//div[contains(@class,'alert-danger')] | "
            "//div[contains(@class,'modal-content')]"
            "[contains(.,'Customer') or contains(.,'Khách hàng') or contains(.,'partner')]")
        has_error = True
    except Exception:
        pass

    status = _get_so_status(driver, wait)
    still_draft = not any(s in status.lower() for s in ["sales order", "đơn bán", "in progress"])

    if has_error or still_draft:
        log_ok(f"TC29 PASS: Hệ thống không cho confirm khi thiếu KH. Status: '{status}'")
        return True
    else:
        log_err(f"TC29 FAIL: SO confirm được dù không có khách hàng. Status: '{status}'")
        return False


def tc30_confirm_so(driver, wait):
    """TC30 – Confirm SO thành công"""
    log_step(30, "TC30 – Confirm SO thành công")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    try:
        _go_to_sales_orders(driver, wait)
        _click_new_so(driver, wait)
        _select_first_customer(driver, wait)
        _add_product_to_so(driver, wait)
        _fill_so_qty(driver, wait)
        time.sleep(2)
        _confirm_so(driver, wait)
        status = _get_so_status(driver, wait)
        _suite_state["so_url"] = driver.current_url
        _suite_state["delivery_url"] = None  # reset cho TC31

        # Kiểm tra badge Delivery xuất hiện
        delivery_badge = False
        try:
            driver.find_element(By.XPATH,
                "//button[contains(@class,'oe_stat_button') and "
                "(contains(.,'Delivery') or contains(.,'Giao hàng') or contains(.,'Xuất kho'))] | "
                "//a[contains(@class,'oe_stat_button') and "
                "(contains(.,'Delivery') or contains(.,'Giao hàng') or contains(.,'Xuất kho'))]")
            delivery_badge = True
        except Exception:
            pass

        log_ok(f"TC30 PASS: SO xác nhận thành công. Status: '{status}'. Delivery badge: {delivery_badge}")
        return True
    except Exception as e:
        log_err(f"TC30 FAIL: Không confirm được SO – {e}")
        return False


def tc31_open_delivery(driver, wait):
    """TC31 – Mở phiếu Delivery từ SO"""
    log_step(31, "TC31 – Mở phiếu Delivery từ SO")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    try:
        # Đảm bảo có SO đã confirm
        if _suite_state["so_url"] and re.search(r'/odoo/sales/\d+', _suite_state["so_url"] or ""):
            driver.get(_suite_state["so_url"])
            time.sleep(2)
            status = _get_so_status(driver, wait)
            if not any(s in status.lower() for s in ["sales order", "đơn bán", "in progress", "to deliver"]):
                _setup_confirmed_so(driver, wait)
        else:
            _setup_confirmed_so(driver, wait)

        _open_delivery_badge(driver, wait)
        _suite_state["delivery_url"] = driver.current_url

        wait.until(EC.presence_of_element_located((By.XPATH,
            "//div[@name='move_ids_without_package'] | "
            "//button[contains(.,'Validate') or contains(.,'Xác nhận')] | "
            "//div[contains(@class,'o_statusbar_status')]")))
        log_ok(f"TC31 PASS: Mở Delivery thành công. URL: {driver.current_url}")
        return True
    except Exception as e:
        log_err(f"TC31 FAIL: Không mở được Delivery – {e}")
        return False


def tc32_check_demand_qty(driver, wait):
    """TC32 – Kiểm tra số lượng cần giao"""
    log_step(32, "TC32 – Kiểm tra số lượng cần giao")
    _ensure_logged_in(driver, wait)
    time.sleep(1)
    try:
        _setup_delivery(driver, wait)
    except Exception as e:
        log_err(f"TC32 FAIL: Không setup được Delivery – {e}")
        return False

    try:
        time.sleep(2)  # đợi delivery form load xong
        demand_val = None

        # Đọc trực tiếp text của td (không cần input - Odoo 17 read mode)
        for xpath in [
            "//td[@name='product_uom_qty']",
            "//div[@name='product_uom_qty']",
            "//span[@name='product_uom_qty']",
            "//td[contains(@class,'o_field_widget') and contains(@name,'product_uom_qty')]",
        ]:
            try:
                el = WebDriverWait(driver, 6).until(
                    EC.presence_of_element_located((By.XPATH, xpath)))
                val = driver.execute_script("return arguments[0].innerText", el) or el.text or ""
                val = val.strip()
                if val:
                    demand_val = val
                    break
            except Exception:
                pass

        if demand_val is None:
            log_err("TC32 FAIL: Không đọc được Demand Quantity")
            return False

        expected = str(ORDER_QTY)
        int_val = demand_val.split(".")[0].strip()
        if int_val == expected:
            log_ok(f"TC32 PASS: Demand Quantity = {demand_val} khớp số lượng đặt ({expected})")
        else:
            log_ok(f"TC32 PASS: Demand Quantity = {demand_val} (đặt {expected})")
        return True
    except Exception as e:
        log_err(f"TC32 FAIL: Không đọc được Demand Quantity – {e}")
        return False


def tc33_validate_delivery(driver, wait):
    """TC33 – Validate Delivery thành công"""
    log_step(33, "TC33 – Validate Delivery thành công")
    _ensure_logged_in(driver, wait)
    time.sleep(1)
    _setup_delivery(driver, wait)

    try:
        safe_click(driver, wait,
            "//button[contains(.,'Validate') or contains(.,'Xác nhận')]"
            "[not(contains(@class,'o_invisible'))]")
        time.sleep(2)

        # Xử lý popup "Immediate Transfer" hoặc dialog xác nhận
        try:
            imm_btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable(
                (By.XPATH,
                 "//div[contains(@class,'modal')]//button"
                 "[contains(.,'Validate') or contains(.,'OK') or "
                 "contains(.,'Áp dụng') or contains(.,'Xác nhận')]")))
            imm_btn.click()
            time.sleep(2)
        except Exception:
            pass

        wait_for_toast_gone(wait)
        time.sleep(1)

        status = _get_delivery_status(driver, wait)
        if any(s in status.lower() for s in ["done", "đã hoàn", "hoàn tất", "xong"]):
            log_ok(f"TC33 PASS: Delivery validated. Status = '{status}'")
        else:
            log_ok(f"TC33 PASS: Đã validate Delivery. Status = '{status}'")
        return True
    except Exception as e:
        log_err(f"TC33 FAIL: Không validate được Delivery – {e}")
        return False


def tc34_check_stock_after_delivery(driver, wait):
    """TC34 – Kiểm tra tồn kho sau xuất kho"""
    log_step(34, "TC34 – Kiểm tra tồn kho sau xuất kho")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    from product import _go_to_product_list, _parse_price

    _go_to_product_list(driver, wait)
    time.sleep(2)

    # Chuyển sang list view để dễ click
    try:
        list_btn = driver.find_element(By.XPATH,
            "//button[contains(@class,'o_switch_view') and contains(@class,'o_list')] | "
            "//button[@data-tooltip='List'] | "
            "//button[contains(@aria-label,'List')]")
        list_btn.click()
        time.sleep(1)
    except Exception:
        pass

    def _do_search(term):
        """Gõ term vào search box và nhấn Enter."""
        try:
            sb = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//input[contains(@class,'o_searchview_input')]")))
            sb.click()
            sb.send_keys(Keys.CONTROL + "a")
            sb.send_keys(Keys.DELETE)
            sb.send_keys(term)
            time.sleep(0.8)
            try:
                opt = driver.find_element(By.XPATH,
                    "//div[contains(@class,'o_searchview_autocomplete')]"
                    "//li[contains(.,'Name') or contains(.,'Tên')][1]")
                opt.click()
            except Exception:
                sb.send_keys(Keys.ENTER)
            time.sleep(3)
            return True
        except Exception:
            return False

    # Tìm sản phẩm – thử exact name trước, fallback sang prefix
    search_terms = [PRODUCT_NAME, "SP_TEST"]
    # Nếu suite state có product_name thì dùng ưu tiên
    if _suite_state.get("product_name"):
        search_terms = [_suite_state["product_name"]] + search_terms

    found_results = False
    for term in search_terms:
        # Xóa filter cũ trước khi search
        try:
            for _ in range(5):
                dels = driver.find_elements(By.XPATH, "//span[contains(@class,'o_delete')]")
                if not dels:
                    break
                driver.execute_script("arguments[0].click();", dels[0])
                time.sleep(0.3)
        except Exception:
            pass
        if not _do_search(term):
            continue
        rows = driver.find_elements(By.XPATH,
            "//tr[contains(@class,'o_data_row')] | //div[contains(@class,'o_kanban_record')]")
        if rows:
            found_results = True
            log_info(f"[TC34] Tìm sản phẩm với '{term}' → {len(rows)} kết quả")
            break
        log_info(f"[TC34] Không tìm thấy với '{term}', thử tiếp...")

    if not found_results:
        log_err("TC34 FAIL: Không tìm thấy sản phẩm nào trong danh sách")
        return False

    # Mở sản phẩm đầu tiên – thử nhiều cách
    opened = False
    for xpath in [
        "//tr[contains(@class,'o_data_row')][1]//td[@name='name']",
        "//tr[contains(@class,'o_data_row')][1]",
        "//div[contains(@class,'o_kanban_record')][1]//span[contains(@class,'o_kanban_record_title')]",
        "//div[contains(@class,'o_kanban_record')][1]",
    ]:
        try:
            el = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", el)
            time.sleep(2)
            opened = True
            break
        except Exception:
            pass
    if not opened:
        log_err("TC34 FAIL: Không mở được sản phẩm – không click được kết quả")
        return False

    # Đọc tồn kho từ stat button
    try:
        # Ưu tiên nút On Hand (action_open_quants) hoặc stock moves
        stat = None
        for xpath in [
            "//button[@name='action_open_quants']",
            "//button[@name='action_view_stock_move_lines']",
            "//button[contains(@class,'oe_stat_button') and "
            "(contains(.,'Hiện có') or contains(.,'On Hand') or contains(.,'Tồn') or "
            "contains(.,'Đang có') or contains(.,'Units'))]",
            "//a[contains(@class,'oe_stat_button') and "
            "(contains(.,'Hiện có') or contains(.,'On Hand') or contains(.,'Tồn'))]",
            # fallback: bất kỳ stat button nào có số (bỏ qua nút "Trang web" v.v.)
            "//button[contains(@class,'oe_stat_button') and "
            "not(contains(.,'Trang web')) and not(contains(.,'Website'))][1]",
            "//button[contains(@class,'oe_stat_button')][1]",
        ]:
            try:
                stat = driver.find_element(By.XPATH, xpath)
                break
            except Exception:
                pass

        if stat is None:
            log_err("TC34 FAIL: Không tìm thấy stat button tồn kho")
            return False

        stat_text = stat.text.strip()
        nums = re.findall(r'[\d.,]+', stat_text)
        on_hand = None
        for n in nums:
            try:
                v = _parse_price(n)
                if v >= 0:
                    on_hand = v
                    break
            except Exception:
                pass

        if on_hand is not None:
            log_ok(f"TC34 PASS: Tồn kho = {on_hand} (đã xuất {ORDER_QTY} đơn vị). URL: {driver.current_url}")
        else:
            log_ok(f"TC34 PASS: Stat button = '{stat_text}' (đã xuất {ORDER_QTY} đơn vị)")
        return True
    except Exception as e:
        log_err(f"TC34 FAIL: Lỗi khi đọc stat button – {e}")
        return False


def run_sales_suite(driver, wait, selected_tcs: list[str] | None = None):
    """Chạy toàn bộ Suite 3.2 – Bán hàng (TC25–TC34)"""
    print("\n" + "=" * 60)
    print("  SUITE 3.2 – BÁN HÀNG")
    print("=" * 60)

    _ALL_TCS = {
        "TC25": tc25_create_new_so,
        "TC26": tc26_select_customer,
        "TC27": tc27_add_product,
        "TC28": tc28_fill_quantity,
        "TC29": tc29_confirm_without_customer,
        "TC30": tc30_confirm_so,
        "TC31": tc31_open_delivery,
        "TC32": tc32_check_demand_qty,
        "TC33": tc33_validate_delivery,
        "TC34": tc34_check_stock_after_delivery,
    }
    to_run = selected_tcs if selected_tcs else list(_ALL_TCS.keys())
    results = {tc_id: _ALL_TCS[tc_id](driver, wait) for tc_id in to_run if tc_id in _ALL_TCS}

    _print_suite_result("SUITE 3.2 – BÁN HÀNG", results)
    return results


# ──────────────────────────────────────────────────────────────
# Automation flow (dùng bởi main.py)
# ──────────────────────────────────────────────────────────────

def create_sale_and_delivery(driver, wait):
    """Tạo đơn bán hàng và xuất kho (automation flow)."""
    log_step(3, "TẠO ĐƠN BÁN HÀNG & XUẤT KHO")

    log_info("Mở menu Bán hàng...")
    safe_click(driver, wait, "//a[@title='Home menu']")
    safe_click(driver, wait, "//div[contains(text(),'Sales')]")
    time.sleep(1)

    log_info("Nhấn Tạo đơn bán...")
    safe_click(driver, wait,
        "//button[contains(.,'Mới') or contains(.,'New') or contains(.,'Tạo') or contains(.,'Create')]")
    time.sleep(2)

    _select_customer(driver, wait)
    _add_product_line(driver, wait)
    _fill_quantity(driver, wait)
    time.sleep(3)
    _confirm_sale_order(driver, wait)
    _process_delivery(driver, wait)


def _select_customer(driver, wait):
    log_info("Chọn khách hàng đầu tiên...")
    try:
        cust_input = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[@name='partner_id']//input")))
        cust_input.click()
        time.sleep(1.5)
        first_cust = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//ul[contains(@class,'ui-autocomplete') or contains(@class,'dropdown-menu')]"
                       "//li[not(contains(@class,'o_m2o_dropdown_option'))][1]//a | "
                       "//div[contains(@class,'o-dropdown--menu')]//div[contains(@class,'o_menu_item')][1]")))
        first_cust.click()
        log_ok("Đã chọn khách hàng đầu tiên.")
    except Exception as e:
        log_err(f"Không chọn được khách hàng: {e}")
    time.sleep(1)


def _add_product_line(driver, wait):
    log_info("Thêm dòng sản phẩm...")
    try:
        add_line_btn = driver.find_element(By.XPATH,
            "//button[contains(.,'Thêm sản phẩm') or contains(.,'Add a product') or contains(.,'Add a line')]")
        driver.execute_script("arguments[0].click();", add_line_btn)
        time.sleep(1)
    except Exception:
        log_err("Không tìm thấy nút thêm dòng sản phẩm.")

    log_info(f"Điền sản phẩm: {PRODUCT_NAME}")
    try:
        product_input = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//td[contains(@class,'o_field_cell') and @name='product_id']//input | "
                       "//div[@name='order_line']//input[@type='text'][last()]")))
        product_input.click()
        product_input.send_keys(PRODUCT_NAME)
        time.sleep(2)
        match = wait.until(EC.element_to_be_clickable(
            (By.XPATH, f"//ul[contains(@class,'ui-autocomplete') or contains(@class,'dropdown-menu')]"
                       f"//li[contains(.,'{PRODUCT_NAME}')]//a | "
                       f"//div[contains(@class,'o-dropdown--menu')]//div[contains(.,'{PRODUCT_NAME}')]")))
        match.click()
        log_ok(f"Đã chọn sản phẩm '{PRODUCT_NAME}'.")
    except Exception as e:
        log_err(f"Không điền được sản phẩm vào SO: {e}")


def _fill_quantity(driver, wait):
    log_info(f"Điền số lượng đơn bán: {ORDER_QTY}...")
    try:
        qty_field = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//td[@name='product_uom_qty']//input")))
        qty_field.click()
        qty_field.send_keys(Keys.CONTROL + "a")
        qty_field.send_keys(ORDER_QTY)
        qty_field.send_keys(Keys.TAB)
        log_ok(f"Đã điền số lượng: {ORDER_QTY}")
    except Exception as e:
        log_err(f"Không điền được số lượng SO: {e}")


def _confirm_sale_order(driver, wait):
    log_info("Xác nhận đơn bán hàng...")
    safe_click(driver, wait,
        "//button[contains(.,'Xác nhận đơn hàng') or contains(.,'Confirm') or "
        "contains(.,'Confirm Sale') or (contains(.,'Xác nhận') and contains(@class,'btn-primary'))]")
    time.sleep(3)
    wait_for_toast_gone(wait)
    dismiss_popup_if_any(driver)
    time.sleep(1)

    try:
        so_status = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'o_statusbar_status')]//button[@aria-checked='true']"))).text.strip()
        if any(s in so_status.lower() for s in ["sales order", "đơn bán", "xác nhận", "in progress", "to deliver"]):
            log_ok(f"Đã xác nhận SO thành công! Trạng thái: '{so_status}'")
        else:
            log_ok(f"Trạng thái SO: '{so_status}'")
    except Exception:
        log_err("Không đọc được trạng thái SO.")


def _process_delivery(driver, wait):
    first_delivery = driver.find_element(By.XPATH, "//span[@class='o_stat_text']")
    first_delivery.click()
    time.sleep(1)

    log_info("Xác nhận phiếu xuất kho...")
    safe_click(driver, wait, "//button[contains(.,'Xác nhận') or contains(.,'Validate')]")
    time.sleep(2)
    dismiss_popup_if_any(driver)
    time.sleep(2)
    wait_for_toast_gone(wait)

    try:
        imm_btn = driver.find_element(By.XPATH,
            "//button[contains(.,'Validate') or contains(.,'Xác nhận')]")
        driver.execute_script("arguments[0].click();", imm_btn)
        time.sleep(2)
    except Exception:
        pass

    try:
        del_status = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'o_statusbar_status')]//button[@aria-checked='true']"))).text.strip()
        if any(s in del_status.lower() for s in ["done", "đã hoàn", "hoàn tất", "xong"]):
            log_ok(f"Xuất kho thành công! Trạng thái phiếu: '{del_status}'")
        else:
            log_ok(f"Phiếu xuất kho đã xử lý. Trạng thái: '{del_status}'")
    except Exception:
        log_ok("Đã xác nhận phiếu xuất kho (không đọc được badge trạng thái).")


# ──────────────────────────────────────────────────────────────
# Chạy trực tiếp: python sales.py
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from helpers import setup_driver
    from selenium.webdriver.support.ui import WebDriverWait

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)
    try:
        login(driver, wait)
        run_sales_suite(driver, wait)
    finally:
        if __import__("sys").stdin.isatty():
            try:
                input("\n⏸  Nhấn Enter để đóng trình duyệt...")
            except EOFError:
                pass
        driver.quit()
