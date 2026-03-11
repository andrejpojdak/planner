from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from .. import db
from ..models import Delivery
from ..models import Material
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DecimalField, SubmitField, IntegerField, DateField
from wtforms.validators import Optional, DataRequired
import os, csv, re
from datetime import datetime

bp = Blueprint('deliveries', __name__)

class DeliveryForm(FlaskForm):
	buyer_plant_id = StringField('Buyer plant i.d.', validators=[Optional()])
	plant_name = StringField('Plant Name', validators=[DataRequired()])
	unloading_point = StringField('Unloading Point', validators=[Optional()])
	buyer_article_number = StringField('Buyer Article Number', validators=[DataRequired()])
	article_description = StringField('Article Description', validators=[DataRequired()])
	engineering_change_level = StringField('Engineering Change Level', validators=[Optional()])
	delivery_instruction_number = StringField('Delivery Instruction Number', validators=[Optional()])
	order_number = StringField('Order Number', validators=[DataRequired()])
	order_position = StringField('Order Position', validators=[DataRequired()])
	delivery_date = DateField('Delivery date', validators=[DataRequired()])
	delivery_quantity = IntegerField('Delivery quantity', validators=[DataRequired()])
	additional_information = StringField('Additional information', validators=[Optional()])
	ecv = StringField('ECV', validators=[Optional()])
	eds = StringField('EDS', validators=[Optional()])
	submit = SubmitField('Save')

class ImportCSVForm(FlaskForm):
	csv_file = FileField('CSV file', validators=[
		FileRequired(message='Please choose a CSV file.'),
		FileAllowed(['csv'], message='Only .csv files allowed.')
	])
	submit = SubmitField('Import')

@bp.route('/', methods=['GET'])
def list_deliveries():
	deliveries = Delivery.query.order_by(Delivery.plant_name).all()
	return render_template('deliveries/list.html', title="Deliveries", deliveries=deliveries)

@bp.route('/create', methods=['GET','POST'])
def create_delivery():

	next_url = request.args.get('next')

	buyer_article_number = request.args.get("buyer_article_number")
	
	if buyer_article_number:
		material = Material.query.filter(Material.material_code == buyer_article_number).first()
		article_description = material.short_text if material else '<material_not_found>'
		plant_name = material.manufacturer if material else '<manufacturer_not_found>'
	
		form = DeliveryForm(plant_name=plant_name, buyer_article_number=buyer_article_number, article_description=article_description)
		
		form.buyer_article_number.render_kw = { "readonly": True}
		form.article_description.render_kw = { "readonly": True}
		form.plant_name.render_kw = { "readonly": True}

	else:
		form = DeliveryForm()

	if form.validate_on_submit():
		d = Delivery(
			buyer_plant_id=form.buyer_plant_id.data,
			plant_name=form.plant_name.data,
			unloading_point=form.unloading_point.data,
			buyer_article_number=form.buyer_article_number.data,
			article_description=form.article_description.data,
			engineering_change_level=form.engineering_change_level.data,
			delivery_instruction_number=form.delivery_instruction_number.data,
			order_number=form.order_number.data,
			order_position=form.order_position.data,
			delivery_date=form.delivery_date.data,
			delivery_quantity=float(form.delivery_quantity.data) if form.delivery_quantity.data is not None else None,
			additional_information=form.additional_information.data,
			ecv=form.ecv.data,
			eds=form.eds.data
		)
		db.session.add(d)
		db.session.commit()
		flash('Delivery created.', 'success')
		return redirect(next_url or url_for('deliveries.list_deliveries'))
	return render_template('deliveries/form.html', title="Create new delivery", form=form, action='Create')

@bp.route('/edit/<int:delivery_id>', methods=['GET','POST'])
def edit_delivery(delivery_id):

	next_url = request.args.get('next')
	
	d = Delivery.query.get_or_404(delivery_id)
	material = Material.query.filter(Material.material_code == d.buyer_article_number).first()
	d.article_description = material.short_text if material else '<material_not_found>'

	form = DeliveryForm(obj=d)
	if form.validate_on_submit():
		d.buyer_plant_id = form.buyer_plant_id.data
		d.plant_name = form.plant_name.data
		d.unloading_point = form.unloading_point.data
		d.buyer_article_number = form.buyer_article_number.data
		d.article_description = form.article_description.data
		d.engineering_change_level = form.engineering_change_level.data
		d.delivery_instruction_number = form.delivery_instruction_number.data
		d.order_number = form.order_number.data
		d.order_position = form.order_position.data
		d.delivery_date = form.delivery_date.data
		d.delivery_quantity = float(form.delivery_quantity.data) if form.delivery_quantity.data is not None else None
		d.additional_information = form.additional_information.data
		d.ecv = form.ecv.data
		d.eds = form.eds.data
		db.session.commit()
		flash('Delivery updated.', 'success')
		return redirect(next_url or url_for('deliveries.list_deliveries'))
	return render_template('deliveries/form.html', title="Edit delivery", form=form, action='Edit')

@bp.route('/delete/<int:delivery_id>', methods=['POST'])
def delete_delivery(delivery_id):
	d = Delivery.query.get_or_404(delivery_id)
	db.session.delete(d)
	db.session.commit()
	flash('Delivery deleted.', 'warning')
	return redirect(url_for('deliveries.list_deliveries'))

@bp.route('/delete_all', methods=['POST'])
def delete_all_deliveries():
	try:
		db.session.query(Delivery).delete(synchronize_session=False)
		db.session.commit()
		flash('All deliveries deleted.', 'warning')
	except Exception as e:
		db.session.rollback()
		flash(f'Error while deleting: {e}', 'danger')
	return redirect(url_for('deliveries.list_deliveries'))

@bp.route('/import', methods=['GET','POST'])
def import_csv():
	form = ImportCSVForm()
	if form.validate_on_submit():
		f = form.csv_file.data
		filename = secure_filename(f.filename)
		saved_path = os.path.join(current_app.config.get('UPLOAD_FOLDER'), filename)
		f.save(saved_path)
		# Read CSV
		with open(saved_path, 'r', encoding='utf-8', errors='ignore') as fh:
			sample = fh.read(2048)
			fh.seek(0)
			try:
				dialect = csv.Sniffer().sniff(sample, delimiters=';')
			except Exception:
				dialect = csv.get_dialect('excel')
			reader = csv.DictReader(fh, delimiter=';')#dialect=dialect)
			reader.fieldnames = list(dict.fromkeys(reader.fieldnames))
			#breakpoint()
			rows = list(reader)
		if not rows:
			flash('CSV has no rows', 'danger')
			return redirect(url_for('deliveries.list_deliveries'))
		# Collect keys to delete
		keys = set()
		for r in rows:
			on = (r.get('Order Number') or r.get('OrderNumber') or '').strip()
			op = (r.get('Order Position') or r.get('OrderPosition') or '').strip()
			if on or op:
				keys.add((on, op))
		# Delete existing entries matching keys
		for on, op in keys:
			q = Delivery.query
			if on:
				q = q.filter(Delivery.order_number == on)
			if op:
				q = q.filter(Delivery.order_position == op)
			q.delete(synchronize_session=False)
		db.session.commit()
		# Insert rows
		added = 0
		for r in rows:
			def get(klist):
				for k in klist:
					if k in r and r[k] is not None:
						return r[k].strip()
				return ''
			buyer_plant_id = get(['Buyer plant i.d.', 'Buyer plant id', 'BuyerPlantId'])
			plant_name = get(['Plant Name', 'PlantName'])
			unloading_point = get(['Unloading Point', 'UnloadingPoint'])
			buyer_article_number = get(['Buyer Article Number', 'BuyerArticleNumber'])
			article_description = get(['Article Description', 'ArticleDescription', 'Description'])
			engineering_change_level = get(['Engineering Change Level','EngineeringChangeLevel'])
			delivery_instruction_number = get(['Delivery Instruction Number','DeliveryInstructionNumber'])
			order_number = get(['Order Number','OrderNumber'])
			order_position = get(['Order Position','OrderPosition'])
			delivery_date = get(['Delivery date','Delivery Date','DeliveryDate'])
			delivery_quantity = get(['Delivery quantity','Delivery Quantity','DeliveryQuantity'])
			additional_information = get(['Additional information'])
			#delivery_quantity = None
			#breakpoint()
			if int(delivery_quantity) == 0:
				continue
			
			pattern = r'\b[A-Z]{3}\s[\w\.\-\/]+?\s[A-Z0-9]{3}(?:\sVersion)?\s[A-Z0-9]{2}\b'
			matches = re.findall(pattern, additional_information)
			ecv, eds = '', ''
			for match in matches:
				pattern = r'Version\s([A-Z0-9]{2})\b'
				if 'ECV' in match:
					version = re.findall(pattern, match)
					ecv = version[0]
				elif 'EDS' in match:
					version = re.findall(pattern, match)
					eds = version[0]
				elif 'EDP' in match:
					version = re.findall(pattern, match)
					eds = version[0]
			
			sap_material = Material.query.filter(Material.material_code == buyer_article_number).first()
			plant_name = sap_material.manufacturer

			d = Delivery(
				buyer_plant_id=buyer_plant_id,
				plant_name=plant_name,
				unloading_point=unloading_point,
				buyer_article_number=buyer_article_number,
				article_description=article_description,
				engineering_change_level=engineering_change_level,
				delivery_instruction_number=delivery_instruction_number,
				order_number=order_number,
				order_position=order_position,
				delivery_date=datetime.strptime(delivery_date, "%d.%m.%Y").date(),
				delivery_quantity=delivery_quantity,
				additional_information=additional_information,
				ecv=ecv,
				eds=eds
			)
			db.session.add(d)
			added += 1
		db.session.commit()
		flash(f'Imported {added} deliveries. Previous matching entries removed.', 'success')
		return redirect(url_for('deliveries.list_deliveries'))
	return render_template('deliveries/form.html', title="Import", import_only=True, form=form)

@bp.route('/query/<buyer_article_number>', methods=['GET','POST'])
def query(buyer_article_number):
	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_date.asc()).all()
	return render_template('deliveries/list.html', deliveries=deliveries)
	