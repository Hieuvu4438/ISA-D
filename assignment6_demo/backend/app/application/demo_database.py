"""Explicit, repeatable import of public demo business data into local SQLite."""
from datetime import UTC, datetime
import json
from pathlib import Path

from app.data.account_repository import AccountRepository
from app.data.admin_repository import AdminRepository
from app.data.catalog_draft_repository import CatalogDraftRepository
from app.data.order_repository import OrderRepository
from app.data.product_repository import ProductRepository, digest
from app.data.purchase_repository import PurchaseRepository
from app.data.return_repository import ReturnRepository
from app.data.shopping_repository import ShoppingRepository
from app.domain import ACCESSORY_SIZES, APPAREL_SIZES, SHOE_SIZES


def import_demo_database(root: Path):
    root = Path(root).resolve()
    products = ProductRepository(root)
    orders = OrderRepository(root)
    seed = json.loads((root / "data/demo_database.json").read_text(encoding="utf-8"))
    if (seed["schema_version"] != 1 or seed["catalog_fingerprint"] != products.fingerprint
            or seed["historical_orders_fingerprint"] != digest(orders.orders)
            or seed["product_count"] != len(products.products) or seed["historical_order_count"] != len(orders.orders)):
        raise ValueError("Demo snapshot does not match the checked-out catalog/orders")
    by_id = {p["product_id"]: p for p in products.products}
    definitions = {}
    for row in seed["variants"]:
        if set(row) != {"variant_id", "product_id", "size"} or row["product_id"] not in by_id:
            raise ValueError("Invalid variant definition")
        category = by_id[row["product_id"]]["category"]
        allowed = APPAREL_SIZES if category in ("t_shirt", "jacket") else SHOE_SIZES if category in (
            "running_shoes", "trail_shoes", "casual_shoes", "boots", "sandals") else ACCESSORY_SIZES
        if (row["size"] not in allowed or row["variant_id"] != f"{row['product_id']}-{row['size']}"
                or row["variant_id"] in definitions):
            raise ValueError("Invalid/duplicate size SKU")
        definitions[row["variant_id"]] = row
    quantities = {}
    for row in seed["inventory"]:
        if (set(row) != {"sku", "quantity"} or row["sku"] in quantities
                or type(row["quantity"]) is not int or not 0 <= row["quantity"] <= 1_000_000):
            raise ValueError("Invalid/duplicate stock row")
        quantities[row["sku"]] = row["quantity"]
    states = {row["product_id"]: row["sale_state"] for row in seed["sale_states"]}
    if (set(quantities) != set(by_id) | set(definitions) or set(states) != set(by_id)
            or len(states) != len(seed["sale_states"]) or not set(states.values()) <= {"active", "archived"}):
        raise ValueError("Incomplete stock/sale-state snapshot")
    snapshot_id = digest(seed)
    accounts = AccountRepository(root / "runtime/commerce/accounts.sqlite3")
    ShoppingRepository(accounts)
    PurchaseRepository(accounts, products.products)
    AdminRepository(accounts)
    ReturnRepository(accounts)
    CatalogDraftRepository(accounts)
    with accounts.connection() as db:
        db.execute("CREATE TABLE IF NOT EXISTS demo_imports (snapshot_id TEXT PRIMARY KEY, imported_at TEXT NOT NULL)")
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT snapshot_id FROM demo_imports").fetchall()
        if previous:
            if previous[0][0] != snapshot_id:
                raise ValueError("A different snapshot was imported; existing data was not overwritten")
            applied = False
        else:
            for table in ("purchases", "product_variants", "catalog_publication", "cart_items", "wishlist_items", "admin_audit"):
                if db.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
                    raise ValueError("Database already contains business activity; refusing to reset it")
            existing = dict(db.execute("SELECT product_id,quantity FROM inventory"))
            if existing != {pid: p["stock_quantity"] for pid, p in by_id.items()}:
                raise ValueError("Existing inventory differs from seed; refusing to overwrite it")
            db.executemany("INSERT INTO product_variants(variant_id,product_id,size) VALUES(?,?,?)",
                           [(r["variant_id"], r["product_id"], r["size"]) for r in definitions.values()])
            db.executemany("INSERT INTO inventory(product_id,quantity) VALUES(?,?) ON CONFLICT(product_id) DO UPDATE SET quantity=excluded.quantity", quantities.items())
            db.executemany("INSERT INTO product_availability(product_id,sale_state) VALUES(?,?) ON CONFLICT(product_id) DO UPDATE SET sale_state=excluded.sale_state", states.items())
            db.execute("UPDATE inventory_state SET revision=revision+1 WHERE singleton=1")
            db.execute("INSERT INTO demo_imports VALUES(?,?)", (snapshot_id, datetime.now(UTC).isoformat()))
            applied = True
        return {"applied": applied, "snapshot_id": snapshot_id, "products": len(by_id),
                "historical_orders": len(orders.orders), "inventory_rows": db.execute("SELECT COUNT(*) FROM inventory").fetchone()[0],
                "size_variants": db.execute("SELECT COUNT(*) FROM product_variants").fetchone()[0]}
