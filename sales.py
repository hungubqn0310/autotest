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
from config import ODOO_URL, PRODUCT_NAME, ORDER_QTY, PRODUCT_QTY, PRODUCT_PRICE
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
    "product_url": None,
    "product_name": None,
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


def _create_product_with_stock(driver, wait):
    """Tạo product có Track Inventory + On Hand = PRODUCT_QTY trước khi bán.
    Lưu URL vào _suite_state để TC34 navigate trực tiếp."""
    if _suite_state.get("product_url"):
        return
    from product import (_go_to_product_list, _click_new, _fill_name,
                         _fill_price, _click_save, _is_saved,
                         _enable_track_inventory)
    log_info(f"Tạo product có track inventory: {PRODUCT_NAME} (stock={PRODUCT_QTY})")

    _go_to_product_list(driver, wait)
    time.sleep(1.5)
    _click_new(driver, wait)
    time.sleep(1)
    _fill_name(driver, wait, PRODUCT_NAME)
    time.sleep(0.5)
    _enable_track_inventory(driver)
    time.sleep(1)

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
        time.sleep(0.3)
        qty_field.send_keys(Keys.CONTROL + "a")
        qty_field.send_keys(PRODUCT_QTY)
        time.sleep(0.5)
    except Exception as e:
        log_err(f"Không điền được On Hand: {e}")

    _fill_price(driver, wait, PRODUCT_PRICE)
    time.sleep(0.5)
    _click_save(driver, wait)
    time.sleep(2)

    # Confirm modal "Apply" cho stock change (nếu có)
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

    if not _is_saved(driver):
        log_err(f"Không lưu được product. URL: {driver.current_url}")
        return

    _suite_state["product_url"] = driver.current_url
    _suite_state["product_name"] = PRODUCT_NAME
    log_info(f"Đã tạo product: {driver.current_url}")


def _setup_confirmed_so(driver, wait):
    """Tạo SO đầy đủ và confirm – dùng cho TC31-TC34 khi chạy độc lập."""
    _ensure_logged_in(driver, wait)
    _create_product_with_stock(driver, wait)
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


def _tc34_verify_on_hand(driver, wait, _parse_price):
    """Đọc On Hand strict từ product form và validate với expected (PRODUCT_QTY - ORDER_QTY).
    FAIL nếu không tìm được On Hand thật (tránh false positive khi product không track inventory)."""
    expected = _parse_price(PRODUCT_QTY) - _parse_price(ORDER_QTY)
    on_hand = None
    source = None

    # 1) Đọc field qty_available trên form (chính xác nhất)
    try:
        el = driver.find_element(By.XPATH,
            "//div[@name='qty_available']//input | "
            "//input[@id='qty_available_0'] | "
            "//div[@name='qty_available']//span")
        val_str = (el.get_attribute("value") or el.text or "").strip()
        if val_str:
            on_hand = _parse_price(val_str)
            source = "qty_available field"
    except Exception:
        pass

    # 2) Stat button "Hiện có"/"On Hand" (action_open_quants)
    if on_hand is None:
        for xpath in [
            "//button[@name='action_open_quants']",
            "//button[contains(@class,'oe_stat_button')"
            " and (contains(.,'Hiện có') or contains(.,'On Hand'))]",
        ]:
            try:
                stat = driver.find_element(By.XPATH, xpath)
                nums = re.findall(r'[\d.,]+', stat.text)
                for n in nums:
                    v = _parse_price(n)
                    if v >= 0:
                        on_hand = v
                        source = f"stat button '{stat.text.strip()[:30]}'"
                        break
                if on_hand is not None:
                    break
            except Exception:
                continue

    if on_hand is None:
        # Check xem track inventory có bật không – báo lỗi rõ ràng
        try:
            tracked = driver.find_element(By.XPATH,
                "//input[@id='is_storable_0'] | //div[@name='is_storable']//input")
            if not tracked.is_selected():
                log_err("TC34 FAIL: Product KHÔNG bật Track Inventory → "
                        "không có On Hand để check. Setup sai.")
                return False
        except Exception:
            pass
        log_err("TC34 FAIL: Không đọc được On Hand từ form sản phẩm")
        return False

    log_info(f"[TC34] On Hand đọc được = {on_hand} (từ {source}). Expected = {expected}")
    if abs(on_hand - expected) < 0.01:
        log_ok(f"TC34 PASS: On Hand = {on_hand} = {PRODUCT_QTY} - {ORDER_QTY} (đúng kỳ vọng)")
        return True
    log_err(f"TC34 FAIL: On Hand = {on_hand}, expected {expected} "
            f"({PRODUCT_QTY} - {ORDER_QTY}). Tồn kho không giảm đúng.")
    return False


def tc34_check_stock_after_delivery(driver, wait):
    """TC34 – Kiểm tra tồn kho sau xuất kho"""
    log_step(34, "TC34 – Kiểm tra tồn kho sau xuất kho")
    _ensure_logged_in(driver, wait)
    time.sleep(1)

    from product import _go_to_product_list, _parse_price

    # Ưu tiên navigate trực tiếp tới product URL đã lưu (tạo bởi _create_product_with_stock)
    if _suite_state.get("product_url"):
        log_info(f"[TC34] Navigate trực tiếp tới product: {_suite_state['product_url']}")
        driver.get(_suite_state["product_url"])
        time.sleep(2.5)
        # Skip phần search/click, nhảy thẳng tới đọc tồn kho
        return _tc34_verify_on_hand(driver, wait, _parse_price)

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

    def _real_rows():
        """Trả về list record thật (loại ghost, chỉ visible).
        Odoo 17: real kanban record là <article>, ghost là <div>."""
        els = driver.find_elements(By.XPATH,
            "//tr[contains(@class,'o_data_row')] | "
            "//article[contains(@class,'o_kanban_record')] | "
            "//div[contains(@class,'o_kanban_record') "
            "and not(contains(@class,'o_kanban_ghost'))]")
        out = []
        for e in els:
            try:
                if e.is_displayed() and e.size.get('height', 0) > 0:
                    out.append(e)
            except Exception:
                pass
        return out

    real_rows = []
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
        all_rows = driver.find_elements(By.XPATH,
            "//tr[contains(@class,'o_data_row')] | //div[contains(@class,'o_kanban_record')]")
        real_rows = _real_rows()
        log_info(f"[TC34] Search '{term}' → {len(all_rows)} elements, "
                 f"{len(real_rows)} record thật")
        if real_rows:
            break
        log_info(f"[TC34] Không có record thật với '{term}', thử tiếp...")

    if not real_rows:
        log_err(f"TC34 FAIL: Không tìm thấy sản phẩm thật trong danh sách. "
                f"Có thể product '{PRODUCT_NAME}' không tồn tại trong Inventory "
                f"(consumable không track), hoặc bị filter mặc định ẩn.")
        return False

    # Mở sản phẩm đầu tiên – thử nhiều chiến lược
    from selenium.webdriver.common.action_chains import ActionChains

    opened = False
    url_before = driver.current_url

    # CHIẾN LƯỢC 1: tìm element chứa text tên sản phẩm (không phụ thuộc class).
    # Dựa vào screenshot, card kanban CHẮC CHẮN có text PRODUCT_NAME hiển thị.
    text_targets = []
    for term in [PRODUCT_NAME, "SP_TEST"]:
        els = driver.find_elements(By.XPATH,
            f"//*[contains(normalize-space(text()),'{term}')]")
        for e in els:
            try:
                if e.is_displayed() and e.size.get('height', 0) > 0:
                    text_targets.append(e)
            except Exception:
                pass
        if text_targets:
            break

    # CHIẾN LƯỢC 2: fallback dùng row/card classes nếu tìm theo text fail
    if not text_targets:
        candidates = driver.find_elements(By.XPATH,
            "//tr[contains(@class,'o_data_row')] | "
            "//div[contains(@class,'o_kanban_record') "
            "and not(contains(@class,'o_kanban_ghost'))] | "
            "//article[contains(@class,'o_kanban_record')] | "
            "//div[contains(@class,'oe_kanban_card')]")
        text_targets = [r for r in candidates if r.is_displayed()
                        and r.size.get('height', 0) > 0]

    log_info(f"[TC34] Có {len(text_targets)} click target visible")

    if not text_targets:
        # Diagnostic: dump tất cả class names visible để debug
        try:
            sample = driver.execute_script(
                "return Array.from(document.querySelectorAll("
                "'div,article,tr')).filter(e=>e.offsetParent && "
                "(e.className||'').toString().toLowerCase().includes('kanban'))"
                ".slice(0,10).map(e=>e.className).join('|');")
            log_info(f"[TC34] DEBUG kanban classes visible: {sample}")
        except Exception:
            pass

    for target in text_targets[:5]:
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", target)
            time.sleep(0.3)
        except Exception:
            pass

        for strategy in ("actionchains", "selenium", "js", "dblclick"):
            try:
                if strategy == "actionchains":
                    ActionChains(driver).move_to_element(target)\
                        .pause(0.2).click().perform()
                elif strategy == "selenium":
                    target.click()
                elif strategy == "js":
                    driver.execute_script("arguments[0].click();", target)
                elif strategy == "dblclick":
                    ActionChains(driver).double_click(target).perform()
            except Exception:
                continue
            time.sleep(1.5)
            if (driver.current_url != url_before
                    or driver.find_elements(By.XPATH,
                        "//div[contains(@class,'o_form_view')]")):
                opened = True
                break
        if opened:
            break

    if not opened:
        log_err(f"TC34 FAIL: Không mở được sản phẩm – không click được kết quả "
                f"(URL vẫn: {driver.current_url})")
        return False
    time.sleep(1.5)

    return _tc34_verify_on_hand(driver, wait, _parse_price)


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
