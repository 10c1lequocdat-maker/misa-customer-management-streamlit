import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

# ============================================================
#  WEB APP: QUẢN LÝ KHÁCH HÀNG MISA
#  Một file app.py độc lập, lưu dữ liệu bằng data/customers.json
# ============================================================

DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "customers.json"

PRODUCTS = ["meInvoice", "MISA SME", "MISA AMIS", "Bamboo"]
PACKAGES = ["Starter", "Standard", "Professional", "Enterprise"]
CUSTOMER_TYPES = ["Cá nhân", "Doanh nghiệp"]
SERVICE_STATUS_ALL = ["Tất cả", "Active", "Sắp hết hạn", "Expired", "Trial", "Đã xóa"]

st.set_page_config(
    page_title="Quản lý khách hàng MISA",
    page_icon="📘",
    layout="wide",
)

# ----------------------------
# CSS giao diện
# ----------------------------
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    .misa-header {
        background: linear-gradient(90deg, #0046b8, #0066d9);
        color: white;
        padding: 18px 22px;
        border-radius: 12px;
        text-align: center;
        font-size: 30px;
        font-weight: 800;
        margin-bottom: 18px;
        letter-spacing: .5px;
    }
    .misa-subtitle {color:#345; margin-top:-8px; margin-bottom:14px;}
    .section-card {
        border: 1px solid #d7e6f7;
        border-radius: 12px;
        padding: 16px 18px;
        background: #ffffff;
        box-shadow: 0 1px 5px rgba(0,0,0,.03);
        margin-bottom: 15px;
    }
    .section-title {
        color: #0052cc;
        font-size: 24px;
        font-weight: 800;
        margin: 6px 0 14px 0;
    }
    .small-note {
        border:1px solid #ffd591;
        background:#fff7e6;
        color:#5f3b00;
        padding:12px 14px;
        border-radius:10px;
        margin-top:10px;
    }
    .info-note {
        border:1px solid #91caff;
        background:#f0f7ff;
        color:#173b64;
        padding:12px 14px;
        border-radius:10px;
        margin-top:10px;
    }
    .danger-note {
        border:1px solid #ffa39e;
        background:#fff1f0;
        color:#a8071a;
        padding:12px 14px;
        border-radius:10px;
        margin-top:10px;
    }
    .metric-card {
        border: 1px solid #d7e6f7;
        border-radius: 12px;
        background: #f8fbff;
        padding: 15px;
        text-align:center;
    }
    div[data-testid="stSidebar"] {
        background: #f7fbff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 1. LƯU TRỮ DỮ LIỆU
# ============================================================

def ensure_data_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def load_customers() -> List[Dict[str, Any]]:
    ensure_data_file()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        st.error("File customers.json đang lỗi định dạng. Hệ thống tạm nạp danh sách rỗng.")
        return []


def save_customers(customers: List[Dict[str, Any]]) -> None:
    ensure_data_file()
    DATA_FILE.write_text(json.dumps(customers, ensure_ascii=False, indent=4), encoding="utf-8")


# ============================================================
# 2. HÀM CHUẨN HÓA - KIỂM TRA DỮ LIỆU
# ============================================================

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def remove_accents(text: str) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def normalize_keyword(text: str) -> str:
    return remove_accents(normalize_spaces(text)).lower()


def digits_only(text: str) -> str:
    return re.sub(r"\D", "", str(text or ""))


def parse_customer_no(customer_id: str) -> int:
    match = re.search(r"KH(\d+)$", str(customer_id or "").upper())
    return int(match.group(1)) if match else 0


def generate_next_customer_id(customers: List[Dict[str, Any]]) -> str:
    """Sinh mã KH mới dựa trên mã lớn nhất trong toàn bộ file, kể cả bản ghi đã xóa."""
    max_no = 0
    for c in customers:
        max_no = max(max_no, parse_customer_no(c.get("customer_id", "")))
    return f"KH{max_no + 1:03d}"


def email_is_valid(email: str) -> bool:
    if not email:
        return True
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}$", email))


def tax_code_is_valid(tax_code: str) -> bool:
    if not tax_code:
        return True
    tax_digits = digits_only(tax_code)
    return len(tax_digits) in (10, 13)


def calculate_service_status(expiry_date: str) -> str:
    """Tính trạng thái thuê bao động dựa trên ngày hết hạn."""
    try:
        exp = datetime.strptime(expiry_date, "%Y-%m-%d").date()
    except Exception:
        return "Trial"

    days_left = (exp - date.today()).days
    if days_left < 0:
        return "Expired"
    if days_left <= 30:
        return "Sắp hết hạn"
    return "Active"


def calculate_payment_status(balance: float) -> str:
    """Theo mô tả: 0 là đã thanh toán, >0 chưa thanh toán, <0 là đã thanh toán nhưng dư."""
    if balance == 0:
        return "Đã thanh toán"
    if balance > 0:
        return "Chưa thanh toán"
    return f"Đã thanh toán (Dư: {abs(balance):,.0f} VND)"


def active_customers(customers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [c for c in customers if not c.get("is_deleted", False)]


def enrich_customer(c: Dict[str, Any]) -> Dict[str, Any]:
    """Bổ sung trạng thái động để hiển thị."""
    c = dict(c)
    c["service_status"] = "Đã xóa" if c.get("is_deleted") else calculate_service_status(c.get("expiry_date", ""))
    c["payment_status"] = calculate_payment_status(float(c.get("balance", 0) or 0))
    return c


def validate_customer(
    customer: Dict[str, Any],
    customers: List[Dict[str, Any]],
    current_id: Optional[str] = None,
) -> List[str]:
    errors: List[str] = []

    # 10 trường bắt buộc theo mô tả
    required_fields = {
        "customer_id": "Mã khách hàng",
        "customer_name": "Tên khách hàng",
        "customer_type": "Loại khách hàng",
        "phone": "Số điện thoại",
        "address": "Địa chỉ",
        "product_service": "Sản phẩm cung cấp",
        "service_package": "Gói dịch vụ",
        "start_date": "Ngày bắt đầu",
        "expiry_date": "Ngày hết hạn",
        "balance": "Công nợ",
    }
    for key, label in required_fields.items():
        if customer.get(key) in (None, ""):
            errors.append(f"{label} không được để trống.")

    # Doanh nghiệp bắt buộc mã số thuế và người đại diện
    if customer.get("customer_type") == "Doanh nghiệp":
        if not customer.get("representative"):
            errors.append("Khách hàng doanh nghiệp phải có người đại diện.")
        if not customer.get("tax_code"):
            errors.append("Khách hàng doanh nghiệp phải có mã số thuế.")

    # Định dạng số điện thoại
    phone = digits_only(customer.get("phone", ""))
    if len(phone) != 10 or not phone.startswith("0"):
        errors.append("Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0.")

    # Unique phone trên bản ghi đang hoạt động
    for c in active_customers(customers):
        if current_id and c.get("customer_id") == current_id:
            continue
        if digits_only(c.get("phone", "")) == phone:
            errors.append("Số điện thoại đã tồn tại ở một khách hàng đang hoạt động.")
            break

    # Email, MST
    if not email_is_valid(customer.get("email", "")):
        errors.append("Email không đúng định dạng.")

    if customer.get("tax_code") and not tax_code_is_valid(customer.get("tax_code", "")):
        errors.append("Mã số thuế phải gồm 10 hoặc 13 chữ số.")

    # Date logic
    try:
        start = datetime.strptime(customer.get("start_date", ""), "%Y-%m-%d").date()
        expiry = datetime.strptime(customer.get("expiry_date", ""), "%Y-%m-%d").date()
        if expiry < start:
            errors.append("Ngày hết hạn phải lớn hơn hoặc bằng ngày bắt đầu.")
        if start < date.today() - timedelta(days=7):
            errors.append("Ngày bắt đầu không được lùi quá 07 ngày so với ngày hiện tại.")
    except Exception:
        errors.append("Ngày bắt đầu hoặc ngày hết hạn không hợp lệ.")

    # Danh mục đóng
    if customer.get("product_service") not in PRODUCTS:
        errors.append("Sản phẩm cung cấp không thuộc danh mục cho phép.")
    if customer.get("service_package") not in PACKAGES:
        errors.append("Gói dịch vụ không thuộc danh mục cho phép.")

    # Length
    if len(customer.get("notes", "")) > 500:
        errors.append("Ghi chú không được vượt quá 500 ký tự.")
    if len(customer.get("address", "")) > 250:
        errors.append("Địa chỉ không được vượt quá 250 ký tự.")

    return errors


def build_customer_record(
    customer_id: str,
    customer_name: str,
    customer_type: str,
    phone: str,
    email: str,
    address: str,
    representative: str,
    tax_code: str,
    product_service: str,
    service_package: str,
    start_date: date,
    expiry_date: date,
    balance: float,
    notes: str,
    created_at: Optional[str] = None,
    is_deleted: bool = False,
    deleted_at: Optional[str] = None,
) -> Dict[str, Any]:
    customer_id = normalize_spaces(customer_id).upper()
    customer_name = normalize_spaces(customer_name)
    phone = digits_only(phone)
    email = normalize_spaces(email).lower()
    address = normalize_spaces(address)
    representative = normalize_spaces(representative) or None
    tax_code = digits_only(tax_code) or None
    notes = normalize_spaces(notes)

    if customer_type == "Cá nhân":
        representative = None if not representative else representative
        tax_code = None if not tax_code else tax_code

    created = created_at or now_str()
    balance = float(balance or 0)
    record = {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "customer_type": customer_type,
        "phone": phone,
        "email": email,
        "address": address,
        "representative": representative,
        "tax_code": tax_code,
        "product_service": product_service,
        "service_package": service_package,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "service_status": calculate_service_status(expiry_date.strftime("%Y-%m-%d")),
        "payment_status": calculate_payment_status(balance),
        "balance": balance,
        "notes": notes,
        "created_at": created,
        "updated_at": now_str(),
        "is_deleted": is_deleted,
        "deleted_at": deleted_at,
    }
    return record


def customers_to_df(customers: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for i, c in enumerate(customers, start=1):
        c = enrich_customer(c)
        rows.append(
            {
                "STT": i,
                "Mã KH": c.get("customer_id", ""),
                "Tên khách hàng": c.get("customer_name", ""),
                "Loại KH": c.get("customer_type", ""),
                "SĐT": c.get("phone", ""),
                "Email": c.get("email", ""),
                "Sản phẩm": c.get("product_service", ""),
                "Gói DV": c.get("service_package", ""),
                "Ngày hết hạn": c.get("expiry_date", ""),
                "Trạng thái": c.get("service_status", ""),
                "Công nợ": f"{float(c.get('balance', 0) or 0):,.0f} VND",
                "Đã xóa": c.get("is_deleted", False),
            }
        )
    return pd.DataFrame(rows)


def find_customer_by_id(customers: List[Dict[str, Any]], customer_id: str) -> Optional[Dict[str, Any]]:
    customer_id = normalize_spaces(customer_id).upper()
    for c in customers:
        if c.get("customer_id") == customer_id:
            return c
    return None


def render_customer_detail(c: Dict[str, Any]) -> None:
    c = enrich_customer(c)
    st.markdown("#### Thông tin chi tiết khách hàng")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Mã khách hàng:** {c.get('customer_id', '')}")
        st.write(f"**Tên khách hàng:** {c.get('customer_name', '')}")
        st.write(f"**Loại khách hàng:** {c.get('customer_type', '')}")
        st.write(f"**Số điện thoại:** {c.get('phone', '')}")
        st.write(f"**Email:** {c.get('email', '')}")
        st.write(f"**Địa chỉ:** {c.get('address', '')}")
        st.write(f"**Người đại diện:** {c.get('representative') or '---'}")
        st.write(f"**Mã số thuế:** {c.get('tax_code') or '---'}")
    with col2:
        st.write(f"**Sản phẩm:** {c.get('product_service', '')}")
        st.write(f"**Gói dịch vụ:** {c.get('service_package', '')}")
        st.write(f"**Ngày bắt đầu:** {c.get('start_date', '')}")
        st.write(f"**Ngày hết hạn:** {c.get('expiry_date', '')}")
        st.write(f"**Trạng thái dịch vụ:** {c.get('service_status', '')}")
        st.write(f"**Trạng thái tài chính:** {c.get('payment_status', '')}")
        st.write(f"**Công nợ:** {float(c.get('balance', 0) or 0):,.0f} VND")
        st.write(f"**Ghi chú:** {c.get('notes', '') or '---'}")
    st.caption(
        f"created_at: {c.get('created_at', '---')} | updated_at: {c.get('updated_at', '---')} | "
        f"is_deleted: {c.get('is_deleted', False)} | deleted_at: {c.get('deleted_at') or '---'}"
    )


# ============================================================
# 3. KHỞI TẠO SESSION
# ============================================================

if "customers" not in st.session_state:
    st.session_state.customers = load_customers()

# Cập nhật trạng thái động khi nạp lên RAM
for item in st.session_state.customers:
    item["service_status"] = calculate_service_status(item.get("expiry_date", ""))
    item["payment_status"] = calculate_payment_status(float(item.get("balance", 0) or 0))

# ============================================================
# 4. GIAO DIỆN CHÍNH
# ============================================================

st.markdown('<div class="misa-header">QUẢN LÝ KHÁCH HÀNG MISA</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## MISA")
    st.markdown("### Menu chức năng")
    menu = st.radio(
        "Chọn chức năng",
        [
            "Nhập thông tin khách hàng",
            "Cập nhật thông tin khách hàng",
            "Tìm kiếm thông tin khách hàng",
            "Xóa thông tin khách hàng",
            "Xem danh sách thông tin khách hàng",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(f"Dữ liệu: {DATA_FILE.as_posix()}")

customers = st.session_state.customers

# ============================================================
# 5. CHỨC NĂNG 1: NHẬP THÔNG TIN KHÁCH HÀNG
# ============================================================

if menu == "Nhập thông tin khách hàng":
    st.markdown('<div class="section-title">Nhập thông tin khách hàng</div>', unsafe_allow_html=True)
    st.markdown("<p class='misa-subtitle'>Hệ thống tự động sinh mã khách hàng và lưu hồ sơ vào file JSON.</p>", unsafe_allow_html=True)

    next_id = generate_next_customer_id(customers)

    with st.form("add_form", clear_on_submit=False):
        st.markdown("#### 1. Thông tin định danh và liên hệ")
        c1, c2, c3 = st.columns(3)
        with c1:
            customer_id = st.text_input("Mã khách hàng *", value=next_id, disabled=True)
            customer_type = st.selectbox("Loại khách hàng *", CUSTOMER_TYPES)
            phone = st.text_input("Số điện thoại *", max_chars=10)
        with c2:
            customer_name = st.text_input("Tên khách hàng *")
            email = st.text_input("Email")
            address = st.text_input("Địa chỉ *", max_chars=250)
        with c3:
            representative = st.text_input("Người đại diện")
            tax_code = st.text_input("Mã số thuế")
            if customer_type == "Doanh nghiệp":
                st.caption("Doanh nghiệp bắt buộc nhập Người đại diện và Mã số thuế.")
            else:
                st.caption("Cá nhân có thể bỏ trống Người đại diện và Mã số thuế.")

        st.markdown("Thông tin dịch vụ sử dụng")
        c4, c5, c6 = st.columns(3)
        with c4:
            product_service = st.selectbox("Sản phẩm cung cấp *", PRODUCTS)
            start_date = st.date_input("Ngày bắt đầu *", value=date.today())
        with c5:
            service_package = st.selectbox("Gói dịch vụ *", PACKAGES)
            expiry_date = st.date_input("Ngày hết hạn *", value=date.today() + timedelta(days=365))
        with c6:
            service_status_preview = calculate_service_status(expiry_date.strftime("%Y-%m-%d"))
            st.text_input("Trạng thái dịch vụ", value=service_status_preview, disabled=True)

        st.markdown("Thông tin tài chính")
        c7, c8 = st.columns([1, 2])
        with c7:
            balance = st.number_input("Công nợ/Số dư (VND)*", value=0, step=100000)
            st.text_input("Trạng thái tài chính", value=calculate_payment_status(float(balance)), disabled=True)
        with c8:
            notes = st.text_area("Ghi chú", max_chars=500)

        st.markdown("Thông tin hệ thống")
        s1, s2, s3 = st.columns(3)
        with s1:
            st.text_input("created_at", value="Tự động khi lưu", disabled=True)
        with s2:
            st.text_input("updated_at", value="Tự động khi lưu", disabled=True)
        with s3:
            st.text_input("is_deleted", value="False", disabled=True)

        submitted = st.form_submit_button("Lưu khách hàng", type="primary")

    if submitted:
        record = build_customer_record(
            customer_id=next_id,
            customer_name=customer_name,
            customer_type=customer_type,
            phone=phone,
            email=email,
            address=address,
            representative=representative,
            tax_code=tax_code,
            product_service=product_service,
            service_package=service_package,
            start_date=start_date,
            expiry_date=expiry_date,
            balance=float(balance),
            notes=notes,
        )
        errors = validate_customer(record, customers)
        if errors:
            for err in errors:
                st.error(err)
        else:
            customers.append(record)
            save_customers(customers)
            st.session_state.customers = customers
            st.success(f"Thêm bản ghi thành công! Mã khách hàng: {next_id}")
            st.info("Tải lại trang hoặc chuyển tab để hệ thống sinh mã khách hàng tiếp theo.")

# ============================================================
# 6. CHỨC NĂNG 2: CẬP NHẬT THÔNG TIN KHÁCH HÀNG
# ============================================================

elif menu == "Cập nhật thông tin khách hàng":
    st.markdown('<div class="section-title">Cập nhật thông tin khách hàng</div>', unsafe_allow_html=True)
    active = active_customers(customers)

    if not active:
        st.warning("Không có khách hàng đang hoạt động để cập nhật.")
    else:
        ids = [f"{c['customer_id']} - {c['customer_name']}" for c in active]
        selected = st.selectbox("Chọn khách hàng cần cập nhật", ids)
        selected_id = selected.split(" - ")[0]
        old = find_customer_by_id(customers, selected_id)

        if old:
            st.markdown("#### Thông tin hiện tại")
            render_customer_detail(old)

            with st.form("update_form"):
                st.markdown("#### Chỉnh sửa thông tin khách hàng")
                u1, u2, u3 = st.columns(3)
                with u1:
                    st.text_input("Mã khách hàng", value=old.get("customer_id", ""), disabled=True)
                    customer_type = st.selectbox(
                        "Loại khách hàng *",
                        CUSTOMER_TYPES,
                        index=CUSTOMER_TYPES.index(old.get("customer_type", "Cá nhân")) if old.get("customer_type") in CUSTOMER_TYPES else 0,
                    )
                    phone = st.text_input("Số điện thoại *", value=old.get("phone", ""), max_chars=10)
                with u2:
                    customer_name = st.text_input("Tên khách hàng *", value=old.get("customer_name", ""))
                    email = st.text_input("Email", value=old.get("email", ""))
                    address = st.text_input("Địa chỉ *", value=old.get("address", ""), max_chars=250)
                with u3:
                    representative = st.text_input("Người đại diện", value=old.get("representative") or "")
                    tax_code = st.text_input("Mã số thuế", value=old.get("tax_code") or "")

                u4, u5, u6 = st.columns(3)
                with u4:
                    product_service = st.selectbox(
                        "Sản phẩm cung cấp *",
                        PRODUCTS,
                        index=PRODUCTS.index(old.get("product_service")) if old.get("product_service") in PRODUCTS else 0,
                    )
                    start_date = st.date_input(
                        "Ngày bắt đầu *",
                        value=datetime.strptime(old.get("start_date", date.today().strftime("%Y-%m-%d")), "%Y-%m-%d").date(),
                    )
                with u5:
                    service_package = st.selectbox(
                        "Gói dịch vụ *",
                        PACKAGES,
                        index=PACKAGES.index(old.get("service_package")) if old.get("service_package") in PACKAGES else 0,
                    )
                    expiry_date = st.date_input(
                        "Ngày hết hạn *",
                        value=datetime.strptime(old.get("expiry_date", date.today().strftime("%Y-%m-%d")), "%Y-%m-%d").date(),
                    )
                with u6:
                    st.text_input("Trạng thái dịch vụ", value=calculate_service_status(expiry_date.strftime("%Y-%m-%d")), disabled=True)

                u7, u8 = st.columns([1, 2])
                with u7:
                    balance = st.number_input("Công nợ / Số dư *", value=float(old.get("balance", 0) or 0), step=100000.0)
                    st.text_input("Trạng thái tài chính", value=calculate_payment_status(float(balance)), disabled=True)
                with u8:
                    notes = st.text_area("Ghi chú", value=old.get("notes", ""), max_chars=500)

                confirm = st.checkbox("Tôi xác nhận muốn lưu các thay đổi này")
                submitted = st.form_submit_button("Cập nhật khách hàng", type="primary")

            if submitted:
                if not confirm:
                    st.warning("Vui lòng tích xác nhận trước khi cập nhật.")
                else:
                    updated = build_customer_record(
                        customer_id=old.get("customer_id", ""),
                        customer_name=customer_name,
                        customer_type=customer_type,
                        phone=phone,
                        email=email,
                        address=address,
                        representative=representative,
                        tax_code=tax_code,
                        product_service=product_service,
                        service_package=service_package,
                        start_date=start_date,
                        expiry_date=expiry_date,
                        balance=float(balance),
                        notes=notes,
                        created_at=old.get("created_at"),
                        is_deleted=old.get("is_deleted", False),
                        deleted_at=old.get("deleted_at"),
                    )
                    errors = validate_customer(updated, customers, current_id=old.get("customer_id"))
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        for idx, c in enumerate(customers):
                            if c.get("customer_id") == old.get("customer_id"):
                                customers[idx] = updated
                                break
                        save_customers(customers)
                        st.session_state.customers = customers
                        st.success("Cập nhật thành công! Trường updated_at đã được ghi nhận tự động.")

# ============================================================
# 7. CHỨC NĂNG 3: TÌM KIẾM THÔNG TIN KHÁCH HÀNG
# ============================================================

elif menu == "Tìm kiếm thông tin khách hàng":
    st.markdown('<div class="section-title">Tìm kiếm thông tin khách hàng</div>', unsafe_allow_html=True)

    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    with f1:
        keyword = st.text_input("Từ khóa", placeholder="Nhập mã, tên, SĐT hoặc email")
    with f2:
        search_type = st.selectbox("Tiêu chí", ["Tất cả", "Mã khách hàng", "Tên khách hàng", "Số điện thoại", "Email"])
    with f3:
        status_filter = st.selectbox("Trạng thái", SERVICE_STATUS_ALL)
    with f4:
        include_deleted = st.checkbox("Bao gồm đã xóa")

    if st.button("Tìm kiếm", type="primary"):
        key = normalize_keyword(keyword)
        results: List[Dict[str, Any]] = []

        for c in customers:
            c2 = enrich_customer(c)

            if not include_deleted and c2.get("is_deleted"):
                continue
            if status_filter != "Tất cả" and c2.get("service_status") != status_filter:
                continue

            if not key:
                matched = True
            elif search_type == "Mã khách hàng":
                matched = c2.get("customer_id", "").upper() == keyword.strip().upper()
            elif search_type == "Tên khách hàng":
                matched = key in normalize_keyword(c2.get("customer_name", ""))
            elif search_type == "Số điện thoại":
                matched = digits_only(keyword) in digits_only(c2.get("phone", ""))
            elif search_type == "Email":
                matched = key in normalize_keyword(c2.get("email", ""))
            else:
                matched = (
                    key in normalize_keyword(c2.get("customer_id", ""))
                    or key in normalize_keyword(c2.get("customer_name", ""))
                    or digits_only(keyword) in digits_only(c2.get("phone", ""))
                    or key in normalize_keyword(c2.get("email", ""))
                )

            if matched:
                results.append(c2)

        st.markdown(f"#### Kết quả tìm kiếm: {len(results)} bản ghi")
        if results:
            st.dataframe(customers_to_df(results), use_container_width=True, hide_index=True)
            chosen = st.selectbox("Xem chi tiết kết quả", [f"{c['customer_id']} - {c['customer_name']}" for c in results])
            chosen_id = chosen.split(" - ")[0]
            render_customer_detail(find_customer_by_id(results, chosen_id) or results[0])
        else:
            st.info("Không tìm thấy khách hàng phù hợp.")

# ============================================================
# 8. CHỨC NĂNG 4: XÓA THÔNG TIN KHÁCH HÀNG
# ============================================================

elif menu == "Xóa thông tin khách hàng":
    st.markdown('<div class="section-title">Xóa thông tin khách hàng</div>', unsafe_allow_html=True)
    st.markdown("<div class='danger-note'>Hệ thống sử dụng xóa mềm: bản ghi không bị xóa vật lý, chỉ cập nhật is_deleted = True và ghi deleted_at.</div>", unsafe_allow_html=True)

    active = active_customers(customers)
    if not active:
        st.warning("Không có khách hàng đang hoạt động để xóa.")
    else:
        selected = st.selectbox("Chọn khách hàng cần xóa", [f"{c['customer_id']} - {c['customer_name']}" for c in active])
        selected_id = selected.split(" - ")[0]
        target = find_customer_by_id(customers, selected_id)

        if target:
            render_customer_detail(target)
            balance = float(target.get("balance", 0) or 0)
            if balance != 0:
                st.error(
                    f"Không thể xóa hồ sơ. Khách hàng hiện đang có số dư công nợ là {balance:,.0f} VND. "
                    "Yêu cầu xử lý tất toán hoặc bù trừ trước khi xóa."
                )
            else:
                confirm_delete = st.checkbox(f"Tôi chắc chắn muốn xóa khách hàng {target.get('customer_name', '')}")
                if st.button("Xóa khách hàng", type="primary", disabled=not confirm_delete):
                    for c in customers:
                        if c.get("customer_id") == target.get("customer_id"):
                            c["is_deleted"] = True
                            c["deleted_at"] = now_str()
                            c["updated_at"] = now_str()
                            break
                    save_customers(customers)
                    st.session_state.customers = customers
                    st.success("Đã xóa thành công và ẩn khách hàng khỏi danh sách hoạt động.")

# ============================================================
# 9. CHỨC NĂNG 5: XEM DANH SÁCH THÔNG TIN KHÁCH HÀNG
# ============================================================

elif menu == "Xem danh sách thông tin khách hàng":
    st.markdown('<div class="section-title">Xem danh sách thông tin khách hàng</div>', unsafe_allow_html=True)

    # Đọc lại file để đúng mô tả xem danh sách: tải dữ liệu từ customers.json
    customers = load_customers()
    st.session_state.customers = customers
    active = active_customers(customers)

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"<div class='metric-card'><b>Tổng bản ghi</b><br>{len(customers)}</div>", unsafe_allow_html=True)
    with m2:
        st.markdown(f"<div class='metric-card'><b>Đang hoạt động</b><br>{len(active)}</div>", unsafe_allow_html=True)
    with m3:
        st.markdown(f"<div class='metric-card'><b>Đã xóa mềm</b><br>{len([c for c in customers if c.get('is_deleted')])}</div>", unsafe_allow_html=True)

    st.markdown("#### Bộ lọc danh sách")
    l1, l2, l3 = st.columns([2, 1, 1])
    with l1:
        list_keyword = st.text_input("Tìm theo mã/tên", placeholder="Nhập mã KH hoặc tên KH...")
    with l2:
        list_type = st.selectbox("Loại khách hàng", ["Tất cả"] + CUSTOMER_TYPES)
    with l3:
        list_status = st.selectbox("Trạng thái dịch vụ", ["Tất cả", "Active", "Sắp hết hạn", "Expired", "Trial"])

    filtered = []
    key = normalize_keyword(list_keyword)
    for c in active:
        c2 = enrich_customer(c)
        if list_type != "Tất cả" and c2.get("customer_type") != list_type:
            continue
        if list_status != "Tất cả" and c2.get("service_status") != list_status:
            continue
        if key and key not in normalize_keyword(c2.get("customer_id", "")) and key not in normalize_keyword(c2.get("customer_name", "")):
            continue
        filtered.append(c2)

    if not filtered:
        st.info("Không có khách hàng nào trên hệ thống hoặc không có bản ghi phù hợp bộ lọc.")
    else:
        st.dataframe(customers_to_df(filtered), use_container_width=True, hide_index=True)
        chosen = st.selectbox("Chọn khách hàng để xem chi tiết", [f"{c['customer_id']} - {c['customer_name']}" for c in filtered])
        chosen_id = chosen.split(" - ")[0]
        chosen_customer = find_customer_by_id(filtered, chosen_id)
        if chosen_customer:
            render_customer_detail(chosen_customer)

    st.markdown(
        "<div class='small-note'>Ghi chú: Chỉ hiển thị khách hàng chưa bị xóa mềm "
        "(<b>is_deleted = False</b>). Các bản ghi đã xóa vẫn được giữ trong file customers.json để phục vụ kiểm toán hoặc khôi phục.</div>",
        unsafe_allow_html=True,
    )
