# proj_audit/main.py
import sys
import os
import argparse
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from common.logger import setup_logger
from seal_detector import detect_seal_compliance
from contract_checker import check_contract_compliance
from contract_checker.validator import validate_contract, export_to_excel
from seal_detector.exporter import export_seal_to_excel
from common.config import Config

logger = setup_logger("AuditMain")

USAGE_FILE = Path(__file__).parent / "usage_count.json"


def load_usage():
    if USAGE_FILE.exists():
        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"seal": 0, "contract": 0}


def save_usage(data):
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"无法保存使用统计: {e}")


def increment_and_save(feature: str):
    usage = load_usage()
    usage[feature] = usage.get(feature, 0) + 1
    save_usage(usage)


def show_usage():
    usage = load_usage()
    print("功能调用统计:")
    print(f"   盖章识别（--seal）   : {usage['seal']}")
    print(f"   合同审核（--contract）: {usage['contract']}")
    print(f"   总计               : {usage['seal'] + usage['contract']}")


def run_seal(pdf_paths: list):
    total = len(pdf_paths)
    for idx, pdf_path in enumerate(pdf_paths, 1):
        logger.info(f"处理第 {idx}/{total} 个文件: {Path(pdf_path).name}")
        logger.info("正在执行【盖章合规性核验】（功能2）...")
        try:
            report = detect_seal_compliance(pdf_path)
            errors = report.get("errors", [])
            warnings = report.get("warnings", [])

            if errors:
                logger.error("❌ 盖章核验不通过，发现以下严重问题：")
                for err in errors:
                    logger.error(f"   • {err}")
            if warnings:
                logger.warning("⚠️ 盖章核验发现以下注意项：")
                for warn in warnings:
                    logger.warning(f"   • {warn}")
            if not errors and not warnings:
                logger.info("✅ 盖章合规性核验通过：所有签章符合要求.")

            # 导出 Excel：与 _seal_raw.json 同目录同名（仅扩展名不同）
            pdf_stem = Path(pdf_path).stem
            excel_path = Config.OUTPUT_DIR / f"{pdf_stem}_seal.xlsx"
            export_seal_to_excel(report, str(excel_path))
            logger.info(f"盖章结果已导出至: {excel_path}")

            increment_and_save("seal")
        except Exception as e:
            logger.error(f"盖章识别失败 ({pdf_path}): {e}")
            continue


def run_contract(pdf_paths: list):
    total = len(pdf_paths)
    for idx, pdf_path in enumerate(pdf_paths, 1):
        logger.info(f"处理第 {idx}/{total} 个文件: {Path(pdf_path).name}")
        logger.info("正在执行【合同合规性核验】（功能6）...")
        try:
            page_results = check_contract_compliance(pdf_path)
            report = validate_contract(page_results, pdf_path)
            errors = report.get("errors", [])
            warnings = report.get("warnings", [])

            if errors:
                logger.error("❌ 合同审核不通过，发现以下严重问题：")
                for err in errors:
                    logger.error(f"   • {err}")
            if warnings:
                logger.warning("⚠️ 合同审核发现以下注意项：")
                for warn in warnings:
                    logger.warning(f"   • {warn}")
            if not errors and not warnings:
                logger.info("✅ 合同合规性核验通过：所有审核项符合要求.")

            # 导出 Excel：与 _raw.json 同目录同名（仅扩展名不同）
            pdf_stem = Path(pdf_path).stem
            excel_path = Config.OUTPUT_DIR / f"{pdf_stem}.xlsx"
            export_to_excel(report, str(excel_path))
            logger.info(f"合同结果已导出至: {excel_path}")

            increment_and_save("contract")
        except Exception as e:
            logger.error(f"合同审核失败 ({pdf_path}): {e}")
            continue


def main():
    parser = argparse.ArgumentParser(
        description="基建档案智能审核工具 - 功能2（盖章识别）、功能6（合同审核）",
        epilog="示例:\n"
               "  python main.py doc1.pdf doc2.pdf              # 同时运行功能2+6\n"
               "  python main.py --seal doc1.pdf doc2.pdf       # 仅执行盖章识别\n"
               "  python main.py --contract doc1.pdf            # 仅执行合同审核\n"
               "  python main.py --count                        # 查看功能调用统计",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("pdf_paths", nargs="*", help="待审核的 PDF 文件路径列表（可选，若使用 --count 则不需要")       
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--seal", action="store_true", help="仅执行盖章识别（功能2）")
    group.add_argument("--contract", action="store_true", help="仅执行合同核验（功能6）")
    group.add_argument("--count", action="store_true", help="显示功能调用统计")

    args = parser.parse_args()

    if args.count:
        show_usage()
        return

    if not args.pdf_paths:
        parser.error("the following arguments are required: pdf_paths (unless using --count)")

    if not os.getenv("DASHSCOPE_API_KEY"):
        logger.error("请设置环境变量 DASHSCOPE_API_KEY")
        sys.exit(1)

    resolved_paths = []
    for p in args.pdf_paths:
        pdf_path = Path(p).resolve()
        if not pdf_path.exists():
            logger.error(f"文件不存在: {pdf_path}")
            sys.exit(1)
        if pdf_path.suffix.lower() != ".pdf":
            logger.error(f"仅支持 .pdf 文件: {pdf_path}")
            sys.exit(1)
        resolved_paths.append(str(pdf_path))

    if args.seal:
        run_seal(resolved_paths)
    elif args.contract:
        run_contract(resolved_paths)
    else:
        # 默认：两者都跑
        run_seal(resolved_paths)
        print()
        run_contract(resolved_paths)


if __name__ == "__main__":
    main()