"""
Module xử lý đơn bán hàng và xuất kho trong Odoo
"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from config import PRODUCT_NAME, ORDER_QTY
from helpers import (log_step, log_info, log_ok, log_err, safe_click,
                     wait_for_toast_gone, dismiss_popup_if_any)


def create_sale_and_delivery(driver, wait):
    """Tạo đơn bán hàng và xuất kho"""
    log_step(3, "TẠO ĐƠN BÁN HÀNG & XUẤT KHO")

    # Vào menu Bán hàng
    log_info("Mở menu Bán hàng...")
    safe_click(driver, wait, "//a[@title='Home menu']")
    safe_click(driver, wait, "//div[contains(text(),'Sales')]")
    time.sleep(1)

    # Nhấn Tạo
    log_info("Nhấn Tạo đơn bán...")
    safe_click(driver, wait,
        "//button[contains(.,'Mới') or contains(.,'New') or contains(.,'Tạo') or contains(.,'Create')]")
    time.sleep(2)

    # Chọn Khách hàng đầu tiên
    _select_customer(driver, wait)

    # Thêm dòng sản phẩm
    _add_product_line(driver, wait)

    # Điền số lượng
    _fill_quantity(driver, wait)

    # Chờ 3s để nhận sản phẩm
    time.sleep(3)

    # Xác nhận SO
    _confirm_sale_order(driver, wait)

    # Xuất kho
    _process_delivery(driver, wait)


def _select_customer(driver, wait):
    """Chọn khách hàng đầu tiên"""
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
    """Thêm dòng sản phẩm vào đơn bán"""
    log_info("Thêm dòng sản phẩm...")
    try:
        add_line_btn = driver.find_element(By.XPATH,
            "//button[contains(.,'Thêm sản phẩm') or contains(.,'Add a product') or contains(.,'Add a line')]")
        driver.execute_script("arguments[0].click();", add_line_btn)
        time.sleep(1)
    except Exception:
        log_err("Không tìm thấy nút thêm dòng sản phẩm.")

    # Điền tên sản phẩm vào dòng SO
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
    """Điền số lượng vào đơn bán"""
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
    """Xác nhận đơn bán hàng"""
    log_info("Xác nhận đơn bán hàng...")
    safe_click(driver, wait,
        "//button[contains(.,'Xác nhận đơn hàng') or contains(.,'Confirm') or "
        "contains(.,'Confirm Sale') or (contains(.,'Xác nhận') and contains(@class,'btn-primary'))]")
    time.sleep(3)
    wait_for_toast_gone(wait)
    dismiss_popup_if_any(driver)
    time.sleep(1)

    # Kiểm tra trạng thái SO
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
    """Xử lý phiếu xuất kho"""
    # Mở danh sách phiếu xuất
    first_delivery = driver.find_element(By.XPATH,"//span[@class='o_stat_text']")
    first_delivery.click()
    time.sleep(1)

    # Xác nhận phiếu xuất kho (Validate)
    log_info("Xác nhận phiếu xuất kho...")
    safe_click(driver, wait,
        "//button[contains(.,'Xác nhận') or contains(.,'Validate')]")
    time.sleep(2)
    dismiss_popup_if_any(driver)
    time.sleep(2)
    wait_for_toast_gone(wait)

    # Xử lý dialog nếu còn
    try:
        imm_btn = driver.find_element(By.XPATH,
            "//button[contains(.,'Validate') or contains(.,'Xác nhận')]")
        driver.execute_script("arguments[0].click();", imm_btn)
        time.sleep(2)
    except Exception:
        pass

    # Kiểm tra trạng thái phiếu xuất kho
    try:
        del_status = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@class,'o_statusbar_status')]//button[@aria-checked='true']"))).text.strip()
        if any(s in del_status.lower() for s in ["done", "đã hoàn", "hoàn tất", "xong"]):
            log_ok(f"Xuất kho thành công! Trạng thái phiếu: '{del_status}'")
        else:
            log_ok(f"Phiếu xuất kho đã xử lý. Trạng thái: '{del_status}'")
    except Exception:
        log_ok("Đã xác nhận phiếu xuất kho (không đọc được badge trạng thái).")
