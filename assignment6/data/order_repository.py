"""Local order data; no production authentication is implied."""
from copy import deepcopy
import json
import math
from pathlib import Path


class OrderRepository:
    def __init__(self, path=None):
        try:
            self.orders = json.loads(Path(path or Path(__file__).with_name('orders.json')).read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError('cannot load orders') from exc
        if not isinstance(self.orders, list):
            raise ValueError('orders must be a list')
        seen = set()
        for order in self.orders:
            fields = {'order_id', 'customer_id', 'date', 'status', 'total'}
            if not isinstance(order, dict) or not fields <= order.keys():
                raise ValueError('order is missing required fields')
            if any(not isinstance(order[k], str) or not order[k].strip() for k in fields - {'total'}):
                raise ValueError('order identifiers/status/date must be strings')
            if order['order_id'] in seen:
                raise ValueError('duplicate order ID')
            seen.add(order['order_id'])
            total = order['total']
            if isinstance(total, bool) or not isinstance(total, (int, float)) or not math.isfinite(total) or total < 0:
                raise ValueError('invalid order total')

    def find_order(self, order_id, customer_id=None):
        return next((deepcopy(o) for o in self.orders if o['order_id'] == order_id and (customer_id is None or o['customer_id'] == customer_id)), None)
