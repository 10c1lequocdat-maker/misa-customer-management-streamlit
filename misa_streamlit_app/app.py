import streamlit as st
import pandas as pd
from datetime import date, datetime

from storage import load_customers, save_customers
from customer_service import (
    add_customer,
    soft_delete_customer,
    update_customer,
    search_customers,
    active_customers,
    get_customer_by_id,
    calculate_service_status,
)

st.set_page_config(
    page_title="Quản lý khách hàng MISA",
    page_icon="👥",
    layout="wide"
)

st.markdown(
    """
    <style>
    .main-title {
        color: #0052cc;
        font-size: 34px;
        font-weight: 800;
        margin-bottom: 0;
    }
    .sub-title {
        color: #4a5c73;
        font-size: 16px;
        margin-bottom: 24px;
    }
    .metric-card {
        padding: 18px;
        border: 1px solid #d6e4f5;
        border-radius: 14px;
        background: #f8fbff;
    }
    .success-badge {
        color: #137333;
        background: #e6f4ea;
        padding: 4px 8px;
        border-radius: 8px;
        font-weight: 600;
    }
    .warning-badge {
        color: #b06000;
        background: #fff4e5;
        padding: 4px 8px;
        border-radius: 8px;
        font-weight: 600;
    }
    .danger-badge {
        color: #b3261e;
        background: #fce8e6;
        padding: 4px 8px;
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if "customers" not in st.session_state:
    st.session_state.customers = load_customers()

def persist():
    save_customers(st.session_state.customers)

def refresh_status():
    for customer in st.session_state.customers:
        if not customer.get("is_deleted", False):
            customer["service_status"] = calculate_service_status(customer.get("expiry_date", ""))
    persist()

def show_customer_table(customers):
    if not customers:
        st.info("Hiện chưa có khách hàng nào trong hệ thống.")
        return

    df = pd.DataFrame(customers)
    display_cols = [
        "customer_id", "name", "customer_type", "phone", "email",
        "service_name", "package_name", "expiry_date",
        "service_status", "payment_status", "debt_amount"
    ]
    rename_cols = {
        "customer_id": "Mã KH",
        "name": "Tên khách hàng",
        "customer_type": "Loại KH",
        "phone": "SĐT",
        "email": "Email",
        "service_name": "Dịch vụ",
        "package_name": "Gói dịch vụ",
        "expiry_date": "Ngày hết hạn",
        "service_status": "Trạng thái dịch vụ",
        "payment_status": "Thanh toán",
        "debt_amount": "Công nợ"
    }
    for col in display_cols:
        if col not in df.columns:
            df[col] = ""
    st.dataframe(
        df[display_cols].rename(columns=rename_cols),
        use_container_width=True,
        hide_index=True
    )

def customer_form(prefix="", default=None):
    default = default or {}
    col1, col2, col3 = st.columns(3)

    with col1:
        customer_id = st.text_input(
            "Mã khách hàng *",
            value=default.get("customer_id", ""),
            disabled=bool(default),
            key=f"{prefix}_customer_id"
        )
        name = st.text_input("Tên khách hàng *", value=default.get("name", ""), key=f"{prefix}_name")
        customer_type = st.selectbox(
            "Loại khách hàng",
            ["Cá nhân", "Doanh nghiệp"],
            index=0 if default.get("customer_type", "Cá nhân") == "Cá nhân" else 1,
            key=f"{prefix}_customer_type"
        )
        phone = st.text_input("Số điện thoại *", value=default.get("phone", ""), key=f"{prefix}_phone")

    with col2:
        email = st.text_input("Email", value=default.get("email", ""), key=f"{prefix}_email")
        address = st.text_input("Địa chỉ", value=default.get("address", ""), key=f"{prefix}_address")
        representative = st.text_input("Người liên hệ đại diện", value=default.get("representative", ""), key=f"{prefix}_representative")
        tax_code = st.text_input("Mã số thuế", value=default.get("tax_code", ""), key=f"{prefix}_tax_code")

    with col3:
        service_name = st.text_input("Sản phẩm / dịch vụ", value=default.get("service_name", "MISA AMIS"), key=f"{prefix}_service_name")
        package_name = st.selectbox(
            "Gói dịch vụ",
            ["Basic", "Standard", "Premium"],
            index=["Basic", "Standard", "Premium"].index(default.get("package_name", "Standard")) if default.get("package_name", "Standard") in ["Basic", "Standard", "Premium"] else 1,
            key=f"{prefix}_package_name"
        )
        start_date = st.date_input(
            "Ngày bắt đầu",
            value=datetime.strptime(default.get("start_date", str(date.today())), "%Y-%m-%d").date() if default.get("start_date") else date.today(),
            key=f"{prefix}_start_date"
        )
        expiry_date = st.date_input(
            "Ngày hết hạn",
            value=datetime.strptime(default.get("expiry_date", str(date.today())), "%Y-%m-%d").date() if default.get("expiry_date") else date.today(),
            key=f"{prefix}_expiry_date"
        )

    col4, col5, col6 = st.columns(3)
    with col4:
        payment_status = st.selectbox(
            "Trạng thái thanh toán",
            ["Đã thanh toán", "Chưa thanh toán", "Còn công nợ"],
            index=["Đã thanh toán", "Chưa thanh toán", "Còn công nợ"].index(default.get("payment_status", "Đã thanh toán")) if default.get("payment_status", "Đã thanh toán") in ["Đã thanh toán", "Chưa thanh toán", "Còn công nợ"] else 0,
            key=f"{prefix}_payment_status"
        )
    with col5:
        debt_amount = st.number_input(
            "Công nợ (VND)",
            min_value=0,
            value=int(default.get("debt_amount", 0) or 0),
            step=100000,
            key=f"{prefix}_debt_amount"
        )
    with col6:
        note = st.text_input("Ghi chú", value=default.get("note", ""), key=f"{prefix}_note")

    return {
        "customer_id": customer_id.strip(),
        "name": name.strip(),
        "customer_type": customer_type,
        "phone": phone.strip(),
        "email": email.strip(),
        "address": address.strip(),
        "representative": representative.strip(),
        "tax_code": tax_code.strip(),
        "service_name": service_name.strip(),
        "package_name": package_name,
        "start_date": start_date.isoformat(),
        "expiry_date": expiry_date.isoformat(),
        "service_status": calculate_service_status(expiry_date.isoformat()),
        "payment_status": payment_status,
        "debt_amount": int(debt_amount),
        "note": note.strip(),
    }

st.sidebar.title("MISA")
page = st.sidebar.radio(
    "Menu chức năng",
    [
        "Trang chủ",
        "Nhập thông tin khách hàng",
        "Xem danh sách khách hàng",
        "Tìm kiếm thông tin khách hàng",
        "Cập nhật thông tin khách hàng",
        "Xóa thông tin khách hàng"
    ]
)

st.markdown('<p class="main-title">QUẢN LÝ KHÁCH HÀNG MISA</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Web app đơn giản xây dựng bằng Streamlit, dữ liệu lưu trong tệp JSON.</p>', unsafe_allow_html=True)

refresh_status()

if page == "Trang chủ":
    st.subheader("Menu chức năng")
    active = active_customers(st.session_state.customers)
    c1, c2, c3 = st.columns(3)
    c1.metric("Khách hàng đang hoạt động", len(active))
    c2.metric("Tổng bản ghi", len(st.session_state.customers))
    c3.metric("Đã xóa mềm", len([c for c in st.session_state.customers if c.get("is_deleted")]))
    st.write("Chọn chức năng ở thanh bên trái để thực hiện thao tác quản lý khách hàng.")

elif page == "Nhập thông tin khách hàng":
    st.subheader("1. Nhập thông tin khách hàng")
    with st.form("add_form"):
        data = customer_form(prefix="add")
        submitted = st.form_submit_button("Lưu khách hàng", type="primary")

    if submitted:
        ok, message, new_list = add_customer(st.session_state.customers, data)
        if ok:
            st.session_state.customers = new_list
            persist()
            st.success(message)
        else:
            st.error(message)

elif page == "Xem danh sách khách hàng":
    st.subheader("5. Xem danh sách khách hàng")
    st.caption("Chỉ hiển thị các khách hàng chưa bị xóa mềm: is_deleted = False.")
    show_customer_table(active_customers(st.session_state.customers))

elif page == "Tìm kiếm thông tin khách hàng":
    st.subheader("4. Tìm kiếm thông tin khách hàng")
    keyword = st.text_input("Nhập mã, tên, số điện thoại hoặc email")
    if st.button("Tìm kiếm", type="primary"):
        results = search_customers(st.session_state.customers, keyword)
        st.write(f"Tìm thấy {len(results)} kết quả.")
        show_customer_table(results)

elif page == "Cập nhật thông tin khách hàng":
    st.subheader("3. Cập nhật thông tin khách hàng")
    update_id = st.text_input("Nhập mã khách hàng cần cập nhật")
    customer = get_customer_by_id(st.session_state.customers, update_id) if update_id else None

    if update_id and not customer:
        st.warning("Không tìm thấy khách hàng đang hoạt động với mã đã nhập.")

    if customer:
        st.info(f"Đang cập nhật khách hàng: {customer['customer_id']} - {customer['name']}")
        with st.form("update_form"):
            updated_data = customer_form(prefix="update", default=customer)
            submitted = st.form_submit_button("Cập nhật khách hàng", type="primary")

        if submitted:
            ok, message, new_list = update_customer(st.session_state.customers, update_id, updated_data)
            if ok:
                st.session_state.customers = new_list
                persist()
                st.success(message)
            else:
                st.error(message)

elif page == "Xóa thông tin khách hàng":
    st.subheader("2. Xóa thông tin khách hàng")
    delete_id = st.text_input("Nhập mã khách hàng cần xóa")
    customer = get_customer_by_id(st.session_state.customers, delete_id) if delete_id else None

    if customer:
        st.warning(f"Bạn đang chọn xóa mềm khách hàng: {customer['customer_id']} - {customer['name']}")
        st.json({
            "customer_id": customer.get("customer_id"),
            "name": customer.get("name"),
            "phone": customer.get("phone"),
            "email": customer.get("email"),
            "service_name": customer.get("service_name"),
            "debt_amount": customer.get("debt_amount")
        })
        confirm = st.checkbox("Tôi xác nhận muốn xóa mềm khách hàng này.")
        if st.button("Xóa khách hàng", type="primary", disabled=not confirm):
            ok, message, new_list = soft_delete_customer(st.session_state.customers, delete_id)
            if ok:
                st.session_state.customers = new_list
                persist()
                st.success(message)
            else:
                st.error(message)
    elif delete_id:
        st.error("Không tìm thấy khách hàng hoặc khách hàng đã bị xóa mềm.")
