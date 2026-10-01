"""Customer-scoped lookup; deliberately distinct from product ranking."""

import re


class OrderService:
    def __init__(self, repository):
        self.repository = repository

    def find_order(self, order_id, customer_id):
        if not isinstance(order_id, str) or not re.fullmatch(r"O\d{3}", order_id):
            raise ValueError("order-id must have format O001")
        if not isinstance(customer_id, str) or not re.fullmatch(r"C\d{3}", customer_id):
            raise ValueError("customer-id is required with format C001")
        order = self.repository.find_order(order_id, customer_id)
        return {
            "query": {"type": "order", "order_id": order_id, "customer_id": customer_id},
            "processing": {"customer_scope": customer_id, "authentication": "simulated customer context"},
            "order": order,
            "message": "Order found" if order else "Order not found for this customer",
        }
