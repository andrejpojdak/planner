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
			Assignments.delivery_id.label("delivery_id"),
			Assignments.order_id.label("order_id"),
			Assignments.tl.label("tl"),
			Assignments.sent.label("sent"),
			Material.material_code.label("buyer_article_number")
		)
		.join(Delivery, Delivery.id == Assignments.delivery_id)
		.join(Order, Order.id == Assignments.order_id)
		.join(Material, Material.material_code == Delivery.buyer_article_number)
		.filter(Assignments.sent == True)
		.all()
	)
	return render_template('sent/list.html', title="Sent", sent=sent)
