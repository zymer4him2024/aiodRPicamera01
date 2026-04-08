import json

def load_config(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(config_path, config):
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
