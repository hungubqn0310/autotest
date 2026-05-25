"""
Cấu hình cho Odoo Automation
Chỉnh sửa các thông số ở đây
"""
from datetime import datetime

# ============================================================
# ⚙️ CẤU HÌNH - Chỉnh sửa các thông số
# ============================================================
ODOO_URL    = "https://lananh.odoo.com/"   # <== URL Odoo
ODOO_USER   = "phamlananh13022004@gmail.com"         # <== Tài khoản đăng nhập
ODOO_PASS   = "Hlanh@9413"                                # <== Mật khẩu
# ============================================================

# Tên sản phẩm tự động theo ngày giờ
now = datetime.now()
PRODUCT_NAME  = f"SP_TEST_{now.strftime('%d%m%Y_%H%M%S')}"
PRODUCT_PRICE = "10000"
PRODUCT_QTY   = "50"          # <== Số lượng tồn kho ban đầu
ORDER_QTY     = "2"           # <== Số lượng mua trên đơn hàng
