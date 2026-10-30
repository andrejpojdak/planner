
from flask import flash
from ..models import Assignments
from ..models import Material
from ..models import Settings
from datetime import timedelta
from .analyze_delays import analyze_delays
from .confirmations import Confirmations
from .stocks import analyze_over_stock, analyze_safety_stock
from .get_current_stock_qty import get_current_stock_qty
from .yearly_demand import yearly_demand
from .get_conflicts import get_conflicts

def deliveries_confirm(buyer_article_number, deliveries, orders, assignments_dict):

	import copy

	def compute_eta(fob, transport):
		
		s = Settings.query.filter_by(key="seafreight").first()
		r = Settings.query.filter_by(key="railfreight").first()
		a = Settings.query.filter_by(key="airfreight").first()

		freight_map = {
			"SEA": s.value,
			"AIR": a.value,
			"RAIL": r.value
		}
		return fob + timedelta(days=freight_map.get(transport, 0))
	
	material = Material.query.filter(Material.material_code == buyer_article_number).first()
	box_qty = material.box_qty if material else 1
	gross_weight = material.gross_weight if material else 0		
	comment = material.comment if material else ''

	brasil_delta = Settings.query.filter_by(key="brasil_delta").first().value
	portugal_delta = Settings.query.filter_by(key="portugal_delta").first().value
	
	for d in deliveries:
		d.confirmations = []
		if d.sufficient_quantity:
			d.original_qty = d.delivery_quantity
			d.delivery_quantity = d.sufficient_quantity
		else:
			d.original_qty = d.delivery_quantity

	unconfirmed_orders = []

	for o in orders:
		o.orig_qty = o.quantity
		if o.transport == "UNCONFIRMED":
			o.eta = None
			unconfirmed_orders.append(o)
		elif o.in_stock_date:
			o.eta = o.in_stock_date
		else:
			eta = compute_eta(o.fob, o.transport)
			o.eta = eta
	
	deliveries.sort(key=lambda d: d.delivery_date)
	orders.sort(key=lambda o: (
		not o.sales_price,
		o.eta is None,
		o.eta
	))
	confirmed_deliveries = []

	current_stock_qty = get_current_stock_qty(copy.deepcopy(orders))
	currenty_yearly_demand = yearly_demand(copy.deepcopy(deliveries))
	conflicts = get_conflicts(copy.deepcopy(deliveries))

	if Material.query.filter(Material.material_code == buyer_article_number).first() == None:
		safety_stock, safety_stock_string, yearly_demand_qty_safety_stock, stock_df_html, stock_alert_list = None, None, None, None, None
		over_stock, over_stock_string, yearly_demand_qty_over_stock, over_stock_df_html, over_stock_alert_list = None, None, None, None, None
	else:
		safety_stock, safety_stock_string, yearly_demand_qty_safety_stock, stock_df_html, stock_alert_list = analyze_safety_stock(buyer_article_number, copy.deepcopy(deliveries), copy.deepcopy(orders), brasil_delta, portugal_delta)
		over_stock, over_stock_string, yearly_demand_qty_over_stock, over_stock_df_html, over_stock_alert_list = analyze_over_stock(buyer_article_number, copy.deepcopy(deliveries), copy.deepcopy(orders), brasil_delta, portugal_delta)

	###Start of Assignment
	if assignments_dict:
		order_qty_reserve_dict = {}
		for v in assignments_dict.values():
			for order, qty, assign, tl in v:
				if order_qty_reserve_dict.get(order):
					order_qty_reserve_dict[order] += qty
				else:
					order_qty_reserve_dict[order] = qty

		for order in orders[:]:
			if order.id in order_qty_reserve_dict.keys():
				if order.quantity == order_qty_reserve_dict[order.id]:
					for d in deliveries[:]:

						delta = 0

						if 'brasil' in str(d.plant_name).lower():
							delta = brasil_delta
						if 'portugal' in str(d.plant_name).lower():
							delta = portugal_delta
							
						if d.id in assignments_dict.keys():
							for s in assignments_dict[d.id]:
								if order.id == s[0]:
									if ( order.eta is None ):
										order.confirmed_date = None
									elif ( order.eta < d.delivery_date - timedelta(days = delta) ):
										order.confirmed_date = d.delivery_date - timedelta(days = delta)
									elif ( Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == order.id).first().sent == True ):
										order.confirmed_date = Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == order.id).first().sent_date
									else:
										order.confirmed_date = order.eta
									d.confirmations.append(
										Confirmations(
											order.id,
											order.order_number,
											s[1],
											order.fob,
											order.transport,
											order.eta,
											order.confirmed_date,
											order.sales_price,
											order.supplier,
											s[1],
											order.ecv,
											order.eds,
											order.comment,
											order.rmb,
											s[3]
										)
									)
									#breakpoint()
									if (d.delivery_quantity - s[1]) <= 0:
										confirmed_deliveries.append(d)
										deliveries.remove(d)
									else:
										d.delivery_quantity -= s[1]
					orders.remove(order)
				
				elif order.quantity > order_qty_reserve_dict[order.id]:
					for d in deliveries[:]:

						delta = 0

						if 'brasil' in str(d.plant_name).lower():
							delta = brasil_delta
						if 'portugal' in str(d.plant_name).lower():
							delta = portugal_delta
							
						if d.id in assignments_dict.keys():
							for s in assignments_dict[d.id]:
								if order.id == s[0]:
									if ( order.eta is None ):
										order.confirmed_date = None
									elif ( order.eta < d.delivery_date - timedelta(days = delta) ):
										order.confirmed_date = d.delivery_date - timedelta(days = delta)
									elif ( Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == order.id).first().sent == True ):
										order.confirmed_date = Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == order.id).first().sent_date
									else:
										order.confirmed_date = order.eta
									d.confirmations.append(
										Confirmations(
											order.id,
											order.order_number,
											s[1],
											order.fob,
											order.transport,
											order.eta,
											order.confirmed_date,
											order.sales_price,
											order.supplier,
											s[1],
											order.ecv,
											order.eds,
											order.comment,
											order.rmb,
											s[3]
										)
									)
									if (d.delivery_quantity - s[1]) <= 0:
										confirmed_deliveries.append(d)
										deliveries.remove(d)
									else:
										d.delivery_quantity -= s[1]
					order.quantity -= order_qty_reserve_dict[order.id]
					#order.orig_qty = str("*") + str(order.orig_qty)
					order.orig_qty -= order_qty_reserve_dict[order.id]
				
				else:
					flash(f"Higher qty to assign than actual qty for order {order.order_number}! Cancel all assignments for this order.", 'danger')
	###End of Assignment
	
	while (len(deliveries) > 0):

		delta = 0

		if 'brasil' in str(deliveries[0].plant_name).lower():
			delta = brasil_delta
		if 'portugal' in str(deliveries[0].plant_name).lower():
			delta = portugal_delta
			
		if len(orders) == 0:
			deliveries[0].confirmations.append(Confirmations(None,None,None,None,None,None,None, None, None,None,None, None, None, None, None))
			confirmed_deliveries.append(deliveries.pop(0))
			continue

		if deliveries[0].delivery_quantity > orders[0].quantity:
			if ( orders[0].eta is None ):
				orders[0].confirmed_date = None
			elif ( orders[0].eta < deliveries[0].delivery_date - timedelta(days = delta) ):
				orders[0].confirmed_date = deliveries[0].delivery_date - timedelta(days = delta)
			else:
				orders[0].confirmed_date = orders[0].eta
			deliveries[0].confirmations.append(
				Confirmations(
					orders[0].id,
					orders[0].order_number,
					orders[0].quantity,
					orders[0].fob,
					orders[0].transport,
					orders[0].eta,
					orders[0].confirmed_date,
					orders[0].sales_price,
					orders[0].supplier,
					orders[0].orig_qty,
					orders[0].ecv,
					orders[0].eds,
					orders[0].comment,
					orders[0].rmb,
					0
				)
			)
			deliveries[0].delivery_quantity -= orders[0].quantity
			#confirmed_deliveries.append(deliveries.pop(0))
			orders.pop(0)
			continue
		
		elif deliveries[0].delivery_quantity < orders[0].quantity:
			if ( orders[0].eta is None ):
				orders[0].confirmed_date = None
			elif ( orders[0].eta < deliveries[0].delivery_date - timedelta(days = delta) ):
				orders[0].confirmed_date = deliveries[0].delivery_date - timedelta(days = delta)
			else:
				orders[0].confirmed_date = orders[0].eta
			
			import math
			if(math.ceil(deliveries[0].delivery_quantity/box_qty)*box_qty >= orders[0].quantity):
				deliveries[0].delivery_quantity = orders[0].quantity
				continue
			else:
				deliveries[0].delivery_quantity = math.ceil(deliveries[0].delivery_quantity/box_qty)*box_qty
				deliveries[0].confirmations.append(
					Confirmations(
						orders[0].id,
						orders[0].order_number,
						deliveries[0].delivery_quantity,
						orders[0].fob,
						orders[0].transport,
						orders[0].eta,
						orders[0].confirmed_date,
						orders[0].sales_price,
						orders[0].supplier,
						orders[0].orig_qty,
						orders[0].ecv,
						orders[0].eds,
						orders[0].comment,
						orders[0].rmb,
						0
					)
				)
				orders[0].orig_qty = ''
				orders[0].quantity -= deliveries[0].delivery_quantity
				confirmed_deliveries.append(deliveries.pop(0))
				continue

		else:
			if ( orders[0].eta < deliveries[0].delivery_date - timedelta(days = delta) ):
				orders[0].confirmed_date = deliveries[0].delivery_date - timedelta(days = delta)
			else:
				orders[0].confirmed_date = orders[0].eta
			deliveries[0].confirmations.append(
				Confirmations(
					orders[0].id,
					orders[0].order_number,
					orders[0].quantity,
					orders[0].fob,
					orders[0].transport,
					orders[0].eta,
					orders[0].confirmed_date,
					orders[0].sales_price,
					orders[0].supplier,
					orders[0].orig_qty,
					orders[0].ecv,
					orders[0].eds,
					orders[0].comment,
					orders[0].rmb,
					0
				)
			)
			confirmed_deliveries.append(deliveries.pop(0))
			orders.pop(0)
			continue
	
	#First sort deliveries, sent deliveries first, then by delivery date
	confirmed_deliveries.sort(
		key=lambda d: (0 if d.sent is True else 2, d.delivery_date)
	)
	#Then sort confirmations in each delivery, first in-stock orders
	for d in confirmed_deliveries:
		d.confirmations.sort(
			key=lambda c: (
				c.order_sales_price is None,
				c.order_eta is None,
				c.order_eta
			)
		)

	delays, to_order_list = analyze_delays(confirmed_deliveries)
	
	return confirmed_deliveries, orders, box_qty, gross_weight, comment, delays, to_order_list, safety_stock, safety_stock_string, yearly_demand_qty_safety_stock, stock_df_html, stock_alert_list, over_stock, over_stock_string, yearly_demand_qty_over_stock, over_stock_df_html, over_stock_alert_list, unconfirmed_orders, current_stock_qty, currenty_yearly_demand, conflicts
