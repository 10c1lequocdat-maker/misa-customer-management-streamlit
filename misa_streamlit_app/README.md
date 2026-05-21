# 🧾 Hệ thống Quản lý Khách hàng Công ty Cổ phần MISA
> Đề tài bài tập lớn học phần Lập trình Python  
> 🚀 Giao diện: Web app với **Streamlit**  
> 📁 Lưu trữ dữ liệu: **File JSON**  
> 💻 Ngôn ngữ lập trình: **Python**

---

## 📌 Mục tiêu đề tài

Đề tài **“Xây dựng chương trình quản lý khách hàng của Công ty Cổ phần MISA”** được thực hiện nhằm xây dựng một hệ thống hỗ trợ quản lý thông tin khách hàng một cách đơn giản, trực quan và dễ sử dụng.

Hệ thống cho phép người dùng thực hiện các thao tác cơ bản đối với dữ liệu khách hàng như nhập mới, cập nhật, tìm kiếm, xóa và xem danh sách khách hàng. Chương trình được tổ chức theo hướng **hàm và module**, giúp mã nguồn rõ ràng, dễ bảo trì và có khả năng mở rộng trong tương lai.

---

## 🧱 Cấu trúc thư mục

```text
misa_streamlit_app/
├── app.py                      # Giao diện Streamlit chính và menu chức năng
├── customer_service.py          # Các hàm xử lý nghiệp vụ khách hàng
├── storage.py                   # Đọc / ghi dữ liệu khách hàng từ file JSON
├── requirements.txt             # Danh sách thư viện cần cài đặt
├── README.md                    # Tài liệu mô tả và hướng dẫn sử dụng
└── data/
    └── customers.json           # File lưu thông tin khách hàng
