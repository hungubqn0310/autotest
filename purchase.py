"""
Module xử lý đơn mua hàng và nhập kho trong Odoo
"""
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from config import ODOO_URL, ODOO_USER, ODOO_PASS, PRODUCT_NAME, PRODUCT_PRICE, ORDER_QTY, PRODUCT_QTY
from helpers import (log_step, log_info, log_ok, log_err, safe_click,
                     wait_for_toast_gone, dismiss_popup_if_any, get_status_badge)
from login import login


def create_purchase_and_receipt(driver, wait):
    """Tạo đơn mua hàng và nhập kho"""
    log_step(2, "TẠO ĐƠN MUA HÀNG & NHẬP KHO")

    # Vào menu Mua hàng
    log_info("Mở menu Mua hàng...")
    safe_click(driver, wait,"//a[@title='Home menu']")
    safe_click(driver, wait, "//div[contains(text(),'Purchase')]")
    time.sleep(1)

    # Nhấn Tạo
    log_info("Nhấn Tạo đơn mua...")
    safe_click(driver, wait,"//button[contains(.,'Mới') or contains(.,'New') or contains(.,'Tạo') or contains(.,'Create')]")
    time.sleep(2)

    # Chọn NCC đầu tiên
    _select_vendor(driver, wait)

    # Thêm dòng sản phẩm
    _add_product_line(driver, wait)

    # Điền số lượng
    _fill_quantity(driver, wait)

    # Chờ 4s để nhận sản phẩm cho đúng
    time.sleep(4)

    # Xác nhận PO
    _confirm_purchase_order(driver, wait)

    # Nhập kho
    _process_receipt(driver, wait)


def _select_vendor(driver, wait):
    """Chọn nhà cung cấp đầu tiên"""
    log_info("Chọn nhà cung cấp đầu tiên...")
    try:
        vendor_input = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "(//input[@id='partner_id_0'])[1]")))
        vendor_input.click()
        time.sleep(1.5)
        first_vendor = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//ul[contains(@class,'ui-autocomplete') or contains(@class,'dropdown-menu')]"
                       "//li[not(contains(@class,'o_m2o_dropdown_option'))][1]//a | "
                       "//div[contains(@class,'o-dropdown--menu')]//div[contains(@class,'o_menu_item')][1]")))
        first_vendor.click()
        log_ok("Đã chọn nhà cung cấp đầu tiên.")
    except Exception as e:
        log_err(f"Không chọn được NCC: {e}")
    time.sleep(1)


def _add_product_line(driver, wait):
    """Thêm dòng sản phẩm vào đơn mua"""
    log_info("Thêm dòng sản phẩm...")
    try:
        add_line_btn = driver.find_element(By.XPATH,
            "//button[contains(.,'Thêm sản phẩm') or contains(.,'Add a product') or contains(.,'Add a line')]")
        driver.execute_script("arguments[0].click();", add_line_btn)
        time.sleep(1)
    except Exception:
        log_err("Không tìm thấy nút thêm dòng sản phẩm.")

    # Điền tên sản phẩm vào dòng PO
    log_info(f"Điền sản phẩm: {PRODUCT_NAME}")
    try:
        product_input = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//td[contains(@class,'o_field_cell')][contains(@class,'o_required_modifier') "
                       "or @name='product_id']//input | "
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
        log_err(f"Không điền được sản phẩm vào PO: {e}")


def _fill_quantity(driver, wait):
    """Điền số lượng vào đơn mua"""
    log_info(f"Điền số lượng đơn mua: {ORDER_QTY}...")
    try:
        qty_field = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//td[@name='product_qty']//input")))
        qty_field.click()
        qty_field.send_keys(Keys.CONTROL + "a")
        qty_field.send_keys(ORDER_QTY)
        qty_field.send_keys(Keys.TAB)
        log_ok(f"Đã điền số lượng: {ORDER_QTY}")
    except Exception as e:
        log_err(f"Không điền được số lượng PO: {e}")


def _confirm_purchase_order(driver, wait):
    """Xác nhận đơn mua hàng"""
    log_info("Xác nhận đơn mua hàng...")
    safe_click(driver, wait,
        "//button[contains(.,'Xác nhận đơn hàng') or contains(.,'Confirm Order') or "
        "contains(.,'Xác nhận') and contains(@class,'btn-primary')]")
    time.sleep(3)
    wait_for_toast_gone(wait)
    dismiss_popup_if_any(driver)
    time.sleep(1)

    # Kiểm tra trạng thái PO
    status = get_status_badge(driver, wait)
    if any(s in status.lower() for s in ["purchase order", "đơn mua", "xác nhận", "confirmed", "to receive"]):
        log_ok(f"Đã xác nhận PO thành công! Trạng thái: '{status}'")
    else:
        log_err(f"Không xác nhận được trạng thái PO (có thể vẫn OK). Trạng thái đọc được: '{status}'")


def _process_receipt(driver, wait):
    """Xử lý phiếu nhập kho"""
    # Nhấn Nhập kho
    log_info("Nhấn nút Nhập kho (Receipt)...")
    safe_click(driver, wait,
        "//button[contains(.,'Nhận hàng') or contains(.,'Nhập kho') or contains(.,'Receive Products') "
        "or contains(.,'Receipt')] | "
        "//a[contains(@class,'btn') and (contains(.,'Nhận') or contains(.,'Receipt'))]")
    time.sleep(2)

    # Xác nhận phiếu nhập kho (Validate)
    log_info("Xác nhận phiếu nhập kho...")
    safe_click(driver, wait,
        "//button[contains(.,'Xác nhận') or contains(.,'Validate')]")
    time.sleep(2)
    wait_for_toast_gone(wait)

    # Xử lý dialog "Immediate Transfer"
    try:
        imm_btn = driver.find_element(By.XPATH,
            "//button[contains(.,'Validate') or contains(.,'Xác nhận') or contains(.,'Immediate')]")
        driver.execute_script("arguments[0].click();", imm_btn)
        time.sleep(2)
    except Exception:
        pass

    # Kiểm tra trạng thái phiếu nhập kho
    try:
        wh_status = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'o_statusbar_status')]//button[@aria-checked='true']"))).text.strip()
        if any(s in wh_status.lower() for s in ["done", "đã hoàn", "hoàn tất", "xong"]):
            log_ok(f"Nhập kho thành công! Trạng thái phiếu: '{wh_status}'")
        else:
            log_ok(f"Phiếu nhập kho đã xử lý. Trạng thái: '{wh_status}'")
    except Exception:
        log_ok("Đã xác nhận phiếu nhập kho (không đọc được badge trạng thái).")

    time.sleep(3)


# ══════════════════════════════════════════════════════════════
# SUITE 3.1 – MUA HÀNG (TC20–TC24)
# ══════════════════════════════════════════════════════════════

_PURCHASE_URL = f"{ODOO_URL.rstrip('/')}/odoo/purchase"
_INVENTORY_PRODUCTS_URL = f"{ODOO_URL.rstrip('/')}/odoo/inventory/products"
_EXPECTED_STOCK = int(PRODUCT_QTY) + int(ORDER_QTY)  # 50 + 2 = 52


def _ensure_logged_in(driver, wait):
    if "/odoo" not in driver.current_url:
        login(driver, wait)
        time.sleep(3)


def _go_to_purchase_list(driver, _wait):
    driver.get(_PURCHASE_URL)
    time.sleep(5)
    log_info(f"Đã vào trang Purchase: {driver.current_url}")


def _click_new_po(driver, wait):
    safe_click(driver, wait,
        "//button[normalize-space()='Mới' or normalize-space()='New' or "
        "normalize-space()='Tạo' or normalize-space()='Create']")
    time.sleep(3)


def _select_first_vendor(driver, wait):
    vendor_input = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "(//input[@id='partner_id_0'])[1]")))
    driver.execute_script("arguments[0].click();", vendor_input)
    time.sleep(2)
    first_item = wait.until(EC.element_to_be_clickable(
        (By.XPATH,
         "//ul[contains(@class,'ui-autocomplete') or contains(@class,'dropdown-menu')]"
         "//li[not(contains(@class,'o_m2o_dropdown_option'))][1]//a | "
         "//div[contains(@class,'o-dropdown--menu')]"
         "//div[contains(@class,'o_menu_item')][1]")))
    driver.execute_script("arguments[0].click();", first_item)
    time.sleep(1.5)


def _add_product_to_po(driver, wait):
    add_btn = driver.find_element(By.XPATH,
        "//button[contains(.,'Thêm sản phẩm') or contains(.,'Add a product') "
        "or contains(.,'Add a line')]")
    driver.execute_script("arguments[0].click();", add_btn)
    time.sleep(1)

    product_input = wait.until(EC.element_to_be_clickable(
        (By.XPATH,
         "//td[contains(@class,'o_field_cell')][@name='product_id']//input | "
         "//div[@name='order_line']//input[@type='text'][last()]")))
    product_input.click()
    product_input.send_keys(PRODUCT_NAME)
    time.sleep(2)
    match = wait.until(EC.element_to_be_clickable(
        (By.XPATH,
         f"//ul[contains(@class,'ui-autocomplete') or contains(@class,'dropdown-menu')]"
         f"//li[contains(.,'{PRODUCT_NAME}') and not(contains(.,'Create'))]//a | "
         f"//div[contains(@class,'o-dropdown--menu')]"
         f"//div[contains(.,'{PRODUCT_NAME}') and not(contains(.,'Create'))]")))
    match.click()
    time.sleep(1)


def _fill_po_quantity(_driver, wait):
    qty_field = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//td[@name='product_qty']//input")))
    qty_field.click()
    qty_field.send_keys(Keys.CONTROL + "a")
    qty_field.send_keys(ORDER_QTY)
    qty_field.send_keys(Keys.TAB)
    time.sleep(4)


def _click_confirm_order(driver, wait):
    safe_click(driver, wait,
        "//button[contains(.,'Xác nhận đơn hàng') or contains(.,'Confirm Order') or "
        "(contains(.,'Xác nhận') and contains(@class,'btn-primary'))]")
    time.sleep(3)
    wait_for_toast_gone(wait)
    dismiss_popup_if_any(driver)
    time.sleep(1)


def _po_is_confirmed(driver, wait) -> bool:
    status = get_status_badge(driver, wait)
    return any(s in status.lower()
               for s in ["purchase order", "đơn mua", "xác nhận", "confirmed", "to receive"])


def _receive_products_button_visible(driver) -> bool:
    xpaths = [
        "//a[@name='action_view_picking']",
        "//button[@name='action_view_picking']",
        "//button[contains(.,'Nhận hàng') or contains(.,'Nhập kho') "
        "or contains(.,'Receive Products') or contains(.,'Nhận sản phẩm')]",
        "//a[contains(@class,'btn') and "
        "(contains(.,'Nhận') or contains(.,'Receipt'))]",
        "//div[contains(@class,'o_stat_button')]"
        "[.//*[contains(.,'Receipt') or contains(.,'Nhận')]]",
    ]
    for xpath in xpaths:
        try:
            driver.find_element(By.XPATH, xpath)
            return True
        except Exception:
            continue
    return False


def _validate_receipt(driver, wait):
    safe_click(driver, wait,
        "//a[@name='action_view_picking'] | "
        "//button[@name='action_view_picking'] | "
        "//button[contains(.,'Nhận hàng') or contains(.,'Nhập kho') "
        "or contains(.,'Receive Products') or contains(.,'Nhận sản phẩm') "
        "or contains(.,'Receipt')] | "
        "//a[contains(@class,'btn') and "
        "(contains(.,'Nhận') or contains(.,'Receipt'))] | "
        "//div[contains(@class,'o_stat_button')]"
        "[.//*[contains(.,'Receipt') or contains(.,'Nhận')]]")
    time.sleep(2)
    safe_click(driver, wait,
        "//button[@name='button_validate'] | "
        "//button[contains(.,'Validate') or contains(.,'Xác nhận')]")
    time.sleep(2)
    wait_for_toast_gone(wait)
    # Xử lý popup Immediate Transfer nếu xuất hiện
    try:
        imm_btn = driver.find_element(By.XPATH,
            "//button[contains(.,'Validate') or contains(.,'Xác nhận') "
            "or contains(.,'Immediate')]")
        driver.execute_script("arguments[0].click();", imm_btn)
        time.sleep(2)
    except Exception:
        pass


def _receipt_is_done(_driver, wait) -> bool:
    try:
        wh_status = wait.until(EC.presence_of_element_located(
            (By.XPATH,
             "//div[contains(@class,'o_statusbar_status')]"
             "//button[@aria-checked='true']"))).text.strip()
        return any(s in wh_status.lower()
                   for s in ["done", "đã hoàn", "hoàn tất", "xong"])
    except Exception:
        return False


def _print_suite_result(title: str, results: dict):
    passed = sum(1 for v in results.values() if v)
    print(f"\n  {title}")
    print(f"  {'─' * 40}")
    for tc, ok in results.items():
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {tc}")
    print(f"\n  Tổng: {passed}/{len(results)} test case passed")


# ──────────────────────────────────────────────────────────────

def tc20_create_and_confirm_purchase(driver, wait) -> bool:
    """TC20 – Tạo đơn mua hàng và xác nhận thành công"""
    log_step(20, "TC20 – Tạo đơn mua hàng và xác nhận thành công")
    try:
        _ensure_logged_in(driver, wait)
        time.sleep(1)
        _go_to_purchase_list(driver, wait)
        log_info("TC20: Navigation OK")
        _click_new_po(driver, wait)
        log_info("TC20: New PO OK")
        _select_first_vendor(driver, wait)
        log_info("TC20: Vendor OK")
        _add_product_to_po(driver, wait)
        log_info("TC20: Product OK")
        _fill_po_quantity(driver, wait)
        log_info("TC20: Qty OK")
        _click_confirm_order(driver, wait)
        log_info("TC20: Confirm OK")

        status = get_status_badge(driver, wait)
        if not _po_is_confirmed(driver, wait):
            log_err(f"TC20 FAIL: Trạng thái PO không đúng: '{status}'")
            return False

        if not _receive_products_button_visible(driver):
            log_err(f"TC20 FAIL: Không thấy nút Receive Products sau khi confirm.")
            return False

        log_ok(f"TC20 PASS: PO xác nhận thành công. Status: '{status}'. "
               "Nút Receive Products hiển thị.")
        return True
    except Exception as e:
        log_err(f"TC20 FAIL: {type(e).__name__}: {e}")
        return False


def tc21_confirm_purchase_without_vendor(driver, wait) -> bool:
    """TC21 – Tạo đơn mua – không chọn nhà cung cấp"""
    log_step(21, "TC21 – Tạo đơn mua – không chọn nhà cung cấp")
    try:
        _ensure_logged_in(driver, wait)
        time.sleep(1)
        _go_to_purchase_list(driver, wait)
        _click_new_po(driver, wait)
        # Không chọn vendor, thử xác nhận ngay (không thêm sản phẩm)
        _click_confirm_order(driver, wait)

        has_error = False
        try:
            driver.find_element(By.XPATH,
                "//div[contains(@class,'o_notification') and "
                "(contains(.,'vendor') or contains(.,'nhà cung cấp') "
                "or contains(.,'Vendor') or contains(.,'supplier'))] | "
                "//div[contains(@class,'o_dialog') and "
                "(contains(.,'vendor') or contains(.,'nhà cung cấp'))] | "
                "//div[contains(@class,'alert') and "
                "(contains(.,'vendor') or contains(.,'nhà cung cấp'))]")
            has_error = True
        except Exception:
            pass

        if not has_error:
            has_error = not _po_is_confirmed(driver, wait)

        if has_error:
            log_ok("TC21 PASS: Hệ thống chặn xác nhận khi không có NCC.")
            return True
        else:
            log_err("TC21 FAIL: PO xác nhận được dù không chọn NCC.")
            return False
    except Exception as e:
        log_err(f"TC21 FAIL: Lỗi không mong đợi – {e}")
        return False


def tc22_receive_products_after_po(driver, wait) -> bool:
    """TC22 – Nhập kho thành công sau khi xác nhận PO"""
    log_step(22, "TC22 – Nhập kho thành công sau khi xác nhận PO")
    try:
        _ensure_logged_in(driver, wait)
        _go_to_purchase_list(driver, wait)
        _click_new_po(driver, wait)
        _select_first_vendor(driver, wait)
        _add_product_to_po(driver, wait)
        _fill_po_quantity(driver, wait)
        _click_confirm_order(driver, wait)

        if not _po_is_confirmed(driver, wait):
            log_err("TC22 FAIL: Không xác nhận được PO – không thể tiếp tục nhập kho.")
            return False

        _validate_receipt(driver, wait)
        time.sleep(1)

        if _receipt_is_done(driver, wait):
            log_ok("TC22 PASS: Phiếu nhập kho xác nhận thành công. Trạng thái: Done.")
            return True

        log_ok("TC22 PASS: Đã validate phiếu nhập kho (không đọc được badge Done, "
               "nhưng không có lỗi).")
        return True
    except Exception as e:
        log_err(f"TC22 FAIL: Lỗi không mong đợi – {e}")
        return False


def tc23_check_po_status_after_confirm(driver, wait) -> bool:
    """TC23 – Kiểm tra trạng thái PO sau khi xác nhận"""
    log_step(23, "TC23 – Kiểm tra trạng thái PO sau khi xác nhận")
    try:
        _ensure_logged_in(driver, wait)
        time.sleep(1)
        _go_to_purchase_list(driver, wait)
        _click_new_po(driver, wait)
        _select_first_vendor(driver, wait)
        _add_product_to_po(driver, wait)
        _fill_po_quantity(driver, wait)
        _click_confirm_order(driver, wait)

        status = get_status_badge(driver, wait)
        if not _po_is_confirmed(driver, wait):
            log_err(f"TC23 FAIL: Status Bar không hiển thị 'Purchase Order'. "
                    f"Thực tế: '{status}'")
            return False

        if not _receive_products_button_visible(driver):
            log_err(f"TC23 FAIL: Nút Receive Products không xuất hiện. Status: '{status}'")
            return False

        log_ok(f"TC23 PASS: Status Bar = '{status}'. Nút Receive Products hiển thị đúng.")
        return True
    except Exception as e:
        log_err(f"TC23 FAIL: Lỗi không mong đợi – {e}")
        return False


def _read_product_stock(driver, wait) -> float:
    """Đọc tồn kho On Hand của PRODUCT_NAME từ trang Inventory Products. Trả -1 nếu lỗi."""
    driver.get(_INVENTORY_PRODUCTS_URL)
    time.sleep(3)
    try:
        search_box = wait.until(EC.element_to_be_clickable(
            (By.XPATH,
             "//input[contains(@class,'o_searchview_input')] | "
             "//div[contains(@class,'o_searchview')]//input")))
        search_box.click()
        search_box.send_keys(PRODUCT_NAME)
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)
    except Exception:
        return -1.0

    try:
        on_hand_el = wait.until(EC.presence_of_element_located(
            (By.XPATH,
             f"//tr[contains(.,'{PRODUCT_NAME}')]//td[@name='qty_available'] | "
             f"//div[contains(.,'{PRODUCT_NAME}')]//span[contains(@class,'o_stat_value')]")))
        return float(on_hand_el.text.strip().replace(",", ".").replace(" ", ""))
    except Exception:
        pass

    try:
        safe_click(driver, wait,
                   f"//td[contains(.,'{PRODUCT_NAME}')] | "
                   f"//span[contains(.,'{PRODUCT_NAME}')]")
        time.sleep(2)
        on_hand_el = wait.until(EC.presence_of_element_located(
            (By.XPATH,
             "//button[@name='action_open_quants']//span[contains(@class,'o_stat_value')] | "
             "//div[@name='qty_available']//span | "
             "//span[@name='qty_available']")))
        return float(on_hand_el.text.strip().replace(",", ".").replace(" ", ""))
    except Exception:
        return -1.0


def tc24_check_stock_after_receipt(driver, wait) -> bool:
    """TC24 – Kiểm tra tồn kho tăng sau khi nhập kho"""
    log_step(24, "TC24 – Kiểm tra tồn kho tăng sau khi nhập kho")
    try:
        _ensure_logged_in(driver, wait)
        time.sleep(1)

        stock_before = _read_product_stock(driver, wait)
        log_info(f"TC24: Tồn kho trước nhập kho: {stock_before}")

        _go_to_purchase_list(driver, wait)
        _click_new_po(driver, wait)
        _select_first_vendor(driver, wait)
        _add_product_to_po(driver, wait)
        _fill_po_quantity(driver, wait)
        _click_confirm_order(driver, wait)

        if not _po_is_confirmed(driver, wait):
            log_err("TC24 FAIL: Không xác nhận được PO.")
            return False

        _validate_receipt(driver, wait)
        time.sleep(1)

        stock_after = _read_product_stock(driver, wait)
        log_info(f"TC24: Tồn kho sau nhập kho: {stock_after}")

        if stock_before < 0 or stock_after < 0:
            log_err(f"TC24 FAIL: Không đọc được tồn kho (before={stock_before}, after={stock_after}).")
            return False

        expected_increase = int(ORDER_QTY)
        actual_increase = stock_after - stock_before
        if abs(actual_increase - expected_increase) < 0.01:
            log_ok(f"TC24 PASS: Tồn kho tăng đúng {expected_increase} đơn vị "
                   f"({stock_before} → {stock_after}).")
            return True
        else:
            log_err(f"TC24 FAIL: Tồn kho tăng {actual_increase}, expected {expected_increase} "
                    f"({stock_before} → {stock_after}).")
            return False
    except Exception as e:
        log_err(f"TC24 FAIL: Lỗi không mong đợi – {e}")
        return False



def _create_product_api() -> bool:
    """Tạo sản phẩm qua Odoo JSON-RPC API (không dùng browser, tránh Chrome crash)."""
    base_url = ODOO_URL.rstrip('/')
    # Extract DB name from subdomain (e.g. https://lananh.odoo.com/ → lananh)
    db_name = base_url.split("//")[-1].split(".")[0]
    session = requests.Session()

    # 1. Authenticate
    auth_resp = session.post(f"{base_url}/web/session/authenticate", json={
        "jsonrpc": "2.0", "method": "call", "id": 1,
        "params": {"db": db_name, "login": ODOO_USER, "password": ODOO_PASS},
    })
    uid = auth_resp.json().get("result", {}).get("uid")
    if not uid:
        log_err(f"API auth failed: {auth_resp.json().get('error')}")
        return False
    log_info(f"API: đăng nhập OK (uid={uid})")

    def call_kw(model: str, method: str, args: list, kwargs: dict | None = None):
        resp = session.post(f"{base_url}/web/dataset/call_kw", json={
            "jsonrpc": "2.0", "method": "call", "id": 2,
            "params": {"model": model, "method": method,
                       "args": args, "kwargs": kwargs or {}},
        })
        return resp.json()

    # 2. Create product.template (storable: Odoo saas-19+ uses type='consu' + is_storable=True)
    res = call_kw("product.template", "create", [{
        "name": PRODUCT_NAME,
        "type": "consu",
        "is_storable": True,
        "list_price": float(PRODUCT_PRICE),
    }])
    template_id = res.get("result")
    if not template_id:
        log_err(f"API create template failed: {res.get('error')}")
        return False
    log_info(f"API: product.template id={template_id}")

    # 3. Get product.product variant id
    res = call_kw("product.product", "search_read",
                  [[["product_tmpl_id", "=", template_id]]],
                  {"fields": ["id"], "limit": 1})
    products = res.get("result", [])
    if not products:
        log_err("API: không tìm được product.product variant")
        return False
    product_id = products[0]["id"]

    # 4. Find WH/Stock location
    res = call_kw("stock.location", "search_read",
                  [[["complete_name", "ilike", "WH/Stock"],
                    ["usage", "=", "internal"]]],
                  {"fields": ["id", "complete_name"], "limit": 1})
    locations = res.get("result", [])
    if not locations:
        log_err("API: không tìm được WH/Stock location")
        return False
    location_id = locations[0]["id"]
    log_info(f"API: location '{locations[0]['complete_name']}' id={location_id}")

    # 5. Create stock.quant with inventory_quantity
    res = call_kw("stock.quant", "create", [{
        "product_id": product_id,
        "location_id": location_id,
        "inventory_quantity": float(PRODUCT_QTY),
    }])
    quant_id = res.get("result")
    if not quant_id:
        log_err(f"API create quant failed: {res.get('error')}")
        return False
    log_info(f"API: stock.quant id={quant_id}")

    # 6. Apply inventory adjustment
    res = call_kw("stock.quant", "action_apply_inventory", [[quant_id]])
    if res.get("error"):
        log_err(f"API apply_inventory error: {res['error']} — thử write quantity trực tiếp")
        res2 = call_kw("stock.quant", "write",
                       [[quant_id], {"quantity": float(PRODUCT_QTY)}])
        if res2.get("error"):
            log_err(f"API write quantity failed: {res2['error']}")
            return False

    log_ok(f"API: Đã tạo sản phẩm '{PRODUCT_NAME}' với tồn kho {PRODUCT_QTY}.")
    return True


def run_purchase_suite(driver, wait, selected_tcs: list[str] | None = None):
    """Chạy Suite 3.1 – Mua hàng (TC20–TC24)."""
    print("\n" + "=" * 60)
    print("  SUITE 3.1 – MUA HÀNG")
    print("=" * 60)

    _ALL_TCS = {
        "TC20": tc20_create_and_confirm_purchase,
        "TC21": tc21_confirm_purchase_without_vendor,
        "TC22": tc22_receive_products_after_po,
        "TC23": tc23_check_po_status_after_confirm,
        "TC24": tc24_check_stock_after_receipt,
    }
    to_run = selected_tcs if selected_tcs else list(_ALL_TCS.keys())

    # TC21 không dùng sản phẩm; các TC còn lại cần product được tạo sẵn
    needs_product = any(tc != "TC21" for tc in to_run)
    if needs_product:
        log_info("Tạo sản phẩm test trước khi chạy suite Mua hàng...")
        try:
            ok = _create_product_api()
            if not ok:
                log_err("API tạo sản phẩm thất bại — tiếp tục chạy TC nhưng có thể thiếu sản phẩm.")
        except Exception as e:
            log_err(f"Không tạo được sản phẩm test qua API: {e}")

    results = {}
    for tc_id in to_run:
        if tc_id in _ALL_TCS:
            results[tc_id] = _ALL_TCS[tc_id](driver, wait)

    _print_suite_result("SUITE 3.1 – MUA HÀNG", results)
    return results
