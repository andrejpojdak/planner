from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from .. import db
from ..models import Order
from ..models import Material
from ..models import Delivery
from ..models import Assignments
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DecimalField, SubmitField, IntegerField, SelectField, DateField
from wtforms.validators import Optional, DataRequired, Length, NumberRange
import os, csv, re

bp = Blueprint('orders', __name__)

class OrderForm(FlaskForm):
	order_number = StringField('Order number', validators=[DataRequired()])
	buyer_article_number = StringField('Material code', validators=[DataRequired()])
	article_description = StringField('Short text', validators=[DataRequired()])
	fob = DateField('Delivery date', validators=[DataRequired()])
	transport = SelectField('Transport type', choices=[('SEA', 'SEA'),('RAIL', 'RAIL'),('AIR', 'AIR'),('UNCONFIRMED', 'UNCONFIRMED')], default='UNCONFIRMED', validators=[DataRequired()])
	quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, message="Qty must be greater than 0")])
	available_quantity = IntegerField('Available Quantity', validators=[Optional()], render_kw={"disabled": True})
	unit_weight = StringField('Unit weight', validators=[Optional()], render_kw={'readonly': True})
	overall_weight = StringField('Overall weight', validators=[Optional()], render_kw={'readonly': True})
	purchase_price = DecimalField('Purchase price', validators=[Optional(), NumberRange(min=0.00001, message="Price must be greater than 0")])
	sales_price = DecimalField('Sales price', validators=[Optional(), NumberRange(min=0.00001, message="Price must be greater than 0")])
	in_stock_date = DateField('In-stock date', validators=[Optional()])
	rmb = IntegerField('RMB', validators=[Optional(), NumberRange(min=1, message="RMB must be greater than 0")])
	ecv = StringField('ECV', validators=[Optional()])
	eds = StringField('EDS', validators=[Optional()])
	supplier = SelectField('Supplier', choices=[('SANX', 'SANX'),('BRCN', 'BRCN'),('JCSK', 'JCSK'),('JWCO', 'JWCO'),('XINT', 'XINT')], default='', validators=[DataRequired()])
	comment = StringField('Comment', validators=[Optional(), Length(max=120)], render_kw={"maxlength": 120})
	submit = SubmitField('Save')

@bp.route('/', methods=['GET'])
def list_orders():

	from ..assignments.views import order_available_qty

	orders = Order.query.order_by(Order.buyer_article_number).order_by(Order.fob).all()
	for o in orders:
		material = Material.query.filter(Material.material_code == o.buyer_article_number).first()
		o.sap_article_description = material.short_text if material else '<material_not_found>'
		o.available_quantity = order_available_qty(o.id)
	return render_template('orders/list.html', title="Orders", orders=orders)

@bp.route('/query/<buyer_article_number>', methods=['GET','POST'])
def query(buyer_article_number):

	from ..assignments.views import order_available_qty

	orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).order_by(Order.fob).all()
	material = Material.query.filter(Material.material_code == buyer_article_number).first()
	for o in orders:
		o.sap_article_description = material.short_text if material else '<material_not_found>'
		o.available_quantity = order_available_qty(o.id)
	return render_template('orders/list.html', title=f"Orders {buyer_article_number} {material.short_text}", orders=orders, query=True, buyer_article_number=buyer_article_number)

@bp.route('/create', methods=['GET','POST'])
def create_order():
	
	next_url = request.args.get('next')
	buyer_article_number = request.args.get('buyer_article_number', '')
	material_comment = ''

	if buyer_article_number:
		material = Material.query.filter(Material.material_code == buyer_article_number).first()
		material_comment = material.comment
		article_description = material.short_text if material else '<material_not_found>'
		unit_weight = material.gross_weight if material else ''

		form = OrderForm(buyer_article_number=buyer_article_number, article_description=article_description, unit_weight=unit_weight)
		
		form.buyer_article_number.render_kw = { "readonly": True}
		form.article_description.render_kw = { "readonly": True}
	else:
		form = OrderForm()

	if form.validate_on_submit():
		d = Order(
			order_number = form.order_number.data.strip(),
			buyer_article_number = form.buyer_article_number.data.strip(),
			article_description = form.article_description.data.strip(),
			fob = form.fob.data,
			transport = form.transport.data.strip(),
			quantity = form.quantity.data,
			purchase_price = form.purchase_price.data,
			sales_price = form.sales_price.data,
			rmb = form.rmb.data,
			ecv = form.ecv.data.strip(),
			eds = form.eds.data.strip(),
			supplier = form.supplier.data.strip(),
			comment = form.comment.data.strip()
		)

		if Order.query.filter(Order.order_number == d.order_number).filter(Order.buyer_article_number == d.buyer_article_number).first():
			flash(f'Order {d.order_number}, {d.article_description} already exists.', 'danger')
			return render_template('orders/form.html', title="Create new order", form=form, action='Create', page="create")
		
		db.session.add(d)
		db.session.commit()
		flash('Order created.', 'success')
		return redirect(next_url or url_for('orders.list_orders'))

	return render_template('orders/form.html', title="Create new order", form=form, action='Create', page="create", material_comment=material_comment)

@bp.route('/edit/<int:order_id>', methods=['GET','POST'])
def edit_order(order_id):

	order_qty = Order.query.filter(Order.id == order_id).first().quantity
	if Assignments.query.filter(Assignments.order_id == order_id).first():
		assignment_qty = Assignments.query.filter(Assignments.order_id == order_id).first().qty

	assignment_list = []
	tl_list = []
	sent_list = []

	query = (
		db.session.query(
			Delivery.delivery_schedule_number.label("delivery_schedule_number"),
			Delivery.delivery_schedule_position.label("delivery_schedule_position"),
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
		.filter(Assignments.order_id == order_id)
	)

	assignment_list = query.filter(Assignments.assign == True, Assignments.tl != True).all()
	tl_list = query.filter(Assignments.tl == True).all()
	sent_list = query.filter(Assignments.sent == True).all()

	next_url = request.args.get('next')
	o = Order.query.get_or_404(order_id)
	material = Material.query.filter(Material.material_code == o.buyer_article_number).first()
	
	o.article_description = material.short_text if material else '<material_not_found>'
	weight = material.gross_weight if material else ''
	o.unit_weight = weight

	form = OrderForm(obj=o)
	form.buyer_article_number.render_kw = { "readonly": True}
	form.article_description.render_kw = { "readonly": True}
	from ..assignments.views import order_available_qty
	form.available_quantity.data = order_available_qty(order_id)

	if form.validate_on_submit():
		o.order_number = form.order_number.data.strip()
		o.buyer_article_number = form.buyer_article_number.data.strip()
		o.article_description = form.article_description.data.strip()
		o.fob = form.fob.data
		o.transport = form.transport.data.strip()
		o.quantity = form.quantity.data
		o.purchase_price = form.purchase_price.data
		o.sales_price = form.sales_price.data
		o.in_stock_date = form.in_stock_date.data
		o.rmb = form.rmb.data
		o.ecv = form.ecv.data.strip()
		o.eds = form.eds.data.strip()
		o.supplier = form.supplier.data.strip()
		o.comment = form.comment.data.strip()
		
		if Order.query.filter(Order.order_number == o.order_number).filter(Order.buyer_article_number == o.buyer_article_number).first().id != order_id:
			flash(f'Order {o.order_number}, {o.article_description} already exists.', 'danger')
			return render_template('orders/form.html', title="Create new order", form=form, action='Create', page="create")

		# Check if exactly 1 assignemnt, so it automatically updates assign qty to updated qty
		assignment_count = len( Assignments.query.filter(Assignments.order_id == order_id).all() )
		if assignment_count == 1:
			if order_qty == assignment_qty:
				Assignments.query.filter(Assignments.order_id == order_id).update({
					Assignments.qty: o.quantity
				})
				db.session.commit()
		
		db.session.commit()
		flash('Order updated.', 'success')
		return redirect(next_url or url_for('orders.list_orders'))
	return render_template('orders/form.html', title="Edit", form=form, action='Edit', order_id=order_id, next_url=next_url, page="edit", assignment_list=assignment_list, tl_list=tl_list, sent_list=sent_list)

@bp.route('/split/<int:order_id>', methods=['GET','POST'])
def split_order(order_id):
	next_url = request.args.get('next')
	o = Order.query.get_or_404(order_id)
	material = Material.query.filter(Material.material_code == o.buyer_article_number).first()
	
	o.article_description = material.short_text if material else '<material_not_found>'
	weight = material.gross_weight if material else ''
	o.unit_weight = weight

	form = OrderForm(obj=o)
	form.buyer_article_number.render_kw = { "readonly": True}
	form.article_description.render_kw = { "readonly": True}

	if form.validate_on_submit():
		d = Order(
			order_number = form.order_number.data.strip(),
			buyer_article_number = form.buyer_article_number.data.strip(),
			article_description = form.article_description.data.strip(),
			fob = form.fob.data,
			transport = form.transport.data.strip(),
			quantity = form.quantity.data,
			purchase_price = form.purchase_price.data,
			sales_price = form.sales_price.data,
			rmb = form.rmb.data,
			ecv = form.ecv.data.strip(),
			eds = form.eds.data.strip(),
			supplier = form.supplier.data.strip(),
			comment = form.comment.data.strip()
		)
		if Order.query.filter(Order.order_number == d.order_number).filter(Order.buyer_article_number == d.buyer_article_number).first():
			flash(f'Order {d.order_number}, {d.article_description} already exists.', 'danger')
			return redirect(url_for('orders.split_order', order_id=order_id))
		db.session.add(d)
		db.session.commit()
		flash('Order split.', 'success')
		return redirect(next_url or url_for('orders.list_orders'))
	return render_template('orders/form.html', title="Split", form=form, action='Split', page="split")

@bp.route('/delete/<int:order_id>', methods=['GET', 'POST'])
def delete_order(order_id):
	next_url = request.args.get('next')
	o = Order.query.get_or_404(order_id)
	db.session.delete(o)
	db.session.commit()
	flash(f'Order {o.order_number}, {o.article_description} deleted.', 'warning')
	return redirect(next_url or url_for('orders.list_orders'))

@bp.route('/delete_all', methods=['POST'])
def delete_all_orders():
	try:
		db.session.query(Order).delete(synchronize_session=False)
		db.session.commit()
		flash('All orders deleted.', 'warning')
	except Exception as e:
		db.session.rollback()
		flash(f'Error while deleting: {e}', 'danger')
	return redirect(url_for('orders.list_orders'))

@bp.route('/filter', methods=['GET','POST'])
def filter():
	
	if not request.args.to_dict():
		return redirect(url_for('orders.list_orders'))
	
	filters = request.args.to_dict()

	query = Order.query

	for key, value in request.args.items():
		if value and hasattr(Order, key):
			query = query.filter(getattr(Order, key).like(f"%{value}%"))

	orders = query.order_by(Order.buyer_article_number).order_by(Order.order_number).all()
	for o in orders:
		material = Material.query.filter(Material.material_code == o.buyer_article_number).first()
		o.sap_article_description = material.short_text if material else '<material_not_found>'
	
	return render_template('orders/list.html', title="Orders", orders=orders, filters=filters)
