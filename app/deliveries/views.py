from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
from .. import db
from ..models import Delivery
from ..models import Material
from ..models import Assignments
from ..models import Order
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DecimalField, SubmitField, IntegerField, DateField
from wtforms.validators import Optional, DataRequired, NumberRange
import os, csv, re
from datetime import datetime
from sqlalchemy import text

bp = Blueprint('deliveries', __name__)

class DeliveryForm(FlaskForm):
	buyer_plant_id = StringField('Buyer plant i.d.', validators=[Optional()])
	plant_name = StringField('Plant Name', validators=[DataRequired()])
	unloading_point = StringField('Unloading Point', validators=[Optional()])
	buyer_article_number = StringField('Buyer Article Number', validators=[DataRequired()])
	article_description = StringField('Article Description', validators=[DataRequired()])
	engineering_change_level = StringField('Engineering Change Level', validators=[Optional()])
	delivery_instruction_number = StringField('Delivery Instruction Number', validators=[Optional()])
	delivery_schedule_number = StringField('Delivery Schedule Number', validators=[DataRequired()])
	delivery_schedule_position = StringField('Delivery Schedule Position', validators=[DataRequired()])
	delivery_date = DateField('Delivery date', validators=[DataRequired()])
	delivery_quantity = IntegerField('Delivery quantity', validators=[DataRequired(), NumberRange(min=1, message="Qty must be greater than 0")])
	sufficient_quantity = IntegerField('Sufficient quantity', validators=[Optional(), NumberRange(min=1, message="Qty must be greater than 0")])
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
	deliveries = Delivery.query.filter(Delivery.sent == None).order_by(Delivery.buyer_article_number).all()
	return render_template('deliveries/list.html', title="Deliveries", deliveries=deliveries, plant_names=plant_names)

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
			delivery_schedule_number=form.delivery_schedule_number.data,
			delivery_schedule_position=form.delivery_schedule_position.data,
			delivery_date=form.delivery_date.data,
			delivery_quantity=float(form.delivery_quantity.data) if form.delivery_quantity.data is not None else None,
			sufficient_quantity=float(form.sufficient_quantity.data) if form.sufficient_quantity.data is not None else None,
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

	assignment_list = []
	assignment_list = (
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
		.filter(Assignments.delivery_id == delivery_id)
		.all()
	)

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
		d.delivery_schedule_number = form.delivery_schedule_number.data
		d.delivery_schedule_position = form.delivery_schedule_position.data
		d.delivery_date = form.delivery_date.data
		d.delivery_quantity = float(form.delivery_quantity.data) if form.delivery_quantity.data is not None else None
		d.sufficient_quantity = float(form.sufficient_quantity.data) if form.sufficient_quantity.data is not None else None
		d.additional_information = form.additional_information.data
		d.ecv = form.ecv.data
		d.eds = form.eds.data
		db.session.commit()
		flash('Delivery updated.', 'success')
		return redirect(next_url or url_for('deliveries.list_deliveries'))
	return render_template('deliveries/form.html', title="Edit delivery", form=form, action='Edit', assignment_list=assignment_list)

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

@bp.route('/delete_selected', methods=['POST'])
def delete_selected_deliveries():
	try:
		for item in request.get_json():
			delivery_id = item.get("delivery_id")
			d = Delivery.query.get_or_404(delivery_id)
			db.session.delete(d)
			db.session.commit()
		flash('Selected deliveries deleted.', 'warning')
	except Exception as e:
		db.session.rollback()
		flash(f'Error while deleting: {e}', 'danger')

	return jsonify(
				{
					"message"	: "ok"
				}
			), 200

@bp.route('/import', methods=['GET','POST'])
def import_csv():
	schaeffler_mappings = {
		"0701": "BRASIL",
		"0254": "PORTUGAL",
		"0200": "SCHWEINFURT",
		"0097": "BRASOV",
		"0095": "SKALICA",
		"0072": "HOCHSTADT",
		"0045": "KYSUCE",
		"0012": "STEINHAGEN",
		"0002": "LAHR"
	}
	missing_materials = {}
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
		version_to_avoid = {}
		for r in rows:
			on = (r.get('Order Number') or r.get('OrderNumber') or '').strip()
			op = (r.get('Order Position') or r.get('OrderPosition') or '').strip()
			if on or op:
				keys.add((on, op))
			din = (r.get('Delivery Instruction Number') or r.get('DeliveryInstructionNumber') or '').strip()
			#breakpoint()
			if not version_to_avoid.get((on, op)):
				version_to_avoid[(on, op)] = [int(din)]
			else:
				if int(din) not in version_to_avoid.get((on, op)):
					version_to_avoid[(on, op)].append(int(din))

		version_to_avoid = {k: v for k, v in version_to_avoid.items() if len(v) != 1}
		for k, v in version_to_avoid.items():
			if len(v) > 1:
				newest = v.pop(0)
				flash(f"Only newest version {newest} processed for {k[0]}-{k[1]} delivery schedule. Older versions {v} ignored.", 'danger')			
				v.sort(reverse=True)
		
		# Delete existing entries matching keys
		for on, op in keys:
			q = Delivery.query
			if on:
				q = q.filter(Delivery.delivery_schedule_number == on)
			if op:
				q = q.filter(Delivery.delivery_schedule_position == op)
			q = q.filter(Delivery.sent == None)
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
			delivery_schedule_number = get(['Order Number','OrderNumber'])
			delivery_schedule_position = get(['Order Position','OrderPosition'])
			if version_to_avoid.get((delivery_schedule_number, delivery_schedule_position)) and int(delivery_instruction_number) in version_to_avoid.get((delivery_schedule_number, delivery_schedule_position)):
				continue
			delivery_date = get(['Delivery date','Delivery Date','DeliveryDate'])
			delivery_date = datetime.strptime(delivery_date, "%d.%m.%Y").date()
			delivery_quantity = get(['Delivery quantity','Delivery Quantity','DeliveryQuantity'])
			if Delivery.query.filter(Delivery.delivery_schedule_number == delivery_schedule_number, Delivery.delivery_schedule_position == delivery_schedule_position, Delivery.delivery_date == delivery_date, Delivery.delivery_quantity == delivery_quantity, Delivery.sent == True).all():
				continue
			additional_information = get(['Additional information'])
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
			if not sap_material:
				if not missing_materials.get(buyer_article_number):
					missing_materials[buyer_article_number] = article_description
			
			if 'schaeffler' in plant_name.casefold() or 'dsv' in plant_name.casefold():
				if schaeffler_mappings.get(buyer_plant_id):
					plant_name = 'SCHAEFFLER' + ' ' + schaeffler_mappings[buyer_plant_id]

			d = Delivery(
				buyer_plant_id=buyer_plant_id,
				plant_name=plant_name,
				unloading_point=unloading_point,
				buyer_article_number=buyer_article_number,
				article_description=article_description,
				engineering_change_level=engineering_change_level,
				delivery_instruction_number=delivery_instruction_number,
				delivery_schedule_number=delivery_schedule_number,
				delivery_schedule_position=delivery_schedule_position,
				delivery_date=delivery_date,
				delivery_quantity=delivery_quantity,
				additional_information=additional_information,
				ecv=ecv,
				eds=eds
			)
			db.session.add(d)
			added += 1
		db.session.commit()

		for k, v in missing_materials.items():
			flash(f'Create material {k} - {v} in "Materials" section!', 'danger')
		flash(f'Imported {added} deliveries. Previous matching entries removed.', 'success')
		
		return redirect(url_for('deliveries.list_deliveries'))
	return render_template('deliveries/form.html', title="Import", import_only=True, form=form)

@bp.route('/filter', methods=['GET','POST'])
def filter():
	
	if not request.args.to_dict():
		return redirect(url_for('deliveries.list_deliveries'))
	
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

	query = Delivery.query.filter(Delivery.sent == None)

	for key, value in request.args.items():
		if value and hasattr(Delivery, key):
			query = query.filter(getattr(Delivery, key).like(f"%{value}%"))

	deliveries = query.order_by(Delivery.plant_name).all()

	return render_template('deliveries/list.html', title="Deliveries", deliveries=deliveries, plant_names=plant_names, filters=filters)

@bp.route('/query/<buyer_article_number>', methods=['GET','POST'])
def query(buyer_article_number):

	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number, Delivery.sent == None).order_by(Delivery.delivery_date.asc()).all()
	material = Material.query.filter(Material.material_code == buyer_article_number).first()
	for d in deliveries:
		d.article_description = material.short_text if material else '<material_not_found>'
	
	return render_template('deliveries/list.html', deliveries=deliveries, title=f"Deliveries {buyer_article_number} {material.short_text}", query=True, buyer_article_number=buyer_article_number)
