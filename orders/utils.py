from decimal import Decimal

def recalculate_totals(self):

    active_items = self.items.exclude(status="cancelled")

    # Prices are already tax-inclusive
    self.subtotal = sum(
        item.price * item.quantity
        for item in active_items
    )

    # IMPORTANT: tax must always be ZERO
    self.tax = Decimal("0.00")

    # FINAL total
    self.total = (
        self.subtotal +
        self.shipping_fee -
        self.discount
    )

    self.save(update_fields=["subtotal", "tax", "total"])

