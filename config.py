import os
import yaml


def load_config():
    """config.yml 파일 읽기"""
    config_path = os.path.join(os.path.dirname(__file__), "config.yml")

    if not os.path.exists(config_path):
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config or {}


def get_dooray_config():
    """dooray 설정 가져오기"""
    config = load_config()
    return config.get("dooray", {})
