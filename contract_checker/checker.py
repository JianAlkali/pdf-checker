# contract_checker/checker.py
import json
from pathlib import Path
from dashscope import MultiModalConversation
from common.config import Config
from common.logger import setup_logger
from common.path_validator import is_safe_path
from common.pdf_to_images import pdf_to_images

logger = setup_logger("ContractChecker")

# 字段命名严格对应13项审核需求
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "contract_name": {"type": "string"},
        "contract_id": {"type": "string"},
        "party_a_name": {"type": "string"},
        "party_b_name": {"type": "string"},
        "effective_start": {"type": "string"},
        "effective_end": {"type": "string"},
        "seal_party_a": {"type": "string"},
        "seal_party_b": {"type": "string"},
        "sign_party_a": {"type": "string"},
        "sign_party_b": {"type": "string"},
        "settlement_method": {"type": "string"},
        "bank_account_name": {"type": "string"},
        "bank_name": {"type": "string"},
        "bank_account_number": {"type": "string"},
        "payment_terms": {"type": "string"},
        "goods_name": {"type": "string"},
        "quantity": {"type": "string"},
        "total_amount_incl_tax": {"type": "string"},
        "related_entities": {"type": "string"}
    },
    "required": []
}


def check_contract_compliance(pdf_path: str):
    """对 PDF 合同逐页调用大模型提取结构化字段。"""
    Config.init_dirs()
    pdf_p = Path(pdf_path).resolve()

    if not is_safe_path(Config.ALLOWED_BASE_DIR, str(pdf_p)):
        raise ValueError("路径不安全")
    if not pdf_p.exists():
        raise FileNotFoundError(f"文件不存在: {pdf_path}")

    image_paths = pdf_to_images(pdf_p, Config.TEMP_DIR)
    results = []

    for img in image_paths:
        page_num = int(img.stem.split('_')[-1])
        try:
            res = _analyze_page(img)
            if not isinstance(res, dict):
                res = {}
            results.append({"page": page_num, "result": res})
        except Exception as e:
            logger.error(f"第 {page_num} 页合同分析失败: {e}")
            results.append({"page": page_num, "result": {}})
    return results


def _analyze_page(image_path: Path):
    """调用多模态大模型分析单页合同图像并返回 JSON 结果。"""
    from .prompt import CONTRACT_PROMPT

    messages = [{
        "role": "user",
        "content": [
            {"image": str(image_path)},
            {"text": CONTRACT_PROMPT}
        ]
    }]

    response = MultiModalConversation.call(
        model=Config.MODEL,
        messages=messages,
        response_format={"type": "json_object", "schema": JSON_SCHEMA},
        temperature=0.01
    )

    if response.status_code != 200:
        raise RuntimeError(f"API 错误: {response.code}")

    raw_text = response.output.choices[0].message.content[0]["text"]
    try:
        data = json.loads(raw_text)
        for key in JSON_SCHEMA["properties"]:
            if key not in data or data[key] is None:
                data[key] = ""
        return data
    except json.JSONDecodeError:
        logger.warning(f"非JSON响应: {raw_text[:100]}...")
        return {k: "" for k in JSON_SCHEMA["properties"]}