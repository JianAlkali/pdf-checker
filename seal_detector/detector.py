# seal_detector/detector.py
import json
from pathlib import Path
from dashscope import MultiModalConversation
from common.config import Config
from common.logger import setup_logger
from common.path_validator import is_safe_path
from common.pdf_to_images import pdf_to_images

logger = setup_logger("SealDetector")

SEAL_SCHEMA = {
    "type": "object",
    "properties": {
        "has_seal": {"type": "boolean"},
        "is_red": {"type": "boolean"},
        "is_complete": {"type": "boolean"},
        "is_normal_size": {"type": "boolean"},
        "seal_text": {"type": "string"}
    },
    "required": ["has_seal"]
}


def detect_seal_compliance(pdf_path: str) -> dict:
    """对 PDF 文档逐页检测印章合规性，并汇总结果。"""
    Config.init_dirs()
    pdf_p = Path(pdf_path).resolve()

    if not is_safe_path(Config.ALLOWED_BASE_DIR, str(pdf_p)):
        raise ValueError("路径不安全")
    if not pdf_p.exists():
        raise FileNotFoundError(f"文件不存在: {pdf_path}")

    image_paths = pdf_to_images(pdf_p, Config.TEMP_DIR)
    all_pages = []

    for img in image_paths:
        page_num = int(img.stem.split('_')[-1])
        try:
            result = _analyze_seal_page(img)
            all_pages.append({"page": page_num, "result": result})
        except Exception as e:
            logger.error(f"第 {page_num} 页盖章分析失败: {e}")
            all_pages.append({
                "page": page_num,
                "result": {
                    "has_seal": False,
                    "is_red": True,
                    "is_complete": True,
                    "is_normal_size": True,
                    "seal_text": ""
                }
            })

    # 保存原始结果
    pdf_stem = Path(pdf_path).stem
    raw_path = Config.OUTPUT_DIR / f"{pdf_stem}_seal_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)
    logger.info(f"盖章原始结果已保存至: {raw_path}")

    # 合并逻辑：只要有一处合格印章即认为“有章”
    has_valid_seal = False
    errors = []
    warnings = []

    for item in all_pages:
        res = item["result"]
        page = item["page"]

        if not res["has_seal"]:
            continue

        has_valid_seal = True

        if not res["is_red"]:
            errors.append(f"【红章】第 {page} 页印章非红色")
        if not res["is_complete"]:
            warnings.append(f"【完整性】第 {page} 页印章不完整（可能被裁剪）")
        if not res["is_normal_size"]:
            warnings.append(f"【尺寸】第 {page} 页印章尺寸异常（过小）")
        if res["seal_text"] == "（印章模糊）":
            warnings.append(f"【清晰度】第 {page} 页印章文字无法辨认")

    if not has_valid_seal:
        errors.insert(0, "【缺失】全文档未检测到任何印章")

    return {
        "errors": errors,
        "warnings": warnings
    }


def _analyze_seal_page(image_path: Path) -> dict:
    """调用多模态大模型分析单页图像中的印章属性。"""
    from .prompt import SEAL_PROMPT

    messages = [{
        "role": "user",
        "content": [
            {"image": str(image_path)},
            {"text": SEAL_PROMPT}
        ]
    }]

    response = MultiModalConversation.call(
        model=Config.MODEL,
        messages=messages,
        response_format={"type": "json_object", "schema": SEAL_SCHEMA},
        temperature=0.01
    )

    if response.status_code != 200:
        raise RuntimeError(f"API 错误: {response.code}")

    raw_text = response.output.choices[0].message.content[0]["text"]
    try:
        data = json.loads(raw_text)
        for key in ["has_seal", "is_red", "is_complete", "is_normal_size"]:
            if key not in data:
                data[key] = True
        if "seal_text" not in data:
            data["seal_text"] = ""
        return data
    except json.JSONDecodeError:
        logger.warning(f"非JSON响应: {raw_text[:100]}...")
        return {
            "has_seal": False,
            "is_red": True,
            "is_complete": True,
            "is_normal_size": True,
            "seal_text": ""
        }