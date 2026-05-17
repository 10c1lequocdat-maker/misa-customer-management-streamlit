from datetime import date, datetime

def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate_service_status(expiry_date):
    try:
        if isinstance(expiry_date, date):
            expiry = expiry_date
        else:
            expiry = datetime.strptime(str(expiry_date), "%Y-%m-%d").date()

        days_left = (expiry - date.today()).days

        if days_left < 0:
            return "Đã hết hạn"
        if days_left <= 30:
            return "Sắp hết hạn"
        return "Đang hoạt động"
    except Exception:
        return "Không xác định"

def validate_customer(customers, customer, is_update=False):
    required_fields = ["customer_id", "name", "phone"]

    for field in required_fields:
        if not customer.get(field):
            return False, "Vui lòng nhập đầy đủ mã khách hàng, tên khách hàng và số điện thoại."

    if not is_update:
        for item in customers:
            if item.get("customer_id") == customer.get("customer_id"):
                return False, "Mã khách hàng đã tồn tại."

    if customer.get("email") and "@" not in customer.get("email"):
        return False, "Email không hợp lệ."

    if int(customer.get("debt_amount", 0)) < 0:
        return False, "Công nợ không được âm."

    if customer.get("payment_status") == "Đã thanh toán" and int(customer.get("debt_amount", 0)) > 0:
        return False, "Khách hàng đã thanh toán thì công nợ phải bằng 0."

    return True, "Dữ liệu hợp lệ."

def add_customer(customers, customer):
    valid, message = validate_customer(customers, customer)
    if not valid:
        return False, message, customers

    customer["created_at"] = now_string()
    customer["updated_at"] = now_string()
    customer["deleted_at"] = None
    customer["is_deleted"] = False

    customers.append(customer)
    return True, "Thêm khách hàng thành công.", customers

def active_customers(customers):
    return [item for item in customers if item.get("is_deleted") is False]

def get_customer_by_id(customers, customer_id):
    customer_id = str(customer_id).strip()
    for item in customers:
        if item.get("customer_id") == customer_id and item.get("is_deleted") is False:
            return item
    return None

def search_customers(customers, keyword):
    keyword = str(keyword).lower().strip()
    if not keyword:
        return []

    results = []
    for item in active_customers(customers):
        searchable = " ".join([
            str(item.get("customer_id", "")),
            str(item.get("name", "")),
            str(item.get("phone", "")),
            str(item.get("email", "")),
            str(item.get("service_name", "")),
            str(item.get("service_status", "")),
        ]).lower()

        if keyword in searchable:
            results.append(item)

    return results

def update_customer(customers, customer_id, new_data):
    old_customer = get_customer_by_id(customers, customer_id)

    if not old_customer:
        return False, "Không tìm thấy khách hàng cần cập nhật.", customers

    valid, message = validate_customer(customers, new_data, is_update=True)
    if not valid:
        return False, message, customers

    for item in customers:
        if item.get("customer_id") == customer_id and item.get("is_deleted") is False:
            item.update(new_data)
            item["updated_at"] = now_string()
            return True, "Cập nhật khách hàng thành công.", customers

    return False, "Cập nhật thất bại.", customers

def soft_delete_customer(customers, customer_id):
    for item in customers:
        if item.get("customer_id") == customer_id and item.get("is_deleted") is False:
            item["is_deleted"] = True
            item["deleted_at"] = now_string()
            item["updated_at"] = now_string()
            return True, "Xóa mềm khách hàng thành công.", customers

    return False, "Không tìm thấy khách hàng cần xóa.", customers
