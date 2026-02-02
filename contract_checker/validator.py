# contract_checker/validator.py
import json
import pandas as pd
from pathlib import Path
from common.config import Config
from common.logger import setup_logger

logger = setup_logger("ContractValidator")


def validate_contract(page_results: list, pdf_path: str) -> dict:
    """
    步骤：
    1. 保存原始每页识别结果（raw_data）
    2. 跨页合并字段，生成完整合同信息（merged_contract）
    3. 基于 merged_contract 进行合规性判断
    4. 返回统一 report 结构
    """
    # === 1. 保存原始数据 ===
    pdf_stem = Path(pdf_path).stem
    raw_path = Config.OUTPUT_DIR / f"{pdf_stem}_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(page_results, f, ensure_ascii=False, indent=2)
    logger.info(f"合同原始结果已保存至: {raw_path}")

    # === 2. 合并字段：取第一个非空值 ===
    merged = {}
    fields = [
        "contract_name", "contract_id", "party_a_name", "party_b_name",
        "effective_start", "effective_end", "seal_party_a", "seal_party_b",
        "sign_party_a", "sign_party_b", "settlement_method", "bank_account_name",
        "bank_name", "bank_account_number", "payment_terms", "goods_name",
        "quantity", "total_amount_incl_tax", "related_entities"
    ]

    for field in fields:
        for page_res in page_results:
            val = page_res["result"].get(field, "").strip()
            if val and val not in ["（签名模糊）", "（印章模糊）"]:
                merged[field] = val
                break
        else:
            merged[field] = ""

    # 特殊处理：签名模糊仍保留提示
    for field in ["sign_party_a", "sign_party_b"]:
        for page_res in page_results:
            val = page_res["result"].get(field, "")
            if val == "（签名模糊）":
                merged[field] = "（签名模糊）"
                break

    # === 3. 合规性判断（基于 merged）===
    errors = []
    warnings = []
    issues_detail = []

    def add_issue(level, msg):
        item = {"Type": level.upper(), "Message": msg}
        issues_detail.append(item)
        (errors if level == "error" else warnings).append(msg)

    # 规则 1: 必须有合同名称
    if not merged["contract_name"]:
        add_issue("error", "【合同名称】未识别到合同名称")

    # 规则 2: 必须有合同编号
    if not merged["contract_id"]:
        add_issue("error", "【合同编号】未识别到合同编号")

    # 规则 3: 甲乙方必须存在
    if not merged["party_a_name"]:
        add_issue("error", "【甲方名称】缺失")
    if not merged["party_b_name"]:
        add_issue("error", "【乙方名称】缺失")

    # 规则 4: 乙方应有印章
    if not merged["seal_party_b"]:
        add_issue("warning", "【乙方印章】未检测到乙方合同专用章")
    elif merged["party_b_name"] not in merged["seal_party_b"]:
        add_issue("warning", "【乙方印章】印章单位与乙方名称不一致")

    # 规则 5: 甲方应有印章（若甲方名称存在）
    if merged["party_a_name"] and not merged["seal_party_a"]:
        add_issue("warning", "【甲方印章】未检测到甲方合同专用章")
    elif merged["seal_party_a"] and merged["party_a_name"] not in merged["seal_party_a"]:
        add_issue("warning", "【甲方印章】印章单位与甲方名称不一致")

    # 规则 6: 签名模糊提示
    if merged.get("sign_party_a") == "（签名模糊）":
        add_issue("warning", "【甲方签名】签名模糊无法辨认")
    if merged.get("sign_party_b") == "（签名模糊）":
        add_issue("warning", "【乙方签名】签名模糊无法辨认")

    # 规则 7: 银行信息完整性（若账户名存在，则账号和开户行应存在）
    if merged["bank_account_name"]:
        if not merged["bank_account_number"]:
            add_issue("warning", "【银行账号】账户名存在但账号缺失")
        if not merged["bank_name"]:
            add_issue("warning", "【开户行】账户名存在但开户行缺失")

    # === 4. 构建 report ===
    summary = {
        "total_pages": len(page_results),
        "merged_contract": merged,
        "total_errors": len(errors),
        "total_warnings": len(warnings)
    }

    return {
        "errors": errors,
        "warnings": warnings,
        "raw_data": page_results,          # 原始每页
        "summary": summary,                # 含 merged_contract
        "issues_detail": issues_detail     # 判定结果（用于 Excel 和控制台）
    }


def export_to_excel(report: dict, output_path: str):
    """导出三部分到 Excel"""
    output_p = Path(output_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)

    # Sheet 1: 原始每页数据
    raw_rows = []
    for page_res in report["raw_data"]:
        page = page_res["page"]
        res = page_res["result"]
        for key, value in res.items():
            raw_rows.append({"Page": page, "Field": key, "Value": str(value) if value is not None else ""})
    df_raw = pd.DataFrame(raw_rows)

    # Sheet 2: 合并后的完整合同
    merged = report["summary"]["merged_contract"]
    merged_rows = [{"Field": k, "Value": str(v) if v is not None else ""} for k, v in merged.items()]
    df_merged = pd.DataFrame(merged_rows)

    # Sheet 3: 判定结果
    issues = report["issues_detail"]
    df_issues = pd.DataFrame(issues) if issues else pd.DataFrame([{"Type": "INFO", "Message": "无问题"}])

    # 写入
    with pd.ExcelWriter(output_p, engine='openpyxl') as writer:
        df_raw.to_excel(writer, sheet_name="原始页数据", index=False)
        df_merged.to_excel(writer, sheet_name="合并后合同信息", index=False)
        df_issues.to_excel(writer, sheet_name="最终判定结果", index=False)

    logger.info(f"完整合同审核报告已导出至: {output_path}")