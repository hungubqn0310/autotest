"""
Module xử lý đăng nhập vào Odoo
"""
import time
from config import ODOO_URL, ODOO_USER, ODOO_PASS
from helpers import log_step, log_ok, safe_fill, safe_click


def login(driver, wait):
    """Đăng nhập vào hệ thống Odoo"""
    log_step(0, "ĐĂNG NHẬP")
    driver.get(f"{ODOO_URL}")
    time.sleep(2)

    safe_fill(driver, wait, "//input[@id='login']", ODOO_USER)
    safe_fill(driver, wait, "//input[@id='password']", ODOO_PASS)
    time.sleep(1)
    safe_click(driver, wait, "//button[normalize-space()='Log in']")
    time.sleep(3)

    if "/odoo" in driver.current_url:
        log_ok("Đăng nhập thành công!")
    else:
        raise Exception("Đăng nhập thất bại! Kiểm tra lại URL / tài khoản / mật khẩu.")
