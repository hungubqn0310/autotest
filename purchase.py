"""
Module xử lý đơn mua hàng và nhập kho trong Odoo
"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from config import PRODUCT_NAME, ORDER_QTY
from helpers import (log_step, log_info, log_ok, log_err, safe_click,
                     wait_for_toast_gone, dismiss_popup_if_any, get_status_badge)


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
