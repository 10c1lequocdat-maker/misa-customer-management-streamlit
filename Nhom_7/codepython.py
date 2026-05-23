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
  PACKAGES = ['Standard', 'Professional', 'Enterprise']
  CUSTOMER_TYPES = ['Cá nhân', 'Doanh nghiệp']
  USAGE_DURATION_TYPES = ['Có thời hạn', 'Vĩnh viễn']
  SERVICE_STATUS_ALL = ['Tất cả', 'Hoạt động', 'Hết hạn', 'Đã xóa']

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

  # NHÓM HÀM CHUẨN HÓA - KIỂM TRA DỮ LIỆU

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

  def calculate_service_status(expiry_date: str, usage_duration_type: str = 'Có thời hạn') -> str:
      """Tính trạng thái dịch vụ dựa trên loại thời hạn sử dụng.

      Quy ước trạng thái:
      - Vĩnh viễn: Hoạt động
      - Có thời hạn và ngày hết hạn chưa qua: Hoạt động
      - Có thời hạn và ngày hết hạn đã qua: Hết hạn
      - Ngày hết hạn lỗi/không hợp lệ: Hết hạn
      """
      if usage_duration_type == 'Vĩnh viễn':
          return 'Hoạt động'

      try:
          exp = datetime.strptime(expiry_date, '%Y-%m-%d').date()
      except Exception:
          return 'Hết hạn'

      if exp < date.today():
          return 'Hết hạn'
      return 'Hoạt động'

  def calculate_payment_status(balance: float) -> str:
      if balance == 0:
          return 'Đã thanh toán'
      if balance > 0:
          return 'Chưa thanh toán'
      return f'Đã thanh toán (Dư: {abs(balance):,.0f} VND)'

  def active_customers(customers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
      return [c for c in customers if not c.get('is_deleted', False)]


  def get_customer_duplicate_error(
      customer: Dict[str, Any],
      customers: List[Dict[str, Any]],
      current_id: Optional[str] = None,
  ) -> Optional[str]:
      """Kiểm tra trùng khách hàng theo quy tắc nghiệp vụ.
      Quy tắc:
      - Cùng tên + cùng số điện thoại + khác sản phẩm: được nhập.
      - Cùng tên + cùng số điện thoại + cùng sản phẩm + khác gói dịch vụ: được nhập.
      - Cùng tên + cùng số điện thoại + cùng sản phẩm + cùng gói dịch vụ: báo trùng.
      - Khác tên + cùng số điện thoại: báo trùng.
      """
      phone = digits_only(customer.get('phone', ''))
      name = normalize_keyword(customer.get('customer_name', ''))
      product = customer.get('product_service', '')
      package = customer.get('service_package', '')

      if not phone:
          return None

      for c in active_customers(customers):
          if current_id and c.get('customer_id') == current_id:
              continue

          same_phone = digits_only(c.get('phone', '')) == phone
          if not same_phone:
              continue

          same_name = normalize_keyword(c.get('customer_name', '')) == name
          same_product = c.get('product_service') == product
          same_package = c.get('service_package') == package

          if not same_name:
              return '⚠️ Số điện thoại này đã tồn tại với một khách hàng khác tên. Vui lòng kiểm tra lại tên khách hàng hoặc số điện thoại.'

          if same_name and same_product and same_package:
              return '⚠️ Khách hàng này đã tồn tại với cùng tên, số điện thoại, sản phẩm và gói dịch vụ.'

      return None

  def enrich_customer(c: Dict[str, Any]) -> Dict[str, Any]:
      c = dict(c)
      usage_type = c.get('usage_duration_type', 'Có thời hạn')
      c['service_status'] = 'Đã xóa' if c.get('is_deleted') else calculate_service_status(c.get('expiry_date', ''), usage_type)
      c['payment_status'] = calculate_payment_status(float(c.get('balance', 0) or 0))
      return c

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
      usage_duration_type: str,
      start_date: Optional[date],
      expiry_date: Optional[date],
      balance: float,
      notes: str,
      created_at: Optional[str] = None,
      is_deleted: bool = False,
      deleted_at: Optional[str] = None,
  ) -> Dict[str, Any]:
      customer_id = normalize_spaces(customer_id).upper()
      customer_name = normalize_spaces(customer_name)
      customer_type = normalize_spaces(customer_type)
      usage_duration_type = normalize_spaces(usage_duration_type) or 'Có thời hạn'
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

      if usage_duration_type == 'Vĩnh viễn':
          start_date_str = ''
          expiry_date_str = 'Vĩnh viễn'
      else:
          start_date_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, date) else ''
          expiry_date_str = expiry_date.strftime('%Y-%m-%d') if isinstance(expiry_date, date) else ''

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
          'usage_duration_type': usage_duration_type,
          'start_date': start_date_str,
          'expiry_date': expiry_date_str,
          'service_status': calculate_service_status(expiry_date_str, usage_duration_type),
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
          'usage_duration_type': 'Thời hạn sử dụng',
          'balance': 'Công nợ',
      }

      for key, label in required_fields.items():
          if customer.get(key) in (None, ''):
              errors.append(f'⚠️ {label} không được để trống.')

      if customer.get('customer_type') not in CUSTOMER_TYPES:
          errors.append('⚠️ Loại khách hàng chỉ được nhập: Cá nhân hoặc Doanh nghiệp.')

      if customer.get('usage_duration_type') not in USAGE_DURATION_TYPES:
          errors.append('⚠️ Thời hạn sử dụng chỉ được nhập: Có thời hạn hoặc Vĩnh viễn.')

      if customer.get('customer_type') == 'Doanh nghiệp':
          if not customer.get('representative'):
              errors.append('⚠️ Khách hàng doanh nghiệp bắt buộc phải nhập người đại diện.')
          if not customer.get('tax_code'):
              errors.append('⚠️ Khách hàng doanh nghiệp bắt buộc phải nhập mã số thuế.')

      phone = digits_only(customer.get('phone', ''))
      if not phone_is_valid(phone):
          errors.append('⚠️ Số điện thoại sai định dạng. Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0.')

      duplicate_error = get_customer_duplicate_error(customer, customers, current_id=current_id)
      if duplicate_error:
          errors.append(duplicate_error)

      if not email_is_valid(customer.get('email', '')):
          errors.append('⚠️ Email sai định dạng. Ví dụ đúng: abc@gmail.com')

      if customer.get('tax_code') and not tax_code_is_valid(customer.get('tax_code', '')):
          errors.append('⚠️ Mã số thuế sai định dạng. Mã số thuế phải gồm 10 hoặc 13 chữ số.')

      if customer.get('usage_duration_type') == 'Có thời hạn':
          if not customer.get('start_date'):
              errors.append('⚠️ Ngày bắt đầu không được để trống khi chọn thời hạn sử dụng là Có thời hạn.')
          if not customer.get('expiry_date'):
              errors.append('⚠️ Ngày hết hạn không được để trống khi chọn thời hạn sử dụng là Có thời hạn.')
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
              print(err)

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
              'Thời hạn sử dụng': c.get('usage_duration_type', 'Có thời hạn'),
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
          ['Thời hạn sử dụng', c.get('usage_duration_type', 'Có thời hạn')],
          ['Ngày bắt đầu', c.get('start_date', '') or '---'],
          ['Ngày hết hạn', c.get('expiry_date', '') or '---'],
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

  # HÀM NHẬP LIỆU CÓ KIỂM TRA TỨC THỜI

  def input_non_empty(label: str, max_length: Optional[int] = None) -> str:
      while True:
          value = input(f'{label}: ').strip()
          if not value:
              print(f'⚠️ {label} không được để trống. Vui lòng nhập lại.')
              continue
          if max_length and len(value) > max_length:
              print(f'⚠️ {label} không được vượt quá {max_length} ký tự. Vui lòng nhập lại.')
              continue
          return value

  def input_customer_type() -> str:
      while True:
          value = input('Loại khách hàng [Cá nhân/Doanh nghiệp]: ').strip() or 'Cá nhân'
          if value in CUSTOMER_TYPES:
              return value
          print('⚠️ Loại khách hàng chỉ được nhập: Cá nhân hoặc Doanh nghiệp.')

  def input_usage_duration_type() -> str:
      while True:
          print('Thời hạn sử dụng:')
          print('1. Có thời hạn')
          print('2. Vĩnh viễn')
          value = input('Chọn thời hạn sử dụng [1/2 hoặc nhập tên]: ').strip()
          if value == '1' or normalize_keyword(value) == normalize_keyword('Có thời hạn'):
              return 'Có thời hạn'
          if value == '2' or normalize_keyword(value) == normalize_keyword('Vĩnh viễn'):
              return 'Vĩnh viễn'
          print('⚠️ Lựa chọn thời hạn sử dụng không hợp lệ. Vui lòng nhập 1 hoặc 2.')

  def input_phone(customers: List[Dict[str, Any]], current_id: Optional[str] = None) -> str:
      while True:
          phone = input('Số điện thoại: ').strip()
          if not phone_is_valid(phone):
              print('⚠️ Số điện thoại sai định dạng. Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0.')
              continue

          # Chưa kiểm tra trùng ngay tại bước nhập số điện thoại vì cần thêm tên khách hàng,
          # sản phẩm và gói dịch vụ để xác định đúng quy tắc nghiệp vụ.
          return digits_only(phone)

  def input_email() -> str:
      while True:
          email = input('Email: ').strip()
          if email_is_valid(email):
              return normalize_spaces(email).lower()
          print('⚠️ Email sai định dạng. Ví dụ đúng: abc@gmail.com')

  def input_tax_code(required: bool = False) -> str:
      while True:
          tax_code = input('Mã số thuế: ').strip()
          if required and not tax_code:
              print('⚠️ Khách hàng doanh nghiệp bắt buộc phải nhập mã số thuế.')
              continue
          if tax_code and not tax_code_is_valid(tax_code):
              print('⚠️ Mã số thuế sai định dạng. Mã số thuế phải gồm 10 hoặc 13 chữ số.')
              continue
          return digits_only(tax_code)

  def input_representative(required: bool = False) -> str:
      while True:
          representative = input('Người đại diện: ').strip()
          if required and not representative:
              print('⚠️ Khách hàng doanh nghiệp bắt buộc phải nhập người đại diện.')
              continue
          return representative

  def input_choice_from_list(label: str, choices: List[str]) -> str:
      while True:
          print(f'{label}:')
          for i, item in enumerate(choices, start=1):
              print(f'{i}. {item}')
          value = input(f'Chọn {label.lower()} bằng số thứ tự hoặc nhập tên: ').strip()

          if value.isdigit() and 1 <= int(value) <= len(choices):
              return choices[int(value) - 1]

          for item in choices:
              if normalize_keyword(value) == normalize_keyword(item):
                  return item

          print(f'⚠️ {label} không hợp lệ. Vui lòng chọn trong danh sách.')

  def input_date_required(label: str) -> date:
      """Bắt buộc người dùng nhập ngày theo định dạng YYYY-MM-DD."""
      while True:
          value = input(f'{label} (YYYY-MM-DD, ví dụ 2026-05-21): ').strip()
          try:
              return parse_date(value)
          except Exception:
              print('⚠️ Ngày không hợp lệ. Vui lòng nhập đúng định dạng YYYY-MM-DD.')

  def input_date_range() -> tuple:
      while True:
          start_date_value = input_date_required('Ngày bắt đầu')
          expiry_date_value = input_date_required('Ngày hết hạn')
          if expiry_date_value < start_date_value:
              print('⚠️ Ngày hết hạn phải lớn hơn hoặc bằng ngày bắt đầu. Vui lòng nhập lại.')
              continue
          return start_date_value, expiry_date_value

  def input_float_required(label: str, default: float = 0) -> float:
      while True:
          value = input(f'{label}: ').strip()
          if value == '':
              return default
          try:
              return float(value)
          except ValueError:
              print('⚠️ Giá trị phải là số. Vui lòng nhập lại.')

  def input_notes() -> str:
      while True:
          notes = input('Ghi chú: ').strip()
          if len(notes) <= 500:
              return notes
          print('⚠️ Ghi chú không được vượt quá 500 ký tự. Vui lòng nhập lại.')

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
      usage_duration_type: str,
      start_date_value: Optional[date],
      expiry_date_value: Optional[date],
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
          usage_duration_type=usage_duration_type,
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

      usage_type = updated_data.get('usage_duration_type', 'Có thời hạn')
      try:
          if usage_type == 'Vĩnh viễn':
              start_value = None
              expiry_value = None
          else:
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
          usage_duration_type=usage_type,
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

  def validate_update_field(field: str, value: Any, old: Dict[str, Any], fields_to_update: Dict[str, Any]) -> bool:
      """Kiểm tra ngay giá trị mới trong chức năng cập nhật."""
      customers = load_customers()
      temp_data = dict(old)
      temp_data.update(fields_to_update)
      temp_data[field] = value

      if temp_data.get('usage_duration_type') == 'Vĩnh viễn':
          temp_data['start_date'] = ''
          temp_data['expiry_date'] = 'Vĩnh viễn'

      # Tạo bản ghi tạm để dùng lại validate_customer.
      try:
          if temp_data.get('usage_duration_type') == 'Vĩnh viễn':
              start_value = None
              expiry_value = None
          else:
              start_value = temp_data.get('start_date')
              expiry_value = temp_data.get('expiry_date')
              if isinstance(start_value, str):
                  start_value = parse_date(start_value)
              if isinstance(expiry_value, str):
                  expiry_value = parse_date(expiry_value)

          temp_record = build_customer_record(
              customer_id=old.get('customer_id', ''),
              customer_name=temp_data.get('customer_name', ''),
              customer_type=temp_data.get('customer_type', ''),
              phone=temp_data.get('phone', ''),
              email=temp_data.get('email', ''),
              address=temp_data.get('address', ''),
              representative=temp_data.get('representative') or '',
              tax_code=temp_data.get('tax_code') or '',
              product_service=temp_data.get('product_service', ''),
              service_package=temp_data.get('service_package', ''),
              usage_duration_type=temp_data.get('usage_duration_type', 'Có thời hạn'),
              start_date=start_value,
              expiry_date=expiry_value,
              balance=float(temp_data.get('balance', 0) or 0),
              notes=temp_data.get('notes', ''),
              created_at=old.get('created_at'),
              is_deleted=old.get('is_deleted', False),
              deleted_at=old.get('deleted_at'),
          )
      except Exception:
          print('⚠️ Dữ liệu cập nhật không hợp lệ.')
          return False

      errors = validate_customer(temp_record, customers, current_id=old.get('customer_id'))
      if errors:
          print_validation_errors(errors)
          return False
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

  def view_customer_detail_by_id(customer_id: str, include_deleted: bool = False) -> None:
      customers = load_customers()
      customer = find_customer_by_id(customers, customer_id)
      if customer is None:
          print('⚠️ Không tìm thấy khách hàng.')
          return
      if customer.get('is_deleted') and not include_deleted:
          print('⚠️ Khách hàng này đã bị xóa mềm. Muốn xem cần chọn include_deleted=True.')
          return
      show_customer_detail(customer)

  # MENU CHƯƠNG TRÌNH CHÍNH

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
              customers = load_customers()
              customer_name = input_non_empty('Tên khách hàng')
              customer_type = input_customer_type()
              phone = input_phone(customers)
              email = input_email()
              address = input_non_empty('Địa chỉ', max_length=250)

              representative = ''
              tax_code = ''
              if customer_type == 'Doanh nghiệp':
                  representative = input_representative(required=True)
                  tax_code = input_tax_code(required=True)
              else:
                  representative = input_representative(required=False)
                  tax_code = input_tax_code(required=False)

              product_service = input_choice_from_list('Sản phẩm cung cấp', PRODUCTS)
              service_package = input_choice_from_list('Gói dịch vụ', PACKAGES)

              while True:
                  temp_customer = {
                      'customer_name': customer_name,
                      'phone': phone,
                      'product_service': product_service,
                      'service_package': service_package,
                  }
                  duplicate_error = get_customer_duplicate_error(temp_customer, customers)
                  if not duplicate_error:
                      break

                  print(duplicate_error)
                  print('Vui lòng nhập lại thông tin để tránh trùng dữ liệu.')
                  print('1. Nhập lại tên khách hàng')
                  print('2. Nhập lại số điện thoại')
                  print('3. Nhập lại sản phẩm')
                  print('4. Nhập lại gói dịch vụ')
                  edit_choice = input('Chọn thông tin muốn nhập lại [1/2/3/4]: ').strip()

                  if edit_choice == '1':
                      customer_name = input_non_empty('Tên khách hàng')
                  elif edit_choice == '2':
                      phone = input_phone(customers)
                  elif edit_choice == '3':
                      product_service = input_choice_from_list('Sản phẩm cung cấp', PRODUCTS)
                  elif edit_choice == '4':
                      service_package = input_choice_from_list('Gói dịch vụ', PACKAGES)
                  else:
                      print('⚠️ Lựa chọn không hợp lệ. Vui lòng chọn lại.')

              usage_duration_type = input_usage_duration_type()
              if usage_duration_type == 'Có thời hạn':
                  start_date_value, expiry_date_value = input_date_range()
              else:
                  start_date_value, expiry_date_value = None, None

              balance = input_float_required('Công nợ', default=0)
              notes = input_notes()

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
                  usage_duration_type=usage_duration_type,
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
                  'usage_duration_type': 'Thời hạn sử dụng',
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
                      print('⚠️ Thông tin cần cập nhật không hợp lệ. Vui lòng nhập đúng số thứ tự hoặc tên thông tin trong danh sách.')
                      continue

                  label = field_labels[field]
                  print(f'Giá trị hiện tại của {label}: {old.get(field, "")}')

                  # Nhập và kiểm tra ngay giá trị của từng thông tin cập nhật.
                  if field == 'customer_name':
                      value = input_non_empty('Tên khách hàng')
                  elif field == 'customer_type':
                      value = input_customer_type()
                      if value == 'Doanh nghiệp':
                          temp_representative = fields_to_update.get('representative', old.get('representative') or '')
                          temp_tax_code = fields_to_update.get('tax_code', old.get('tax_code') or '')
                          if not temp_representative:
                              fields_to_update['representative'] = input_representative(required=True)
                          if not temp_tax_code:
                              fields_to_update['tax_code'] = input_tax_code(required=True)
                  elif field == 'phone':
                      value = input_phone(customers, current_id=old.get('customer_id'))
                  elif field == 'email':
                      value = input_email()
                  elif field == 'address':
                      value = input_non_empty('Địa chỉ', max_length=250)
                  elif field == 'representative':
                      required = (fields_to_update.get('customer_type', old.get('customer_type')) == 'Doanh nghiệp')
                      value = input_representative(required=required)
                  elif field == 'tax_code':
                      required = (fields_to_update.get('customer_type', old.get('customer_type')) == 'Doanh nghiệp')
                      value = input_tax_code(required=required)
                  elif field == 'product_service':
                      value = input_choice_from_list('Sản phẩm cung cấp', PRODUCTS)
                  elif field == 'service_package':
                      value = input_choice_from_list('Gói dịch vụ', PACKAGES)
                  elif field == 'usage_duration_type':
                      value = input_usage_duration_type()
                      if value == 'Có thời hạn':
                          start_date_value, expiry_date_value = input_date_range()
                          fields_to_update['start_date'] = start_date_value.strftime('%Y-%m-%d')
                          fields_to_update['expiry_date'] = expiry_date_value.strftime('%Y-%m-%d')
                      else:
                          fields_to_update['start_date'] = ''
                          fields_to_update['expiry_date'] = 'Vĩnh viễn'
                  elif field in ['start_date', 'expiry_date']:
                      if fields_to_update.get('usage_duration_type', old.get('usage_duration_type', 'Có thời hạn')) == 'Vĩnh viễn':
                          print('⚠️ Khách hàng đang chọn thời hạn sử dụng là Vĩnh viễn nên không cần cập nhật ngày bắt đầu/ngày hết hạn.')
                          continue
                      value_date = input_date_required(label)
                      value = value_date.strftime('%Y-%m-%d')
                  elif field == 'balance':
                      value = input_float_required('Công nợ', default=0)
                  elif field == 'notes':
                      value = input_notes()

                  if validate_update_field(field, value, old, fields_to_update):
                      fields_to_update[field] = value
                      print(f'✅ Đã ghi nhận thay đổi: {label} = {value}')
                  else:
                      print('Thông tin này chưa được ghi nhận. Vui lòng nhập lại nếu cần.')

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
              result = list_customers()

              if result:
                  view_detail = input('Bạn có muốn xem chi tiết khách hàng không? [Y/N]: ').strip().lower()
                  if view_detail == 'y':
                      while True:
                          customer_id = input('Nhập mã khách hàng cần xem chi tiết, ví dụ KH001, hoặc nhấn Enter để quay lại menu: ').strip()
                          if customer_id == '':
                              break
                          customer = find_customer_by_id(result, customer_id)
                          if customer:
                              show_customer_detail(customer)
                              break
                          print('⚠️ Mã khách hàng không nằm trong danh sách đang hiển thị. Vui lòng nhập lại.')

          elif choice == '0':
              print('Kết thúc chương trình.')
              break

          else:
              print('⚠️ Lựa chọn không hợp lệ. Vui lòng chọn lại.')

  main_menu()
