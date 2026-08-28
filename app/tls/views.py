from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from .. import db
from ..models import Assignments
from ..models import Order
from ..models import Delivery
from ..models import Material
import os, csv, re
from datetime import datetime

bp = Blueprint('tls', __name__)

@bp.route('/', methods=['GET'])
def list_tls():
	assignments = (
		db.session.query(
			Delivery.plant_name.label("plant_name"),
			Delivery.delivery_schedule_number.label("delivery_schedule_number"),
			Delivery.delivery_schedule_position.label("delivery_schedule_position"),
			Material.short_text.label("short_text"),
			Delivery.delivery_date.label("delivery_date"),
			Delivery.delivery_quantity.label("delivery_quantity"),
			Order.order_number.label("order_number"),
			Order.sales_price.label("sales_price"),
			Assignments.qty.label("order_qty"),
			Assignments.delivery_id.label("delivery_id"),
			Assignments.order_id.label("order_id"),
			Assignments.assign.label("assign"),
			Assignments.tl.label("tl"),
			Assignments.tl_name.label("tl_name"),
			Assignments.sent.label("sent"),
			Material.material_code.label("buyer_article_number")
		)
		.join(Delivery, Delivery.id == Assignments.delivery_id)
		.join(Order, Order.id == Assignments.order_id)
		.join(Material, Material.material_code == Delivery.buyer_article_number)
		.filter(Assignments.tl == True, Assignments.sent != True)
		.all()
	)
	return render_template('tls/list.html', title="Transport Lists", assignments=assignments)

@bp.route('/query/', methods=['GET'])
def query_tl():

	tl_name = request.args.get("tl_name")

	assignments = (
		db.session.query(
			Delivery.plant_name.label("plant_name"),
			Delivery.delivery_schedule_number.label("delivery_schedule_number"),
			Delivery.delivery_schedule_position.label("delivery_schedule_position"),
			Material.short_text.label("short_text"),
			Delivery.delivery_date.label("delivery_date"),
			Delivery.delivery_quantity.label("delivery_quantity"),
			Order.order_number.label("order_number"),
			Order.sales_price.label("sales_price"),
			Assignments.qty.label("order_qty"),
			Assignments.delivery_id.label("delivery_id"),
			Assignments.order_id.label("order_id"),
			Assignments.assign.label("assign"),
			Assignments.tl.label("tl"),
			Assignments.tl_name.label("tl_name"),
			Assignments.sent.label("sent"),
			Material.material_code.label("buyer_article_number")
		)
		.join(Delivery, Delivery.id == Assignments.delivery_id)
		.join(Order, Order.id == Assignments.order_id)
		.join(Material, Material.material_code == Delivery.buyer_article_number)
		.filter(Assignments.tl == True, Assignments.sent != True, Assignments.tl_name == tl_name)
		.all()
	)
	return render_template('tls/list.html', title="Transport Lists", assignments=assignments)

@bp.route('/create', methods=['GET', 'POST'])
def create_tl():
	flash_messages = []
	for item in request.get_json():
		delivery_id = item.get("delivery_id")
		order_id = item.get("order_id")
		qty = item.get("qty")
		tl_name = item.get("tl_name")
		
		query = Assignments.query.filter(Assignments.delivery_id == delivery_id, Assignments.order_id == order_id, Assignments.sent != True).first()
		
		if query:

			if query.tl == True:
				d = Delivery.query.filter(Delivery.id == delivery_id).first()
				o = Order.query.filter(Order.id == order_id).first()
				flash_messages.append(f"TL of {o.order_number} for { d.delivery_schedule_number.lstrip('0') }-{ d.delivery_schedule_position }, { d.article_description }, { d.delivery_date.strftime('%d.%m.%Y') }, { d.delivery_date.strftime('CW%V/%g') }  already exists!")

			elif query.assign == True and query.tl == False:
				query.tl = True
				query.tl_name = tl_name
				db.session.add(query)
				db.session.commit()

		else:
			a = Assignments(
				delivery_id = delivery_id,
				order_id = order_id,
				qty = qty,
				assign = False,
				tl = True,
				sent = False,
				tl_name = tl_name
				)
			db.session.add(a)
			db.session.commit()			

	if len(flash_messages) > 0:
		for fm in flash_messages:
			flash(fm, 'danger')
	
	return jsonify(
			{
				"message"	: "ok"
			}
		), 200

@bp.route('/change_qty', methods=['GET'])
def change_qty():

	delivery_id = int(request.args.get('delivery_id'))
	order_id = int(request.args.get('order_id'))
	qty = int(request.args.get('qty'))
	buyer_article_number = request.args.get('buyer_article_number')

	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_date).all()
	orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.fob).all()

	from ..assignments.views import order_available_qty

	available_qty = order_available_qty(order_id)
	max_qty = available_qty + qty
	
	return render_template('tls/form.html', max_qty=max_qty, action="Save", title="Edit transport list", deliveries=deliveries, orders=orders, delivery_id=delivery_id, order_id=order_id, qty=qty)

@bp.route('/edit/<int:delivery_id>/<int:order_id>', methods=['GET', 'POST'])
def edit_tl(delivery_id, order_id):
	d = Delivery.query.filter(Delivery.id == delivery_id).first()
	o =  Order.query.filter(Order.id == order_id).first()
	qty = request.form.get("qty")
	assignment = db.session.get(Assignments, (delivery_id, order_id))

	if assignment:
		assignment.qty = qty

	db.session.commit()

	flash(f"TL of {qty}pcs from order {o.order_number} to delivery { d.delivery_schedule_number.lstrip('0') }-{ d.delivery_schedule_position }, { d.article_description }, { d.delivery_date.strftime('%d.%m.%Y') }, { d.delivery_date.strftime('CW%V/%g') } updated.", 'success')
	return redirect(url_for('tls.list_tls'))

@bp.route('/delete/<int:delivery_id>/<int:order_id>', methods=['GET', 'POST'])
def delete_tl(delivery_id, order_id):

	query = Assignments.query.filter(Assignments.delivery_id == delivery_id, Assignments.order_id == order_id, Assignments.sent != True).first()
	d = Delivery.query.filter(Delivery.id == delivery_id).first()
	o =  Order.query.filter(Order.id == order_id).first()

	if query.assign:
		query.tl = False
		db.session.add(query)
		db.session.commit()
	
	else:
		db.session.delete(query)
		db.session.commit()

	flash(f"TL of {query.qty}pcs from order {o.order_number} to delivery { d.delivery_schedule_number.lstrip('0') }-{ d.delivery_schedule_position }, { d.article_description }, { d.delivery_date.strftime('%d.%m.%Y') }, { d.delivery_date.strftime('CW%V/%g') } deleted.", 'danger')

	return redirect(url_for('tls.list_tls'))

@bp.route('/tl_sent', methods=['GET', 'POST'])
def sent():
	for item in request.get_json():
		
		delivery_id = item.get("delivery_id")
		order_id = item.get("order_id")
		qty = item.get("qty")

		query_assignment = Assignments.query.filter(Assignments.delivery_id == delivery_id, Assignments.order_id == order_id, Assignments.tl == True).first()
		query_delivery = Delivery.query.filter(Delivery.id == delivery_id).first()
		query_order = Order.query.filter(Order.id == order_id).first()

		if query_assignment:

			query_assignment.assign = False
			query_assignment.tl = False
			query_assignment.sent = True
			db.session.add(query_assignment)
			db.session.commit()

			query_delivery.sent = True
			db.session.add(query_delivery)
			db.session.commit()
		
		else:
			flash(f"TL not found!")
			return redirect(url_for('tls.list_tls'))

	return jsonify(
				{
					"message"	: "ok"
				}
			), 200
