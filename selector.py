"""
Giao diện chọn test case tương tác trên terminal.
"""
import os
import re

# ── Registry test cases theo suite ────────────────────────────
SUITE_META = {
    "login": {
        "label": "Suite 1.1 – Đăng nhập",
        "tcs": [],           # chạy cả suite, không tách TC lẻ
    },
    "logout": {
        "label": "Suite 1.2 – Đăng xuất",
        "tcs": [],
    },
    "product": {
        "label": "Suite 2.1 – Sản phẩm",
        "tcs": [],
    },
    "purchase": {
        "label": "Suite 3.1 – Mua hàng",
        "tcs": [
            ("TC12", "Tạo đơn mua hàng và xác nhận thành công"),
            ("TC13", "Tạo đơn mua – không chọn nhà cung cấp"),
            ("TC14", "Nhập kho thành công sau khi xác nhận PO"),
            ("TC15", "Kiểm tra trạng thái PO sau khi xác nhận"),
            ("TC16", "Kiểm tra tồn kho tăng sau khi nhập kho"),
            ("TC17", "Nhập số lượng âm vào đơn mua"),
        ],
    },
}

_SUITE_KEYS = list(SUITE_META.keys())   # thứ tự cố định


# ── Helpers in/out ─────────────────────────────────────────────

def _clear():
    os.system("clear" if os.name != "nt" else "cls")


def _banner():
    w = 60
    print("╔" + "═" * (w - 2) + "╗")
    print("║" + "  🧪  ODOO AUTOTEST – CHỌN TEST".center(w - 2) + "║")
    print("╚" + "═" * (w - 2) + "╝")
    print()


def _parse_selection(raw: str, max_idx: int) -> list[int] | None:
    """
    Phân tích chuỗi nhập: '1', '1,3,5', '2-4', 'all', 'a'.
    Trả về list index 0-based, hoặc None nếu không hợp lệ.
    """
    raw = raw.strip().lower()
    if raw in ("all", "a"):
        return list(range(max_idx))

    indices: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if lo < 1 or hi > max_idx or lo > hi:
                return None
            indices.extend(range(lo - 1, hi))
        elif re.fullmatch(r"\d+", part):
            n = int(part)
            if n < 1 or n > max_idx:
                return None
            indices.append(n - 1)
        else:
            return None

    return sorted(set(indices)) if indices else None


# ── Màn hình 1: Chọn suite ─────────────────────────────────────

def _select_suite() -> str | None:
    """Hiển thị menu suite, trả về key suite được chọn (hoặc None để thoát)."""
    while True:
        _clear()
        _banner()
        print("  Chọn Suite cần test:\n")
        for i, key in enumerate(_SUITE_KEYS, 1):
            label = SUITE_META[key]["label"]
            n_tc  = len(SUITE_META[key]["tcs"])
            tc_hint = f"  ({n_tc} TC)" if n_tc else "  (cả suite)"
            print(f"  [{i}] {label}{tc_hint}")
        print()
        print("  [q] Thoát")
        print()
        raw = input("  Chọn (số): ").strip().lower()

        if raw == "q":
            return None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(_SUITE_KEYS):
                return _SUITE_KEYS[idx]
        print("\n  ⚠  Lựa chọn không hợp lệ, thử lại...")
        input("  Nhấn Enter để tiếp tục...")


# ── Màn hình 2: Chọn TC lẻ (nếu suite có TC registry) ──────────

def _select_tcs(suite_key: str) -> list[str] | None:
    """
    Hiển thị danh sách TC, trả về list TC id được chọn.
    Trả None nếu user thoát.
    Trả [] nghĩa là chạy cả suite.
    """
    meta = SUITE_META[suite_key]
    tcs  = meta["tcs"]

    if not tcs:
        return []   # suite không có TC lẻ → chạy cả suite

    while True:
        _clear()
        _banner()
        print(f"  Suite: {meta['label']}\n")
        for i, (tc_id, desc) in enumerate(tcs, 1):
            print(f"  [{i:2}] {tc_id}  –  {desc}")
        print()
        print("  Nhập: số (1,3,5 | 2-4 | all)    [b] Quay lại    [q] Thoát")
        print()
        raw = input("  Chọn TC: ").strip().lower()

        if raw == "q":
            return None
        if raw == "b":
            return "back"   # type: ignore

        idxs = _parse_selection(raw, len(tcs))
        if idxs is None:
            print("\n  ⚠  Nhập không hợp lệ (vd: 1,3,5 | 2-4 | all)")
            input("  Nhấn Enter để thử lại...")
            continue

        selected_ids = [tcs[i][0] for i in idxs]

        # Xác nhận lại
        _clear()
        _banner()
        print(f"  Suite: {meta['label']}\n")
        print("  Sẽ chạy:")
        for tc_id in selected_ids:
            desc = next(d for tid, d in tcs if tid == tc_id)
            print(f"    ✔  {tc_id}  –  {desc}")
        print()
        confirm = input("  Xác nhận chạy? [Enter = có | b = chọn lại]: ").strip().lower()
        if confirm == "b":
            continue
        return selected_ids


# ── Entry point chính ──────────────────────────────────────────

def show_menu() -> tuple[str, list[str]]:
    """
    Hiển thị toàn bộ menu chọn.
    Trả về (suite_key, [tc_ids]).
    tc_ids rỗng = chạy cả suite.
    """
    while True:
        suite_key = _select_suite()
        if suite_key is None:
            raise SystemExit(0)

        result = _select_tcs(suite_key)

        if result is None:
            raise SystemExit(0)
        if result == "back":   # type: ignore
            continue
        return suite_key, result
