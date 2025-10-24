import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from core.utils.monitor_system import start_monitor
from core.integrations.epicor.invoice_creator import create_invoice_in_epicor

app = Flask(__name__)
CORS(app)


@app.route('/health')
def health():
    return jsonify({"status": "ok"})


@app.route('/api/email/<path:email_id>')
def get_email_data(email_id):
    file_path = os.path.join('emails_data', f"{email_id}.json")
    
    if not os.path.exists(file_path):
        id_mapping_path = os.path.join('emails_data', 'id_mapping.json')
        if os.path.exists(id_mapping_path):
            with open(id_mapping_path, 'r', encoding='utf-8') as f:
                id_mapping = json.load(f)
                
                actual_id = id_mapping.get(email_id)
                if not actual_id:
                    actual_id = id_mapping.get(f"<{email_id}>")
                
                if actual_id:
                    file_path = os.path.join('emails_data', f"{actual_id}.json")
    
    if not os.path.exists(file_path):
        return jsonify({"error": "Email not processed yet"}), 404
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return jsonify(data)


@app.route('/taskpane')
def taskpane():
    return render_template('taskpane.html')


@app.route('/commands')
def commands():
    return render_template('commands.html')


@app.route('/api/invoice/import', methods=['POST'])
def import_invoice():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        required_fields = ['vendor_id', 'invoice_num', 'invoice_date', 'invoice_total']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400
        
        invoice_data = {
            'company': data.get('company', 'SAINC'),
            'vendor_id': data.get('vendor_id'),
            'invoice_num': data.get('invoice_num'),
            'invoice_date': data.get('invoice_date'),
            'invoice_total': data.get('invoice_total'),
            'line_items': data.get('line_items', [])
        }
        
        result = create_invoice_in_epicor(invoice_data)
        
        if result.get('success'):
            return jsonify({
                "success": True,
                "epicor_url": result.get('epicor_url'),
                "invoice_num": result.get('invoice_num'),
                "vendor_num": result.get('vendor_num')
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error occurred')
            }), 400
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    start_monitor()
    
    cert_file = os.path.join(os.path.dirname(__file__), 'localhost.crt')
    key_file = os.path.join(os.path.dirname(__file__), 'localhost.key')
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("Starting Flask server on https://localhost:5000")
        app.run(debug=True, port=5000, use_reloader=False, ssl_context=(cert_file, key_file))
    else:
        print("WARNING: SSL certificate not found. Run 'python dev/generate_cert.py' first.")
        print("Starting Flask server on http://localhost:5000")
        app.run(debug=True, port=5000, use_reloader=False)

