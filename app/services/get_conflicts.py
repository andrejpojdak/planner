

from ..models import Delivery
from datetime import date, timedelta

from collections import defaultdict

def get_conflicts(deliveries):
	
	conflicts = []

	newest_sent = max((d.delivery_date for d in deliveries if d.sent), default=None)	

	for i, delivery in enumerate(deliveries):
		
		#print((newest_sent, d.delivery_date))
		if newest_sent != None and delivery.sent != True and delivery.delivery_date != None and delivery.delivery_date <= newest_sent:
			conflicts.append(delivery)

		#print(delivery.plant_name, delivery.delivery_quantity, delivery.delivery_date, delivery.delivery_instruction_number)
		if any(
			delivery.delivery_date == other.delivery_date
			and delivery.delivery_instruction_number != other.delivery_instruction_number
			for j, other in enumerate(deliveries)
			if i != j
		):
			conflicts.append(delivery)
	
	return conflicts
