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
        "requires_seal": {"type": "boolean"},
        "seals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "is_red": {"type": "boolean"},
                    "is_complete": {"type": "boolean"},
                    "is_normal_size": {"type": "boolean"},
                    "seal_text": {"type": "string"}
                },
                "required": ["is_red", "is_complete", "is_normal_size", "seal_text"]
            }
        }
    },
    "required": ["requires_seal", "seals"]
}


def detect_seal_compliance(pdf_path: str) -> dict:
    """对 PDF 文档逐页检测印章，并返回完整报告（含原始、汇总、判定）。"""
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
                    "requires_seal": False,
                    "seals": []
                }
            })

    # 保存原始结果
    pdf_stem = Path(pdf_path).stem
    raw_path = Config.OUTPUT_DIR / f"{pdf_stem}_seal_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)
    logger.info(f"盖章原始结果已保存至: {raw_path}")

    # === 全局分析 ===
    errors = []
    warnings = []
    any_valid_seal = False
    pages_requiring_seal = []

    # 收集每页问题（用于 Excel）
    page_issues = []

    for item in all_pages:
        page = item["page"]
        res = item["result"]
        requires = res.get("requires_seal", False)
        seals = res.get("seals", [])

        if requires:
            pages_requiring_seal.append(page)

        if seals:
            any_valid_seal = True

        # 分析每页印章问题
        for i, seal in enumerate(seals, 1):
            prefix = f"第 {page} 页印章#{i}"
            if not seal.get("is_red", True):
                msg = f"【红章】{prefix} 非红色"
                errors.append(msg)
                page_issues.append({"Page": page, "Type": "ERROR", "Message": msg})
            if not seal.get("is_complete", True):
                msg = f"【完整性】{prefix} 不完整（被裁剪）"
                warnings.append(msg)
                page_issues.append({"Page": page, "Type": "WARNING", "Message": msg})
            if not seal.get("is_normal_size", True):
                msg = f"【尺寸】{prefix} 尺寸异常（过小）"
                warnings.append(msg)
                page_issues.append({"Page": page, "Type": "WARNING", "Message": msg})
            text = seal.get("seal_text", "").strip()
            if text == "（印章模糊）":
                msg = f"【清晰度】{prefix} 文字无法辨认"
                warnings.append(msg)
                page_issues.append({"Page": page, "Type": "WARNING", "Message": msg})

    # 全局规则
    global_issues = []
    if pages_requiring_seal and not any_valid_seal:
        msg = f"【缺失】文档中存在需盖章页面（如第 {pages_requiring_seal[0]} 页），但全文未检测到有效印章"
        errors.insert(0, msg)
        global_issues.append({"Type": "ERROR", "Message": msg})
    elif not pages_requiring_seal and any_valid_seal:
        msg = "【冗余】文档无需盖章，但检测到印章"
        warnings.append(msg)
        global_issues.append({"Type": "WARNING", "Message": msg})

    # 构建 summary 供 Excel 使用
    summary = {
        "total_pages": len(all_pages),
        "pages_requiring_seal": pages_requiring_seal,
        "any_valid_seal_detected": any_valid_seal,
        "global_errors": [item["Message"] for item in global_issues if item["Type"] == "ERROR"],
        "global_warnings": [item["Message"] for item in global_issues if item["Type"] == "WARNING"]
    }

    return {
        "errors": errors,
        "warnings": warnings,
        "raw_data": all_pages,
        "summary": summary,
        "issues_detail": page_issues + global_issues  # 所有 ERROR/WARNING 条目（含页码）
    }


def _analyze_seal_page(image_path: Path) -> dict:
    """调用多模态大模型分析单页图像中的印章属性（支持多章）。"""
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
        if "requires_seal" not in data:
            data["requires_seal"] = False
        if "seals" not in data or not isinstance(data["seals"], list):
            data["seals"] = []
        for seal in data["seals"]:
            for key in ["is_red", "is_complete", "is_normal_size"]:
                if key not in seal:
                    seal[key] = True
            if "seal_text" not in seal:
                seal["seal_text"] = ""
        return data
    except json.JSONDecodeError:
        logger.warning(f"非JSON响应: {raw_text[:100]}...")
        return {"requires_seal": False, "seals": []}