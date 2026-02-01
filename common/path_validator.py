# common/path_validator.py
from pathlib import Path
from .logger import setup_logger

logger = setup_logger("PathValidator")


def is_safe_path(base_dir: Path, user_path: str) -> bool:
    """检查用户提供的路径是否在允许的基目录内，防止路径穿越。"""
    try:
        resolved = Path(user_path).resolve()
        base_resolved = base_dir.resolve()
        return str(resolved).startswith(str(base_resolved))
    except Exception as e:
        logger.error(f"路径解析失败: {e}")
        return False