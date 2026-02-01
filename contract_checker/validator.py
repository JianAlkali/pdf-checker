# contract_checker/validator.py
import json
from datetime import datetime
from pathlib import Path
from common.config import Config
from common.logger import setup_logger

logger = setup_logger("ContractValidator")


def validate_contract(page_results: list, pdf_path: str) -> dict:
    """合并多页提取结果，并根据业务规则校验合同合规性。"""
    merged = merge_contract_fields(page_results)

    # 保存原始 JSON
    pdf_stem = Path(pdf_path).stem
    raw_output_path = Config.OUTPUT_DIR / f"{pdf_stem}_raw.json"
    with open(raw_output_path, "w", encoding="utf-8") as f:
        json.dump({
            "pdf_path": str(pdf_path),
            "page_results": page_results,
            "merged_fields": merged
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"原始提取结果已保存至: {raw_output_path}")

    errors = []
    warnings = []

    # 基础字段存在性检查
    if not merged["contract_name"].strip():
        errors.append("【1】未识别到合同名称")
    if not merged["contract_id"].strip():
        errors.append("【2】未识别到合同编号")
    if not merged["party_a_name"].strip() or not merged["party_b_name"].strip():
        errors.append("【3】甲乙方名称不完整")
    if not merged["settlement_method"].strip():
        errors.append("【6】未识别结算方式")
    if not (merged["bank_account_name"].strip() and merged["bank_name"].strip() and merged["bank_account_number"].strip()):
        errors.append("【7】收款账户信息（户名/开户行/账号）不完整")
    if not merged["payment_terms"].strip():
        errors.append("【8】未识别付款条件")
    if not merged["goods_name"].strip():
        errors.append("【9】未识别货物名称")
    if not merged["quantity"].strip() or not merged["total_amount_incl_tax"].strip():
        errors.append("【10】数量或金额信息不完整")

    # 生效期间检查
    start_str, end_str = merged["effective_start"], merged["effective_end"]
    if not start_str or not end_str:
        errors.append("【4】合同生效期间缺失")
    else:
        try:
            start = datetime.strptime(start_str, "%Y-%m-%d")
            end = datetime.strptime(end_str, "%Y-%m-%d")
            today = datetime.today()
            if today > end:
                errors.append("【4】合同已过期")
            elif today < start:
                warnings.append("【4】合同尚未生效")
        except ValueError:
            errors.append("【4】合同生效日期格式错误（应为 YYYY-MM-DD）")

    # 盖章检查
    for party, seal in [("甲方", merged["seal_party_a"]), ("乙方", merged["seal_party_b"])]:
        if not seal.strip():
            errors.append(f"【11】{party}盖章缺失")
        elif "合同专用章" not in seal and "公章" not in seal:
            errors.append(f"【11】{party}盖章类型不合规（需含‘合同专用章’或‘公章’）")

    # 签字检查
    for party, sign in [("甲方", merged["sign_party_a"]), ("乙方", merged["sign_party_b"])]:
        s = sign.strip()
        if not s:
            errors.append(f"【12】{party}签字缺失")
        elif s == "（签名模糊）":
            warnings.append(f"【12】{party}签字存在但无法辨认")

    # 关联主体检查
    if not merged["related_entities"].strip():
        warnings.append("【13】未识别合同关联主体")

    return {
        "errors": errors,
        "warnings": warnings
    }


def merge_contract_fields(pages: list) -> dict:
    """从多页结果中合并非空字段，优先取首次出现的非空值。"""
    fields = [
        "contract_name", "contract_id",
        "party_a_name", "party_b_name",
        "effective_start", "effective_end",
        "seal_party_a", "seal_party_b",
        "sign_party_a", "sign_party_b",
        "settlement_method",
        "bank_account_name", "bank_name", "bank_account_number",
        "payment_terms",
        "goods_name", "quantity", "total_amount_incl_tax",
        "related_entities"
    ]
    merged = {f: "" for f in fields}
    for page in pages:
        res = page.get("result", {})
        if not isinstance(res, dict):
            continue
        for f in fields:
            if not merged[f] and f in res and res[f]:
                merged[f] = str(res[f]).strip()
    return merged