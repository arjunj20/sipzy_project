def recalculate_totals(self):
    # Get only non-cancelled items
    active_items = self.items.exclude(status="cancelled")

    # Recalculate subtotal
    self.subtotal = sum(item.price * item.quantity for item in active_items)

    # Recalculate tax (example 18% GST – change if needed)
    tax_rate = 0.18  
    self.tax = round(self.subtotal * tax_rate, 2)

    # Recalculate total
    self.total = self.subtotal + self.tax + self.shipping_fee - self.discount

    self.save(update_fields=["subtotal", "tax", "total"])
