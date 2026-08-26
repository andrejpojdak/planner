from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
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

class FilterForm(FlaskForm):
	plant_name = StringField('Plant name', validators=[Optional()])
	so_number = StringField('SO Number', validators=[Optional()])
	sap_article_description = StringField('SAP Article Description', validators=[Optional()])
	conf_week = StringField('Confirmed Week', validators=[Optional()])
	submit = SubmitField('Filter')

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

class Assignment():

	def __init__(self, delivery_id, order_id, qty):
		self.delivery_id = delivery_id
		self.order_id = order_id
		self.qty = qty
	
	def __repr__(self):
		return f"<Assignment {self.delivery_id}, {self.order_id}, {self.qty}pcs>"

def iso_week_range(isoweek_cwMMYY_format):

	year = 2000 + int(isoweek_cwMMYY_format.split('/')[1])
	week = int(re.sub("CW", "", isoweek_cwMMYY_format.split('/')[0]), flags=re.IGNORECASE)

	monday = date.fromisocalendar(year, week, 1)
	sunday = date.fromisocalendar(year, week, 7)

	return monday, sunday

def deliveries_confirm(deliveries, orders, box_qty, gross_weight, assignments_dict):
	
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
	
	for d in deliveries:
		d.confirmations = []
		d.original_qty = d.delivery_quantity
	
	for o in orders:
		o.orig_qty = o.quantity
		if o.transport == "UNCONFIRMED":
			o.eta = None
		else:
			eta = compute_eta(o.fob, o.transport)
			o.eta = eta
	
	deliveries.sort(key=lambda d: d.delivery_date)
	orders.sort(key=lambda o: (not o.sales_price, o.in_stock_date is None, o.in_stock_date, o.eta is None, o.eta))
	confirmed_deliveries = []

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
						if d.id in assignments_dict.keys():
							for s in assignments_dict[d.id]:
								if order.id == s[0]:
									if ( order.eta is None ):
										order.confirmed_date = None
									elif ( order.eta < d.delivery_date ):
										order.confirmed_date = d.delivery_date
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
						if d.id in assignments_dict.keys():
							for s in assignments_dict[d.id]:
								if order.id == s[0]:
									if ( order.eta is None ):
										order.confirmed_date = None
									elif ( order.eta < d.delivery_date ):
										order.confirmed_date = d.delivery_date
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
	#for d in deliveries:
	#	print(d.id, d.delivery_quantity, d.confirmations)
	
	while (len(deliveries) > 0):
			#breakpoint()
			#for o in orders:
			#	print(o)
			#print("---")
			if len(orders) == 0:
				deliveries[0].confirmations.append(Confirmations(None,None,None,None,None,None,None, None, None,None,None, None, None, None, None))
				confirmed_deliveries.append(deliveries.pop(0))
				continue

			if deliveries[0].delivery_quantity > orders[0].quantity:
				if ( orders[0].eta is None ):
					orders[0].confirmed_date = None
				elif ( orders[0].eta < deliveries[0].delivery_date ):
					orders[0].confirmed_date = deliveries[0].delivery_date
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
				elif ( orders[0].eta < deliveries[0].delivery_date ):
					orders[0].confirmed_date = deliveries[0].delivery_date
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
				if ( orders[0].eta < deliveries[0].delivery_date ):
					orders[0].confirmed_date = deliveries[0].delivery_date
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
	
	confirmed_deliveries.sort(key=lambda d: d.delivery_date)
	#print(*confirmed_deliveries, sep="\n")
	return confirmed_deliveries, orders, box_qty, gross_weight

@bp.route('/', methods=['GET', 'POST'])
def list_plans():

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

		deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.order_number, Delivery.order_position).all()
		orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()

		material = Material.query.filter(Material.material_code == buyer_article_number).first()
		box_qty = material.box_qty if material else 1
		gross_weight = material.gross_weight if material else 0		
		for d in deliveries:
			d.article_description = material.short_text if material else '<material_not_found>'
			#d.plant_name = material.manufacturer if material else '<material_not_found>'
		
		buyer_article_numbers_list.append(deliveries_confirm(deliveries, orders, box_qty, gross_weight, assignments_dict))

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
				order_number = None
				order_position = None
				article_description = b[0][0].article_description
				buyer_article_number = b[0][0].buyer_article_number

				new_delivery = Delivery(
					plant_name = plant_name,
					ecv = ecv,
					eds = eds,
					order_number = order_number,
					order_position = order_position,
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

	return render_template('planning/list.html', title="Planning", buyer_article_numbers_list=buyer_article_numbers_list, plant_names=plant_names, weeks=weeks)

@bp.route('/query/<buyer_article_number>', methods=['GET'])
def list_plans_buyer_article_number(buyer_article_number):
	
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

	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number, Delivery.sent == None).order_by(Delivery.order_number, Delivery.order_position).all()
	orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()
	
	material = Material.query.filter(Material.material_code == buyer_article_number).first()
	short_text = material.short_text if material else ''
	box_qty = material.box_qty if material else 1
	gross_weight = material.gross_weight if material else 0

	for d in deliveries:
		d.article_description = material.short_text if material else '<material_not_found>'
		d.plant_name = material.manufacturer if material else '<material_not_found>'
	
	buyer_article_numbers_list.append(deliveries_confirm(deliveries, orders, box_qty, gross_weight, assignments_dict))
	return render_template('planning/list.html', title=f"{buyer_article_number} - {short_text} - Planning", buyer_article_numbers_list=buyer_article_numbers_list)

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

		deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.order_number, Delivery.order_position).all()
		orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()

		material = Material.query.filter(Material.material_code == buyer_article_number).first()
		box_qty = material.box_qty if material else 1
		gross_weight = material.gross_weight if material else 0		
		for d in deliveries:
			d.article_description = material.short_text if material else '<material_not_found>'
			#d.plant_name = material.manufacturer if material else '<material_not_found>'
		
		buyer_article_numbers_list.append(deliveries_confirm(deliveries, orders, box_qty, gross_weight, assignments_dict))

	filtered_list = []
	'''
	for key, value in request.args.items():
		for b in buyer_article_numbers_list:
			for d in b[0]:
				print(d)
				if value and hasattr(d, key) and getattr(d, key) == value:
					filtered_list.append(b)
					break
	print(filtered_list)
	'''
	for b in buyer_article_numbers_list:
		# Assign a sent boolean value to a confirmation, if it is present in Assignemtns table
		for d in b[0]:
			for c in d.confirmations:
				if Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == c.id, Assignments.sent == True).all():
					c.sent = True
		# For filtering purposes, stock order list is turned into en empty Delivery object
		if len (b[0]) > 0 and len(b[1]) > 0:
			#Find most common order, most probably delivery schedule number
			'''
			from collections import Counter
			most_common = Counter(
				(d.order_number, d.order_position)
				for d in b[0]
			).most_common(1)[0]
			most_common_order, most_common_position = most_common[0]
			'''
			for o in b[1][:]:
				plant_name = b[0][0].plant_name
				ecv = ''
				eds = ''
				order_number = None
				order_position = None
				article_description = b[0][0].article_description
				buyer_article_number = b[0][0].buyer_article_number

				new_delivery = Delivery(
					plant_name = plant_name,
					ecv = ecv,
					eds = eds,
					order_number = order_number,
					order_position = order_position,
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
		for p in b[0]:
			print(p.buyer_article_number)
		result = [
			p for p in b[0]
			if all(
				str(value).lower() in str(getattr(p, attr)).lower()
				for attr, value in filters.items()
				if value is not None and "order_" not in attr
			)
		]

		if len(result) > 0:
			filtered_list.append((result, b[1], b[2], b[3]))
		
	return render_template('planning/list.html', title="Planning", buyer_article_numbers_list=filtered_list, filters=filters, plant_names=plant_names, weeks=weeks)