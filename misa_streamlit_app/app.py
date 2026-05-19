import streamlit as st

st.set_page_config(
    page_title="Quản lý khách hàng MISA",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        background-color: #0052cc;
        padding: 18px;
        border-radius: 8px;
        color: white;
        text-align: center;
        font-size: 30px;
        font-weight: bold;
        margin-bottom: 20px;
    }

    .section-title {
        color: #0052cc;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 16px;
    }

    .note-box {
        background-color: #fff7e6;
        border: 1px solid #ffd591;
        padding: 14px;
        border-radius: 8px;
        margin-top: 20px;
    }

    .status-active {
        background-color: #d9f7be;
        color: #237804;
        padding: 5px 10px;
        border-radius: 6px;
        font-weight: bold;
    }

    .status-warning {
        background-color: #fff1b8;
        color: #ad6800;
        padding: 5px 10px;
        border-radius: 6px;
        font-weight: bold;
    }

    .status-expired {
        background-color: #ffccc7;
        color: #a8071a;
        padding: 5px 10px;
        border-radius: 6px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="main-header">QUẢN LÝ KHÁCH HÀNG MISA</div>',
    unsafe_allow_html=True
)

with st.sidebar:
    st.markdown("## MISA")
    st.markdown("### Menu chức năng")

    menu = st.radio(
        "Chọn chức năng",
        [
            "1. Nhập thông tin khách hàng",
            "2. Cập nhật thông tin khách hàng",
            "3. Tìm kiếm thông tin khách hàng",
            "4. Xóa thông tin khách hàng",
            "5. Xem danh sách thông tin khách hàng"
        ],
        label_visibility="collapsed"
    )

if menu == "1. Nhập thông tin khách hàng":
    st.markdown('<div class="section-title">Nhập thông tin khách hàng</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        ma_kh = st.text_input("Mã khách hàng")
        ten_kh = st.text_input("Tên khách hàng")
        loai_kh = st.selectbox("Loại khách hàng", ["Cá nhân", "Doanh nghiệp"])

    with col2:
        sdt = st.text_input("Số điện thoại")
        email = st.text_input("Email")
        dia_chi = st.text_input("Địa chỉ")

    with col3:
        goi_dv = st.selectbox("Gói dịch vụ", ["MISA AMIS", "MISA SME", "meInvoice"])
        ngay_het_han = st.date_input("Ngày hết hạn")
        cong_no = st.number_input("Công nợ", min_value=0)

    if st.button("Lưu khách hàng"):
        st.success("Đã lưu thông tin khách hàng.")

elif menu == "2. Cập nhật thông tin khách hàng":
    st.markdown('<div class="section-title">Cập nhật thông tin khách hàng</div>', unsafe_allow_html=True)

    ma_tim = st.text_input("Nhập mã khách hàng cần cập nhật")

    if st.button("Tải thông tin"):
        st.info("Hiển thị thông tin khách hàng cần cập nhật.")

    st.text_input("Tên khách hàng")
    st.text_input("Số điện thoại")
    st.text_input("Email")
    st.text_input("Địa chỉ")
    st.selectbox("Gói dịch vụ", ["MISA AMIS", "MISA SME", "meInvoice"])
    st.number_input("Công nợ", min_value=0)

    if st.button("Cập nhật khách hàng"):
        st.success("Cập nhật thông tin khách hàng thành công.")

elif menu == "3. Tìm kiếm thông tin khách hàng":
    st.markdown('<div class="section-title">Tìm kiếm thông tin khách hàng</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        keyword = st.text_input("Tìm theo mã, tên, SĐT hoặc email")

    with col2:
        loai_kh = st.selectbox("Loại khách hàng", ["Tất cả", "Cá nhân", "Doanh nghiệp"])

    with col3:
        trang_thai = st.selectbox("Trạng thái dịch vụ", ["Tất cả", "Đang hoạt động", "Sắp hết hạn", "Đã hết hạn"])

    if st.button("Tìm kiếm"):
        st.success("Hiển thị kết quả tìm kiếm.")

elif menu == "4. Xóa thông tin khách hàng":
    st.markdown('<div class="section-title">Xóa thông tin khách hàng</div>', unsafe_allow_html=True)

    ma_xoa = st.text_input("Nhập mã khách hàng cần xóa")

    st.warning("Hệ thống sử dụng cơ chế xóa mềm: is_deleted = True.")

    if st.button("Xóa khách hàng"):
        st.error("Khách hàng đã được xóa mềm khỏi danh sách hoạt động.")

elif menu == "5. Xem danh sách thông tin khách hàng":
    st.markdown('<div class="section-title">Xem danh sách thông tin khách hàng</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        st.text_input("Tìm theo mã/tên", placeholder="Nhập mã KH hoặc tên KH...")

    with col2:
        st.selectbox("Loại khách hàng", ["Tất cả", "Cá nhân", "Doanh nghiệp"])

    with col3:
        st.selectbox("Trạng thái dịch vụ", ["Tất cả", "Đang hoạt động", "Sắp hết hạn", "Đã hết hạn"])

    with col4:
        st.write("")
        st.button("Tìm kiếm")

    data = [
        {
            "STT": 1,
            "Mã KH": "KH001",
            "Tên khách hàng": "Nguyễn Văn An",
            "Loại KH": "Doanh nghiệp",
            "SĐT": "0912 345 678",
            "Email": "an.nguyen@anphat.com.vn",
            "Gói dịch vụ": "MISA AMIS",
            "Ngày hết hạn": "31/12/2025",
            "Trạng thái": "Đang hoạt động",
            "Công nợ": "2.350.000"
        },
        {
            "STT": 2,
            "Mã KH": "KH002",
            "Tên khách hàng": "Trần Thị Bình",
            "Loại KH": "Cá nhân",
            "SĐT": "0909 876 543",
            "Email": "binh.tran@gmail.com",
            "Gói dịch vụ": "MISA SME",
            "Ngày hết hạn": "15/06/2025",
            "Trạng thái": "Sắp hết hạn",
            "Công nợ": "0"
        },
        {
            "STT": 3,
            "Mã KH": "KH003",
            "Tên khách hàng": "Công ty TNHH Minh Phát",
            "Loại KH": "Doanh nghiệp",
            "SĐT": "028 7300 1234",
            "Email": "info@minhphat.com.vn",
            "Gói dịch vụ": "meInvoice",
            "Ngày hết hạn": "20/05/2025",
            "Trạng thái": "Đã hết hạn",
            "Công nợ": "1.200.000"
        }
    ]

    st.dataframe(data, use_container_width=True)

    st.markdown("### Thông tin chi tiết khách hàng")

    col_left, col_right = st.columns(2)

    with col_left:
        st.write("**Mã khách hàng:** KH001")
        st.write("**Tên khách hàng:** Nguyễn Văn An")
        st.write("**Loại khách hàng:** Doanh nghiệp")
        st.write("**Số điện thoại:** 0912 345 678")
        st.write("**Email:** an.nguyen@anphat.com.vn")
        st.write("**Địa chỉ:** Số 125 Nguyễn Trãi, Thanh Xuân, Hà Nội")
        st.write("**Người liên hệ:** Nguyễn Văn An – Giám đốc")
        st.write("**Gói dịch vụ:** MISA AMIS")

    with col_right:
        st.write("**Ngày bắt đầu:** 01/01/2025")
        st.write("**Ngày hết hạn:** 31/12/2025")
        st.write("**Trạng thái dịch vụ:** Đang hoạt động")
        st.write("**Công nợ:** 2.350.000 VND")
        st.write("**Ghi chú:** Khách hàng sử dụng đầy đủ các phân hệ kế toán, nhân sự, bán hàng.")

    st.markdown(
        '<div class="note-box">Ghi chú: Chỉ hiển thị khách hàng chưa bị xóa mềm '
        '(is_deleted = False).</div>',
        unsafe_allow_html=True
    )
