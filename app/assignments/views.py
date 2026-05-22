from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from .. import db
from ..models import Assignments
from ..models import Order
from ..models import Delivery
from ..models import Material
import os, csv, re
from datetime import datetime

bp = Blueprint('assignments', __name__)

@bp.route('/', methods=['GET'])
def list_assignments():
	assignments = (
		db.session.query(
			Delivery.order_number.label("delivery_order_number"),
			Delivery.order_position.label("delivery_order_position"),
			Material.short_text.label("short_text"),
			Delivery.delivery_date.label("delivery_date"),
			Delivery.delivery_quantity.label("delivery_quantity"),
			Order.order_number.label("order_number"),
			Assignments.qty.label("order_qty"),
			Assignments.delivery_id.label("delivery_id"),
			Assignments.order_id.label("order_id")
		)
		.join(Delivery, Delivery.id == Assignments.delivery_id)
		.join(Order, Order.id == Assignments.order_id)
		.join(Material, Material.material_code == Delivery.buyer_article_number)
		.all()
	)
	return render_template('assignments/list.html', title="Assignments", assignments=assignments)

@bp.route('/delete/<int:delivery_id>/<int:order_id>', methods=['GET', 'POST'])
def delete_assignment(delivery_id, order_id):
	a = Assignments.query.get_or_404((delivery_id, order_id))
	db.session.delete(a)
	db.session.commit()
	flash(f'Assignment of order {a.order_number} to delivery {a.delivery_order_number} deleted.', 'warning')
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