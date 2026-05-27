"""
Main script - Điểm vào chính của chương trình Odoo Automation

Cách chạy:
  python main.py          → chạy automation bình thường
  python main.py test     → chạy toàn bộ test suite (Suite 1.1 Login)
  python main.py test login  → chỉ chạy suite đăng nhập
"""
import warnings
warnings.filterwarnings("ignore", message="urllib3")

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import traceback
from selenium.webdriver.support.ui import WebDriverWait

from config import PRODUCT_NAME, PRODUCT_QTY
from helpers import setup_driver, log_err, show_results_overlay, init_progress
from login import login, run_login_suite
from logout import run_logout_suite
from product import create_product, run_product_suite
from purchase import create_purchase_and_receipt, run_purchase_suite
from inventory import run_inventory_suite
from sales import create_sale_and_delivery, run_sales_suite


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


def run_tests(driver, wait, suite=None, selected_tcs=None):
    """Chạy test suite theo tên, hoặc chạy tất cả nếu không chỉ định."""
    _labels = {
        "login":     "Suite 1.1 – Đăng nhập",
        "logout":    "Suite 1.2 – Đăng xuất",
        "product":   "Suite 2.1 – Sản phẩm",
        "inventory": "Suite 2.2 – Tồn kho",
        "purchase":  "Suite 3.1 – Mua hàng",
        "sales":     "Suite 3.2 – Bán hàng",
    }
    _suite_tcs = {
        "login":     ["TC01","TC02","TC03","TC04","TC05"],
        "logout":    ["TC06","TC07","TC08","TC09"],
        "product":   ["TC10","TC11","TC12","TC13","TC14","TC15","TC16","TC17"],
        "inventory": ["TC18","TC19"],
        "purchase":  ["TC20","TC21","TC22","TC23","TC24"],
        "sales":     ["TC25","TC26","TC27","TC28","TC29","TC30","TC31","TC32","TC33","TC34"],
    }
    suites = {
        "login":     run_login_suite,
        "logout":    run_logout_suite,
        "product":   run_product_suite,
        "inventory": run_inventory_suite,
        "purchase":  run_purchase_suite,
        "sales":     run_sales_suite,
    }

    if suite and suite in suites:
        tc_ids = selected_tcs or _suite_tcs.get(suite, [])
        init_progress(driver, tc_ids, _labels.get(suite, suite))
        fn = suites[suite]
        results = fn(driver, wait, selected_tcs=selected_tcs) if selected_tcs else fn(driver, wait)
        show_results_overlay(driver, _labels.get(suite, suite), results or {})
    else:
        all_results = {}
        print("\n  Chạy tất cả test suites...\n")
        for name, fn in suites.items():
            print(f"\n>>> Suite: {name.upper()}")
            tc_ids = _suite_tcs.get(name, [])
            init_progress(driver, tc_ids, _labels.get(name, name))
            results = fn(driver, wait)
            all_results.update(results or {})
        show_results_overlay(driver, "Tất cả Suites", all_results)


def main():
    args = sys.argv[1:]  # bỏ tên script
    mode = args[0] if args else "auto"
    suite = args[1] if len(args) > 1 else None
    # args[2] = "TC12,TC15,TC16" → filter TC lẻ khi chạy từ web UI
    selected_tcs = args[2].split(",") if len(args) > 2 else None

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    try:
        if mode == "test":
            run_tests(driver, wait, suite, selected_tcs)
        else:
            run_automation(driver, wait)

    except Exception as e:
        log_err(f"Lỗi nghiêm trọng: {e}")
        traceback.print_exc()

    finally:
        try:
            input("\n⏸  Nhấn Enter để đóng trình duyệt...")
        except EOFError:
            pass
        driver.quit()


if __name__ == "__main__":
    main()
