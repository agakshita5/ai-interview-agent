import yaml
def load_config():
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f)

print(load_config()['introduction_prompt'])
