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
		return f"<Material {self.material_code}>"

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
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

	def __repr__(self):
		return f"<Delivery {self.order_number}:{self.order_position}>"

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
	ecv = db.Column(db.String(120), nullable=True)
	eds = db.Column(db.String(120), nullable=True)
	purchase_price = db.Column(db.Float, nullable=True)
	sales_price = db.Column(db.Float, nullable=True)
	rmb = db.Column(db.Integer, nullable=True)
	supplier = db.Column(db.String(15), nullable=True)
	created_at = db.Column(db.Date, default=datetime.datetime.utcnow)
	
	def __repr__(self):
		return f"<Order {self.order_number}:{self.order_position}>"

class Settings(db.Model):
	__tablename__ = "settings"
	key = db.Column(db.String(50), primary_key=True)
	value = db.Column(db.Integer)
	
	def __repr__(self):
		return f"<Settings for {self.key}>"
