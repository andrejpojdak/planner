from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
from .. import db
from ..models import Order
from ..models import Delivery
from ..models import Settings
from ..models import Material
from ..models import Assignments
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DecimalField, SubmitField, IntegerField, SelectField
from wtforms.validators import Optional
import os, csv, re
from datetime import date, timedelta
from datetime import datetime
from datetime import date

bp = Blueprint('planning', __name__)

class ConfirmedDeliveries():

	def __init__(self, confirmed_deliveries, buyer_article_number, orders, box_qty, gross_weight, comment, delays, to_order_list, safety_stock, safety_stock_string, yearly_demand):
			self.confirmed_deliveries = confirmed_deliveries
			self.buyer_article_number = buyer_article_number
			self.orders = orders
			self.box_qty = box_qty
			self.gross_weight = gross_weight
			self.comment = comment
			self.delays = delays
			self.to_order_list = to_order_list
			self.safety_stock = safety_stock
			self.safety_stock_string = safety_stock_string
			self.yearly_demand = yearly_demand

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

def iso_week_range(isoweek_cwMMYY_format):

	year = 2000 + int(isoweek_cwMMYY_format.split('/')[1])
	week = int(re.sub("CW", "", isoweek_cwMMYY_format.split('/')[0]), flags=re.IGNORECASE)

	monday = date.fromisocalendar(year, week, 1)
	sunday = date.fromisocalendar(year, week, 7)

	return monday, sunday

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
	
	return confirmed_deliveries, orders, box_qty, gross_weight, comment, delays, to_order_list, safety_stock, safety_stock_string, yearly_demand_qty_safety_stock, stock_df_html, stock_alert_list, over_stock, over_stock_string, yearly_demand_qty_over_stock, over_stock_df_html, over_stock_alert_list, unconfirmed_orders

def analyze_delays(confirmed_deliveries):

	brasil_delta = Settings.query.filter_by(key="brasil_delta").first().value
	portugal_delta = Settings.query.filter_by(key="portugal_delta").first().value
	leadtime = Settings.query.filter_by(key="leadtime").first().value
	today = date.today()
	
	delay_list = []
	to_order_list = []

	for cd in confirmed_deliveries:

		delta = 0
		if 'brasil' in str(cd.plant_name).lower():
			delta = brasil_delta
		if 'portugal' in str(cd.plant_name).lower():
			delta = portugal_delta
		
		for c in cd.confirmations:
			if c.id is None and (today + timedelta(days = leadtime + delta)) > cd.delivery_date:
				to_order_list.append((cd.buyer_article_number, cd.plant_name, f"{cd.delivery_schedule_number.lstrip('0')}-{cd.delivery_schedule_position}", cd.article_description, cd.delivery_date))
			if Assignments.query.filter(Assignments.delivery_id == cd.id, Assignments.order_id == c.id, Assignments.sent == True).all():
				c.sent = True
			else:
				c.sent = False
			if c.order_confirmed is not None and c.sent is False:
				if cd.delivery_date < (c.order_confirmed + timedelta(days = delta)):
					delay_list.append((cd.buyer_article_number, cd.plant_name, f"{cd.delivery_schedule_number.lstrip('0')}-{cd.delivery_schedule_position}", cd.article_description, cd.original_qty, c.order_supplier, c.order_number, c.order_qty, ((c.order_confirmed + timedelta(days = delta)) - cd.delivery_date).days))

	return delay_list, to_order_list

def all_plans():

	plant_names = [
		row.plant_name
		for row in (
			Delivery.query
			.with_entities(Delivery.plant_name)
			.distinct()
			.order_by(Delivery.plant_name)
			.all()
		)
	]

	today = date.today()
	current_week = today.isocalendar().week
	current_year = today.isocalendar().year

	weeks = [
		f"CW{(current_week + offset):02d}/{str(current_year)[-2:]}"
		for offset in range(-2, 3)
	]

	buyer_article_numbers_list = []
	buyer_article_numbers = [
		row.buyer_article_number
		for row in (
			Delivery.query
			.with_entities(Delivery.buyer_article_number)
			.distinct()
			.order_by(Delivery.plant_name, Delivery.buyer_article_number)
			.all()
		)
	]

	for buyer_article_number in buyer_article_numbers:

		assignments_dict = {}
		assignments = (
			db.session.query(
				Assignments.delivery_id.label("delivery_id"),
				Assignments.order_id.label("order_id"),
				Assignments.qty.label("qty"),
				Assignments.assign.label("assign"),
				Assignments.tl.label("tl"),
				Assignments.sent.label("sent")
			)
			.join(Delivery, Delivery.id == Assignments.delivery_id)
			.join(Order, Order.id == Assignments.order_id)
			.join(Material, Material.material_code == Delivery.buyer_article_number)
			.filter(Material.material_code == buyer_article_number)
			.all()
		)

		for a in assignments:
			if assignments_dict.get(a[0]):
				assignments_dict[a[0]].append((a[1], a[2], a[3], a[4]))
			else:	
				assignments_dict[a[0]] = [(a[1], a[2], a[3], a[4])]

		deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_schedule_number, Delivery.delivery_schedule_position).all()
		orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()

		material = Material.query.filter(Material.material_code == buyer_article_number).first()
		for d in deliveries:
			d.article_description = material.short_text if material else '<material_not_found>'
			#d.plant_name = material.manufacturer if material else '<material_not_found>'
		
		buyer_article_numbers_list.append(deliveries_confirm(buyer_article_number, deliveries, orders, assignments_dict))

	overall_delays_list = []
	overall_new_orders_list = []
	overall_safety_stock_list = []
	overall_over_stock_list = []
	overall_unconfirmed_orders_list = []

	for b in buyer_article_numbers_list:

		for x in b[5]:
			overall_delays_list.append(x)
		for y in b[6]:
			overall_new_orders_list.append(y)
		if b[11]:
			for p in b[11]:
				overall_safety_stock_list.append((b[0][0].buyer_article_number, b[0][0].plant_name, b[0][0].article_description, p[0], p[1]))
		if b[16]:
			for q in b[16]:
				overall_over_stock_list.append((b[0][0].buyer_article_number, b[0][0].plant_name, b[0][0].article_description, q[0], q[1]))
		if b[17]:
			for r in b[17]:
				overall_unconfirmed_orders_list.append((r.buyer_article_number, r.supplier, r.order_number, r.article_description, r.fob))

		# Assign a sent boolean value to a confirmation, if it is present in Assignemtns table
		for d in b[0]:
			for c in d.confirmations:
				if Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == c.id, Assignments.sent == True).all():
					c.sent = True
		# For filtering purposes, stock order list is turned into en empty Delivery object
		if len (b[0]) > 0 and len(b[1]) > 0:
			#breakpoint()
			for o in b[1][:]:
				plant_name = b[0][0].plant_name
				ecv = ''
				eds = ''
				delivery_schedule_number = None
				delivery_schedule_position = None
				article_description = b[0][0].article_description
				buyer_article_number = b[0][0].buyer_article_number

				new_delivery = Delivery(
					plant_name = plant_name,
					ecv = ecv,
					eds = eds,
					delivery_schedule_number = delivery_schedule_number,
					delivery_schedule_position = delivery_schedule_position,
					article_description = article_description
					)
				new_delivery.original_qty = ''
				new_delivery.confirmations = []
				new_delivery.confirmations.append(
					Confirmations(
						o.id,
						o.order_number,
						o.quantity,
						o.fob,
						o.transport,
						o.eta,
						'',
						o.sales_price,
						o.supplier,
						'stock',
						o.ecv,
						o.eds,
						o.comment,
						o.rmb,
						0
					)
				)
				b[0].append(new_delivery)
				b[1].remove(o)

	return buyer_article_numbers_list, plant_names, weeks, overall_delays_list, overall_new_orders_list, overall_safety_stock_list, overall_over_stock_list, overall_unconfirmed_orders_list

def yearly_demand(deliveries):

	today = date.today()
	today_plus_365 = today + timedelta(days=365)

	yearly_demand_qty = sum(
		delivery.delivery_quantity
		for delivery in deliveries
		if today <= delivery.delivery_date <= today_plus_365
	)
	
	return yearly_demand_qty

def get_order_available_qty_excluding_sent(order_id):
	assignment_list = Assignments.query.filter(Assignments.order_id == order_id, Assignments.sent == True).all()
	sum_of_assignment_list = sum(a.qty for a in assignment_list)
	order_qty = Order.query.filter(Order.id == order_id).first().quantity
	return order_qty - sum_of_assignment_list

def analyze_safety_stock(buyer_article_number, deliveries, orders, brasil_delta, portugal_delta):
	
	import pandas as pd

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
				
				stock_obj.stock_alert_list.append(( i.available_quantity_excluding_sent, current_stock_qty - stock_obj.safety_stock_qty ))
			
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

@bp.route('/', methods=['GET', 'POST'])
def list_plans():

	buyer_article_numbers_list, plant_names, weeks, overall_delays_list, overall_new_orders_list, overall_safety_stock_list, overall_over_stock_list, overall_unconfirmed_orders_list = all_plans()

	return render_template('planning/list.html', title="Planning", buyer_article_numbers_list=buyer_article_numbers_list, plant_names=plant_names, weeks=weeks)

@bp.route('/dashboard', methods=['GET'])
def dashboard():

	import pandas as pd

	buyer_article_numbers_list, plant_names, weeks, overall_delays_list, overall_new_orders_list, overall_safety_stock_list, overall_over_stock_list, overall_unconfirmed_orders_list = all_plans()

	#Delays
	overall_delays_list_df = pd.DataFrame(columns=[
		'Plant Name',
		'SO Number',
		'SAP Article Description',
		'Req. Qty',
		'Conf. Qty',
		'Supplier',
		'PO No.',
		'Conf. Qty',
		'Delay',
		''
	])

	overall_delays_list.sort(key=lambda x: x[8], reverse=True) 

	for odl in overall_delays_list:

		from html import escape
		
		url = url_for('planning.list_plans', _anchor=str(odl[0]))
		url_link = f'<a href="{escape(url, quote=True)}" title="View plan">&#128065;</a>'
		
		overall_delays_list_df.loc[len(overall_delays_list_df)] = {
			'Plant Name':	odl[1],
			'SO Number'	:	odl[2],
			'SAP Article Description':	odl[3],
			'Req. Qty'	:	odl[4],
			'Supplier'	:	odl[5],
			'PO No.'	:	odl[6],
			'Conf. Qty'	:	odl[7],
			'Delay'		:	f"{odl[8]} days",
			''			:	url_link
		}
	
	overall_delays_list_df = overall_delays_list_df.to_html(index=False, escape=False, render_links=True).replace('class="dataframe"', f'class="delayed-df dashboard"')

	#New orders
	overall_new_orders_list_df = pd.DataFrame(columns=[
			'Plant Name',
			'SO Number',
			'SAP Article Description',
			'Req. Date',
			''
		])

	###Only unique materials
	overall_new_orders_list = list({row[0]: row for row in reversed(overall_new_orders_list)}.values())[::-1]
	
	overall_new_orders_list.sort(key=lambda x: x[4], reverse=False) 

	for onol in overall_new_orders_list:

		from html import escape
		
		url = url_for('planning.list_plans', _anchor=str(onol[0]))
		url_link = f'<a href="{escape(url, quote=True)}" title="View plan">&#128065;</a>'
		
		overall_new_orders_list_df.loc[len(overall_new_orders_list_df)] = {
			'Plant Name':	onol[1],
			'SO Number'	:	onol[2],
			'SAP Article Description':	onol[3],
			'Req. Date'	:	f'{onol[4].strftime("%d.%m.%Y")} ({onol[4].strftime("%B %Y")})',
			''			:	url_link
		}

	overall_new_orders_list_df = overall_new_orders_list_df.to_html(index=False, escape=False, render_links=True).replace('class="dataframe"', f'class="new-orders-df dashboard"')

	#Safety stock
	overall_safety_stock_list_df = pd.DataFrame(columns=[
			'Plant Name',
			'SAP Article Description',
			'Date',
			'Qty',
			''
		])

	overall_safety_stock_list.sort(key=lambda x: x[4], reverse=False) 

	for ossl in overall_safety_stock_list:
	
			from html import escape
			
			url = url_for('planning.list_plans', _anchor=str(ossl[0]))
			url_link = f'<a href="{escape(url, quote=True)}" title="View plan">&#128065;</a>'
			
			overall_safety_stock_list_df.loc[len(overall_safety_stock_list_df)] = {
				'Plant Name':	ossl[1],
				'SAP Article Description'	:	ossl[2],
				'Date'	:	f'{ossl[3].strftime("%d.%m.%Y")} ({ossl[3].strftime("%B %Y")})',
				'Qty'	:	ossl[4],
				''			:	url_link
			}

	overall_safety_stock_list_df = overall_safety_stock_list_df.to_html(index=False, escape=False, render_links=True).replace('class="dataframe"', f'class="safetystock-df dashboard"')

	#Over stock
	overall_over_stock_list_df = pd.DataFrame(columns=[
			'Plant Name',
			'SAP Article Description',
			'Date',
			'Qty',
			''
		])

	overall_over_stock_list.sort(key=lambda x: x[4], reverse=True) 

	for oosl in overall_over_stock_list:
	
			from html import escape
			
			url = url_for('planning.list_plans', _anchor=str(oosl[0]))
			url_link = f'<a href="{escape(url, quote=True)}" title="View plan">&#128065;</a>'
			
			overall_over_stock_list_df.loc[len(overall_over_stock_list_df)] = {
				'Plant Name':	oosl[1],
				'SAP Article Description'	:	oosl[2],
				'Date'	:	f'{oosl[3].strftime("%d.%m.%Y")} ({oosl[3].strftime("%B %Y")})',
				'Qty'	:	oosl[4],
				''			:	url_link
			}

	overall_over_stock_list_df = overall_over_stock_list_df.to_html(index=False, escape=False, render_links=True).replace('class="dataframe"', f'class="overstock-df dashboard"')

	#Unconfirmed
	overall_unconfirmed_orders_list_df = pd.DataFrame(columns=[
			'Supplier',
			'Order Number',
			'SAP Article Description',
			'FOB',
			''
		])

	overall_unconfirmed_orders_list.sort(key=lambda x: x[3], reverse=True) 

	for ouol in overall_unconfirmed_orders_list:
	
			from html import escape
			
			url = url_for('planning.list_plans', _anchor=str(ouol[0]))
			url_link = f'<a href="{escape(url, quote=True)}" title="View plan">&#128065;</a>'
			
			overall_unconfirmed_orders_list_df.loc[len(overall_unconfirmed_orders_list_df)] = {
				'Supplier':	ouol[1],
				'Order Number'	:	ouol[2],
				'SAP Article Description'	:	ouol[3],
				'FOB'	:	f'{ouol[4].strftime("%d.%m.%Y")} ({ouol[4].strftime("%B %Y")})',
				''			:	url_link
			}

	overall_unconfirmed_orders_list_df = overall_unconfirmed_orders_list_df.to_html(index=False, escape=False, render_links=True).replace('class="dataframe"', f'class="unconfirmed-df dashboard"')

	return render_template(
		'planning/dashboard.html',
		title="Dashboard",
		buyer_article_numbers_list=buyer_article_numbers_list,
		plant_names=plant_names,
		weeks=weeks,
		overall_delays_list=overall_delays_list,
		overall_delays_list_df=overall_delays_list_df,
		overall_new_orders_list=overall_new_orders_list,
		overall_new_orders_list_df=overall_new_orders_list_df,
		overall_safety_stock_list=overall_safety_stock_list,
		overall_safety_stock_list_df=overall_safety_stock_list_df,
		overall_over_stock_list=overall_over_stock_list,
		overall_over_stock_list_df=overall_over_stock_list_df,
		overall_unconfirmed_orders_list=overall_unconfirmed_orders_list,
		overall_unconfirmed_orders_list_df=overall_unconfirmed_orders_list_df
	)

@bp.route('/query/<buyer_article_number>', methods=['GET'])
def list_plans_buyer_article_number(buyer_article_number):

	plant_names = [
		row.plant_name
		for row in (
			Delivery.query
			.with_entities(Delivery.plant_name)
			.distinct()
			.order_by(Delivery.plant_name)
			.all()
		)
	]

	today = date.today()
	current_week = today.isocalendar().week
	current_year = today.isocalendar().year

	weeks = [
		f"CW{(current_week + offset):02d}/{str(current_year)[-2:]}"
		for offset in range(-2, 3)
	]
	
	buyer_article_numbers_list = []
	assignments_dict = {}
	assignments = (
		db.session.query(
			#Material.material_code.label("material_code"),
			Assignments.delivery_id.label("delivery_id"),
			Assignments.order_id.label("order_id"),
			Assignments.qty.label("qty"),
			Assignments.assign.label("assign"),
			Assignments.tl.label("tl"),
			Assignments.sent.label("sent")
		)
		.join(Delivery, Delivery.id == Assignments.delivery_id)
		.join(Order, Order.id == Assignments.order_id)
		.join(Material, Material.material_code == Delivery.buyer_article_number)
		.filter(Material.material_code == buyer_article_number)
		.all()
	)
	for a in assignments:
		if assignments_dict.get(a[0]):
			assignments_dict[a[0]].append((a[1], a[2], a[3], a[4]))
		else:	
			assignments_dict[a[0]] = [(a[1], a[2], a[3], a[4])]

	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_schedule_number, Delivery.delivery_schedule_position).all()
	orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()
	
	material = Material.query.filter(Material.material_code == buyer_article_number).first()
	short_text = material.short_text if material else ''
	for d in deliveries:
		d.article_description = material.short_text if material else '<material_not_found>'
		#d.plant_name = material.manufacturer if material else '<material_not_found>'
	
	buyer_article_numbers_list.append(deliveries_confirm(buyer_article_number, deliveries, orders, assignments_dict))

	overall_delays_list = []
	overall_new_orders_list = []

	for b in buyer_article_numbers_list:
		for x in b[5]:
			overall_delays_list.append(x)
		for y in b[6]:
			overall_new_orders_list.append(y)
		# Assign a sent boolean value to a confirmation, if it is present in Assignemtns table
		for d in b[0]:
			for c in d.confirmations:
				if Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == c.id, Assignments.sent == True).all():
					c.sent = True
		# For filtering purposes, stock order list is turned into en empty Delivery object
		if len (b[0]) > 0 and len(b[1]) > 0:
			#breakpoint()
			for o in b[1][:]:
				plant_name = b[0][0].plant_name
				ecv = ''
				eds = ''
				delivery_schedule_number = None
				delivery_schedule_position = None
				article_description = b[0][0].article_description
				buyer_article_number = b[0][0].buyer_article_number

				new_delivery = Delivery(
					plant_name = plant_name,
					ecv = ecv,
					eds = eds,
					delivery_schedule_number = delivery_schedule_number,
					delivery_schedule_position = delivery_schedule_position,
					article_description = article_description
					)
				new_delivery.original_qty = ''
				new_delivery.confirmations = []
				new_delivery.confirmations.append(
					Confirmations(
						o.id,
						o.order_number,
						o.quantity,
						o.fob,
						o.transport,
						o.eta,
						'',
						o.sales_price,
						o.supplier,
						'stock',
						o.ecv,
						o.eds,
						o.comment,
						o.rmb,
						0
					)
				)
				b[0].append(new_delivery)
				b[1].remove(o)
	
	return render_template('planning/list.html', title=f"Planning - {short_text} - {buyer_article_number}", buyer_article_numbers_list=buyer_article_numbers_list, plant_names=plant_names, weeks=weeks)

@bp.route('/filter', methods=['GET','POST'])
def filter():
	
	if not request.args.to_dict():
		return redirect(url_for('planning.list_plans'))
	
	filters = request.args.to_dict()
	
	plant_names = [
		row.plant_name
		for row in (
			Delivery.query
			.with_entities(Delivery.plant_name)
			.distinct()
			.order_by(Delivery.plant_name)
			.all()
		)
	]

	today = date.today()
	current_week = today.isocalendar().week
	current_year = today.isocalendar().year

	weeks = [
		f"CW{(current_week + offset):02d}/{str(current_year)[-2:]}"
		for offset in range(-2, 3)
	]

	buyer_article_numbers_list = []
	buyer_article_numbers = [
		row.buyer_article_number
		for row in (
			Delivery.query
			.with_entities(Delivery.buyer_article_number)
			.distinct()
			.order_by(Delivery.plant_name, Delivery.buyer_article_number)
			.all()
		)
	]

	for buyer_article_number in buyer_article_numbers:

		assignments_dict = {}
		assignments = (
			db.session.query(
				#Material.material_code.label("material_code"),
				Assignments.delivery_id.label("delivery_id"),
				Assignments.order_id.label("order_id"),
				Assignments.qty.label("qty"),
				Assignments.assign.label("assign"),
				Assignments.tl.label("tl"),
				Assignments.sent.label("sent")
			)
			.join(Delivery, Delivery.id == Assignments.delivery_id)
			.join(Order, Order.id == Assignments.order_id)
			.join(Material, Material.material_code == Delivery.buyer_article_number)
			.filter(Material.material_code == buyer_article_number)
			.all()
		)

		for a in assignments:
			if assignments_dict.get(a[0]):
				assignments_dict[a[0]].append((a[1], a[2], a[3], a[4]))
			else:	
				assignments_dict[a[0]] = [(a[1], a[2], a[3], a[4])]

		deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_schedule_number, Delivery.delivery_schedule_position).all()
		orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()

		material = Material.query.filter(Material.material_code == buyer_article_number).first()
		for d in deliveries:
			d.article_description = material.short_text if material else '<material_not_found>'
			#d.plant_name = material.manufacturer if material else '<material_not_found>'
		
		buyer_article_numbers_list.append(deliveries_confirm(buyer_article_number, deliveries, orders, assignments_dict))

	filtered_list = []
	for b in buyer_article_numbers_list:
		# Assign a sent boolean value to a confirmation, if it is present in Assignemtns table
		for d in b[0]:
			for c in d.confirmations:
				if Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == c.id, Assignments.sent == True).all():
					c.sent = True
		# For filtering purposes, stock order list is turned into en empty Delivery object
		if len (b[0]) > 0 and len(b[1]) > 0:
			for o in b[1][:]:
				plant_name = b[0][0].plant_name
				ecv = ''
				eds = ''
				delivery_schedule_number = None
				delivery_schedule_position = None
				article_description = b[0][0].article_description
				buyer_article_number = b[0][0].buyer_article_number

				new_delivery = Delivery(
					plant_name = plant_name,
					ecv = ecv,
					eds = eds,
					delivery_schedule_number = delivery_schedule_number,
					delivery_schedule_position = delivery_schedule_position,
					article_description = article_description,
					buyer_article_number = buyer_article_number
					)
				new_delivery.original_qty = ''
				new_delivery.confirmations = []
				new_delivery.confirmations.append(
					Confirmations(
						o.id,
						o.order_number,
						o.quantity,
						o.fob,
						o.transport,
						o.eta,
						'',
						o.sales_price,
						o.supplier,
						'stock',
						o.ecv,
						o.eds,
						o.comment,
						o.rmb,
						0
					)
				)
				b[0].append(new_delivery)
				b[1].remove(o)
			
		if request.args.get("delivery_week"):
			for d in b[0]:
				if d.delivery_date:
					d.delivery_week = d.delivery_date.strftime('CW%V/%g')
				else:
					d.delivery_week = ''
		if request.args.get("order_week_confirmed"):
			for d in b[0]:
				for c in d.confirmations:
					if c.order_confirmed:
						c.order_week_confirmed = c.order_confirmed.strftime('CW%V/%g')
					else:
						c.order_week_confirmed = ''
		if request.args.get("order_eta_week"):
			for d in b[0]:
				for c in d.confirmations:
					if c.order_eta:
						c.order_eta_week = c.order_eta.strftime('CW%V/%g')
					else:
						c.order_eta_week = ''
		
		#Filtering through Confirmations objects, attributes starting with "order_"
		for k, v in request.args.items():
			if "order_" in k:
				for d in b[0][:]:
					filtered_confirmations = []
					for fc in d.confirmations:
						if k == 'order_orig_qty' and v == 'stock' and fc.order_orig_qty == 'stock':
							filtered_confirmations.append(fc)
							continue
						if fc.id is None:
							continue
						if str(v).lower() in str(getattr(fc, k)).lower() and v is not None and getattr(fc, k) is not None:
							filtered_confirmations.append(fc)
					
					if len(filtered_confirmations) == 0:
						b[0].remove(d)
					else:
						d.confirmations = filtered_confirmations
		
		#Filtering through Delivery objects, attributes not starting with "order_"
		result = [
			p for p in b[0]
			if all(
				str(value).lower() in str(getattr(p, attr)).lower()
				for attr, value in filters.items()
				if value is not None and "order_" not in attr
			)
		]
		
		if len(result) > 0:
			filtered_list.append((result, b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15], b[16]))
		
	return render_template('planning/list.html', title="Planning", buyer_article_numbers_list=filtered_list, filters=filters, plant_names=plant_names, weeks=weeks)

@bp.route('/zlpi', methods=['GET', 'POST'])
def zlpi():

	buyer_article_numbers_list = []
	buyer_article_numbers = [
		row.buyer_article_number
		for row in (
			Delivery.query
			.with_entities(Delivery.buyer_article_number)
			.distinct()
			.order_by(Delivery.plant_name, Delivery.buyer_article_number)
			.all()
		)
	]

	for buyer_article_number in buyer_article_numbers:

		assignments_dict = {}
		assignments = (
			db.session.query(
				Assignments.delivery_id.label("delivery_id"),
				Assignments.order_id.label("order_id"),
				Assignments.qty.label("qty"),
				Assignments.assign.label("assign"),
				Assignments.tl.label("tl"),
				Assignments.sent.label("sent")
			)
			.join(Delivery, Delivery.id == Assignments.delivery_id)
			.join(Order, Order.id == Assignments.order_id)
			.join(Material, Material.material_code == Delivery.buyer_article_number)
			.filter(Material.material_code == buyer_article_number)
			.all()
		)

		for a in assignments:
			if assignments_dict.get(a[0]):
				assignments_dict[a[0]].append((a[1], a[2], a[3], a[4]))
			else:	
				assignments_dict[a[0]] = [(a[1], a[2], a[3], a[4])]

		deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_schedule_number, Delivery.delivery_schedule_position).all()
		orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()

		material = Material.query.filter(Material.material_code == buyer_article_number).first()
		for d in deliveries:
			d.article_description = material.short_text if material else '<material_not_found>'
			#d.plant_name = material.manufacturer if material else '<material_not_found>'
		
		buyer_article_numbers_list.append(deliveries_confirm(buyer_article_number, deliveries, orders, assignments_dict))

	for b in buyer_article_numbers_list:
		# Assign a sent boolean value to a confirmation, if it is present in Assignemtns table
		for d in b[0]:
			for c in d.confirmations:
				if Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == c.id, Assignments.sent == True).all():
					c.sent = True
		# For filtering purposes, stock order list is turned into en empty Delivery object
		if len (b[0]) > 0 and len(b[1]) > 0:
			#breakpoint()
			for o in b[1][:]:
				plant_name = b[0][0].plant_name
				ecv = ''
				eds = ''
				delivery_schedule_number = None
				delivery_schedule_position = None
				article_description = b[0][0].article_description
				buyer_article_number = b[0][0].buyer_article_number

				new_delivery = Delivery(
					plant_name = plant_name,
					ecv = ecv,
					eds = eds,
					delivery_schedule_number = delivery_schedule_number,
					delivery_schedule_position = delivery_schedule_position,
					article_description = article_description
					)
				new_delivery.original_qty = ''
				new_delivery.confirmations = []
				new_delivery.confirmations.append(
					Confirmations(
						o.id,
						o.order_number,
						o.quantity,
						o.fob,
						o.transport,
						o.eta,
						'',
						o.sales_price,
						o.supplier,
						'stock',
						o.ecv,
						o.eds,
						o.comment,
						o.rmb,
						0
					)
				)
				b[0].append(new_delivery)
				b[1].remove(o)

	zlpi = []
	for b in buyer_article_numbers_list:
		deliveries = [
			{
				"odb": d.plant_name,
				"plan": d.delivery_schedule_number.lstrip('0'),
				"position": d.delivery_schedule_position,
				"part": d.article_description,
				"req_qty": d.original_qty,
				"req_day": d.delivery_date.strftime('%Y-%m-%d') if d.delivery_date else '',
				"req_wk": d.delivery_date.strftime('CW%V/%g') if d.delivery_date else '',
				"confirmations": [
					{
						"conf_wk": c.order_confirmed.strftime('CW%V/%g') if c.order_confirmed else '',
						"conf_qty": c.order_qty
					}
					for c in d.confirmations
					if c.order_confirmed and c.order_qty
				]
			}
			for d in b[0]
			if any(c.order_confirmed and c.order_qty for c in d.confirmations)
		]

		if deliveries:
			zlpi.append(deliveries)

	import pandas as pd
	df = pd.DataFrame([
		{
			"odb": d.plant_name,
			"plan": d.delivery_schedule_number.lstrip('0'),
			"position": d.delivery_schedule_position,
			"part": d.article_description,
			"req_qty": d.original_qty,
			"req_day": d.delivery_date.strftime('%Y-%m-%d') if d.delivery_date else '',
			"req_wk": d.delivery_date.strftime('CW%V/%g') if d.delivery_date else '',
			"conf_wk": c.order_confirmed.strftime('CW%V/%g') if c.order_confirmed else '',
			"conf_qty": c.order_qty
		}
		for b in buyer_article_numbers_list
		for d in b[0]
		for c in d.confirmations
		if c.order_confirmed and c.order_qty
	])

	df.to_excel("zlpi.xlsx", index=False)

	return jsonify(zlpi), 200