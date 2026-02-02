# seal_detector/exporter.py
import pandas as pd
from pathlib import Path
from common.logger import setup_logger

logger = setup_logger("SealExporter")


def export_seal_to_excel(report: dict, output_path: str):
    """
    导出完整的盖章审核报告到 Excel，包含：
    - 原始页数据（每页是否需章、印章列表）
    - 详细问题（ERROR/WARNING，含页码）
    - 全局摘要（是否缺章、冗余等）
    """
    output_p = Path(output_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)

    # === Sheet 1: 原始印章数据 ===
    raw_rows = []
    for page_info in report["raw_data"]:
        page = page_info["page"]
        res = page_info["result"]
        requires = res.get("requires_seal", False)
        seals = res.get("seals", [])
        if not seals:
            raw_rows.append({
                "Page": page,
                "RequiresSeal": requires,
                "SealIndex": "",
                "IsRed": "",
                "IsComplete": "",
                "IsNormalSize": "",
                "SealText": ""
            })
        else:
            for i, seal in enumerate(seals, 1):
                raw_rows.append({
                    "Page": page,
                    "RequiresSeal": requires,
                    "SealIndex": i,
                    "IsRed": seal.get("is_red", ""),
                    "IsComplete": seal.get("is_complete", ""),
                    "IsNormalSize": seal.get("is_normal_size", ""),
                    "SealText": seal.get("seal_text", "")
                })

    df_raw = pd.DataFrame(raw_rows)

    # === Sheet 2: 问题详情（含页码）===
    issues = report.get("issues_detail", [])
    df_issues = pd.DataFrame(issues) if issues else pd.DataFrame([{"Page": "", "Type": "INFO", "Message": "无问题"}])

    # === Sheet 3: 全局摘要 ===
    summary = report["summary"]
    summary_rows = [
        {"Key": "总页数", "Value": summary["total_pages"]},
        {"Key": "需盖章页面", "Value": ", ".join(map(str, summary["pages_requiring_seal"])) or "无"},
        {"Key": "是否检测到有效印章", "Value": "是" if summary["any_valid_seal_detected"] else "否"},
        {"Key": "全局错误 (ERROR)", "Value": "; ".join(summary["global_errors"]) or "无"},
        {"Key": "全局警告 (WARNING)", "Value": "; ".join(summary["global_warnings"]) or "无"},
    ]
    df_summary = pd.DataFrame(summary_rows)

    # === 写入多 sheet ===
    with pd.ExcelWriter(output_p, engine='openpyxl') as writer:
        df_raw.to_excel(writer, sheet_name="原始印章数据", index=False)
        df_issues.to_excel(writer, sheet_name="问题详情", index=False)
        df_summary.to_excel(writer, sheet_name="全局摘要", index=False)

    logger.info(f"完整盖章审核报告已导出至: {output_path}")