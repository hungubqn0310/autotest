"""
Main script - Điểm vào chính của chương trình Odoo Automation
"""
import traceback
from selenium.webdriver.support.ui import WebDriverWait

from config import PRODUCT_NAME, PRODUCT_QTY
from helpers import setup_driver, log_err
from login import login
from product import create_product
from purchase import create_purchase_and_receipt
from sales import create_sale_and_delivery


def main():
    """Hàm chính chạy toàn bộ quy trình automation"""
    print("\n" + "="*60)
    print("  🚀 BẮT ĐẦU TỰ ĐỘNG HÓA ODOO")
    print(f"  📦 Tên sản phẩm sẽ tạo: {PRODUCT_NAME}")
    print(f"  🔢 Số lượng tồn kho: {PRODUCT_QTY}")
    print("="*60)

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    try:
        # Bước 0: Đăng nhập
        login(driver, wait)

        # Bước 1: Tạo sản phẩm
        create_product(driver, wait)

        # Bước 2: Tạo đơn mua và nhập kho
        create_purchase_and_receipt(driver, wait)

        # Bước 3: Tạo đơn bán và xuất kho
        create_sale_and_delivery(driver, wait)

        print("\n" + "="*60)
        print("  🎉 HOÀN THÀNH TẤT CẢ CÁC BƯỚC!")
        print("="*60 + "\n")

    except Exception as e:
        log_err(f"Lỗi nghiêm trọng: {e}")
        traceback.print_exc()

    finally:
        input("\n⏸  Nhấn Enter để đóng trình duyệt...")
        driver.quit()


if __name__ == "__main__":
    main()
