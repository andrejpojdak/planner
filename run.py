from app import create_app
from flask import Flask, url_for, render_template_string

app = create_app()

@app.route('/')
def index():
	return render_template_string('''
		<a href="{{ url_for('orders.list_orders') }}">Orders</a><br>
		<a href="{{ url_for('deliveries.list_deliveries') }}">Deliveries</a><br>
		<a href="{{ url_for('materials.list_materials') }}">Materials</a><br>
		<a href="{{ url_for('settings.edit_settings') }}">Settings</a><br>
		<a href="{{ url_for('planning.list_plans') }}">Planning</a>
	''')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
