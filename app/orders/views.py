from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from .. import db
from ..models import Order
from ..models import Material
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DecimalField, SubmitField, IntegerField, SelectField, DateField
from wtforms.validators import Optional, DataRequired
import os, csv, re

bp = Blueprint('orders', __name__)

class OrderForm(FlaskForm):
	order_number = StringField('Order number', validators=[DataRequired()])
	buyer_article_number = StringField('Material code', validators=[DataRequired()])
	article_description = StringField('Short text', validators=[DataRequired()])
	fob = DateField('Delivery date', validators=[DataRequired()])
	transport = SelectField('Transport type', choices=[('SEA', 'SEA'),('RAIL', 'RAIL'),('AIR', 'AIR'),('UNCONFIRMED', 'UNCONFIRMED')], default='UNCONFIRMED', validators=[DataRequired()])
	quantity = IntegerField('Quantity', validators=[DataRequired()])
	unit_weight = StringField('Unit weight', validators=[Optional()], render_kw={'readonly': True})
	overall_weight = StringField('Overall weight', validators=[Optional()], render_kw={'readonly': True})
	purchase_price = DecimalField('Purchase price', validators=[Optional()])
	sales_price = DecimalField('Sales price', validators=[Optional()])
	rmb = IntegerField('RMB', validators=[Optional()])
	ecv = StringField('ECV', validators=[Optional()])
	eds = StringField('EDS', validators=[Optional()])
	supplier = SelectField('Supplier', choices=[('SANX', 'SANX'),('BRCN', 'BRCN'),('JCSK', 'JCSK'),('JWCO', 'JWCO')], default='', validators=[DataRequired()])
	submit = SubmitField('Save')

@bp.route('/', methods=['GET'])
def list_orders():
	orders = Order.query.order_by(Order.buyer_article_number).order_by(Order.order_number).all()
	for o in orders:
		material = Material.query.filter(Material.material_code == o.buyer_article_number).first()
		o.sap_article_description = material.short_text if material else '<material_not_found>'
	return render_template('orders/list.html', title="Orders", orders=orders)

@bp.route('/create', methods=['GET','POST'])
def create_order():
	
	next_url = request.args.get('next')
	buyer_article_number = request.args.get('buyer_article_number', '')
	
	if buyer_article_number:
		material = Material.query.filter(Material.material_code == buyer_article_number).first()
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
			supplier = form.supplier.data.strip()
		)

		if Order.query.filter(Order.order_number == d.order_number).filter(Order.buyer_article_number == d.buyer_article_number).first():
			flash(f'Order {d.order_number}, {d.article_description} already exists.', 'danger')
			return render_template('orders/form.html', title="Create new order", form=form, action='Create', page="create")
		
		db.session.add(d)
		db.session.commit()
		flash('Order created.', 'success')
		return redirect(next_url or url_for('orders.list_orders'))
	return render_template('orders/form.html', title="Create new order", form=form, action='Create', page="create")

@bp.route('/edit/<int:order_id>', methods=['GET','POST'])
def edit_order(order_id):
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
		o.order_number = form.order_number.data.strip()
		o.buyer_article_number = form.buyer_article_number.data.strip()
		o.article_description = form.article_description.data.strip()
		o.fob = form.fob.data
		o.transport = form.transport.data.strip()
		o.quantity = form.quantity.data
		o.purchase_price = form.purchase_price.data
		o.sales_price = form.sales_price.data
		o.rmb = form.rmb.data
		o.ecv = form.ecv.data.strip()
		o.eds = form.eds.data.strip()
		o.supplier = form.supplier.data.strip()
		
		db.session.commit()
		flash('Order updated.', 'success')
		return redirect(next_url or url_for('orders.list_orders'))
	return render_template('orders/form.html', title="Edit", form=form, action='Edit', order_id=order_id, next_url=next_url, page="edit")

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
			supplier = form.supplier.data.strip()
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
