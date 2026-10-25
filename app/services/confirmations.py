
class Confirmations():
	
	def __init__(self, id, order_number, order_qty, order_fob, order_transport, order_eta, order_confirmed, order_sales_prices, order_supplier, order_orig_qty, order_ecv, order_eds, order_comment, order_rmb, order_tl):
		self.id = id
		self.order_number = order_number
		self.order_qty = order_qty
		self.order_fob = order_fob
		self.order_transport = order_transport
		self.order_eta = order_eta
		self.order_confirmed = order_confirmed
		self.order_sales_price = order_sales_prices
		self.order_supplier = order_supplier
		self.order_orig_qty = order_orig_qty
		self.order_ecv = order_ecv
		self.order_eds = order_eds
		self.order_comment = order_comment
		self.order_rmb = order_rmb
		self.order_tl = order_tl

	def __repr__(self):
		return f"<Confirmation {self.id}, {self.order_number}, {self.order_qty}>"
