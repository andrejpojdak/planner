from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from .. import db
from ..models import Assignments
from ..models import Order
from ..models import Delivery
from ..models import Material
import os, csv, re
from datetime import datetime

bp = Blueprint('sent', __name__)

@bp.route('/', methods=['GET'])
def list_sent():
	sent = (
		db.session.query(
			Delivery.delivery_schedule_number.label("delivery_schedule_number"),
			Delivery.delivery_schedule_position.label("delivery_schedule_position"),
			Delivery.plant_name.label("delivery_plant_name"),
			Material.short_text.label("short_text"),
			Delivery.delivery_date.label("delivery_date"),
			Delivery.delivery_quantity.label("delivery_quantity"),
			Order.order_number.label("order_number"),
			Assignments.qty.label("order_qty"),
			Assignments.tl_name.label("tl_name"),
			Assignments.delivery_id.label("delivery_id"),
			Assignments.order_id.label("order_id"),
			Assignments.tl.label("tl"),
			Assignments.sent.label("sent"),
			Assignments.sent_date.label("sent_date"),
			Assignments.del_note.label("del_note"),
			Material.material_code.label("buyer_article_number")
		)
		.join(Delivery, Delivery.id == Assignments.delivery_id)
		.join(Order, Order.id == Assignments.order_id)
		.join(Material, Material.material_code == Delivery.buyer_article_number)
		.filter(Assignments.sent == True)
		.order_by(Material.material_code, Assignments.sent_date)
		.all()
	)
	return render_template('sent/list.html', title="Sent", sent=sent)

@bp.route('/change_del_note', methods=['GET'])
def change_del_note():

	delivery_id = int(request.args.get('delivery_id'))
	order_id = int(request.args.get('order_id'))
	qty = int(request.args.get('qty'))
	buyer_article_number = request.args.get('buyer_article_number')

	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_date).all()
	orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.fob).all()
	assignment = db.session.get(Assignments, (delivery_id, order_id))

	return render_template('sent/form.html', action="Save", title="Edit delivery note", deliveries=deliveries, orders=orders, delivery_id=delivery_id, order_id=order_id, qty=qty, tl_name=assignment.tl_name, del_note=assignment.del_note)

@bp.route('/edit/<int:delivery_id>/<int:order_id>', methods=['GET', 'POST'])
def edit_del_note(delivery_id, order_id):
	d = Delivery.query.filter(Delivery.id == delivery_id).first()
	o =  Order.query.filter(Order.id == order_id).first()

	tl_name = request.form.get("tl_name")
	del_note = request.form.get("del_note")

	assignment = db.session.get(Assignments, (delivery_id, order_id))

	if assignment:
		assignment.tl_name = tl_name or None
		assignment.del_note = del_note or None

	db.session.commit()

	flash(f"Delivery note added.", 'success')
	return redirect(url_for('sent.list_sent'))
