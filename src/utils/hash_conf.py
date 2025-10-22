import json
import hashlib

def generate_config_hash(config_data: dict) -> str:
    canonical_string = json.dumps(config_data, sort_keys=True, indent=None)

    config_hash = hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()

    return config_hash
