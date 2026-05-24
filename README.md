# Odoo Automation Project

Script tự động hóa các tác vụ trên hệ thống Odoo sử dụng Selenium.

## Chức năng

1. Đăng nhập vào Odoo
2. Tạo sản phẩm mới
3. Cập nhật số lượng tồn kho
4. Tạo đơn mua hàng và nhập kho
5. Tạo đơn bán hàng và xuất kho

## Cài đặt

```bash
pip install -r requirements.txt
```

## Cấu hình

Chỉnh sửa các thông số trong file `odoo_automation.py`:

- `ODOO_URL`: URL của hệ thống Odoo
- `ODOO_USER`: Tài khoản đăng nhập
- `ODOO_PASS`: Mật khẩu
- `PRODUCT_PRICE`: Giá sản phẩm
- `PRODUCT_QTY`: Số lượng tồn kho
- `ORDER_QTY`: Số lượng đặt hàng

## Chạy script

```bash
python odoo_automation.py
```

## Yêu cầu

- Python 3.7+
- Chrome browser
- ChromeDriver (tự động tải qua selenium)
