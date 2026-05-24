"""
Module xử lý tạo sản phẩm trong Odoo
"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from config import PRODUCT_NAME, PRODUCT_PRICE, PRODUCT_QTY
from helpers import (log_step, log_info, log_ok, log_err, safe_click,
                     wait_for_toast_gone)


def create_product(driver, wait):
    """Tạo sản phẩm mới trong Odoo"""
    log_step(1, f"TẠO SẢN PHẨM: {PRODUCT_NAME}")

    # Vào menu Sales > Products > Products
    log_info("Mở menu Sales...")
    safe_click(driver, wait, "//div[contains(text(),'Sales')]")
    time.sleep(1)

    log_info("Mở Products...")
    safe_click(driver, wait, "(//span[contains(text(),'Products')])[1]")
    safe_click(driver, wait, "//a[normalize-space()='Products']")
    time.sleep(2)

    # Nhấn Tạo / New
    log_info("Nhấn nút Tạo mới...")
    safe_click(driver, wait, "//button[contains(.,'Mới') or contains(.,'New') or contains(.,'Tạo') or contains(.,'Create')]")
    time.sleep(2)

    # Điền tên sản phẩm
    log_info(f"Điền tên sản phẩm: {PRODUCT_NAME}")
    name_field = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "(//textarea[@id='name_0'])[1]")))
    name_field.triple_click() if hasattr(name_field, 'triple_click') else None
    name_field.send_keys(Keys.CONTROL + "a")
    name_field.send_keys(PRODUCT_NAME)
    time.sleep(0.5)

    # Điền giá bán
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

    # Lưu
    log_info("Lưu sản phẩm...")
    try:
        save_btn = driver.find_element(By.XPATH,"(//i[@class='fa fa-cloud-upload fa-fw'])[1]")
        driver.execute_script("arguments[0].click();", save_btn)
    except Exception:
        # Odoo auto-save khi rời form, dùng breadcrumb
        pass
    time.sleep(2)
    wait_for_toast_gone(wait)

    # Kiểm tra sản phẩm đã được lưu (URL chứa id)
    wait.until(lambda d: d.find_element(By.XPATH, "(//span[@class='min-w-0 text-truncate'])[1]").text.strip() != "New")
    log_ok(f"Tạo sản phẩm '{PRODUCT_NAME}' thành công! URL: {driver.current_url}")

    # Cập nhật số lượng tồn kho
    _update_inventory(driver, wait)


def _update_inventory(driver, wait):
    """Cập nhật số lượng tồn kho cho sản phẩm"""
    log_info(f"Cập nhật số lượng tồn kho: {PRODUCT_QTY}...")
    try:
        # Nhấn nút "Cập nhật số lượng" / "Update Quantity"
        update_qty_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//button[contains(.,'Cập nhật số lượng') or contains(.,'Update Quantity') "
            "or contains(.,'Số lượng') and contains(@class,'btn')]")))
        driver.execute_script("arguments[0].click();", update_qty_btn)
        time.sleep(2)

        # Nhấn "Tạo" / "Create" trong màn hình quản lý tồn kho
        try:
            create_quant_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
                "//button[contains(.,'Mới') or contains(.,'New') or contains(.,'Tạo') or contains(.,'Create')]"
                "[not(contains(@class,'o_invisible'))]")))
            driver.execute_script("arguments[0].click();", create_quant_btn)
            time.sleep(1.5)
        except Exception:
            pass  # Odoo 17 có thể hiển thị trực tiếp form không cần nhấn Create

        # Điền số lượng vào trường "Quantity On Hand" / "Số lượng thực tế"
        qty_input = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//div[@name='inventory_quantity']//input | "
            "//td[@name='inventory_quantity']//input | "
            "//input[@id='inventory_quantity_0'] | "
            "//div[@name='quantity']//input | "
            "//label[contains(.,'Số lượng') or contains(.,'Quantity')]"
            "/following-sibling::div//input | "
            "//td[@name='quantity']//input")))
        qty_input.click()
        qty_input.send_keys(Keys.CONTROL + "a")
        qty_input.send_keys(PRODUCT_QTY)
        time.sleep(0.5)

        # Nhấn "Áp dụng tất cả" / "Apply All" để xác nhận
        apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//button[contains(.,'Áp dụng tất cả') or contains(.,'Apply All') "
            "or contains(.,'Áp dụng') or contains(.,'Apply')]")))
        driver.execute_script("arguments[0].click();", apply_btn)
        time.sleep(1.5)

        # Xử lý popup xác nhận nếu có
        try:
            confirm_btn = WebDriverWait(driver, 4).until(EC.element_to_be_clickable((By.XPATH,
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
