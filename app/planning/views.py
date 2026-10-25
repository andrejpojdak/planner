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

from ..services.deliveries_confirm import deliveries_confirm
from ..services.confirmations import Confirmations
from ..services.all_plans import all_plans

bp = Blueprint('planning', __name__)

'''class ConfirmedDeliveries():

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
'''

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
'''
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
'''
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