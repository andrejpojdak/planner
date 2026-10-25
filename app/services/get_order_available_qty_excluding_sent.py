
from ..models import Assignments
from ..models import Order

def get_order_available_qty_excluding_sent(order_id):
	assignment_list = Assignments.query.filter(Assignments.order_id == order_id, Assignments.sent == True).all()
	sum_of_assignment_list = sum(a.qty for a in assignment_list)
	order_qty = Order.query.filter(Order.id == order_id).first().quantity
	return order_qty - sum_of_assignment_list
