
from .get_order_available_qty_excluding_sent import get_order_available_qty_excluding_sent

def get_current_stock_qty(orders):

	stock_orders = []

	for o in orders[:]:
		o.available_quantity_excluding_sent = get_order_available_qty_excluding_sent(o.id)
		if o.available_quantity_excluding_sent > 0 and o.sales_price:
			stock_orders.append(o)

	current_stock_qty = sum(so.available_quantity_excluding_sent for so in stock_orders)

	return current_stock_qty