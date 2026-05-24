"""
Main script - Điểm vào chính của chương trình Odoo Automation

Cách chạy:
  python main.py          → chạy automation bình thường
  python main.py test     → chạy toàn bộ test suite (Suite 1.1 Login)
  python main.py test login  → chỉ chạy suite đăng nhập
"""
import sys
import traceback
from selenium.webdriver.support.ui import WebDriverWait

from config import PRODUCT_NAME, PRODUCT_QTY
from helpers import setup_driver, log_err
from login import login, run_login_suite
from logout import run_logout_suite
from product import create_product
from purchase import create_purchase_and_receipt
from sales import create_sale_and_delivery


def run_automation(driver, wait):
    """Chạy toàn bộ quy trình automation chính."""
    print("\n" + "="*60)
    print("  BẮT ĐẦU TỰ ĐỘNG HÓA ODOO")
    print(f"  Tên sản phẩm sẽ tạo: {PRODUCT_NAME}")
    print(f"  Số lượng tồn kho: {PRODUCT_QTY}")
    print("="*60)

    login(driver, wait)
    create_product(driver, wait)
    create_purchase_and_receipt(driver, wait)
    create_sale_and_delivery(driver, wait)

    print("\n" + "="*60)
    print("  HOÀN THÀNH TẤT CẢ CÁC BƯỚC!")
    print("="*60 + "\n")


def run_tests(driver, wait, suite=None):
    """Chạy test suite theo tên, hoặc chạy tất cả nếu không chỉ định."""
    suites = {
        "login":  run_login_suite,
        "logout": run_logout_suite,
        # Thêm suite khác vào đây khi có: "product": run_product_suite, ...
    }

    if suite and suite in suites:
        suites[suite](driver, wait)
    else:
        print("\n  Chạy tất cả test suites...\n")
        for name, fn in suites.items():
            print(f"\n>>> Suite: {name.upper()}")
            fn(driver, wait)


def main():
    args = sys.argv[1:]  # bỏ tên script
    mode = args[0] if args else "auto"
    suite = args[1] if len(args) > 1 else None

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    try:
        if mode == "test":
            run_tests(driver, wait, suite)
        else:
            run_automation(driver, wait)

    except Exception as e:
        log_err(f"Lỗi nghiêm trọng: {e}")
        traceback.print_exc()

    finally:
        input("\n⏸  Nhấn Enter để đóng trình duyệt...")
        driver.quit()


if __name__ == "__main__":
    main()
