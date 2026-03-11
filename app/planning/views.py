from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from .. import db
from ..models import Order
from ..models import Delivery
from ..models import Settings
from ..models import Material
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
	
	def __init__(self, id, order_number, order_qty, order_fob, order_transport, order_eta, order_confirmed, order_sales_prices, order_supplier, order_orig_qty, order_ecv, order_eds):
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

def iso_week_range(isoweek_cwMMYY_format):

	year = 2000 + int(isoweek_cwMMYY_format.split('/')[1])
	week = int(re.sub("CW", "", isoweek_cwMMYY_format.split('/')[0]), flags=re.IGNORECASE)

	monday = date.fromisocalendar(year, week, 1)
	sunday = date.fromisocalendar(year, week, 7)

	return monday, sunday

def deliveries_confirm(deliveries, orders, box = 35):

	def compute_eta(fob, transport):
		
		s = Settings.query.filter_by(key="SEA").first()
		r = Settings.query.filter_by(key="RAIL").first()
		a = Settings.query.filter_by(key="AIR").first()

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
	orders.sort(key=lambda o: (not o.sales_price, o.eta == None, o.eta))
	confirmed_deliveries = []

	while (len(deliveries) > 0):
			
			if len(orders) == 0:
				deliveries[0].confirmations.append(Confirmations(None,None,None,None, None, None,None,None, None, None, None, None))
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
						orders[0].eds
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
						orders[0].eds
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
						orders[0].eds
					)
				)
				confirmed_deliveries.append(deliveries.pop(0))
				orders.pop(0)
				continue
	#stock = [(s.quantity, s.order_number) for s in orders if len(orders) > 0]
	return confirmed_deliveries, orders

@bp.route('/', methods=['GET', 'POST'])
def list_plans():

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

		deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.order_number, Delivery.order_position).all()
		orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()

		for d in deliveries:
			material = Material.query.filter(Material.material_code == d.buyer_article_number).first()
			d.article_description = material.short_text if material else '<material_not_found>'
			d.plant_name = material.manufacturer if material else '<material_not_found>'
		
		buyer_article_numbers_list.append(deliveries_confirm(deliveries, orders))

	return render_template('planning/list.html', title="Planning", buyer_article_numbers_list=buyer_article_numbers_list)

@bp.route('/query/<buyer_article_number>', methods=['GET'])
def list_plans_buyer_article_number(buyer_article_number):
	buyer_article_numbers_list = []

	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.order_number, Delivery.order_position).all()
	orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()
	
	for d in deliveries:
		material = Material.query.filter(Material.material_code == d.buyer_article_number).first()
		d.article_description = material.short_text if material else '<material_not_found>'
		d.plant_name = material.manufacturer if material else '<material_not_found>'
	
	buyer_article_numbers_list.append(deliveries_confirm(deliveries, orders))
	return render_template('planning/list.html', title=f"{buyer_article_number} - Planning", orders=orders, buyer_article_numbers_list=buyer_article_numbers_list)
