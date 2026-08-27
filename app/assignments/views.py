from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from .. import db
from ..models import Assignments
from ..models import Order
from ..models import Delivery
from ..models import Material
import os, csv, re
from datetime import datetime

bp = Blueprint('assignments', __name__)

def order_available_qty(order_id):
	assignment_list = Assignments.query.filter(Assignments.order_id == order_id).all()
	sum_of_assignment_list = sum(a.qty for a in assignment_list)
	order_qty = Order.query.filter(Order.id == order_id).first().quantity
	return order_qty - sum_of_assignment_list

@bp.route('/', methods=['GET'])
def list_assignments():
	assignments = (
		db.session.query(
			Delivery.delivery_schedule_number.label("delivery_schedule_number"),
			Delivery.delivery_schedule_position.label("delivery_schedule_position"),
			Material.short_text.label("short_text"),
			Delivery.delivery_date.label("delivery_date"),
			Delivery.delivery_quantity.label("delivery_quantity"),
			Order.order_number.label("order_number"),
			Assignments.qty.label("order_qty"),
			Assignments.delivery_id.label("delivery_id"),
			Assignments.order_id.label("order_id"),
			Assignments.assign.label("assign"),
			Assignments.tl.label("tl"),
			Assignments.sent.label("sent"),
			Material.material_code.label("buyer_article_number")
		)
		.join(Delivery, Delivery.id == Assignments.delivery_id)
		.join(Order, Order.id == Assignments.order_id)
		.join(Material, Material.material_code == Delivery.buyer_article_number)
		.filter(Assignments.assign == True, Assignments.sent == False)
		.all()
	)
	return render_template('assignments/list.html', title="Assignments", assignments=assignments)

@bp.route('/assign', methods=['GET'])
def assign():

	delivery_id = int(request.args.get('delivery_id'))
	order_id = int(request.args.get('order_id'))
	qty = int(request.args.get('qty'))
	buyer_article_number = request.args.get('buyer_article_number')

	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_date).all()
	orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.fob).all()

	available_qty = order_available_qty(order_id)
	
	if Assignments.query.filter(Assignments.delivery_id == delivery_id).filter(Assignments.order_id == order_id).first():
		max_qty = available_qty + qty
		return render_template('assignments/form.html', max_qty=max_qty, edit=1, action="Save", title="Edit assignment", deliveries=deliveries, orders=orders, delivery_id=delivery_id, order_id=order_id, qty=qty)

	else:
		max_qty = available_qty
		return render_template('assignments/form.html', max_qty=max_qty, edit=0, action="Create", title="Create new assignment", deliveries=deliveries, orders=orders, delivery_id=delivery_id, order_id=order_id, qty=qty)

@bp.route('/create/<int:delivery_id>/<int:order_id>', methods=['GET', 'POST'])
def create_assignment(delivery_id, order_id):
	d = Delivery.query.filter(Delivery.id == delivery_id).first()
	o =  Order.query.filter(Order.id == order_id).first()
	qty = request.form.get("qty")
	a = Assignments(
		delivery_id = delivery_id,
		order_id = order_id,
		qty = qty,
		assign = True,
		tl = False,
		sent = False
		)
	db.session.add(a)
	db.session.commit()

	flash(f"Assignment of {qty}pcs from order {o.order_number} to delivery { d.delivery_schedule_number.lstrip('0') }-{ d.delivery_schedule_position }, { d.article_description }, { d.delivery_date.strftime('%d.%m.%Y') }, { d.delivery_date.strftime('CW%V/%g') } created.", 'success')
	return redirect(url_for('assignments.list_assignments'))

@bp.route('/edit/<int:delivery_id>/<int:order_id>', methods=['GET', 'POST'])
def edit_assignment(delivery_id, order_id):
	d = Delivery.query.filter(Delivery.id == delivery_id).first()
	o =  Order.query.filter(Order.id == order_id).first()
	qty = request.form.get("qty")
	assignment = db.session.get(Assignments, (delivery_id, order_id))

	if assignment:
		assignment.qty = qty
	else:
		db.session.add(
			Assignments(
				delivery_id = delivery_id,
				order_id = order_id,
				qty = qty,
				assign = True,
				tl = False,
				sent = False
			)
		)
	db.session.commit()

	flash(f"Assignment of {qty}pcs from order {o.order_number} to delivery { d.delivery_schedule_number.lstrip('0') }-{ d.delivery_schedule_position }, { d.article_description }, { d.delivery_date.strftime('%d.%m.%Y') }, { d.delivery_date.strftime('CW%V/%g') } updated.", 'success')
	return redirect(url_for('assignments.list_assignments'))

@bp.route('/delete/<int:delivery_id>/<int:order_id>', methods=['GET', 'POST'])
def delete_assignment(delivery_id, order_id):
	a = Assignments.query.get_or_404((delivery_id, order_id))
	d = Delivery.query.filter(Delivery.id == delivery_id).first()
	o =  Order.query.filter(Order.id == order_id).first()

	if a.tl:
		flash(f'It is not possible to delete an assignment within an active TL. Delete TL first!', 'danger')
	else:
		db.session.delete(a)
		db.session.commit()
		flash(f"Assignment of {a.qty}pcs from order {o.order_number} to delivery { d.delivery_schedule_number.lstrip('0') }-{ d.delivery_schedule_position }, { d.article_description }, { d.delivery_date.strftime('%d.%m.%Y') }, { d.delivery_date.strftime('CW%V/%g') } deleted.", 'danger')
	return redirect(url_for('assignments.list_assignments'))

@bp.route('/delete_all', methods=['POST'])
def delete_all_assignments():
	try:
		db.session.query(Assignments).delete(synchronize_session=False)
		db.session.commit()
		flash('All assignments deleted.', 'warning')
	except Exception as e:
		db.session.rollback()
		flash(f'Error while deleting: {e}', 'danger')
	return redirect(url_for('assignments.list_assignments'))