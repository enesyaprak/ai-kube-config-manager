import os
import json
import argparse
from flask import Flask, jsonify, abort

app = Flask(__name__)

@app.route('/<app_name>', methods=['GET'])
def get_schema(app_name):
    # Dışarıdan argüman olarak gelen dizini kullan
    schema_path = os.path.join(app.config['SCHEMA_DIR'], f"{app_name}.schema.json")

    if not os.path.exists(schema_path):
        return jsonify({"error": "Schema not found"}), 404

    try:
        with open(schema_path, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5001)
    parser.add_argument('--schema-dir', type=str, default="/data/schemas")
    args = parser.parse_args()

    app.config['SCHEMA_DIR'] = args.schema_dir
    app.run(host='0.0.0.0', port=args.port)