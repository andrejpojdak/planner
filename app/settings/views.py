from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from werkzeug.utils import secure_filename
from .. import db
from ..models import Settings
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Optional
from bs4 import BeautifulSoup
import os
import re

bp = Blueprint('settings', __name__)

class SettingsForm(FlaskForm):
	seafreight = StringField('Seafreight (days)', validators=[DataRequired()])
	railfreight = StringField('Railfreight (days)', validators=[DataRequired()])
	airfreight = StringField('Airfreight (days)', validators=[DataRequired()])
	submit = SubmitField('Save')

@bp.route('/', methods=['GET', 'POST'])
def edit_settings():
	def get_or_create(key):
			setting = Settings.query.filter_by(key=key).first()
			if not setting:
				setting = Settings(key=key, value=0)
				db.session.add(setting)
			return setting

	s = get_or_create("seafreight")
	r = get_or_create("railfreight")
	a = get_or_create("airfreight")

	s = Settings.query.filter_by(key="seafreight").first()
	r = Settings.query.filter_by(key="railfreight").first()
	a = Settings.query.filter_by(key="airfreight").first()

	form = SettingsForm()

	if form.validate_on_submit():
		s.value = form.seafreight.data
		r.value = form.railfreight.data
		a.value = form.airfreight.data

		db.session.commit()
		return redirect(url_for('settings.edit_settings'))

	# GET request → populate form
	form.seafreight.data = s.value
	form.railfreight.data = r.value
	form.airfreight.data = a.value

	return render_template(
		'settings/form.html',
		title="Settings",
		form=form,
		action='Edit'
	)