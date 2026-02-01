# common/pdf_to_images.py
from pathlib import Path
from pdf2image import convert_from_path
from .logger import setup_logger

logger = setup_logger("PDFConverter")


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
    """将 PDF 文件转换为 PNG 图像序列，每页一张图。"""
    logger.debug(f"将 PDF 转为图像 (DPI={dpi})...")
    try:
        images = convert_from_path(str(pdf_path), dpi=dpi)
    except Exception as e:
        logger.error(f"PDF 转图像失败: {e}")
        raise RuntimeError(f"PDF 转图像失败: {e}")

    image_paths = []
    for i, img in enumerate(images, start=1):
        img_path = output_dir / f"page_{i:03d}.png"
        img.save(img_path, "PNG")
        image_paths.append(img_path)
    return image_paths