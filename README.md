# Odoo Automation Project

Tự động hóa và kiểm thử hệ thống Odoo 17 bằng Selenium + giao diện web.

## Yêu cầu hệ thống

| Thành phần | Phiên bản |
|---|---|
| Python | **3.10 trở lên** |
| Google Chrome | Phiên bản mới nhất |
| ChromeDriver | **Tự động tải** (không cần cài thủ công) |

> Không cần cài ChromeDriver thủ công — `webdriver-manager` sẽ tự tải đúng phiên bản.

---

## Cài đặt

### 1. Clone hoặc tải project

```bash
git clone <repo-url>
cd odoo_automation_project
```

### 2. Cài thư viện Python

```bash
pip install -r requirements.txt
```

Hoặc nếu dùng virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

### 3. Cấu hình tài khoản Odoo

Chỉnh sửa file `config.py`:

```python
ODOO_URL   = "https://your-odoo.com/"
ODOO_USER  = "email@example.com"
ODOO_PASS  = "your-password"
```

---

## Cách chạy

### Giao diện web (khuyến nghị)

```bash
python web_ui.py
```

Mở trình duyệt tại `http://localhost:5000` — chọn suite và test case muốn chạy, xem kết quả real-time.

### Dòng lệnh

```bash
# Chạy toàn bộ automation (tạo sản phẩm → mua → bán)
python main.py

# Chạy toàn bộ một suite test
python main.py test sales
python main.py test purchase
python main.py test product

# Chạy một số test case cụ thể
python main.py test sales TC30,TC31,TC32
```

---

## Cấu trúc project

```
odoo_automation_project/
├── config.py        # Cấu hình URL, tài khoản, tham số
├── main.py          # Entry point chính
├── web_ui.py        # Giao diện web (Flask)
├── helpers.py       # Hàm dùng chung (driver, log, click...)
├── login.py         # Suite 1.1 – Đăng nhập (TC01–TC05)
├── logout.py        # Suite 1.2 – Đăng xuất (TC06–TC09)
├── product.py       # Suite 2.1 – Sản phẩm (TC10–TC17)
├── inventory.py     # Suite 2.2 – Tồn kho (TC18–TC19)
├── purchase.py      # Suite 3.1 – Mua hàng (TC20–TC24)
├── sales.py         # Suite 3.2 – Bán hàng (TC25–TC34)
└── requirements.txt
```

---

## Danh sách test suite

| Suite | Module | Test Cases |
|---|---|---|
| 1.1 – Đăng nhập | login.py | TC01–TC05 |
| 1.2 – Đăng xuất | logout.py | TC06–TC09 |
| 2.1 – Sản phẩm | product.py | TC10–TC17 |
| 2.2 – Tồn kho | inventory.py | TC18–TC19 |
| 3.1 – Mua hàng | purchase.py | TC20–TC24 |
| 3.2 – Bán hàng | sales.py | TC25–TC34 |

---

## Lưu ý

- Mỗi lần chạy tạo sản phẩm mới có tên theo timestamp (ví dụ: `SP_TEST_26052026_153045`) để tránh trùng lặp.
- `PRODUCT_QTY`: số lượng tồn kho ban đầu (mặc định 50).
- `ORDER_QTY`: số lượng mỗi đơn hàng (mặc định 2).
