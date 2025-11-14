import yaml
def load_config():
    with open("backend/config/config.yaml", "r") as f:
        return yaml.safe_load(f)