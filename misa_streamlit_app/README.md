# Web app quản lý khách hàng MISA

Đây là web app đơn giản xây dựng bằng Streamlit cho đề tài: **Xây dựng chương trình quản lý khách hàng của Công ty cổ phần MISA**.

## Chức năng

1. Nhập thông tin khách hàng
2. Xóa thông tin khách hàng bằng cơ chế xóa mềm
3. Cập nhật thông tin khách hàng
4. Tìm kiếm thông tin khách hàng
5. Xem danh sách khách hàng đang hoạt động

## Cấu trúc thư mục

```text
misa-streamlit-app/
├── app.py
├── codepython.py
├── customer_service.py
├── storage.py
├── requirements.txt
├── README.md
└── data/
    └── customers.json
```

## Chạy trên máy cá nhân

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Ghi chú

Dữ liệu được lưu trong tệp `data/customers.json`. Ứng dụng sử dụng cơ chế xóa mềm: khi xóa khách hàng, hệ thống cập nhật `is_deleted = True`, không xóa vĩnh viễn bản ghi.
