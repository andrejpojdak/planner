
from datetime import date, timedelta

def yearly_demand(deliveries):

	today = date.today()
	today_plus_365 = today + timedelta(days=365)

	yearly_demand_qty = sum(
		delivery.delivery_quantity
		for delivery in deliveries
		if today <= delivery.delivery_date <= today_plus_365
	)
	
	return yearly_demand_qty
