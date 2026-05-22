import json
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from IPython.display import display

DATA_DIR = Path('data')
DATA_FILE = DATA_DIR / 'customers.json'

PRODUCTS = ['meInvoice', 'MISA SME', 'MISA AMIS', 'Bamboo']
PACKAGES = ['Starter', 'Standard', 'Professional', 'Enterprise']
CUSTOMER_TYPES = ['Cá nhân', 'Doanh nghiệp']
SERVICE_STATUS_ALL = ['Tất cả', 'Active', 'Sắp hết hạn', 'Expired', 'Trial', 'Đã xóa']

#print('Đã nạp thư viện và cấu hình đường dẫn dữ liệu.')
#print('File dữ liệu:', DATA_FILE)

# NHÓM HÀM LƯU TRỮ DỮ LIỆU

def ensure_data_file() -> None:
    """Tạo thư mục data và file customers.json nếu chưa tồn tại."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text('[]', encoding='utf-8')

def load_customers() -> List[Dict[str, Any]]:
    """Đọc danh sách khách hàng từ file JSON."""
    ensure_data_file()
    try:
        data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        print('⚠️ File customers.json bị lỗi định dạng. Hệ thống nạp danh sách rỗng.')
        return []

def save_customers(customers: List[Dict[str, Any]]) -> None:
    """Ghi danh sách khách hàng vào file JSON."""
    ensure_data_file()
    DATA_FILE.write_text(json.dumps(customers, ensure_ascii=False, indent=4), encoding='utf-8')

ensure_data_file()
# print('Đã nạp nhóm hàm lưu trữ dữ liệu.')

def now_str() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def normalize_spaces(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text or '').strip())

def remove_accents(text: str) -> str:
    text = str(text or '')
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
    return text.replace('đ', 'd').replace('Đ', 'D')

def normalize_keyword(text: str) -> str:
    return remove_accents(normalize_spaces(text)).lower()

def digits_only(text: str) -> str:
    return re.sub(r'\D', '', str(text or ''))

def parse_customer_no(customer_id: str) -> int:
    match = re.search(r'KH(\d+)$', str(customer_id or '').upper())
    return int(match.group(1)) if match else 0

def generate_next_customer_id(customers: List[Dict[str, Any]]) -> str:
    """Sinh mã khách hàng mới dựa trên mã lớn nhất trong file, kể cả bản ghi đã xóa."""
    max_no = 0
    for c in customers:
        max_no = max(max_no, parse_customer_no(c.get('customer_id', '')))
    return f'KH{max_no + 1:03d}'

def phone_is_valid(phone: str) -> bool:
    phone_digits = digits_only(phone)
    return len(phone_digits) == 10 and phone_digits.startswith('0')

def email_is_valid(email: str) -> bool:
    # Email có thể để trống. Nếu đã nhập thì phải đúng định dạng.
    if not normalize_spaces(email):
        return True
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.[A-Za-z]{2,}$', normalize_spaces(email)))

def tax_code_is_valid(tax_code: str) -> bool:
    # Mã số thuế có thể trống với khách hàng cá nhân.
    if not normalize_spaces(tax_code):
        return True
    tax_digits = digits_only(tax_code)
    return len(tax_digits) in (10, 13)

def parse_date(date_text: str) -> date:
    """Chuyển chuỗi ngày dạng YYYY-MM-DD sang kiểu date."""
    return datetime.strptime(normalize_spaces(date_text), '%Y-%m-%d').date()

def calculate_service_status(expiry_date: str) -> str:
    try:
        exp = datetime.strptime(expiry_date, '%Y-%m-%d').date()
    except Exception:
        return 'Trial'

    days_left = (exp - date.today()).days
    if days_left < 0:
        return 'Expired'
    if days_left <= 30:
        return 'Sắp hết hạn'
    return 'Active'

def calculate_payment_status(balance: float) -> str:
    if balance == 0:
        return 'Đã thanh toán'
    if balance > 0:
        return 'Chưa thanh toán'
    return f'Đã thanh toán (Dư: {abs(balance):,.0f} VND)'

def active_customers(customers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [c for c in customers if not c.get('is_deleted', False)]


def enrich_customer(c: Dict[str, Any]) -> Dict[str, Any]:
    c = dict(c)
    c['service_status'] = 'Đã xóa' if c.get('is_deleted') else calculate_service_status(c.get('expiry_date', ''))
    c['payment_status'] = calculate_payment_status(float(c.get('balance', 0) or 0))
    return c

# print('Đã nạp nhóm hàm chuẩn hóa và kiểm tra dữ liệu.')

# HÀM TẠO BẢN GHI VÀ KIỂM TRA TÍNH HỢP LỆ

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
    customer_type = normalize_spaces(customer_type)
    phone = digits_only(phone)
    email = normalize_spaces(email).lower()
    address = normalize_spaces(address)
    representative = normalize_spaces(representative) or None
    tax_code = digits_only(tax_code) or None
    notes = normalize_spaces(notes)

    if customer_type == 'Cá nhân':
        representative = None if not representative else representative
        tax_code = None if not tax_code else tax_code

    balance = float(balance or 0)
    start_date_str = start_date.strftime('%Y-%m-%d')
    expiry_date_str = expiry_date.strftime('%Y-%m-%d')

    return {
        'customer_id': customer_id,
        'customer_name': customer_name,
        'customer_type': customer_type,
        'phone': phone,
        'email': email,
        'address': address,
        'representative': representative,
        'tax_code': tax_code,
        'product_service': product_service,
        'service_package': service_package,
        'start_date': start_date_str,
        'expiry_date': expiry_date_str,
        'service_status': calculate_service_status(expiry_date_str),
        'payment_status': calculate_payment_status(balance),
        'balance': balance,
        'notes': notes,
        'created_at': created_at or now_str(),
        'updated_at': now_str(),
        'is_deleted': is_deleted,
        'deleted_at': deleted_at,
    }


def validate_customer(
    customer: Dict[str, Any],
    customers: List[Dict[str, Any]],
    current_id: Optional[str] = None,
) -> List[str]:
    """Trả về danh sách cảnh báo/lỗi. Nếu danh sách rỗng thì dữ liệu hợp lệ."""
    errors: List[str] = []

    required_fields = {
        'customer_id': 'Mã khách hàng',
        'customer_name': 'Tên khách hàng',
        'customer_type': 'Loại khách hàng',
        'phone': 'Số điện thoại',
        'address': 'Địa chỉ',
        'product_service': 'Sản phẩm cung cấp',
        'service_package': 'Gói dịch vụ',
        'start_date': 'Ngày bắt đầu',
        'expiry_date': 'Ngày hết hạn',
        'balance': 'Công nợ',
    }

    for key, label in required_fields.items():
        if customer.get(key) in (None, ''):
            errors.append(f'⚠️ {label} không được để trống.')

    if customer.get('customer_type') not in CUSTOMER_TYPES:
        errors.append('⚠️ Loại khách hàng chỉ được nhập: Cá nhân hoặc Doanh nghiệp.')

    if customer.get('customer_type') == 'Doanh nghiệp':
        if not customer.get('representative'):
            errors.append('⚠️ Khách hàng doanh nghiệp bắt buộc phải nhập người đại diện.')
        if not customer.get('tax_code'):
            errors.append('⚠️ Khách hàng doanh nghiệp bắt buộc phải nhập mã số thuế.')

    phone = digits_only(customer.get('phone', ''))
    if not phone_is_valid(phone):
        errors.append('⚠️ Số điện thoại sai định dạng. Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0.')

    for c in active_customers(customers):
        if current_id and c.get('customer_id') == current_id:
            continue
        if phone and digits_only(c.get('phone', '')) == phone:
            errors.append('⚠️ Số điện thoại đã tồn tại ở một khách hàng đang hoạt động.')
            break

    if not email_is_valid(customer.get('email', '')):
        errors.append('⚠️ Email sai định dạng. Ví dụ đúng: abc@gmail.com')

    if customer.get('tax_code') and not tax_code_is_valid(customer.get('tax_code', '')):
        errors.append('⚠️ Mã số thuế sai định dạng. Mã số thuế phải gồm 10 hoặc 13 chữ số.')

    try:
        start = datetime.strptime(customer.get('start_date', ''), '%Y-%m-%d').date()
        expiry = datetime.strptime(customer.get('expiry_date', ''), '%Y-%m-%d').date()
        if expiry < start:
            errors.append('⚠️ Ngày hết hạn phải lớn hơn hoặc bằng ngày bắt đầu.')
    except Exception:
        errors.append('⚠️ Ngày bắt đầu hoặc ngày hết hạn không hợp lệ. Định dạng đúng: YYYY-MM-DD, ví dụ 2026-05-21.')

    if customer.get('product_service') not in PRODUCTS:
        errors.append(f'⚠️ Sản phẩm cung cấp không hợp lệ. Chọn một trong các giá trị: {PRODUCTS}')
    if customer.get('service_package') not in PACKAGES:
        errors.append(f'⚠️ Gói dịch vụ không hợp lệ. Chọn một trong các giá trị: {PACKAGES}')

    if len(customer.get('notes', '') or '') > 500:
        errors.append('⚠️ Ghi chú không được vượt quá 500 ký tự.')
    if len(customer.get('address', '') or '') > 250:
        errors.append('⚠️ Địa chỉ không được vượt quá 250 ký tự.')

    return errors

def print_validation_errors(errors: List[str]) -> None:
    if errors:
        print('Dữ liệu chưa hợp lệ. Vui lòng kiểm tra các cảnh báo sau:')
        for err in errors:
            print('-', err)

# print('Đã nạp hàm tạo bản ghi và kiểm tra tính hợp lệ.')

# NHÓM HÀM HIỂN THỊ DỮ LIỆU

def customers_to_df(customers: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for i, c in enumerate(customers, start=1):
        c = enrich_customer(c)
        rows.append({
            'STT': i,
            'Mã KH': c.get('customer_id', ''),
            'Tên khách hàng': c.get('customer_name', ''),
            'Loại KH': c.get('customer_type', ''),
            'SĐT': c.get('phone', ''),
            'Email': c.get('email', ''),
            'Sản phẩm': c.get('product_service', ''),
            'Gói DV': c.get('service_package', ''),
            'Ngày bắt đầu': c.get('start_date', ''),
            'Ngày hết hạn': c.get('expiry_date', ''),
            'Trạng thái': c.get('service_status', ''),
            'Công nợ': f"{float(c.get('balance', 0) or 0):,.0f} VND",
            'Đã xóa': c.get('is_deleted', False),
        })
    return pd.DataFrame(rows)


def find_customer_by_id(customers: List[Dict[str, Any]], customer_id: str) -> Optional[Dict[str, Any]]:
    customer_id = normalize_spaces(customer_id).upper()
    for c in customers:
        if c.get('customer_id') == customer_id:
            return c
    return None


def show_table(customers: List[Dict[str, Any]]) -> None:
    df = customers_to_df(customers)
    if df.empty:
        print('Không có dữ liệu để hiển thị.')
    else:
        display(df)

def show_customer_detail(c: Dict[str, Any]) -> None:
    c = enrich_customer(c)
    detail = pd.DataFrame([
        ['Mã khách hàng', c.get('customer_id', '')],
        ['Tên khách hàng', c.get('customer_name', '')],
        ['Loại khách hàng', c.get('customer_type', '')],
        ['Số điện thoại', c.get('phone', '')],
        ['Email', c.get('email', '')],
        ['Địa chỉ', c.get('address', '')],
        ['Người đại diện', c.get('representative') or '---'],
        ['Mã số thuế', c.get('tax_code') or '---'],
        ['Sản phẩm', c.get('product_service', '')],
        ['Gói dịch vụ', c.get('service_package', '')],
        ['Ngày bắt đầu', c.get('start_date', '')],
        ['Ngày hết hạn', c.get('expiry_date', '')],
        ['Trạng thái dịch vụ', c.get('service_status', '')],
        ['Trạng thái tài chính', c.get('payment_status', '')],
        ['Công nợ', f"{float(c.get('balance', 0) or 0):,.0f} VND"],
        ['Ghi chú', c.get('notes', '') or '---'],
        ['created_at', c.get('created_at', '---')],
        ['updated_at', c.get('updated_at', '---')],
        ['is_deleted', c.get('is_deleted', False)],
        ['deleted_at', c.get('deleted_at') or '---'],
    ], columns=['Trường thông tin', 'Giá trị'])
    display(detail)

# print('Đã nạp nhóm hàm hiển thị.')

# NHẬP THÔNG TIN KHÁCH HÀNG

def add_customer(
    customer_name: str,
    customer_type: str,
    phone: str,
    email: str,
    address: str,
    representative: str,
    tax_code: str,
    product_service: str,
    service_package: str,
    start_date_value: date,
    expiry_date_value: date,
    balance: float,
    notes: str = '',
) -> bool:
    customers = load_customers()
    next_id = generate_next_customer_id(customers)

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
        start_date=start_date_value,
        expiry_date=expiry_date_value,
        balance=balance,
        notes=notes,
    )

    errors = validate_customer(record, customers)
    if errors:
        print_validation_errors(errors)
        return False

    customers.append(record)
    save_customers(customers)
    print(f'✅ Thêm bản ghi thành công! Mã khách hàng: {next_id}')
    show_customer_detail(record)
    return True

# XÓA THÔNG TIN KHÁCH HÀNG

def soft_delete_customer(customer_id: str) -> bool:
    customers = load_customers()
    target = find_customer_by_id(customers, customer_id)

    if target is None:
        print('⚠️ Không tìm thấy khách hàng cần xóa.')
        return False
    if target.get('is_deleted'):
        print('⚠️ Khách hàng này đã được xóa trước đó.')
        return False

    balance = float(target.get('balance', 0) or 0)
    if balance != 0:
        print(f'⚠️ Không thể xóa. Khách hàng đang có công nợ: {balance:,.0f} VND.')
        print('Yêu cầu xử lý tất toán hoặc bù trừ trước khi xóa.')
        return False

    for c in customers:
        if c.get('customer_id') == target.get('customer_id'):
            c['is_deleted'] = True
            c['deleted_at'] = now_str()
            c['updated_at'] = now_str()
            break

    save_customers(customers)
    print('✅ Đã xóa mềm khách hàng thành công.')
    return True

# CẬP NHẬT THÔNG TIN KHÁCH HÀNG

def update_customer(customer_id: str, **fields) -> bool:
    customers = load_customers()
    old = find_customer_by_id(customers, customer_id)

    if old is None:
        print('⚠️ Không tìm thấy khách hàng cần cập nhật.')
        return False
    if old.get('is_deleted'):
        print('⚠️ Không thể cập nhật khách hàng đã xóa.')
        return False

    updated_data = dict(old)
    updated_data.update(fields)

    try:
        start_value = updated_data.get('start_date')
        expiry_value = updated_data.get('expiry_date')
        if isinstance(start_value, str):
            start_value = parse_date(start_value)
        if isinstance(expiry_value, str):
            expiry_value = parse_date(expiry_value)
    except Exception:
        print('⚠️ Ngày bắt đầu hoặc ngày hết hạn không hợp lệ. Định dạng đúng: YYYY-MM-DD.')
        return False

    updated_record = build_customer_record(
        customer_id=old.get('customer_id', ''),
        customer_name=updated_data.get('customer_name', ''),
        customer_type=updated_data.get('customer_type', ''),
        phone=updated_data.get('phone', ''),
        email=updated_data.get('email', ''),
        address=updated_data.get('address', ''),
        representative=updated_data.get('representative') or '',
        tax_code=updated_data.get('tax_code') or '',
        product_service=updated_data.get('product_service', ''),
        service_package=updated_data.get('service_package', ''),
        start_date=start_value,
        expiry_date=expiry_value,
        balance=float(updated_data.get('balance', 0) or 0),
        notes=updated_data.get('notes', ''),
        created_at=old.get('created_at'),
        is_deleted=old.get('is_deleted', False),
        deleted_at=old.get('deleted_at'),
    )

    errors = validate_customer(updated_record, customers, current_id=old.get('customer_id'))
    if errors:
        print_validation_errors(errors)
        return False

    for idx, c in enumerate(customers):
        if c.get('customer_id') == old.get('customer_id'):
            customers[idx] = updated_record
            break

    save_customers(customers)
    print('✅ Cập nhật thành công!')
    show_customer_detail(updated_record)
    return True

# TÌM KIẾM THÔNG TIN KHÁCH HÀNG

def search_customers(
    keyword: str,
    status_filter: str = 'Tất cả',
    include_deleted: bool = False,
) -> List[Dict[str, Any]]:
    customers = load_customers()
    key = normalize_keyword(keyword)
    phone_key = digits_only(keyword)

    if not key and not phone_key:
        print('⚠️ Vui lòng nhập từ khóa tìm kiếm.')
        return []

    keyword_results = []
    for c in customers:
        c2 = enrich_customer(c)
        if not include_deleted and c2.get('is_deleted'):
            continue

        matched = (
            key in normalize_keyword(c2.get('customer_id', ''))
            or key in normalize_keyword(c2.get('customer_name', ''))
            or key in normalize_keyword(c2.get('email', ''))
            or (bool(phone_key) and phone_key in digits_only(c2.get('phone', '')))
        )

        if matched:
            keyword_results.append(c2)

    final_results = [
        c for c in keyword_results
        if status_filter == 'Tất cả' or c.get('service_status') == status_filter
    ]

    if not final_results:
        print('Không tìm thấy khách hàng phù hợp.')
    else:
        print(f'Kết quả tìm kiếm: {len(final_results)} bản ghi')
        show_table(final_results)

    return final_results

# XEM DANH SÁCH KHÁCH HÀNG

def list_customers(
    keyword: str = '',
    customer_type: str = 'Tất cả',
    service_status: str = 'Tất cả',
    include_deleted: bool = False,
) -> List[Dict[str, Any]]:
    customers = load_customers()
    result = []
    key = normalize_keyword(keyword)

    for c in customers:
        c2 = enrich_customer(c)
        if not include_deleted and c2.get('is_deleted'):
            continue
        if customer_type != 'Tất cả' and c2.get('customer_type') != customer_type:
            continue
        if service_status != 'Tất cả' and c2.get('service_status') != service_status:
            continue
        if key and key not in normalize_keyword(c2.get('customer_id', '')) and key not in normalize_keyword(c2.get('customer_name', '')):
            continue
        result.append(c2)

    print('Tổng bản ghi trong file:', len(customers))
    print('Số bản ghi phù hợp:', len(result))
    show_table(result)
    return result

# print('Đã nạp 5 chức năng chính theo yêu cầu.')

# MENU CHƯƠNG TRÌNH CHÍNH

def input_date_required(label: str) -> date:
    """Bắt buộc người dùng nhập ngày theo định dạng YYYY-MM-DD."""
    while True:
        value = input(f'{label} (YYYY-MM-DD, ví dụ 2026-05-21): ').strip()
        try:
            return parse_date(value)
        except Exception:
            print('⚠️ Ngày không hợp lệ. Vui lòng nhập đúng định dạng YYYY-MM-DD.')


def input_float_required(label: str, default: float = 0) -> float:
    while True:
        value = input(f'{label}: ').strip()
        if value == '':
            return default
        try:
            return float(value)
        except ValueError:
            print('⚠️ Giá trị phải là số. Vui lòng nhập lại.')


def print_menu():
    print('\n' + '-' * 65)
    print('CHƯƠNG TRÌNH QUẢN LÝ KHÁCH HÀNG MISA')
    print('1. Nhập thông tin khách hàng')
    print('2. Xóa thông tin khách hàng')
    print('3. Cập nhật thông tin khách hàng')
    print('4. Tìm kiếm thông tin khách hàng')
    print('5. Xem danh sách khách hàng')
    print('0. Thoát')
    print('-' * 65)


def main_menu():
    while True:
        print_menu()
        choice = input('Chọn chức năng: ').strip()

        if choice == '1':
            print('\nNHẬP THÔNG TIN KHÁCH HÀNG')
            print('Lưu ý: Ngày bắt đầu và ngày hết hạn bắt buộc nhập thủ công.')
            print('Danh mục sản phẩm:', PRODUCTS)
            print('Danh mục gói dịch vụ:', PACKAGES)

            customer_name = input('Tên khách hàng: ')
            customer_type = input('Loại khách hàng [Cá nhân/Doanh nghiệp]: ') or 'Cá nhân'
            phone = input('Số điện thoại: ')
            email = input('Email: ')
            address = input('Địa chỉ: ')
            representative = input('Người đại diện: ')
            tax_code = input('Mã số thuế: ')
            product_service = input(f'Sản phẩm {PRODUCTS}: ') or PRODUCTS[0]
            service_package = input(f'Gói dịch vụ {PACKAGES}: ') or PACKAGES[0]
            start_date_value = input_date_required('Ngày bắt đầu')
            expiry_date_value = input_date_required('Ngày hết hạn')
            balance = input_float_required('Công nợ', default=0)
            notes = input('Ghi chú: ')

            add_customer(
                customer_name=customer_name,
                customer_type=customer_type,
                phone=phone,
                email=email,
                address=address,
                representative=representative,
                tax_code=tax_code,
                product_service=product_service,
                service_package=service_package,
                start_date_value=start_date_value,
                expiry_date_value=expiry_date_value,
                balance=balance,
                notes=notes,
            )

        elif choice == '2':
            print('\nXÓA THÔNG TIN KHÁCH HÀNG')
            customer_id = input('Nhập mã khách hàng cần xóa, ví dụ KH001: ')
            soft_delete_customer(customer_id)

        elif choice == '3':
            print('\nCẬP NHẬT THÔNG TIN KHÁCH HÀNG')
            customer_id = input('Nhập mã khách hàng cần cập nhật, ví dụ KH001: ').strip()

            customers = load_customers()
            old = find_customer_by_id(customers, customer_id)

            if old is None:
                print('⚠️ Không tìm thấy khách hàng cần cập nhật.')
                continue
            if old.get('is_deleted'):
                print('⚠️ Không thể cập nhật khách hàng đã xóa.')
                continue

            print('\nTHÔNG TIN HIỆN TẠI CỦA KHÁCH HÀNG')
            show_customer_detail(old)

            field_labels = {
                'customer_name': 'Tên khách hàng',
                'customer_type': 'Loại khách hàng',
                'phone': 'Số điện thoại',
                'email': 'Email',
                'address': 'Địa chỉ',
                'representative': 'Người đại diện',
                'tax_code': 'Mã số thuế',
                'product_service': 'Sản phẩm cung cấp',
                'service_package': 'Gói dịch vụ',
                'start_date': 'Ngày bắt đầu',
                'expiry_date': 'Ngày hết hạn',
                'balance': 'Công nợ',
                'notes': 'Ghi chú',
            }

            allowed_fields = list(field_labels.keys())
            label_to_field = {normalize_keyword(label): field for field, label in field_labels.items()}

            print('\nCác thông tin có thể cập nhật:')
            for index, field in enumerate(allowed_fields, start=1):
                print(f'{index}. {field_labels[field]}')

            fields_to_update = {}

            while True:
                field_input = input('\nNhập số thứ tự hoặc tên thông tin cần cập nhật, nhấn Enter để kết thúc: ').strip()

                if field_input == '':
                    break

                if field_input.isdigit() and 1 <= int(field_input) <= len(allowed_fields):
                    field = allowed_fields[int(field_input) - 1]
                else:
                    field = label_to_field.get(normalize_keyword(field_input), field_input)

                if field not in allowed_fields:
                    print('⚠️ Thông tin cần cập nhật không hợp lệ. Vui lòng nhập đúng số thứ tự hoặc tên chức năng trong danh sách.')
                    continue

                label = field_labels[field]
                print(f'Giá trị hiện tại của {label}: {old.get(field, "")}')
                value = input(f'Nhập {label} mới: ').strip()

                if field in ['start_date', 'expiry_date']:
                    try:
                        value = parse_date(value).strftime('%Y-%m-%d')
                    except Exception:
                        print('⚠️ Ngày không hợp lệ. Định dạng đúng: YYYY-MM-DD.')
                        continue
                elif field == 'balance':
                    try:
                        value = float(value)
                    except ValueError:
                        print('⚠️ Công nợ phải là số.')
                        continue

                fields_to_update[field] = value
                print(f'Đã ghi nhận thay đổi: {label} = {value}')

            if not fields_to_update:
                print('Bạn chưa nhập trường nào cần cập nhật. Không có thay đổi nào được lưu.')
                continue

            print('\nTHÔNG TIN THAY ĐỔI TRƯỚC KHI LƯU')
            for key, value in fields_to_update.items():
                label = field_labels.get(key, key)
                print(f'- {label}: {old.get(key, "")} -> {value}')

            confirm = input('Xác nhận lưu các thay đổi? [Y/N]: ').strip().lower()
            if confirm == 'y':
                update_customer(customer_id, **fields_to_update)
            else:
                print('Đã hủy thao tác cập nhật.')

        elif choice == '4':
            print('\nTÌM KIẾM THÔNG TIN KHÁCH HÀNG')
            keyword = input('Nhập từ khóa tìm kiếm: ')
            search_customers(keyword)

        elif choice == '5':
            print('\nXEM DANH SÁCH KHÁCH HÀNG')
            list_customers()

        elif choice == '0':
            print('Kết thúc chương trình.')
            break

        else:
            print('⚠️ Lựa chọn không hợp lệ. Vui lòng chọn lại.')
main_menu()
