def recalculate_totals(self):

    active_items = self.items.exclude(status="cancelled")

    self.subtotal = sum(item.price * item.quantity for item in active_items)


    tax_rate = 0.18  
    self.tax = round(self.subtotal * tax_rate, 2)


    self.total = self.subtotal + self.tax + self.shipping_fee - self.discount

    self.save(update_fields=["subtotal", "tax", "total"])
