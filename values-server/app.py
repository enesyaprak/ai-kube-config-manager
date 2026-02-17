import os
import json
import argparse
from flask import Flask, jsonify, abort

app = Flask(__name__)

@app.route('/<app_name>', methods=['GET'])
def get_values(app_name):
    # Dosya isimlendirmesi "appname.value.json" şeklinde
    values_path = os.path.join(app.config['VALUES_DIR'], f"{app_name}.value.json")

    if not os.path.exists(values_path):
        return jsonify({"error": "Values not found"}), 404

    try:
        with open(values_path, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5002)
    parser.add_argument('--values-dir', type=str, default="/data/values")
    args = parser.parse_args()

    app.config['VALUES_DIR'] = args.values_dir
    app.run(host='0.0.0.0', port=args.port)