
from ..models import Assignments
from ..models import Settings
from datetime import date, timedelta

def analyze_delays(confirmed_deliveries):

	brasil_delta = Settings.query.filter_by(key="brasil_delta").first().value
	portugal_delta = Settings.query.filter_by(key="portugal_delta").first().value
	leadtime = Settings.query.filter_by(key="leadtime").first().value
	today = date.today()
	
	delay_list = []
	to_order_list = []

	for cd in confirmed_deliveries:
		print(cd.article_description)
		delta = 0
		if 'brasil' in str(cd.plant_name).lower():
			delta = brasil_delta
		if 'portugal' in str(cd.plant_name).lower():
			delta = portugal_delta
		
		for c in cd.confirmations:
			if c.id is None and (today + timedelta(days = leadtime + delta)) > cd.delivery_date:
				to_order_list.append((cd.buyer_article_number, cd.plant_name, f"{cd.delivery_schedule_number.lstrip('0')}-{cd.delivery_schedule_position}", "New material!" if 'material_not_found' in cd.article_description else cd.article_description, cd.delivery_date))
			if Assignments.query.filter(Assignments.delivery_id == cd.id, Assignments.order_id == c.id, Assignments.sent == True).all():
				c.sent = True
			else:
				c.sent = False
			if c.order_confirmed is not None and c.sent is False:
				if cd.delivery_date < (c.order_confirmed + timedelta(days = delta)):
					delay_list.append((cd.buyer_article_number, cd.plant_name, f"{cd.delivery_schedule_number.lstrip('0')}-{cd.delivery_schedule_position}", cd.article_description, cd.original_qty, c.order_supplier, c.order_number, c.order_qty, ((c.order_confirmed + timedelta(days = delta)) - cd.delivery_date).days))

	return delay_list, to_order_list
