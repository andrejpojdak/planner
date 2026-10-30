

from ..models import Delivery
from datetime import date, timedelta

def get_conflicts(deliveries):

	conflicts = []

	newest_sent = max((d.delivery_date for d in deliveries if d.sent), default=None)	

	if newest_sent == None:
		return []
	
	for d in deliveries:
		#print((newest_sent, d.delivery_date))
		if d.sent != True and d.delivery_date != None and d.delivery_date <= newest_sent:

			conflicts.append(d)
	
	return conflicts
