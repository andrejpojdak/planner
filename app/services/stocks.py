import pandas as pd
from ..models import Material
from .yearly_demand import yearly_demand
from .get_order_available_qty_excluding_sent import get_order_available_qty_excluding_sent
from ..models import Delivery
from datetime import date, timedelta

def analyze_safety_stock(buyer_article_number, deliveries, orders, brasil_delta, portugal_delta):
	
	class Stock():

		def __init__(self, safety_stock_qty, safety_stock_string, yearly_demand_qty, stock_df_html, stock_alert_list):
			
			self.safety_stock_qty = safety_stock_qty
			self.safety_stock_string = safety_stock_string
			self.yearly_demand_qty = yearly_demand_qty
			self.stock_df_html = stock_df_html
			self.stock_alert_list = stock_alert_list

	safety_stock_string = Material.query.filter(Material.material_code == buyer_article_number).first().safety_stock

	if '%' in safety_stock_string:

		safety_stock_perc = int(safety_stock_string.removesuffix("%")) / 100
		yearly_demand_qty = yearly_demand(deliveries)
		safety_stock = yearly_demand_qty * safety_stock_perc

		stock_obj = Stock(
			int(safety_stock),
			safety_stock_string,
			yearly_demand_qty,
			None,
			[]
		)
	
	elif 'pcs' in safety_stock_string:

		safety_stock = int(safety_stock_string.removesuffix("pcs"))
		yearly_demand_qty = yearly_demand(deliveries)

		stock_obj = Stock(
			int(safety_stock),
			safety_stock_string,
			yearly_demand_qty,
			None,
			[]
		)
	else:
		return None, None, None, None, None
	
	stock_orders = []
	remaining_orders = []
	remaining_deliveries = []
	stock_analyze_list = []

	for o in orders[:]:
		o.available_quantity_excluding_sent = get_order_available_qty_excluding_sent(o.id)
		if o.available_quantity_excluding_sent > 0 and o.sales_price:
			stock_orders.append(o)
		if o.available_quantity_excluding_sent > 0 and not o.sales_price and o.eta:
			remaining_orders.append(o)

	current_stock_qty = sum(so.available_quantity_excluding_sent for so in stock_orders)

	for d in deliveries:
		if d.sent is not True:
			remaining_deliveries.append(d)

	stock_analyze_list = remaining_orders + remaining_deliveries
	for i in stock_analyze_list:
		if isinstance(i, Delivery):
			delta = 0
			if 'brasil' in str(d.plant_name).lower():
				delta = brasil_delta
			if 'portugal' in str(d.plant_name).lower():
				delta = portugal_delta
			i.delivery_date = i.delivery_date - timedelta(days = delta)
	
	stock_analyze_list = sorted(
		stock_analyze_list,
		key=lambda obj: obj.delivery_date if isinstance(obj, Delivery) else obj.eta
	)
	stock_df = pd.DataFrame(columns=['SO/PO', '+/-', 'Date', 'Stock', 'Alert'])

	if current_stock_qty > stock_obj.safety_stock_qty:
		stock_df.loc[len(stock_df)] = {
			'SO/PO': 'Current stock',
			'+/-': '',
			'Date': '',
			'Stock': current_stock_qty,
			'Alert': ''
		}
	
	else:
		stock_obj.stock_alert_list.append(( date.today(), current_stock_qty - stock_obj.safety_stock_qty ))

		stock_df.loc[len(stock_df)] = {
			'SO/PO': 'Current stock',
			'+/-': '',
			'Date': '',
			'Stock': current_stock_qty,
			'Alert': current_stock_qty - stock_obj.safety_stock_qty
		}
	
	for i in stock_analyze_list:
		if isinstance(i, Delivery):

			current_stock_qty = current_stock_qty - i.delivery_quantity

			if current_stock_qty < stock_obj.safety_stock_qty:
				
				stock_obj.stock_alert_list.append(( i.delivery_date, current_stock_qty - stock_obj.safety_stock_qty ))
				
				stock_df.loc[len(stock_df)] = {
					'SO/PO': f"{d.delivery_schedule_number.lstrip('0')}-{d.delivery_schedule_position}",
					'+/-': f'-{i.delivery_quantity}',
					'Date': i.delivery_date,
					'Stock': current_stock_qty,
					'Alert': current_stock_qty - stock_obj.safety_stock_qty
				}

			else:

				stock_df.loc[len(stock_df)] = {
					'SO/PO': f"{d.delivery_schedule_number.lstrip('0')}-{d.delivery_schedule_position}",
					'+/-': f'-{i.delivery_quantity}',
					'Date': i.delivery_date,
					'Stock': current_stock_qty,
					'Alert': ''
				}
		else:

			current_stock_qty = current_stock_qty + i.available_quantity_excluding_sent
			
			if current_stock_qty < stock_obj.safety_stock_qty:
				
				stock_obj.stock_alert_list.append(( i.eta, current_stock_qty - stock_obj.safety_stock_qty ))
			
				stock_df.loc[len(stock_df)] = {
					'SO/PO': i.order_number,
					'+/-': f'+{i.available_quantity_excluding_sent}',
					'Date': i.eta,
					'Stock': current_stock_qty,
					'Alert': current_stock_qty - stock_obj.safety_stock_qty
				}
			else:
				stock_df.loc[len(stock_df)] = {
					'SO/PO': i.order_number,
					'+/-': f'+{i.available_quantity_excluding_sent}',
					'Date': i.eta,
					'Stock': current_stock_qty,
					'Alert': ''
				}
	stock_df["Date"] = pd.to_datetime(stock_df["Date"]).dt.strftime("%d.%m.%Y").fillna("")
	stock_obj.stock_df_html = stock_df.to_html(index=False).replace('class="dataframe"', f'class="stock-df"')
	
	return stock_obj.safety_stock_qty, stock_obj.safety_stock_string, stock_obj.yearly_demand_qty, stock_obj.stock_df_html, stock_obj.stock_alert_list

def analyze_over_stock(buyer_article_number, deliveries, orders, brasil_delta, portugal_delta):
	
	import pandas as pd

	class OverStock():

		def __init__(self, over_stock_qty, over_stock_string, yearly_demand_qty, over_stock_df_html, over_stock_alert_list):
			
			self.over_stock_qty = over_stock_qty
			self.over_stock_string = over_stock_string
			self.yearly_demand_qty = yearly_demand_qty
			self.over_stock_df_html = over_stock_df_html
			self.over_stock_alert_list = over_stock_alert_list

	over_stock_string = Material.query.filter(Material.material_code == buyer_article_number).first().over_stock

	if '%' in over_stock_string:

		over_stock_perc = int(over_stock_string.removesuffix("%")) / 100
		yearly_demand_qty = yearly_demand(deliveries)
		over_stock = yearly_demand_qty * over_stock_perc

		over_stock_obj = OverStock(
			int(over_stock),
			over_stock_string,
			yearly_demand_qty,
			None,
			[]
		)
	
	elif 'pcs' in over_stock_string:

		over_stock = int(over_stock_string.removesuffix("pcs"))
		yearly_demand_qty = yearly_demand(deliveries)

		over_stock_obj = OverStock(
			int(over_stock),
			over_stock_string,
			yearly_demand_qty,
			None,
			[]
		)
	else:
		return None, None, None, None, None
	
	stock_orders = []
	remaining_orders = []
	remaining_deliveries = []
	over_stock_analyze_list = []

	for o in orders[:]:
		o.available_quantity_excluding_sent = get_order_available_qty_excluding_sent(o.id)
		if o.available_quantity_excluding_sent > 0 and o.sales_price:
			stock_orders.append(o)
		if o.available_quantity_excluding_sent > 0 and not o.sales_price and o.eta:
			remaining_orders.append(o)

	current_stock_qty = sum(so.available_quantity_excluding_sent for so in stock_orders)

	for d in deliveries:
		if d.sent is not True:
			remaining_deliveries.append(d)

	over_stock_analyze_list = remaining_orders + remaining_deliveries
	for i in over_stock_analyze_list:
		if isinstance(i, Delivery):
			delta = 0
			if 'brasil' in str(d.plant_name).lower():
				delta = brasil_delta
			if 'portugal' in str(d.plant_name).lower():
				delta = portugal_delta
			i.delivery_date = i.delivery_date - timedelta(days = delta)
	
	over_stock_analyze_list = sorted(
		over_stock_analyze_list,
		key=lambda obj: obj.delivery_date if isinstance(obj, Delivery) else obj.eta
	)

	over_stock_df = pd.DataFrame(columns=['SO/PO', '+/-', 'Date', 'Stock', 'Alert'])

	if current_stock_qty < over_stock_obj.over_stock_qty:
		over_stock_df.loc[len(over_stock_df)] = {
			'SO/PO': 'Current stock',
			'+/-': '',
			'Date': '',
			'Stock': current_stock_qty,
			'Alert': ''
		}
	
	else:
		over_stock_obj.over_stock_alert_list.append(( date.today(), current_stock_qty - over_stock_obj.over_stock_qty ))

		over_stock_df.loc[len(over_stock_df)] = {
			'SO/PO': 'Current stock',
			'+/-': '',
			'Date': '',
			'Stock': current_stock_qty,
			'Alert': str('+') + str(current_stock_qty - over_stock_obj.over_stock_qty)
		}
	
	for i in over_stock_analyze_list:
		if isinstance(i, Delivery):

			current_stock_qty = current_stock_qty - i.delivery_quantity

			if current_stock_qty > over_stock_obj.over_stock_qty:
				
				over_stock_obj.over_stock_alert_list.append(( i.delivery_date, current_stock_qty - over_stock_obj.over_stock_qty ))
				
				over_stock_df.loc[len(over_stock_df)] = {
					'SO/PO': f"{d.delivery_schedule_number.lstrip('0')}-{d.delivery_schedule_position}",
					'+/-': f'-{i.delivery_quantity}',
					'Date': i.delivery_date,
					'Stock': current_stock_qty,
					'Alert': str('+') + str(current_stock_qty - over_stock_obj.over_stock_qty)
				}

			else:

				over_stock_df.loc[len(over_stock_df)] = {
					'SO/PO': f"{d.delivery_schedule_number.lstrip('0')}-{d.delivery_schedule_position}",
					'+/-': f'-{i.delivery_quantity}',
					'Date': i.delivery_date,
					'Stock': current_stock_qty,
					'Alert': ''
				}
		else:

			current_stock_qty = current_stock_qty + i.available_quantity_excluding_sent
			
			if current_stock_qty > over_stock_obj.over_stock_qty:
				
				over_stock_obj.over_stock_alert_list.append(( i.eta, current_stock_qty - over_stock_obj.over_stock_qty ))
			
				over_stock_df.loc[len(over_stock_df)] = {
					'SO/PO': i.order_number,
					'+/-': f'+{i.available_quantity_excluding_sent}',
					'Date': i.eta,
					'Stock': current_stock_qty,
					'Alert': str('+') + str(current_stock_qty - over_stock_obj.over_stock_qty)
				}
			else:
				over_stock_df.loc[len(over_stock_df)] = {
					'SO/PO': i.order_number,
					'+/-': f'+{i.available_quantity_excluding_sent}',
					'Date': i.eta,
					'Stock': current_stock_qty,
					'Alert': ''
				}
	over_stock_df["Date"] = pd.to_datetime(over_stock_df["Date"]).dt.strftime("%d.%m.%Y").fillna("")
	over_stock_obj.over_stock_df_html = over_stock_df.to_html(index=False).replace('class="dataframe"', f'class="over-stock-df"')
	
	return over_stock_obj.over_stock_qty, over_stock_obj.over_stock_string, over_stock_obj.yearly_demand_qty, over_stock_obj.over_stock_df_html, over_stock_obj.over_stock_alert_list
