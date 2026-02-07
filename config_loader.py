import yaml
import os

def load_config():
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config

# Usage example
if __name__ == "__main__":
    config = load_config()
    print(f"Project: {config['project']['name']}")
    print(f"Database: {config['mongodb']['database']}")
    print(f"Embedding Model: {config['nlp']['embedding_model']}")