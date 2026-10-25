
from .. import db

from ..models import Assignments
from ..models import Delivery
from ..models import Order
from ..models import Material
from .deliveries_confirm import deliveries_confirm
from .confirmations import Confirmations

from datetime import date

def all_plans():

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

	today = date.today()
	current_week = today.isocalendar().week
	current_year = today.isocalendar().year

	weeks = [
		f"CW{(current_week + offset):02d}/{str(current_year)[-2:]}"
		for offset in range(-2, 3)
	]

	buyer_article_numbers_list = []
	buyer_article_numbers = [
		row.buyer_article_number
		for row in (
			Delivery.query
			.with_entities(Delivery.buyer_article_number)
			.distinct()
			.order_by(Delivery.plant_name, Delivery.buyer_article_number)
			.all()
		)
	]

	for buyer_article_number in buyer_article_numbers:

		assignments_dict = {}
		assignments = (
			db.session.query(
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

		material = Material.query.filter(Material.material_code == buyer_article_number).first()
		for d in deliveries:
			d.article_description = material.short_text if material else '<material_not_found>'
			#d.plant_name = material.manufacturer if material else '<material_not_found>'
		
		buyer_article_numbers_list.append(deliveries_confirm(buyer_article_number, deliveries, orders, assignments_dict))

	overall_delays_list = []
	overall_new_orders_list = []
	overall_safety_stock_list = []
	overall_over_stock_list = []
	overall_unconfirmed_orders_list = []

	for b in buyer_article_numbers_list:

		for x in b[5]:
			overall_delays_list.append(x)
		for y in b[6]:
			overall_new_orders_list.append(y)
		if b[11]:
			for p in b[11]:
				overall_safety_stock_list.append((b[0][0].buyer_article_number, b[0][0].plant_name, b[0][0].article_description, p[0], p[1]))
		if b[16]:
			for q in b[16]:
				overall_over_stock_list.append((b[0][0].buyer_article_number, b[0][0].plant_name, b[0][0].article_description, q[0], q[1]))
		if b[17]:
			for r in b[17]:
				overall_unconfirmed_orders_list.append((r.buyer_article_number, r.supplier, r.order_number, r.article_description, r.fob))

		# Assign a sent boolean value to a confirmation, if it is present in Assignemtns table
		for d in b[0]:
			for c in d.confirmations:
				if Assignments.query.filter(Assignments.delivery_id == d.id, Assignments.order_id == c.id, Assignments.sent == True).all():
					c.sent = True
		# For filtering purposes, stock order list is turned into en empty Delivery object
		if len (b[0]) > 0 and len(b[1]) > 0:
			#breakpoint()
			for o in b[1][:]:
				plant_name = b[0][0].plant_name
				ecv = ''
				eds = ''
				delivery_schedule_number = None
				delivery_schedule_position = None
				article_description = b[0][0].article_description
				buyer_article_number = b[0][0].buyer_article_number

				new_delivery = Delivery(
					plant_name = plant_name,
					ecv = ecv,
					eds = eds,
					delivery_schedule_number = delivery_schedule_number,
					delivery_schedule_position = delivery_schedule_position,
					article_description = article_description
					)
				new_delivery.original_qty = ''
				new_delivery.confirmations = []
				new_delivery.confirmations.append(
					Confirmations(
						o.id,
						o.order_number,
						o.quantity,
						o.fob,
						o.transport,
						o.eta,
						'',
						o.sales_price,
						o.supplier,
						'stock',
						o.ecv,
						o.eds,
						o.comment,
						o.rmb,
						0
					)
				)
				b[0].append(new_delivery)
				b[1].remove(o)

	return buyer_article_numbers_list, plant_names, weeks, overall_delays_list, overall_new_orders_list, overall_safety_stock_list, overall_over_stock_list, overall_unconfirmed_orders_list
