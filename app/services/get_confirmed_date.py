
from .. import db

import copy
from ..models import Assignments
from ..models import Delivery
from ..models import Material
from ..models import Order

from .deliveries_confirm import deliveries_confirm

def get_confirmed_date(delivery_id, order_id):

	buyer_article_number = Delivery.query.filter(Delivery.id == delivery_id).first().buyer_article_number

	assignments_dict = {}
	assignments = (
		db.session.query(
			#Material.material_code.label("material_code"),
			Assignments.delivery_id.label("delivery_id"),
			Assignments.order_id.label("order_id"),
			Assignments.qty.label("qty"),
			Assignments.assign.label("assign"),
			Assignments.tl.label("tl"),
			Assignments.sent.label("sent")
		)
		.join(Delivery, Delivery.id == Assignments.delivery_id)
		.join(Order, Order.id == Assignments.order_id)
		.join(Material, Material.material_code == Delivery.buyer_article_number)
		.filter(Material.material_code == buyer_article_number)
		.all()
	)
	for a in assignments:
		if assignments_dict.get(a[0]):
			assignments_dict[a[0]].append((a[1], a[2], a[3], a[4]))
		else:	
			assignments_dict[a[0]] = [(a[1], a[2], a[3], a[4])]

	deliveries = Delivery.query.filter(Delivery.buyer_article_number == buyer_article_number).order_by(Delivery.delivery_schedule_number, Delivery.delivery_schedule_position).all()
	orders = Order.query.filter(Order.buyer_article_number == buyer_article_number).order_by(Order.buyer_article_number).all()

	confirmed_deliveries, *args = deliveries_confirm(buyer_article_number, copy.deepcopy(deliveries), copy.deepcopy(orders), assignments_dict)

	for d in confirmed_deliveries:
		for o in d.confirmations:
			if o.id == order_id and d.id == delivery_id:
				confirmed_date = o.order_confirmed

	return confirmed_date