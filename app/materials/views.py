from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from .. import db
from ..models import Material
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange
from bs4 import BeautifulSoup
import os
import re

bp = Blueprint('materials', __name__)

class MaterialForm(FlaskForm):
    material_code = StringField('Material code', validators=[DataRequired()])
    short_text = StringField('Short text', validators=[DataRequired()])
    gross_weight = DecimalField('Gross weight', validators=[DataRequired(), NumberRange(min=0.000001, message="Gross weight must be greater than 0")], places=3)
    manufacturer = StringField('Manufacturer', validators=[DataRequired()])
    box_qty = StringField('Box Qty', validators=[Optional()])
    submit = SubmitField('Save')

class ImportForm(FlaskForm):
    html_file = FileField('HTML file', validators=[
        FileRequired(message='Please choose an HTML file.'),
        FileAllowed(['html', 'htm'], message='Only .html/.htm files allowed.')
    ])
    submit = SubmitField('Import')

def parse_html_table(html_content):
    if isinstance(html_content, (bytes, bytearray)):
        try:
            html_content = html_content.decode('utf-8')
        except Exception:
            html_content = html_content.decode('latin-1', errors='ignore')
    soup = BeautifulSoup(html_content, 'lxml')
    table = soup.find('table')
    if not table:
        return [], 'No table found in uploaded HTML.'
    rows = table.find_all('tr')
    if not rows or len(rows) < 1:
        return [], 'Table contains no rows.'
    # detect header row and skip it
    header_keywords = ['materi', 'mater', 'krát', 'krat', 'hmot', 'výrob', 'vyrob', 'odber', 'name']
    header_row_idx = None
    for i, tr in enumerate(rows):
        cells_text = ' '.join([c.get_text(strip=True).lower() for c in tr.find_all(['th','td'])])
        for kw in header_keywords:
            if kw in cells_text:
                header_row_idx = i
                break
        if header_row_idx is not None:
            break
    start_idx = header_row_idx + 1 if header_row_idx is not None else 0
    parsed = []
    for tr in rows[start_idx:]:
        cols = tr.find_all(['td','th'])
        values = [c.get_text(strip=True) for c in cols]
        mat = re.sub(r'^O', '0', values[0]) if len(values) > 0 else ''
        mat = re.sub(r'[\-\u2010\u2011\u2012\u2013\u2014\u2015\u2212\s]+', '', mat) if len(values) > 0 else ''
        short = values[1] if len(values) > 1 else ''
        weight = values[4] if len(values) > 2 else ''
        manuf = values[12] if len(values) > 3 else ''
        lowrow = ' '.join([v.lower() for v in values if v])
        if any(kw in lowrow for kw in header_keywords):
            continue
        weight_norm = None
        if weight:
            try:
                w = weight.replace('\u00A0','').replace(' ','').replace(',','.')
                weight_norm = float(w)
            except Exception:
                weight_norm = None
        parsed.append({'material_code': mat, 'short_text': short, 'gross_weight': weight_norm, 'manufacturer': manuf})
    return parsed, None

@bp.route('/', methods=['GET'])
def list_materials():
    materials = Material.query.order_by(Material.manufacturer).all()
    return render_template('materials/list.html', title="Materials", materials=materials)

@bp.route('/create', methods=['GET','POST'])
def create_material():

    args_material_code=request.args.get('material_code', '')
    args_short_text=request.args.get('short_text', '')
    args_gross_weight=float(request.args.get('gross_weight', 0))
    args_manufacturer=request.args.get('manufacturer', '')
    
    form = MaterialForm(material_code=args_material_code,
                        short_text=args_short_text,
                        gross_weight=args_gross_weight,
                        manufacturer=args_manufacturer)

    if form.validate_on_submit():
        m = Material(material_code=form.material_code.data,
                     short_text=form.short_text.data,
                     gross_weight=float(form.gross_weight.data) if form.gross_weight.data is not None else None,
                     manufacturer=form.manufacturer.data)
        if Material.query.filter(Material.material_code == m.material_code).first():
            flash(f'Material code {m.material_code} already exists.', 'danger')
            return redirect(url_for('materials.create_material', material_code=m.material_code, short_text=m.short_text, gross_weight=m.gross_weight, manufacturer=m.manufacturer))

        db.session.add(m)
        db.session.commit()
        flash('Material created.', 'success')
        return redirect(url_for('materials.list_materials'))
    return render_template('materials/form.html', title="Create new material", form=form, action='Create', disabled=False)

@bp.route('/edit', methods=['GET','POST'])
def edit_material():

    next_url = request.args.get('next')
    
    if request.args.get("id"):
        m = Material.query.filter(Material.id == request.args.get("id")).first()
    if request.args.get("buyer_article_number"):
        m = Material.query.filter(Material.material_code == request.args.get("buyer_article_number")).first()
    
    form = MaterialForm(obj=m)
    
    if form.validate_on_submit():
        m.material_code = form.material_code.data
        m.short_text = form.short_text.data
        m.gross_weight = float(form.gross_weight.data) if form.gross_weight.data is not None else None
        m.manufacturer = form.manufacturer.data
        db.session.commit()
        flash('Material updated.', 'success')
        return redirect(next_url or url_for('materials.list_materials'))
    
    return render_template('materials/form.html', title="Edit material", form=form, action='Edit', disabled=True)

@bp.route('/delete/<int:id>', methods=['POST'])
def delete_material(id):
    m = Material.query.get_or_404(id)
    db.session.delete(m)
    db.session.commit()
    flash('Material deleted.', 'warning')
    return redirect(url_for('materials.list_materials'))

@bp.route('/import', methods=['GET','POST'])
def import_html():
    form = ImportForm()
    if form.validate_on_submit():
        file = form.html_file.data
        filename = secure_filename(file.filename)
        saved_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(saved_path)
        with open(saved_path, 'rb') as f:
            content = f.read()
        parsed, err = parse_html_table(content)
        if err:
            flash(f'Import error: {err}', 'danger')
            return redirect(url_for('materials.list_materials'))
        added = 0
        existing = 0
        existing_list = []

        for row in parsed:
            
            na = [
                'nepou',
                'nepoužívať',
                'nepopuživať',
                'nepopuživat',
                'nepouzivat'
            ]

            pattern = re.compile(r'nepou[zž][ií]va[tť]', re.IGNORECASE)
            combined = f"{row['material_code']} {row['short_text']}"
            if pattern.search(combined):
                print(row['material_code'], row['short_text'])
                continue

            current_material = Material.query.filter(Material.material_code == row['material_code']).first()
            if not row['material_code']:
                continue
            elif current_material:
                existing += 1
                existing_list.append(row['material_code'])
                continue
            
            manufacturer = row['manufacturer']
            manufacturer = re.sub("STEINH", "STEINHAGEN", manufacturer)
            manufacturer = re.sub("INA", "SCHAEFFLER", manufacturer)
            manufacturer = re.sub("ELFERSH", "SCHWEINFURT", manufacturer)
            manufacturer = re.sub("^SCHAEFFLER SCHWEIN$", "SCHAEFFLER SCHWEINFURT", manufacturer)
            manufacturer = re.sub("SCHAEFLLER SCHWEIN", "SCHAEFFLER SCHWEINFURT", manufacturer)
            manufacturer = re.sub("HOCHST", "HOCHSTAD", manufacturer)
            manufacturer = re.sub("WUPPERT", "WUPPERTAL", manufacturer)
            manufacturer = re.sub("PORTUGA", "PORTUGAL", manufacturer)

            m = Material(material_code=row['material_code'],
                         short_text=row['short_text'],
                         gross_weight=row['gross_weight'],
                         manufacturer=manufacturer,
                         box_qty=0)

            db.session.add(m)
            added += 1
        db.session.commit()
        flash(f'Ignored {existing} rows, because material code already exists.{existing_list}', 'danger')
        flash(f'Imported {added} rows.', 'success')
        return redirect(url_for('materials.list_materials'))
    return render_template('materials/form.html', title="Import", import_only=True, form=form)

@bp.route('/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@bp.route('/delete_all', methods=['POST'])
def delete_all_materials():
	try:
		db.session.query(Material).delete(synchronize_session=False)
		db.session.commit()
		flash('All materials deleted.', 'warning')
	except Exception as e:
		db.session.rollback()
		flash(f'Error while deleting: {e}', 'danger')
	return redirect(url_for('materials.list_materials'))

@bp.route('/query', methods=['GET','POST'])
def query_material():
    text = request.args.get('text', '')
    material_list = Material.query.with_entities(Material.material_code, Material.short_text, Material.gross_weight, Material.manufacturer).filter(Material.short_text.ilike(f'%{text}%')).all()
    return jsonify([
        {
            "buyer_article_number"    :   material_code,
            "article_descritption": short_text,
            "gross_weight"   :   gross_weight,
            "plant_name"   :   manufacturer,
            "box_qty"   :   box_qty
        }
        for material_code, short_text, gross_weight, manufacturer, box_qty in material_list
    ])