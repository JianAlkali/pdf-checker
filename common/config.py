# common/config.py
import os
from pathlib import Path

class Config:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    if not DASHSCOPE_API_KEY:
        raise EnvironmentError("❌ 环境变量 DASHSCOPE_API_KEY 未设置！")

    MODEL = "qwen-vl-max"
    TEMP_DIR = Path("temp_audit_images")
    OUTPUT_DIR = Path("output")
    ALLOWED_BASE_DIR = Path.cwd()

    @classmethod
    def init_dirs(cls):
        cls.TEMP_DIR.mkdir(exist_ok=True)
        cls.OUTPUT_DIR.mkdir(exist_ok=True)