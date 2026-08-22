from . import db
import datetime
from datetime import date

class Material(db.Model):
	__tablename__ = "materials"
	id = db.Column(db.Integer, primary_key=True)
	material_code = db.Column(db.String(120), unique=False, nullable=False)
	short_text = db.Column(db.String(255), nullable=True)
	gross_weight = db.Column(db.Float, nullable=True)
	manufacturer = db.Column(db.String(255), nullable=True)
	box_qty = db.Column(db.Integer, nullable=True)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

	def __repr__(self):
		return f"<Material {self.material_code}, {self.short_text} >"

class Delivery(db.Model):
	__tablename__ = "deliveries"
	id = db.Column(db.Integer, primary_key=True)
	buyer_plant_id = db.Column(db.String(120), nullable=True)
	plant_name = db.Column(db.String(255), nullable=True)
	unloading_point = db.Column(db.String(255), nullable=True)
	buyer_article_number = db.Column(db.String(255), nullable=True)
	article_description = db.Column(db.String(1024), nullable=True)
	engineering_change_level = db.Column(db.String(120), nullable=True)
	delivery_instruction_number = db.Column(db.String(120), nullable=True)
	order_number = db.Column(db.String(120), nullable=True, index=True)
	order_position = db.Column(db.String(120), nullable=True, index=True)
	delivery_date = db.Column(db.Date)
	delivery_quantity = db.Column(db.Integer, nullable=True)
	additional_information = db.Column(db.String(1024), nullable=True)
	ecv = db.Column(db.String(120), nullable=True)
	eds = db.Column(db.String(120), nullable=True)
	sent = db.Column(db.Boolean)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	delivery_orders = db.relationship("Assignments", back_populates="delivery")

	def __repr__(self):
		return f"<Delivery {self.id} {self.order_number}-{self.order_position}, {self.article_description}, {self.delivery_quantity}, {self.delivery_date}>"

class Order(db.Model):
	__tablename__ = "orders"
	id = db.Column(db.Integer, primary_key=True)
	buyer_article_number = db.Column(db.String(255), nullable=True)
	article_description = db.Column(db.String(1024), nullable=True)
	order_number = db.Column(db.String(120), nullable=True, index=True)
	order_position = db.Column(db.String(120), nullable=True, index=True)
	fob = db.Column(db.Date)
	transport = db.Column(db.String(120), nullable=True)
	quantity = db.Column(db.Integer, nullable=True)
	avail_quantity = db.Column(db.Integer, nullable=True)
	ecv = db.Column(db.String(120), nullable=True)
	eds = db.Column(db.String(120), nullable=True)
	purchase_price = db.Column(db.Float, nullable=True)
	sales_price = db.Column(db.Float, nullable=True)
	rmb = db.Column(db.Integer, nullable=True)
	supplier = db.Column(db.String(15), nullable=True)
	comment = db.Column(db.String(120), nullable=True)
	created_at = db.Column(db.Date, default=datetime.datetime.utcnow)
	in_stock_date = db.Column(db.Date)
	delivery_orders = db.relationship("Assignments", back_populates="order")
	
	def __repr__(self):
		return f"<Order {self.id} {self.order_number}-{self.order_position}, {self.article_description} {self.quantity} {self.fob}>"

class Settings(db.Model):
	__tablename__ = "settings"
	key = db.Column(db.String(50), primary_key=True)
	value = db.Column(db.Integer)
	
	def __repr__(self):
		return f"<Settings for {self.key}>"

class Assignments(db.Model):
	__tablename__ = "assignments"
	delivery_id = db.Column(db.Integer, db.ForeignKey("deliveries.id"), primary_key=True)
	order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), primary_key=True)
	qty = db.Column(db.Integer)
	assign = db.Column(db.Boolean)
	tl = db.Column(db.Boolean)
	sent = db.Column(db.Boolean)

	delivery = db.relationship("Delivery", back_populates="delivery_orders")
	order = db.relationship("Order", back_populates="delivery_orders")

	def __repr__(self):
		return f"<Assignment for {self.delivery_id}:{self.order_id} for {self.qty} pcs>"