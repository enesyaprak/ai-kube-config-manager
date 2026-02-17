from flask import Flask, request, jsonify
import requests
import json
import os
import re
import sys

app = Flask(__name__)

# Service URLs
SCHEMA_SERVICE_URL = os.getenv("SCHEMA_SERVICE_URL", "http://schema-server:5001")
VALUES_SERVICE_URL = os.getenv("VALUES_SERVICE_URL", "http://values-server:5002")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

# Application name mapping
APP_NAME_KEYWORDS = {
    "tournament": "tournament",
    "matchmaking": "matchmaking",
    "chat": "chat"
}

def log(message):
    """Print to stdout and flush immediately for Docker logs"""
    print(message, file=sys.stdout, flush=True)

def extract_app_name(user_input):
    """
    Use LLM to identify the application name from user input.
    """
    # Simple keyword matching first (most reliable)
    for keyword, app in APP_NAME_KEYWORDS.items():
        if keyword in user_input.lower():
            return app

    # Fallback to LLM if no keyword match
    prompt = f"""You are a configuration assistant. The user wants to modify a configuration.
Available applications are: tournament, matchmaking, chat

User request: "{user_input}"

Respond with ONLY the application name (tournament, matchmaking, or chat). 
No explanation, no punctuation, just the application name in lowercase."""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "temperature": 0.1
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            app_name = result.get("response", "").strip().lower()
            app_name = re.sub(r'[^a-z]', '', app_name)

            if app_name in APP_NAME_KEYWORDS.values():
                return app_name

        return None

    except Exception as e:
        log(f"Error calling LLM for app name extraction: {e}")
        return None


def get_schema(app_name):
    """Fetch JSON Schema from schema service."""
    try:
        response = requests.get(f"{SCHEMA_SERVICE_URL}/{app_name}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        log(f"Error fetching schema: {e}")
        return None


def get_values(app_name):
    """Fetch current values from values service."""
    try:
        response = requests.get(f"{VALUES_SERVICE_URL}/{app_name}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        log(f"Error fetching values: {e}")
        return None


def repair_json(text):
    """
    Attempt to repair common JSON issues.
    """
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    # Fix single quotes to double quotes (common LLM mistake)
    # Be careful not to replace quotes inside strings
    text = re.sub(r"'([^']*)':", r'"\1":', text)

    # Remove any BOM or special characters at the start
    text = text.lstrip('\ufeff\ufffe')

    return text


def extract_json_from_text(text):
    """Extract JSON object from text that might contain markdown or explanations."""
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Find JSON object boundaries
    start_idx = text.find('{')
    end_idx = text.rfind('}')

    if start_idx != -1 and end_idx != -1:
        json_text = text[start_idx:end_idx+1]
        # Try to repair common issues
        json_text = repair_json(json_text)
        return json_text

    return repair_json(text)


def apply_changes_with_llm_jk(user_input, schema, current_values):
    """Use LLM to apply the requested changes to the current values."""

    # Analyze current values to understand units
    sample_memory_value = None
    try:
        if 'workloads' in current_values:
            for workload_type in current_values['workloads'].values():
                for workload in workload_type.values():
                    if 'containers' in workload:
                        for container in workload['containers'].values():
                            if 'resources' in container and 'memory' in container['resources']:
                                mem = container['resources']['memory']
                                if 'limitMiB' in mem:
                                    sample_memory_value = mem['limitMiB']
                                    break
    except:
        pass

    use_mib_directly = sample_memory_value is not None and sample_memory_value < 100000

    # Build a simple, focused prompt
    prompt = f"""You are a JSON editor. Your task is to modify a JSON configuration.

User request: "{user_input}"

Current configuration (JSON):
{json.dumps(current_values, indent=2)}

Instructions:
- If request mentions "memory": modify resources -> memory -> limitMiB and requestMiB fields (use value like 1024 for 1024mb)
- If request mentions "cpu": modify resources -> cpu fields
- If request mentions "env" or "environment": modify the envs array
- Otherwise: keep everything exactly the same
- IMPORTANT: Only change what the user specifically requests
- Do NOT add new fields or env variables unless explicitly requested
- Output valid JSON only, no explanations

Output:"""

    try:
        log(f"Request: {user_input}")

        # Try multiple models in order of preference
        models_to_try = [
            ("qwen2.5-coder:1.5b", "Small, fast coder model"),
            ("llama3.2:1b", "Small llama model"),
            ("llama3.2", "Standard llama 3.2"),
            ("llama3", "Standard llama 3")
        ]

        for model_name, description in models_to_try:
            try:
                log(f"Trying {model_name} ({description})...")

                response = requests.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.0,
                        "format": "json",  # Request JSON format
                        "num_predict": 4096
                    },
                    timeout=180
                )

                if response.status_code == 200:
                    result = response.json()
                    llm_response = result.get("response", "").strip()

                    log(f"Got response ({len(llm_response)} chars)")

                    # Extract and clean JSON
                    json_str = extract_json_from_text(llm_response)

                    # Try to parse
                    try:
                        modified_values = json.loads(json_str)
                        log(f"✓ Success with {model_name}")
                        return modified_values
                    except json.JSONDecodeError as e:
                        log(f"JSON parse failed with {model_name}: {e}")
                        log(f"Problematic JSON around char {e.pos}: ...{json_str[max(0,e.pos-50):e.pos+50]}...")
                        continue

            except requests.exceptions.Timeout:
                log(f"{model_name} timed out")
                continue
            except requests.exceptions.ConnectionError as e:
                if "Name or service not known" in str(e) or "404" in str(e):
                    log(f"{model_name} not available, trying next...")
                    continue
                raise
            except Exception as e:
                log(f"Error with {model_name}: {e}")
                continue

        log("ERROR: All models failed")
        return None

    except Exception as e:
        log(f"Fatal error: {e}")
        import traceback
        log(traceback.format_exc())
        return None


@app.route('/message', methods=['POST'])
def handle_message():
    """Main endpoint for processing user configuration requests."""
    try:
        data = request.get_json()

        if not data or 'input' not in data:
            return jsonify({"error": "Missing 'input' field"}), 400

        user_input = data['input']
        log(f"\n{'='*60}")
        log(f"REQUEST: {user_input}")
        log(f"{'='*60}")

        app_name = extract_app_name(user_input)
        if not app_name:
            return jsonify({"error": "Could not identify application"}), 400

        log(f"✓ App: {app_name}")

        schema = get_schema(app_name)
        if not schema:
            return jsonify({"error": f"Schema not found: {app_name}"}), 404

        current_values = get_values(app_name)
        if not current_values:
            return jsonify({"error": f"Values not found: {app_name}"}), 404

        log(f"✓ Data loaded")

        modified_values = apply_changes_with_llm_jk(user_input, schema, current_values)
        if not modified_values:
            return jsonify({"error": "Failed to apply changes. Try installing qwen2.5-coder:1.5b model."}), 500

        log(f"✓ Success\n{'='*60}\n")

        return jsonify(modified_values), 200

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        log(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    log("\n" + "="*60)
    log("Bot Server Starting")
    log("="*60)
    log(f"Schema: {SCHEMA_SERVICE_URL}")
    log(f"Values: {VALUES_SERVICE_URL}")
    log(f"Ollama: {OLLAMA_URL}")
    log("="*60 + "\n")
    app.run(host='0.0.0.0', port=5003, debug=True)