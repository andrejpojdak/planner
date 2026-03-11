from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app(config=None):
	app = Flask(__name__, instance_relative_config=False)
	app.config.from_mapping(
		SECRET_KEY=os.environ.get("SECRET_KEY", "devkey"),
		SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URI", "sqlite:///materials.db"),
		SQLALCHEMY_TRACK_MODIFICATIONS=False,
		UPLOAD_FOLDER=os.path.join(app.instance_path, "uploads")
	)

	try:
		os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
	except OSError:
		pass

	db.init_app(app)

	# import models so they are registered with SQLAlchemy
	from . import models

	# register blueprints
	from .materials.views import bp as materials_bp
	app.register_blueprint(materials_bp, url_prefix="/materials")
	
	from .deliveries.views import bp as deliveries_bp
	app.register_blueprint(deliveries_bp, url_prefix="/deliveries")
	
	from .orders.views import bp as orders_bp
	app.register_blueprint(orders_bp, url_prefix="/orders")
	
	from .settings.views import bp as settings_bp
	app.register_blueprint(settings_bp, url_prefix="/settings")
	
	from .planning.views import bp as planning_bp
	app.register_blueprint(planning_bp, url_prefix="/planning")
		
	# create DB tables for quick start
	with app.app_context():
		db.create_all()

		from .models import Settings
		
		data = {
			"SEA": 50,
			"RAIL": 25,
			"AIR": 12
		}

		for k, v in data.items():
			setting = Settings.query.get(k)
			if setting:
				setting.value = v
			else:
				db.session.add(Settings(key=k, value=v))

		db.session.commit()

	return app
