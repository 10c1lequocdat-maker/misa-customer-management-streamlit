import json
from pathlib import Path

DATA_FILE = Path("data/customers.json")

def load_customers():
    DATA_FILE.parent.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")
        return []

    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

def save_customers(customers):
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(customers, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )
